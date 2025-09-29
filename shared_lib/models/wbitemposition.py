import datetime
from typing import Optional, Dict, Any

class WBItemPosition:
    nmid: Optional[int] = None
    position: Optional[int] = None
    timestamp: Optional[datetime.datetime] = None
    adv_id: Optional[int] = None
    keyword_text: Optional[str] = None
    adv_type: Optional[int] = None

    @property
    def type_native(self) -> Optional[str]:
        if self.adv_type == 9:
            return "search"
        elif self.adv_type == 8:
            return "auto"
        return None

    def to_dict(self) -> Dict[str, Any]:
        str_timestamp = self.timestamp.isoformat() if self.timestamp else None
        return {
            "real_position": self.position,
            "promo_position": self.position,
            "base_position": self.position,
            "position": self.position,
            "keyword_text": self.keyword_text,
            "adv_id": self.adv_id,
            "nmid": self.nmid,
            "timestamp": str_timestamp,
            "adv_type": self.adv_type,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WBItemPosition":
        position = WBItemPosition()
        position.position = data.get("position", data.get("base_position", 0))
        position.adv_id = data.get("adv_id")
        position.nmid = data.get("nmid")
        str_timestamp = data.get("timestamp")
        if str_timestamp:
            try:
                position.timestamp = datetime.datetime.fromisoformat(str_timestamp)
            except Exception:
                position.timestamp = None
        position.keyword_text = data.get("keyword_text")
        position.adv_type = data.get("adv_type")
        return position
