"""Интеграционные тесты выгрузки/импорта Excel по активным РК (реальная Postgres-сессия)."""

from __future__ import annotations

import uuid
from typing import cast
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.services.adv_excel_roundtrip.export_build import (
    build_adv_excel_export,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.import_apply import (
    AdvExcelImportError,
    apply_adv_excel_rows,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EXCEL_TEMPLATE_VERSION,
    column_header,
    edit_header,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from tests.factories.adv_factory import AdvSettingFactory

pytestmark = pytest.mark.integration

_PATCH_IMPORT_SM = (
    "app.client_bot.user_interface.services.adv_excel_roundtrip.import_apply._sm"
)
_PATCH_EXPORT_SM = (
    "app.client_bot.user_interface.services.adv_excel_roundtrip.export_build._sm"
)
_PATCH_EXPORT_FACT = (
    "app.client_bot.user_interface.services.adv_excel_roundtrip.export_build._fact_snapshot"
)


async def _fact_snapshot_stub(_adv: AdvSetting) -> tuple[float | None, float | None]:
    """Без ClickHouse/PlanFact: экспорт проверяем по колонкам и AdvSetting."""
    return None, None


class MockSessionMaker:
    """Тестовая фабрика сессий (как в test_default_settings_integration)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self, read_only: bool = False) -> MockSessionMaker:
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture
async def excel_shop_bundle(async_session: AsyncSession) -> dict[str, object]:
    """Пользователь + кабинет + одна активная РК с согласованными RO-полями для импорта."""
    uid = 900_000 + (uuid.uuid4().int % 90_000)
    user = User(user_telegram_id=uid, username="excel_roundtrip_user")
    async_session.add(user)
    await async_session.flush()

    # Без factory.Sequence(id=1,2,…): в общей test-БД id уже заняты другими тестами → UniqueViolation.
    wb_cabinet = WBCabinet(
        shop_id=f"excel_rt_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()

    wuc = WBUserCabinet(user_id=user.id, wb_cabinet_id=wb_cabinet.id, name="Excel shop")
    async_session.add(wuc)
    await async_session.flush()

    adv = cast(
        AdvSetting,
        AdvSettingFactory.build(
            wb_cabinet=wb_cabinet,
            name="Excel integration adv",
            bot_active=True,
            active_status="started",
            adv_id=600_000 + (uuid.uuid4().int % 10_000),
            min_views_for_ml_predict=11,
        ),
    )
    adv.nmids = [200_000 + (uuid.uuid4().int % 50_000)]
    adv.search_adv_id = 700_000 + (uuid.uuid4().int % 10_000)
    async_session.add(adv)
    await async_session.flush()

    return {"user": user, "wb_user_cabinet": wuc, "adv": adv}


@pytest.mark.asyncio
async def test_adv_excel_export_import_roundtrip_updates_adv(
    async_session: AsyncSession, excel_shop_bundle: dict[str, object]
) -> None:
    """Happy path: выгрузка → правка числового EDIT-поля → импорт → значение в БД."""
    user = excel_shop_bundle["user"]
    assert isinstance(user, User)
    wuc = excel_shop_bundle["wb_user_cabinet"]
    assert isinstance(wuc, WBUserCabinet)
    adv = excel_shop_bundle["adv"]
    assert isinstance(adv, AdvSetting)

    mock_sm = MockSessionMaker(async_session)
    with (
        patch(_PATCH_IMPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_FACT, _fact_snapshot_stub),
    ):
        _headers, rows = await build_adv_excel_export(wb_user_cabinet_id=wuc.id)
    assert len(rows) == 1
    row = rows[0]
    key_mv = edit_header("min_views_for_ml_predict")
    assert key_mv in row
    row[key_mv] = 47

    with patch(_PATCH_IMPORT_SM, mock_sm):
        updated = await apply_adv_excel_rows(
            telegram_user_id=int(user.user_telegram_id),
            expected_wb_user_cabinet_id=wuc.id,
            rows=rows,
        )
    assert updated == 1

    await async_session.commit()
    fresh = (
        await async_session.execute(select(AdvSetting).where(AdvSetting.id == adv.id))
    ).scalar_one()
    assert fresh.min_views_for_ml_predict == 47


@pytest.mark.asyncio
async def test_adv_excel_import_template_v1_rejected(
    async_session: AsyncSession, excel_shop_bundle: dict[str, object]
) -> None:
    """После bump шаблона до v2 файлы с версией 1 отклоняются (нужна новая выгрузка)."""
    user = excel_shop_bundle["user"]
    assert isinstance(user, User)
    wuc = excel_shop_bundle["wb_user_cabinet"]
    assert isinstance(wuc, WBUserCabinet)

    mock_sm = MockSessionMaker(async_session)
    with (
        patch(_PATCH_IMPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_FACT, _fact_snapshot_stub),
    ):
        _headers, rows = await build_adv_excel_export(wb_user_cabinet_id=wuc.id)

    row = rows[0]
    tpl_key = column_header("RO", "excel_template_version")
    assert tpl_key in row
    row[tpl_key] = 1

    with patch(_PATCH_IMPORT_SM, mock_sm):
        with pytest.raises(AdvExcelImportError) as excinfo:
            _ = await apply_adv_excel_rows(
                telegram_user_id=int(user.user_telegram_id),
                expected_wb_user_cabinet_id=wuc.id,
                rows=rows,
            )
    assert "Версия шаблона" in str(excinfo.value)


@pytest.mark.asyncio
async def test_adv_excel_import_invalid_enum_rejected(
    async_session: AsyncSession, excel_shop_bundle: dict[str, object]
) -> None:
    """Недопустимое имя enum в EDIT-колонке → AdvExcelImportError (fail-fast)."""
    user = excel_shop_bundle["user"]
    assert isinstance(user, User)
    wuc = excel_shop_bundle["wb_user_cabinet"]
    assert isinstance(wuc, WBUserCabinet)

    mock_sm = MockSessionMaker(async_session)
    with (
        patch(_PATCH_IMPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_FACT, _fact_snapshot_stub),
    ):
        _headers, rows = await build_adv_excel_export(wb_user_cabinet_id=wuc.id)

    row = rows[0]
    row[edit_header("strategy")] = "NOT_A_VALID_STRATEGY_ENUM_NAME"

    mock_sm = MockSessionMaker(async_session)
    with patch(_PATCH_IMPORT_SM, mock_sm):
        with pytest.raises(AdvExcelImportError) as excinfo:
            _ = await apply_adv_excel_rows(
                telegram_user_id=int(user.user_telegram_id),
                expected_wb_user_cabinet_id=wuc.id,
                rows=rows,
            )
    assert "Недопустимое значение enum" in str(excinfo.value)


@pytest.mark.asyncio
async def test_adv_excel_import_old_template_version_rejected(
    async_session: AsyncSession, excel_shop_bundle: dict[str, object]
) -> None:
    """Файл с устаревшей/иной версией шаблона отклоняется до разбора строк."""
    user = excel_shop_bundle["user"]
    assert isinstance(user, User)
    wuc = excel_shop_bundle["wb_user_cabinet"]
    assert isinstance(wuc, WBUserCabinet)

    mock_sm = MockSessionMaker(async_session)
    with (
        patch(_PATCH_IMPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_SM, mock_sm),
        patch(_PATCH_EXPORT_FACT, _fact_snapshot_stub),
    ):
        _headers, rows = await build_adv_excel_export(wb_user_cabinet_id=wuc.id)

    row = rows[0]
    tpl_key = column_header("RO", "excel_template_version")
    assert tpl_key in row
    row[tpl_key] = EXCEL_TEMPLATE_VERSION + 99

    mock_sm = MockSessionMaker(async_session)
    with patch(_PATCH_IMPORT_SM, mock_sm):
        with pytest.raises(AdvExcelImportError) as excinfo:
            _ = await apply_adv_excel_rows(
                telegram_user_id=int(user.user_telegram_id),
                expected_wb_user_cabinet_id=wuc.id,
                rows=rows,
            )
    assert "Версия шаблона" in str(excinfo.value)
