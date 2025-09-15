"""Мапперы ответов для специфичных методов Promotion API v1."""

from typing import List, Dict, Any, Union, cast
import logging

logger = logging.getLogger(__name__)


class GetCampaignIdsResponseMapper:
    """Маппер для ответа get_campaign_ids."""
    
    @staticmethod
    def map_response(response: Any) -> List[int]:
        """
        Маппинг ответа get_adv_v1_promotion_count в список ID кампаний.
        
        На этом этапе response уже проверен BaseAPIAdapter и является GetAdvV1PromotionCountResponse200.
        """
        from .client_methods_and_models.get_adv_v1_promotion_count import (
            GetAdvV1PromotionCountResponse200,
            GetAdvV1PromotionCountResponse200AdvertsType0Item,
            GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem,
        )
        
        # Проверяем тип (для отладки)
        if not isinstance(response, GetAdvV1PromotionCountResponse200):
            logger.warning(f"Unexpected response type: {type(response)}")
            return []
            
        # Проверяем наличие данных
        if not response.adverts:
            logger.warning("No adverts in response")
            return []
            
        campaign_ids: List[int] = []
        
        # Проходим по группам кампаний (по типу и статусу)
        for group in response.adverts:
            if not isinstance(group, GetAdvV1PromotionCountResponse200AdvertsType0Item):
                continue
                
            # Фильтруем только поисковые кампании (тип 8)
            if group.type_ != 8:
                continue
                
            # Проходим по списку конкретных кампаний в группе
            if not group.advert_list:
                continue
                
            for campaign in group.advert_list:
                if not isinstance(campaign, GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem):
                    continue
                    
                if campaign.advert_id is not None:
                    campaign_ids.append(campaign.advert_id)
                    
        logger.debug(f"Extracted {len(campaign_ids)} campaign IDs from {len(response.adverts)} groups")
        return campaign_ids


class GetCampaignsByIdsResponseMapper:
    """Маппер для ответа get_campaigns_by_ids."""
    
    @staticmethod  
    def map_response(response: Any) -> List[Dict[str, Any]]:
        """Маппинг ответа post_adv_v1_promotion_adverts в список данных кампаний."""
        if not response:
            return []
            
        campaigns: List[Dict[str, Any]] = []
        for campaign_obj in response:
            try:
                data = GetCampaignsByIdsResponseMapper._extract_campaign_data(campaign_obj)
                campaigns.append(data)
            except Exception as e:
                logger.warning(f"Failed to extract campaign data: {e}")
                continue
                
        return campaigns
    
    @staticmethod
    def _extract_campaign_data(campaign_obj: Any) -> Dict[str, Any]:
        """Извлечь данные кампании из объекта ответа."""
        data: Dict[str, Any] = {
            "advert_id": getattr(campaign_obj, "advert_id", None),
            "name": getattr(campaign_obj, "name", None),
            "status": getattr(campaign_obj, "status", None),
            "type": getattr(campaign_obj, "type_", None),
            "create_time": getattr(campaign_obj, "create_time", None),
            "change_time": getattr(campaign_obj, "change_time", None),
            "start_time": getattr(campaign_obj, "start_time", None),
            "end_time": getattr(campaign_obj, "end_time", None),
            "daily_budget": getattr(campaign_obj, "daily_budget", None),
            "payment_type": getattr(campaign_obj, "payment_type", None),
        }

        # Извлекаем nmids из params
        params = getattr(campaign_obj, "params", None) or []
        nmids: List[int] = []
        for p in params:
            if hasattr(p, "nms") and getattr(p, "nms"):
                nmids.extend(list(getattr(p, "nms")))
        if nmids:
            data["nmids"] = nmids

        # Обрабатываем auto_params
        auto_params = getattr(campaign_obj, "auto_params", None)
        if auto_params is not None:
            GetCampaignsByIdsResponseMapper._extract_auto_params_data(data, auto_params)

        return data
    
    @staticmethod
    def _extract_auto_params_data(data: Dict[str, Any], auto_params: Any) -> None:
        """Извлечь данные из auto_params."""
        # Извлекаем bids
        nm_cpm = getattr(auto_params, "nm_cpm", None) or []
        bids_map: Dict[int, int] = {}
        for item in nm_cpm:
            nm_val = getattr(item, "nm", None)
            cpm_val = getattr(item, "cpm", None)
            if isinstance(nm_val, int) and isinstance(cpm_val, int):
                bids_map[nm_val] = cpm_val
        if bids_map:
            data["bids"] = bids_map

        # Активности зон показов
        active = getattr(auto_params, "active", None)
        if active is not None:
            data["auto_active"] = {
                k: getattr(active, k)
                for k in ["carousel", "recom", "booster"]
                if hasattr(active, k)
            }

        # Subject данные
        subject = getattr(auto_params, "subject", None)
        if subject is not None:
            data["auto_subject_id"] = getattr(subject, "id", None)
            data["auto_subject_name"] = getattr(subject, "name", None)

        # Sets данные
        sets = getattr(auto_params, "sets", None) or []
        if sets:
            data["auto_sets"] = [
                {
                    "id": getattr(s, "id", None),
                    "name": getattr(s, "name", None),
                }
                for s in sets
            ]


class GetMinBidsResponseMapper:
    """Маппер для ответа get_min_bids."""
    
    @staticmethod
    def map_response(response: Any, nmids: List[int]) -> List[Dict[str, Any]]:
        """Маппинг ответа post_adv_v0_bids_min в список минимальных ставок."""
        if not response or not response.bids:
            logger.warning("Пустой ответ при получении минимальных ставок")
            return []

        result = []
        for item in response.bids:
            if not item.bids or len(item.bids) == 0:
                logger.warning(f"Нет ставок для товара {item.nm_id}")
                continue

            first_bid = item.bids[0]
            if first_bid.value is None:
                logger.warning(f"Пустое значение ставки для товара {item.nm_id}")
                continue

            result.append({"nmid": item.nm_id, "min_bid": float(first_bid.value)})

        logger.debug(f"Получены минимальные ставки для {len(result)} товаров из {len(nmids)}")
        return result
