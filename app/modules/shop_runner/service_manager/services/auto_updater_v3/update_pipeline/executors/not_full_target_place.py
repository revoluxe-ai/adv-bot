"""NF bootstrap и plan-fact регулировка ``target_place`` для no-CH PFO ключей.

Этот модуль закрывает только одну часть V3-контракта: как активный no-CH ключ
переходит от состояния ``target_place=0`` к состоянию «есть стартовая
позиция» и как потом эта позиция двигается на ``±1`` по plan/fact.

Важно понимать смысл ``0`` в этом контуре. Здесь ``0`` — это не целевой
результат и не осмысленный reset. Это только признак того, что стартовая
позиция ещё не создана. Как только ключ получает первую рабочую WB-позицию,
``0`` перестаёт быть значимым и дальше остаётся только план-факт коррекция.

Разделение здесь намеренно жёсткое:

- ``NotFullTargetPlaceMigrateExecutor`` делает только первый bootstrap и
  фиксирует стартовую WB-позицию как ``target_place``;
- ``NotFullTargetPlacePlanFactExecutor`` делает только последующую коррекцию
  на ``±1`` и никогда не превращает ключ обратно в ``0``;
- FULL-ключи игнорируются, потому что у них свой ladder-контур;
- GAP-ключи игнорируются, потому что они обслуживаются отдельным
  enable/reset-контуром и ещё не имеют права на NF bootstrap;
- ``OFF`` не инициализируется вообще, чтобы NF-контур не подменял enable.

Именно поэтому этот модуль не является «общим no-CH регулятором». Его задача
гораздо уже: принять уже активный PFO no-CH ключ, один раз инициализировать
ему стартовую позицию и дальше вести его малыми шагами ``±1`` без reset в
``0``.
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import NextTargetPlace
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    current_position_as_target_place,
    plan_fact_target_place_skip_reason,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    KeywordV3DataTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class NotFullTargetPlaceMigrateExecutor:
    """Инициализировать ``target_place`` для активных PFO ключей.

    Это стартовая операция NF bootstrap. Её цель не в том, чтобы выбрать
    «лучшее» место в ladder, а в том, чтобы убрать семантическое значение
    ``0`` как «пусто» и заменить его на реальную стартовую WB-позицию.

    Почему это отдельная фаза:

    - до migrate ``target_place=0`` означает отсутствие инициализации, а не
      намеренный целевой ноль;
    - после migrate у ключа появляется первая рабочая точка, от которой уже
      можно безопасно выполнять plan-fact ``±1``;
    - если делать это вместе с plan-fact, первый тик смешает bootstrap и
      коррекцию, и контракт станет нечитаемым;
    - FULL, GAP и OFF в этой фазе сознательно не трогаются, чтобы не размывать
      границу между PFO-bootstrap и enable/reset-контуром.

    Иными словами, migrate отвечает только за «инициализировать стартовую
    позицию PFO-ключа», а не за какие-либо overspend/reset сценарии.

    Смысл для продукта простой: сначала мы говорим ключу «ты уже активен и у
    тебя есть опорная точка», а уже потом позволяем plan-fact немного сдвигать
    эту точку вверх или вниз. Благодаря этому один и тот же тик не смешивает
    bootstrap и корректировку, а `0` не превращается в универсальный reset.
    """

    phase_name = "not_full_target_place_migrate"
    _skip_reason: str | None = None

    def execute(self, context: UpdateContext) -> None:
        """Заполнить пустой ``target_place`` для активных PFO ключей.

        Логика здесь консервативная: фаза ничего не «улучшает», а только
        инициализирует стартовую точку, если она ещё не создана.

        Проверки идут в таком порядке, чтобы избежать случайного смешения
        контуров:

        - сначала отсеиваются не-PFO tier'ы;
        - затем проверяется, что режим уже ``MIN_CPA``;
        - затем убеждаемся, что ``target_place`` ещё не был инициализирован;
        - только после этого берём текущую WB-позицию и фиксируем её как
          стартовый target_place.

        Это гарантирует, что FULL не попадёт в NF bootstrap, GAP не будет
        инициализирован как будто он уже PFO, а OFF не будет случайно оживлён.

        В результате на выходе получаем не «обнулённый» ключ, а ключ с первой
        осмысленной опорной позицией, от которой уже можно строить plan-fact
        движение без риска перепутать bootstrap с reset.

        Анатомия старой проблемы была именно в смешении уровней:

        - один локальный признак у ключа пытались трактовать как решение уровня
          кампании;
        - ``target_place=0`` читался как будто это осмысленный reset, хотя это
          только отсутствие инициализации;
        - bootstrap и reset оказались рядом в одном контуре, хотя по контракту
          это разные фазы;
        - NF bootstrap начал выглядеть как универсальная no-CH логика, хотя он
          должен обслуживать только PFO.

        Поэтому текущий контракт жёсткий: migrate создаёт стартовую точку,
        plan-fact только корректирует уже созданную позицию, а reset вообще не
        живёт внутри этой фазы.
        """
        self._skip_reason = None
        for dto in context.keywords:
            if dto.data_tier != KeywordV3DataTier.PFO:
                continue
            if dto.current_mode != KeywordStrategyMode.MIN_CPA:
                continue
            if dto.current_target_place != 0:
                continue
            new_place = current_position_as_target_place(dto)
            if new_place is None:
                continue
            dto.current_target_place = NextTargetPlace(
                new_target_place=new_place,
                executor_name=self.__class__.__name__,
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _restore_plan_fact_target_place_if_zero(
    dto: KeywordDTO,
    *,
    previous_target_place: int,
    executor_name: str,
) -> None:
    """Защитить NF plan-fact от любого будущего reset-в-0.

    ``NotFullTargetPlacePlanFactExecutor`` по контракту может только сдвигать
    уже инициализированный PFO target_place на ``±1``. Если зависимый слой когда-
    нибудь снова попытается записать ``0``, это будет ровно возврат старого
    бага “NF reset lacks overspend gate”: локальная plan-fact ветка превратится
    в campaign-level reset без явного overspend gate.

    Поэтому executor держит собственный invariant рядом с местом вызова:
    ``0`` не является допустимым результатом NF plan-fact. Если после
    корректировки он появился, возвращаем предыдущее рабочее значение.
    """
    if dto.current_target_place != 0:
        return
    dto.current_target_place = NextTargetPlace(
        new_target_place=previous_target_place,
        executor_name=executor_name,
    )


class NotFullTargetPlacePlanFactExecutor:
    """Корректировать ``target_place`` для активных PFO ключей по plan-fact.

    Это вторая часть NF-контракта. Она работает только после bootstrap и
    обязана оставаться маленькой и предсказуемой: взять уже инициализированный
    PFO ключ и сдвинуть его на ``±1`` в зависимости от отношения фактического
    и целевого CPO.

    Что эта фаза не делает:

    - не инициализирует ``target_place`` с нуля;
    - не сбрасывает ключ обратно в ``0``;
    - не обслуживает FULL;
    - не обслуживает GAP;
    - не подменяет отдельный gap enable/reset или ladder reset.

    Дополнительно: если migrate уже сработал в этом же тике, plan-fact не
    должен сразу переезжать стартовую позицию. Первый тик остаётся чистым
    bootstrap, а коррекция начинается со следующего тика.

    Идея этой фазы в том, чтобы не тащить в код сложную decision-machine.
    Здесь нет поиска лучшего target_place, нет reset-логики, нет решения по
    campaign overspend и нет интерпретации GAP. Есть только заранее подготовленный
    PFO-ключ и очень локальное правило: в зависимости от факта и resolve
    сделать шаг на одну позицию вверх или вниз.

    Важная деталь исторического бага: раньше в похожем месте пытались ответить
    на вопрос “ключ стал хуже плана, значит надо reset-нуть его в 0?”. На уровне
    продукта это ошибочно, потому что:

    - локальный PFO одного ключа не равен overspend всей кампании;
    - ``0`` для NF-контракта означает отсутствие bootstrap, а не целевое
      состояние;
    - если в той же фазе разрешить и bootstrap, и reset, и коррекцию, то одна
      и та же функция начнёт подменять сразу три разных ответа на три разных
      вопроса.

    Это именно та точка, которую Bugbot формулирует как “NF reset lacks overspend
    gate”: внешний триггер выглядит как проверка одного ключа, но фактическое
    действие — reset в ``0`` — уже претендует на решение уровня кампании. В
    старой реализации ещё и sync fallback продолжал смотреть на campaign
    overspend как на отдельный сигнал, поэтому внутри системы получались два
    разных источника правды для одного и того же ``0``. Поэтому Bugbot и
    формулирует проблему именно как “reset без overspend gate”: в коде был
    branch, который мог дойти до reset, не пройдя отдельную кампанийную
    проверку, хотя reset по смыслу принадлежит именно этому уровню.

    Поэтому здесь сохраняется только узкий контракт корректора: когда стартовая
    точка уже есть, сдвинуть её на ``±1``; когда стартовой точки нет, ничего не
    делать.

    Решение проблемы здесь можно описать совсем просто:

    - migrate создаёт стартовую позицию;
    - plan-fact работает только после этой инициализации;
    - sentinel ``0`` не является рабочим target_place и не может быть поднят
      в ``1`` здесь;
    - campaign overspend gate вынесен в отдельный уровень, поэтому локальный
      PFO одного ключа больше не может провоцировать reset-в-0.

    Исторический баг, который здесь закрыт, был именно в том, что локальный
    PFO одного ключа начали трактовать как повод для reset-в-0. На уровне
    продукта это неверно: один ключ может выглядеть "хуже плана", но это ещё не
    означает, что кампания уже в overspend и что no-CH target_place нужно
    обнулять.

    Ещё более важная гарантия: если migrate не смог дать стартовую позицию и
    ``target_place`` всё ещё равен ``0``, plan-fact не имеет права “поднять”
    этот sentinel в рабочее значение. Иначе корректор начнёт подменять сам
    bootstrap и нарушит контракт разделения фаз.

    Отсюда следует практическое правило: если migrate не сработал, plan-fact
    должен остаться полностью бездействующим по этому ключу. Он не “подлечит”
    sentinel и не сделает вид, что bootstrap уже состоялся.

    Важный смысл этого правила в том, что корректор не должен скрывать проблему
    bootstrap'а. Если в ``target_place`` всё ещё ``0``, значит стартовая
    WB-позиция не создана, и этот факт нельзя “исправить” локальной plan-fact
    коррекцией. Иначе одна и та же фаза начнёт одновременно выполнять роль
    bootstrap, корректора и reset-механизма. Именно этого Bugbot и боится в
    старом коде: там один и тот же branch мог “показаться” обычной корректировкой,
    но фактически завершаться reset-в-0 без отдельного campaign gate.

    Решение проблемы здесь очень простое и очень жёсткое:

    - bootstrap делает только migrate;
    - plan-fact работает только по уже инициализированному PFO;
    - ``0`` остаётся sentinel и не превращается в “первую настоящую позицию”;
    - any overspend logic вынесена из этого executor-а в отдельные campaign-
      level gates.
    """

    phase_name = "not_full_target_place_plan_fact"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(NotFullTargetPlacePlanFactExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Применить NF plan-fact логику к активным PFO ключам.

        Алгоритм намеренно простой:

        1. Проверить, что сам тик вообще допускает plan-fact коррекцию.
        2. Оставить в работе только PFO tier.
        3. Не трогать ключ, который только что прошёл migrate в этом же тике.
        4. Для остальных PFO-ключей вычислить направление ``±1`` и применить
           его к текущему target_place.

        Благодаря этому plan-fact остаётся именно корректором, а не скрытым
        bootstrap/reset механизмом.

        Если смотреть на поведение сверху, эта фаза отвечает на вопрос
        «ключ уже инициализирован, теперь двигать его или нет?». Она не отвечает
        на вопрос «надо ли ключ вообще запускать» и не отвечает на вопрос
        «нужно ли его обнулить». Эти решения живут в других фазах контракта.
        """
        self._skip_reason = plan_fact_target_place_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
        state = context.adv_state
        fact = float(state.fact_pay_for_order)  # type: ignore[arg-type]
        resolve = float(state.resolve)
        for dto in context.keywords:
            if dto.data_tier != KeywordV3DataTier.PFO:
                continue
            if dto.current_target_place == 0:
                continue
            if (
                dto.history_target_place
                and dto.history_target_place[-1].executor_name
                == NotFullTargetPlaceMigrateExecutor.__name__
            ):
                continue
            previous_target_place = dto.current_target_place
            self._next_state_manager.adjust_not_full_target_place_plan_fact(
                dto,
                fact_pay_for_order=fact,
                resolve=resolve,
            )
            _restore_plan_fact_target_place_if_zero(
                dto,
                previous_target_place=previous_target_place,
                executor_name=self.__class__.__name__,
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
