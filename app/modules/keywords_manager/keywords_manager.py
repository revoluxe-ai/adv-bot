from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus


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
