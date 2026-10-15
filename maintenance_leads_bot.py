"""Dependency-free Telegram maintenance/lead intake mode for WB Sky.

One replica, polling, no DB, no Wildberries API, no ad writes.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import FrameType
from typing import Any, cast

LOG = logging.getLogger("wb_sky_maintenance")
TEXT = (
    "🔧 WB Sky обновляется\n\n"
    "В боте проходят масштабные обновления.\n\n"
    "Для продолжения работы потребуется короткий инструктаж и перенастройка системы.\n\n"
    "Оставьте заявку — мы свяжемся с вами и поможем продолжить работу."
)
CTA = "📩 Оставить заявку"
CONTACT_CTA = "📱 Поделиться номером"
MAIN_KEYBOARD = {"keyboard": [[{"text": CTA}]], "resize_keyboard": True}
PHONE_KEYBOARD = {
    "keyboard": [[{"text": CONTACT_CTA, "request_contact": True}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}
MSK = timezone(timedelta(hours=3))


def owner_admin_chat_id(constants_path: Path | None = None) -> int:
    """Read the existing const.py authority without importing the full app.

    The main presentation notification recipient is the owner's configured
    recipient and must also be among the built-in WB Sky administrators.
    """
    path = constants_path or (
        Path(__file__).resolve().parent / "app" / "client_bot" / "const.py"
    )
    values: dict[str, Any] = {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "_BASE_ADMINS",
                    "MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID",
                }:
                    values[target.id] = ast.literal_eval(node.value)
    except (OSError, SyntaxError, ValueError, TypeError) as exc:
        raise RuntimeError("Cannot resolve WB Sky owner administrator") from exc
    admins = values.get("_BASE_ADMINS")
    recipient = values.get("MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID")
    if (
        not isinstance(admins, list)
        or not isinstance(recipient, int)
        or isinstance(recipient, bool)
        or recipient <= 0
        or recipient not in admins
        or not admins
        or recipient != admins[0]
    ):
        raise RuntimeError("WB Sky owner administrator identity is inconsistent")
    return recipient


def apply_legacy_proxy() -> str | None:
    """Подключить urllib к уже заданному WB Sky ``PROXY``.

    Клиентский бот кладёт адрес xray в ``PROXY`` для aiohttp. Стандартный
    urllib читает только ``HTTP(S)_PROXY``. Явный ``HTTPS_PROXY`` не
    перезаписывается. Возвращает используемый URL или None.
    """
    explicit = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if explicit:
        return explicit
    legacy = os.environ.get("PROXY", "").strip()
    if not legacy:
        return None
    os.environ["HTTPS_PROXY"] = legacy
    os.environ["HTTP_PROXY"] = legacy
    return legacy


def _as_str(value: object) -> str:
    """Строка для полей Telegram update без протаскивания Any в str()."""
    if value is None:
        return ""
    return str(value)


def normalize_phone(raw: str) -> str | None:
    """Accept 10-digit Russian mobiles, 8/7 Russian prefixes, or E.164-like numbers."""
    raw = raw.strip()
    if not re.fullmatch(r"\+?[\d\s()\-]+", raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10 and digits.startswith("9"):
        return "+7" + digits
    if len(digits) == 11 and digits[0] in "78" and digits[1] == "9":
        return "+7" + digits[1:]
    if raw.startswith("+") and 10 <= len(digits) <= 15 and digits[0] != "0":
        return "+" + digits
    return None


class TelegramAPI:
    """Минимальный клиент Bot API без зависимостей приложения."""

    def __init__(self, token: str):
        self._base = "https://api.telegram.org/bot" + token + "/"

    def call(self, method: str, **fields: Any) -> Any:
        """POST method Bot API. Raises RuntimeError on transport or ok=false."""
        values = {
            key: json.dumps(value, ensure_ascii=False)
            if isinstance(value, (list, dict))
            else str(value)
            for key, value in fields.items()
        }
        request = urllib.request.Request(
            self._base + method,
            data=urllib.parse.urlencode(values).encode("utf-8"),
            method="POST",
        )
        # API responses may contain user data: never log payloads.
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError("Telegram transport failure") from None
        if not result.get("ok"):
            raise RuntimeError(f"Telegram {method} rejected request")
        return result.get("result")


class MaintenanceBot:
    """Один long-poll consumer: экран обслуживания и заявка с телефоном."""

    def __init__(self, api: TelegramAPI, admin_chat_id: int):
        self.api = api
        self.admin_chat_id = admin_chat_id
        self.stopping = False

    def send(
        self, chat_id: int, text: str, *, keyboard: dict[str, Any] | None = None
    ) -> None:
        """Отправить сообщение. Ошибка доставки пробрасывается вызывающему."""
        fields: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if keyboard is not None:
            fields["reply_markup"] = keyboard
        self.api.call("sendMessage", **fields)

    def handle(self, update: dict[str, Any]) -> None:
        """Обработать одно обновление. Заявку подтверждает только доставка Owner."""
        callback = update.get("callback_query")
        if callback:
            self.api.call(
                "answerCallbackQuery",
                callback_query_id=callback["id"],
                text="Функция временно недоступна",
            )
            self.send(int(callback["from"]["id"]), TEXT, keyboard=MAIN_KEYBOARD)
            return

        message = update.get("message")
        if not message or message.get("chat", {}).get("type") != "private":
            return
        user_raw = cast(object, message.get("from"))
        user: dict[str, Any] = (
            cast(dict[str, Any], user_raw) if isinstance(user_raw, dict) else {}
        )
        chat_id = int(message["chat"]["id"])
        if not user.get("id"):
            return
        content = str(message.get("text") or "").strip()
        if content == CTA:
            self.send(
                chat_id,
                "Укажите ваш номер телефона, чтобы мы могли связаться с вами. "
                "Нажмите кнопку ниже или отправьте номер сообщением.",
                keyboard=PHONE_KEYBOARD,
            )
            return

        phone: str | None = None
        contact = message.get("contact")
        if contact:
            # A forwarded/third-party contact is not proof of the user's phone.
            if contact.get("user_id") != user["id"]:
                self.send(
                    chat_id,
                    "Отправьте свой номер кнопкой ниже или введите его вручную.",
                    keyboard=PHONE_KEYBOARD,
                )
                return
            phone = normalize_phone(str(contact.get("phone_number", "")))
        elif content and not content.startswith("/"):
            phone = normalize_phone(content)

        if not phone:
            # Любая slash-команда, включая deep-link «/start payload», — экран
            # обслуживания, а не попытка ввести телефон.
            attempted_phone = bool(contact) or (
                bool(content) and not content.startswith("/")
            )
            if attempted_phone:
                self.send(
                    chat_id,
                    "Номер не распознан. Нажмите «Поделиться номером» "
                    "или введите телефон в международном формате (+79991234567).",
                    keyboard=PHONE_KEYBOARD,
                )
            else:
                self.send(chat_id, TEXT, keyboard=MAIN_KEYBOARD)
            return

        display_name = (
            " ".join(
                _as_str(cast(object, user.get(key)))
                for key in ("first_name", "last_name")
            ).strip()
            or "не указано"
        )
        raw_username = cast(object, user.get("username"))
        username = "@" + _as_str(raw_username) if raw_username else "не указан"
        created = datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")
        notice = (
            f"📩 Новая заявка WB Sky\nИмя: {display_name}\n"
            f"Телефон: {phone}\nTelegram: {username}\n"
            f"Telegram ID: {user['id']}\nДата: {created}\n"
            f"Update ID: {update.get('update_id', '—')}"
        )
        # A lead is NEVER acknowledged unless admin delivery succeeded.
        self.send(self.admin_chat_id, notice)
        try:
            self.send(
                chat_id,
                "✅ Заявка принята. Мы свяжемся с вами для инструктажа и перенастройки.",
                keyboard=MAIN_KEYBOARD,
            )
        except RuntimeError:
            LOG.warning("Lead delivered to admin; user acknowledgement failed")

    def run(self) -> None:
        """Снять webhook и держать единственный long poll до SIGTERM."""
        self.api.call("deleteWebhook", drop_pending_updates=False)
        offset: int | None = None
        while not self.stopping:
            try:
                kwargs: dict[str, Any] = {
                    "timeout": 25,
                    "allowed_updates": ["message", "callback_query"],
                }
                if offset is not None:
                    kwargs["offset"] = offset
                updates = self.api.call("getUpdates", **kwargs)
                for update in updates:
                    self.handle(update)
                    offset = int(update["update_id"]) + 1
            except Exception as exc:  # noqa: BLE001 — poll must survive one bad update
                LOG.warning("Poll/update failed: %s", type(exc).__name__)
                if not self.stopping:
                    time.sleep(5)


def main() -> None:
    """Точка входа: токен, Owner id из const.py, один polling-цикл."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    if apply_legacy_proxy():
        LOG.info("Using existing PROXY for Telegram transport")
    token = os.getenv("CLIENT_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Missing CLIENT_BOT_TOKEN/TELEGRAM_BOT_TOKEN")
    try:
        admin_chat_id = owner_admin_chat_id()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    bot = MaintenanceBot(TelegramAPI(token), admin_chat_id)

    def _request_stop(_signum: int, _frame: FrameType | None) -> None:
        bot.stopping = True

    _ = signal.signal(signal.SIGTERM, _request_stop)
    _ = signal.signal(signal.SIGINT, _request_stop)
    bot.run()


if __name__ == "__main__":
    main()
