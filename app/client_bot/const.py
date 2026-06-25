from app.settings.settings_master import settings

PRICE_PER_MONTH = 4500
EMAIL_FOR_PAYMENT_RECEIPT = "revoluxe@gmail.com"

CLIENT_BOT_LINK = "https://t.me/wb_adv_master_bot/"

TELEGRAM_TEXT_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024
MAX_MESSAGE_LENGTH = TELEGRAM_TEXT_MESSAGE_LIMIT

MAX_TOKENS = 2

SUPPORT_CHANNEL_ID = -1002006645663
SUPPORT_CHANNEL_URL = "t.me/skyline_project"

#
# Статус коды ключевых слов
#

BLACK_LIST = 0

AUTO_MODE = 1

WHITE_LIST = 2

TURN_OFF = 3

ALWAYS_ON = 4  # фикс.фразы (всегда вкл)

PARSING_PRICE = 15

AUTO_BIDDER_PRICE = 25

MIN_CPM = 100

_BASE_ADMINS = [
    373435337,  # я
    707068503,  # Лена
    5401359037,  # Рома
]

ADMINS = _BASE_ADMINS + list(settings.extra_admin_telegram_ids)

DEFAULT_BIDDER_STEP = 2

min_sum = settings.MIN_SUM

MIN_SUM = min_sum

GATE_ENTRY_AMOUNT = MIN_SUM  # Default entry amount for the gate

OFFERTA_URL = (
    "https://docs.google.com/document/d/1SK9ixZO1LD3yc_-rzkE5K_uOG5qWNCO-4RwGd1fq24A/edit?usp=sharing"
)

PRICE_LINK = 'https://telegra.ph/Tarify-Servisa-Gorizont-Avtomatizaciya-vnutrennej-reklamy-WB-02-06'

SUPPORT_LINK = "https://t.me/sky_manager_1"
SUPPORT_USER_NAME = "sky_manager_1"  # username для лички (без @)

# Получатель уведомлений о заявке на презентацию (главный менеджер @sky_manager_1).
# Переопределение: PRESENTATION_NOTIFY_TELEGRAM_ID в окружении.
MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID = 373435337
PARTNER_PAYOUT_REQUEST_URL = SUPPORT_LINK
