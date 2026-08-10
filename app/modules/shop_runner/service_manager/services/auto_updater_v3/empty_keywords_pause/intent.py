"""One-shot Redis intent: V3 запросил pause; activity-control исполнит следующим шагом.

Spec: pause = следующий шаг после OFF, не concurrent с OFF.
"""

from __future__ import annotations

from datetime import timedelta

from app.core.redis_manager import RedisManager


class EmptyKeywordsPauseIntentManager(RedisManager):
    """Хранит one-shot intent паузы empty-keywords на adv_id (auto).

    Spec ``pause-on-empty-keywords``: V3 ставит intent после OFF;
    ``ensure_campaigns_active`` потребляет и делает pause (следующий шаг).
    """

    _PREFIX = "empty-keywords-pause-intent"
    _TTL = int(timedelta(hours=6).total_seconds())
    _NOTIFY_PREFIX = "empty-keywords-pause-notified"
    _NOTIFY_TTL = int(timedelta(hours=24).total_seconds())

    def _intent_key(self, adv_id: int) -> str:
        return f"{self._PREFIX}:{adv_id}"

    def _notify_key(self, adv_id: int) -> str:
        return f"{self._NOTIFY_PREFIX}:{adv_id}"

    async def set_intent(self, adv_id: int) -> None:
        """Запросить pause empty-keywords как следующий шаг shop-runner."""
        await self.client.set(self._intent_key(adv_id), "1", ex=self._TTL)

    async def consume_intent(self, adv_id: int) -> bool:
        """Забрать intent. True если был установлен."""
        key = self._intent_key(adv_id)
        raw = await self.client.get(key)
        if not raw:
            return False
        await self.client.delete(key)
        return True

    async def peek_intent(self, adv_id: int) -> bool:
        """True если intent ещё не потреблён."""
        raw = await self.client.get(self._intent_key(adv_id))
        return bool(raw)

    async def mark_notified(self, adv_id: int) -> bool:
        """Debounce notify: True если первое уведомление в окне TTL (SET NX)."""
        key = self._notify_key(adv_id)
        ok = await self.client.set(key, "1", ex=self._NOTIFY_TTL, nx=True)
        return bool(ok)

    async def was_notified(self, adv_id: int) -> bool:
        """True если debounce-ключ pause notify ещё активен (delivered episode).

        Используется resume/re-enable notify: без prior pause-notify episode
        ordinary Search start MUST NOT слать resume-сообщение.
        """
        raw = await self.client.get(self._notify_key(adv_id))
        return bool(raw)

    async def release_notified(self, adv_id: int) -> None:
        """Снять debounce-ключ, если доставка не подтверждена.

        Нужен, когда ``mark_notified`` уже занял окно TTL, но ни один
        ``send_message`` не завершился успешно — иначе повтор в том же
        окне будет подавлен без доставки.

        Также закрывает episode после успешного resume/re-enable notify.
        """
        await self.client.delete(self._notify_key(adv_id))
