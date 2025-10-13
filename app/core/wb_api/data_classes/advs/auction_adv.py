from app.modules.common_slaves.wildberries.data_classes.adv import Adv


class AuctionAdv(Adv):
    """Auction advertising campaign (type 9).

    For auction campaigns, CPM is located in unitedParams[0].searchCPM.
    """

    @property
    def cpm(self) -> int | None:
        """Get CPM for auction advertising campaign from unitedParams[0].searchCPM."""
        try:
            united_params = self._data.get("unitedParams", [])
            if isinstance(united_params, list) and len(united_params) > 0:
                first_param = united_params[0]
                if isinstance(first_param, dict):
                    return first_param.get("searchCPM")
            return None
        except (KeyError, TypeError, AttributeError, IndexError):
            return None


__all__ = ["AuctionAdv"]
