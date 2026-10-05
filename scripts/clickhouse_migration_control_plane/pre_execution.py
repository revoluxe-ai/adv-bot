"""Сухие команды ``status``, ``validate``, ``plan``, ``inspect`` и отказ apply.

Spec ``clickhouse-migration-lifecycle``: drift сырых байтов, подмена класса
``005``, точка с запятой в строке и числовой префикс вне отпечатка
останавливают ``validate`` и ``apply``. ``status``, ``plan`` и ``inspect``
печатают корпус или чтение порта и не пишут журнал. Эти четыре команды
координатор не открывают. Положительный прогон statement здесь не
начинается: его держит более поздний срез apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    RecordingCoordinatorSession,
)
from scripts.clickhouse_migration_control_plane.ledger import operator_state
from scripts.clickhouse_migration_control_plane.corpus import (
    CorpusAcceptanceError,
    CorpusFingerprint,
    immutable_fingerprint,
    unreviewed_numeric_filenames,
    validate as accept_corpus,
)
from scripts.clickhouse_migration_control_plane.statements import (
    StatementParseError,
    split_statements,
)
from scripts.clickhouse_migration_control_plane.target_port import (
    IsolatedTargetPort,
    LedgerEvent,
    LedgerReadResult,
)


@dataclass(frozen=True)
class PlannedVersion:
    """Одна версия сухого плана. Это не запись журнала и не вызов writer.

    Spec ``clickhouse-migration-lifecycle``: план показывает порядок, класс,
    SHA-256 и statement до причины остановки. Наличие statement не означает,
    что SQL ушёл в порт.
    """

    version_id: str
    privilege_class: str
    sha256: str
    statements: tuple[str, ...]


@dataclass(frozen=True)
class VersionReport:
    """Строка ``status``: идентичность корпуса и состояние из журнала.

    Spec ``clickhouse-migration-lifecycle``: файл и ``IF NOT EXISTS`` эту
    строку не заполняют. ``state`` берётся из факта цели или из её отсутствия.
    """

    version_id: str
    privilege_class: str
    sha256: str
    state: str


@dataclass(frozen=True)
class CommandResult:
    """Итог команды до записи на цель.

    Spec ``clickhouse-migration-lifecycle``: ``success`` ложь означает
    неуспешный результат. ``parsed_statements`` — нарезка цельного
    ``validate``, не список отправленных statement. На отказе нарезка пуста,
    чтобы отказ не выглядел как начатый apply. ``exit_code`` ``0`` допустим
    для цельного ``validate``, честного ``status`` и построенного ``plan``.
    ``satisfies_reconcile`` у осмотра всегда ложь: осмотр не базовая линия.
    """

    success: bool
    code: str
    parsed_statements: tuple[str, ...] = ()
    exit_code: int = 1
    planned_versions: tuple[PlannedVersion, ...] = ()
    version_reports: tuple[VersionReport, ...] = ()
    applied_version_ids: tuple[str, ...] = ()
    satisfies_reconcile: bool = False
    catalog_reads: tuple[str, ...] = ()


def validate(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
) -> CommandResult:
    """Проверить корпус до сети и до координатора.

    Spec ``clickhouse-migration-lifecycle``: сценарии drift, подмены класса
    ``005``, точки с запятой в строке и непроверенного префикса. Цельный
    корпус возвращает код ``ok`` и нарезку без вызова порта.

    Args:
        corpus_dir: каталог, из которого читаются файлы.
        recorded: отпечаток, с которым сравниваются сырые байты и класс.
        port: шов цели. Этот вызов его методы не вызывает.
        coordinator: шов координатора. Этот вызов в него не входит.

    Returns:
        Неуспех с кодом отказа либо ``ok`` без мутации.
    """
    _ = (port, coordinator)
    blocked = gate_corpus(corpus_dir, recorded)
    if blocked is not None:
        return blocked
    return _clear_validate(corpus_dir)


def status(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort | None,
    coordinator: RecordingCoordinatorSession,
) -> CommandResult:
    """Напечатать корпус и, если цель передана, состояние журнала.

    Spec ``clickhouse-migration-lifecycle``, сценарии ``Status without a
    target is not an applied record`` и ``File presence is not applied
    state``. Без порта код ``target_not_attached``. Пустой журнал —
    ``ledger_absent``, а не список файлов и не ``IF NOT EXISTS``. Координатор
    не открывается, ``version_applied`` не пишется. Честный отчёт, включая
    неизвестную историю, имеет код выхода ``0``.

    Args:
        corpus_dir: каталог корпуса. Этот вызов его байты не меняет.
        recorded: отпечаток идентичности. Он не подставляет состояние цели.
        port: шов цели или ``None``, если цель не прикреплена.
        coordinator: шов координатора. Этот вызов в него не входит.

    Returns:
        Отчёт по версиям без мутации.
    """
    _ = (corpus_dir, coordinator)
    if port is None:
        return _status_report(recorded, state="target_not_attached", applied=())
    latest = _latest_by_version(_read_ledger(port).events)
    applied = _applied_ids(recorded, latest)
    if latest == {}:
        return _status_report(recorded, state="ledger_absent", applied=())
    reports = _version_reports(recorded, latest)
    if any(item.state == "drift" for item in reports):
        return CommandResult(
            success=False,
            code="drift",
            exit_code=1,
            version_reports=reports,
            applied_version_ids=applied,
            satisfies_reconcile=False,
        )
    return CommandResult(
        success=True,
        code=_status_code(latest),
        exit_code=0,
        version_reports=reports,
        applied_version_ids=applied,
        satisfies_reconcile=False,
    )


def plan(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort | None,
    coordinator: RecordingCoordinatorSession,
    target_class: str = "isolated",
) -> CommandResult:
    """Показать сухой порядок версий и причину остановки.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Plan is dry``: нет
    цели, неизвестная история, ``005``, drift, ``partial`` и прод-класс.
    SQL не исполняется, журнал не пишется, lock не берётся. Прод-класс не
    открывает порт. Построенный план имеет код выхода ``0``. Drift остаётся
    неуспешным. Цельный корпус без причины остановки не начинает мутацию:
    код ``mutation_not_opened``.

    Args:
        corpus_dir: каталог, из которого читаются файлы плана.
        recorded: отпечаток, с которым сравниваются сырые байты и класс.
        port: шов цели или ``None``, если цель не прикреплена.
        coordinator: шов координатора. Этот вызов в него не входит.
        target_class: класс цели. ``production`` останавливает план до порта.
    """
    _ = coordinator
    planned = _planned_versions(corpus_dir)
    blocked = gate_corpus(corpus_dir, recorded)
    if blocked is not None:
        if blocked.code == "corpus_drift":
            return CommandResult(
                success=False,
                code="corpus_drift",
                planned_versions=planned,
            )
        return blocked
    if target_class == "production":
        return _dry_plan("blocked_production_target", planned)
    if port is None:
        return _dry_plan("target_not_attached", planned)
    events = _read_ledger(port).events
    reason = _plan_stop(recorded, events)
    if reason is None:
        return CommandResult(success=False, code="mutation_not_opened")
    if reason == "drift":
        return CommandResult(
            success=False,
            code="drift",
            exit_code=1,
            planned_versions=planned,
            version_reports=_version_reports(
                recorded,
                _latest_by_version(events),
            ),
        )
    return _dry_plan(reason, planned)


def inspect(
    *,
    port: IsolatedTargetPort | None,
    coordinator: RecordingCoordinatorSession,
) -> CommandResult:
    """Прочитать метаданные цели и не делать из них базовую линию.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Inspect does not
    write and does not baseline``. Без порта сеть и чтение каталога не
    открываются. С портом вызывается только ``inspect_read``. Журнал не
    пишется, lock не берётся, сверка не выполняется.

    Args:
        port: шов цели или ``None``, если цель не прикреплена.
        coordinator: шов координатора. Этот вызов в него не входит.

    Returns:
        Чтение каталогов подстановки либо ``target_not_attached``.
    """
    _ = coordinator
    if port is None:
        return CommandResult(
            success=True,
            code="target_not_attached",
            exit_code=0,
            satisfies_reconcile=False,
        )
    metadata = port.inspect_read()
    return CommandResult(
        success=True,
        code="inspect_read",
        exit_code=0,
        catalog_reads=metadata.catalog_reads,
        satisfies_reconcile=False,
    )


def apply(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
) -> CommandResult:
    """Отказать в apply до ``execute``.

    Spec ``clickhouse-migration-lifecycle``: тот же отказ корпуса, что у
    ``plan``. Расхождение SHA-256 журнала и файла — ``drift``: SQL не
    исполняется и файлы ``001``–``005`` не переписываются. Успешный прогон
    ``001``–``004`` этот срез не начинает и журнал не пишет.
    """
    blocked = gate_corpus(corpus_dir, recorded)
    if blocked is not None:
        return blocked
    _ = coordinator
    latest = _latest_by_version(_read_ledger(port).events)
    if _ledger_drift(recorded, latest):
        return CommandResult(
            success=False,
            code="drift",
            exit_code=1,
            version_reports=_version_reports(recorded, latest),
        )
    return CommandResult(success=False, code="mutation_not_opened")


def gate_corpus(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
) -> CommandResult | None:
    """Найти причину остановки до любого statement.

    Непроверенный числовой префикс сверяется с отпечатком пакета, а не с
    меткой вызывающего: чужой ``006`` нельзя пометить проверенным.
    Подмена класса и чужой SHA-256 — один код ``corpus_drift``.
    Порт и координатор эта функция не принимает и не открывает.

    Args:
        corpus_dir: каталог, из которого читаются файлы корпуса.
        recorded: отпечаток, с которым сравниваются сырые байты и класс.

    Returns:
        Отказ команды либо ``None``, если корпус совпал с отпечатком.
    """
    if unreviewed_numeric_filenames(corpus_dir) != ():
        return CommandResult(success=False, code="unreviewed_version")
    try:
        current = accept_corpus(corpus_dir)
    except CorpusAcceptanceError as exc:
        return CommandResult(success=False, code=exc.code)
    if _identity_key(current) != _identity_key(recorded):
        return CommandResult(success=False, code="corpus_drift")
    return None


def _identity_key(
    fingerprint: CorpusFingerprint,
) -> tuple[tuple[str, str, str, str], ...]:
    """Сравнить id, имя, сырой SHA-256 и класс привилегии.

    Комментарии и переводы строк входят в SHA-256, потому что хеш считается
    по сырым байтам файла, а не по нарезке statement.
    """
    return tuple(
        (version.id, version.filename, version.sha256, version.privilege_class)
        for version in fingerprint.versions
    )


def _status_report(
    recorded: CorpusFingerprint,
    *,
    state: str,
    applied: tuple[str, ...],
) -> CommandResult:
    """Один и тот же state у всех версий, когда журнал ответа не даёт.

    Spec ``clickhouse-migration-lifecycle``: отсутствие цели и пустой журнал
    не превращаются в ``version_applied``.
    """
    return CommandResult(
        success=True,
        code=state,
        exit_code=0,
        version_reports=tuple(
            VersionReport(
                version_id=version.id,
                privilege_class=version.privilege_class,
                sha256=version.sha256,
                state=state,
            )
            for version in recorded.versions
        ),
        applied_version_ids=applied,
        satisfies_reconcile=False,
    )


def _status_code(latest: dict[str, LedgerEvent]) -> str:
    """Свернуть последний event каждой версии в код честного status.

    Неизвестная история и ``partial`` печатаются как есть. Это не санкция
    apply и не запись ``version_applied``.
    """
    kinds = {event.event_type for event in latest.values()}
    if "history_unresolved" in kinds:
        return "history_unresolved"
    if kinds & _OPEN_VERSION_EVENTS:
        return "partial"
    if kinds == {"version_applied"}:
        return "applied"
    return "ledger_absent"


def _dry_plan(
    code: str,
    planned: tuple[PlannedVersion, ...],
) -> CommandResult:
    """Построенный план: порядок версий есть, statement в порт не уходят."""
    return CommandResult(
        success=True,
        code=code,
        exit_code=0,
        planned_versions=planned,
    )


def _planned_versions(corpus_dir: Path) -> tuple[PlannedVersion, ...]:
    """Собрать класс, SHA-256 и statement текущих файлов ``001``–``005``.

    Ошибка приёмки корпуса оставляет план пустым: отказ уже несёт код
    ``gate_corpus``, а нарезка не должна выглядеть как начатый apply.
    """
    try:
        current = accept_corpus(corpus_dir)
    except CorpusAcceptanceError:
        return ()
    planned: list[PlannedVersion] = []
    for version in current.versions:
        text = (corpus_dir / version.filename).read_text(encoding="utf-8")
        try:
            statements = split_statements(text)
        except StatementParseError:
            return ()
        planned.append(
            PlannedVersion(
                version_id=version.id,
                privilege_class=version.privilege_class,
                sha256=version.sha256,
                statements=statements,
            )
        )
    return tuple(planned)


def _read_ledger(port: IsolatedTargetPort) -> LedgerReadResult:
    """Прочитать журнал шва. Append и ``exec_sql`` не вызываются.

    Идентичность берётся из порта, а не из имени хоста.
    """
    identity = port.server_uuid()
    database = port.session_database()
    target_id = identity.raw if identity.raw is not None else ""
    return port.ledger_read(target_id, database.name)


def _applied_ids(
    recorded: CorpusFingerprint,
    latest: dict[str, LedgerEvent],
) -> tuple[str, ...]:
    """Версии с ``version_applied`` и тем же SHA-256, что у файла.

    Чужой хеш в журнале — drift, а не applied-status.
    """
    return tuple(
        version.id
        for version in recorded.versions
        if version.id in latest
        and latest[version.id].event_type == "version_applied"
        and latest[version.id].sha256 == version.sha256
    )


def _version_reports(
    recorded: CorpusFingerprint,
    latest: dict[str, LedgerEvent],
) -> tuple[VersionReport, ...]:
    """Состояние каждой версии: журнал или ``ledger_absent``."""
    return tuple(
        VersionReport(
            version_id=version.id,
            privilege_class=version.privilege_class,
            sha256=version.sha256,
            state=operator_state(
                latest.get(version.id),
                file_sha256=version.sha256,
            ),
        )
        for version in recorded.versions
    )


def ledger_has_drift(
    recorded: CorpusFingerprint,
    latest: dict[str, LedgerEvent],
) -> bool:
    """Публичный read-only predicate drift для общего lifecycle.

    Spec ``clickhouse-migration-lifecycle``: mutating и read-only команды
    обязаны одинаково трактовать чужой SHA-256 журнала и не исполнять SQL.
    """
    return _ledger_drift(recorded, latest)


def _ledger_drift(
    recorded: CorpusFingerprint,
    latest: dict[str, LedgerEvent],
) -> bool:
    """Есть событие, чей SHA-256 не равен сырым байтам файла."""
    return any(
        item.state == "drift" for item in _version_reports(recorded, latest)
    )


def latest_by_version(
    events: tuple[LedgerEvent, ...],
) -> dict[str, LedgerEvent]:
    """Публично свернуть append-only ledger до latest event per version.

    Spec ``clickhouse-migration-lifecycle``: restart и mutating path читают
    durable ledger тем же правилом максимального ``event_seq``.
    """
    return _latest_by_version(events)


def _latest_by_version(
    events: tuple[LedgerEvent, ...],
) -> dict[str, LedgerEvent]:
    """Последний event версии по ``event_seq``. Более ранние не затирают его."""
    latest: dict[str, LedgerEvent] = {}
    for event in events:
        current = latest.get(event.version_id)
        if current is None or event.event_seq >= current.event_seq:
            latest[event.version_id] = event
    return latest


def _plan_stop(
    recorded: CorpusFingerprint,
    events: tuple[LedgerEvent, ...],
) -> str | None:
    """Причина остановки сухого плана по уже прочитанному журналу.

    Пустой журнал не является причиной этого среза: положительный apply ещё
    закрыт кодом ``mutation_not_opened``. ``005`` останавливает план, когда
    предыдущие schema-версии уже ``version_applied``.
    """
    latest = _latest_by_version(events)
    if latest == {}:
        return None
    if _ledger_drift(recorded, latest):
        return "drift"
    kinds = {event.event_type for event in latest.values()}
    if "history_unresolved" in kinds:
        return "history_unresolved"
    if kinds & _OPEN_VERSION_EVENTS:
        return "partial"
    applied = {
        version_id
        for version_id, event in latest.items()
        if event.event_type == "version_applied"
    }
    for version in recorded.versions:
        if version.id in applied:
            continue
        if version.privilege_class == "privileged_grant":
            return "blocked_privileged_grant"
        return None
    return None


_OPEN_VERSION_EVENTS = frozenset(
    {"statement_ok", "apply_started", "partial", "applying"}
)


def _clear_validate(corpus_dir: Path) -> CommandResult:
    """Нарезка цельного корпуса без передачи текста в порт.

    ``005`` остаётся в нарезке как текст ``GRANT``, но writer его не
    получает: порт в эту функцию не передаётся.
    """
    parsed: list[str] = []
    for version in immutable_fingerprint().versions:
        text = (corpus_dir / version.filename).read_text(encoding="utf-8")
        parsed.extend(split_statements(text))
    return CommandResult(
        success=True,
        code="ok",
        parsed_statements=tuple(parsed),
        exit_code=0,
    )
