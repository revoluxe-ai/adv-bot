from collections.abc import Callable, Sequence

from sqlalchemy import select, update

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    sync_keyword_setting_mode_for_v3,
)
from app.utils.db.session_maker import get_async_session_maker as sm

from .not_relevante_template import NotRelevantTemplate
from .relevant_phrase_template import RelevantPhraseTemplate


class RelevantPhraseManager:
    def __init__(self, adv: AdvSetting):
        self._adv = adv

    @staticmethod
    def _safe_str_list(raw: object) -> list[str]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            return []
        return [x for x in raw if isinstance(x, str)]

    @staticmethod
    def build_initial_flags_evaluator(
        adv: AdvSetting,
    ) -> Callable[[str], tuple[int, bool]]:
        """Скомпилировать шаблоны один раз; вызывать возвращаемую функцию на каждую фразу."""
        only_rel = bool(getattr(adv, "auto_add_only_relevant_phrase", False))
        if only_rel:
            rel_rows = RelevantPhraseManager._safe_str_list(
                getattr(adv, "relevant_phrases", None)
            )
            rel_t = RelevantPhraseTemplate(rel_rows)

            def _flags_only_relevant(text: str) -> tuple[int, bool]:
                return (1, rel_t.matches(text))

            return _flags_only_relevant
        black_rows = RelevantPhraseManager._safe_str_list(
            getattr(adv, "black_phrases", None)
        )
        not_rel = NotRelevantTemplate(black_rows)

        def _flags_black(text: str) -> tuple[int, bool]:
            hard = 0 if not not_rel.is_relevant(text) else 1
            return (hard, False)

        return _flags_black

    @staticmethod
    def initial_flags_for_new_keyword(text: str, adv: AdvSetting) -> tuple[int, bool]:
        return RelevantPhraseManager.build_initial_flags_evaluator(adv)(text)

    async def update_black_phrases(self, keywords: list[str]) -> None:
        adv_setting_id = self._adv.id
        async with sm(read_only=False) as session:
            _ = await session.execute(
                update(AdvSetting)
                .where(AdvSetting.id == adv_setting_id)
                .values(black_phrases=keywords)
            )
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    AdvSetting.id == int(adv_setting_id),
                    KeywordSetting.hard_status != 0,
                )
            )
            result = await session.execute(stmt)
            keyword_settings: Sequence[KeywordSetting] = result.scalars().all()
            templator = NotRelevantTemplate(keywords)

            for keyword_setting in keyword_settings:
                if keyword_setting.hard_status == 4:
                    continue
                text = str(keyword_setting.text)
                if not templator.is_relevant(text):
                    keyword_setting.hard_status = 0
                    keyword_setting.relevant = False
                    _ = sync_keyword_setting_mode_for_v3(
                        keyword_setting,
                        bot_active=self._adv.bot_active,
                        hard_status_override=0,
                        adv_strategy=self._adv.strategy,
                    )

            await session.commit()

    async def update_relevant_phrases_templates(self, keywords: list[str]) -> None:
        adv_setting_id = self._adv.id
        async with sm(read_only=False) as session:
            _ = await session.execute(
                update(AdvSetting)
                .where(AdvSetting.id == adv_setting_id)
                .values(relevant_phrases=keywords)
            )
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    AdvSetting.id == int(adv_setting_id),
                    KeywordSetting.hard_status != 0,
                )
            )
            result = await session.execute(stmt)
            keyword_settings: Sequence[KeywordSetting] = result.scalars().all()
            templator = RelevantPhraseTemplate(keywords)

            for keyword_setting in keyword_settings:
                if keyword_setting.hard_status == 4:
                    continue
                text = str(keyword_setting.text)
                keyword_setting.relevant = templator.matches(text)

            await session.commit()

    async def get_relevant_template_data(self) -> list[str]:
        result = getattr(self._adv, "black_phrases", None)
        if result is None:
            return []
        if not isinstance(result, list):
            return []
        return result

    async def get_relevant_phrases_template_data(self) -> list[str]:
        result = getattr(self._adv, "relevant_phrases", None)
        if result is None:
            return []
        if not isinstance(result, list):
            return []
        return [x for x in result if isinstance(x, str)]
