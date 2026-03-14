from typing import Sequence
from sqlalchemy import select

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import NormqueryStatsDTO
from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.modules.relevant_phrase_manager.not_relevante_template import NotRelevantTemplate
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import KeywordStat
from app.utils.db.session_maker import get_async_session_maker as sm



class KeywordsManager:
    @staticmethod
    async def get_candidates_to_white_list(complex_adv: ComplexAdv):
        # TODO: Централизовать отбор кандидатов в БС
        # Фильтруем кандидатов для белого списка
        def candidate_filter(keyword: CalculatedKeyword) -> bool | None:
            if keyword.views == 0:
                return False
            if keyword.hard_status != 1:
                return False
            if keyword.status == KeywordStatus.GOOD:
                return False
            if complex_adv.auto_add_only_relevant_phrase and not keyword.relevant:
                return False
            if (complex_adv.rec_system_promotion_mode_active
                    and keyword.above_rec_conversion is False
                    and complex_adv.auto_adv_active_status):
                return False
            return True

        keywords = await complex_adv.get_keywords()
        candidates = list(filter(candidate_filter, keywords))
        return candidates

    async def create_new_keyword_settings_for_complex_advs(self,
                                                           complex_advs: list[ComplexAdv],
                                                           stats: list["NormqueryStatsDTO"]):
        async with sm(read_only=False) as session:
            adv_id_to_complex_adv = {adv_id: adv for adv in complex_advs for adv_id in adv.all_adv_ids}
            for stat in stats:
                adv_id = stat.adv_id
                complex_adv = adv_id_to_complex_adv[adv_id]
                original_adv_id = complex_adv.original_adv_setting_id
                texts: list[str] = [st.norm_query for st in stat.stats]
                exists_keywords_text: Sequence[str] = \
                    await self.__get_exists_keyword_settings_text(original_adv_id,
                                                                   texts)
                new_texts: set[str] = set(texts) - set(exists_keywords_text)
                relevant_phrase_manager = RelevantPhraseManager(complex_adv.adv_setting)
                template_data = await relevant_phrase_manager.get_relevant_template_data()
                not_rel_templator = NotRelevantTemplate(template_data)
                for text in new_texts:
                    if not not_rel_templator.is_relevant(text):
                        hard_status = 0
                    else:
                        hard_status = 1
                    new_keyword_setting = KeywordSetting(
                        text=text,
                        hard_status=hard_status,
                        adv_setting_id=complex_adv.original_adv_setting_id
                    )
                    session.add(new_keyword_setting)
            await session.commit()


    @staticmethod
    async def __get_exists_keyword_settings_text(original_adv_id: int, texts: list[str]) -> Sequence[str]:
        # TODO: Тут ошибка в рантайм попала
        stmt = select(KeywordSetting.text).where(KeywordSetting.text.in_(texts),
                                                 KeywordSetting.adv_setting_id == original_adv_id)
        async with sm(read_only=True) as session:
            results = await session.execute(stmt)
            texts_exists: Sequence[str] = results.scalars().all()
        return texts_exists

    async def create_new_keyword_settings(self, complex_adv: ComplexAdv, stats: list[KeywordStat]):
        async with sm(read_only=False) as session:
            original_adv_id = complex_adv.original_adv_setting_id
            texts: list[str] = [stat.text for stat in stats]
            exists_keywords_text: Sequence[str] = await self.__get_exists_keyword_settings_text(
                original_adv_id,
                texts
            )
            new_texts: set[str] = set(texts) - set(exists_keywords_text)

            relevant_phrase_manager = RelevantPhraseManager(complex_adv.adv_setting)
            template_data = await relevant_phrase_manager.get_relevant_template_data()
            not_rel_templator = NotRelevantTemplate(template_data)

            for text in new_texts:
                if not not_rel_templator.is_relevant(text):
                    hard_status = 0
                else:
                    hard_status = 1
                new_keyword_setting = KeywordSetting(
                    text=text,
                    hard_status=hard_status,
                    adv_setting_id=complex_adv.original_adv_setting_id
                )
                session.add(new_keyword_setting)

            await session.commit()
