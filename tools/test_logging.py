from app import settings
from python_modules.logger import _normalize_log_level, setup_logging
import logging

print("raw LOG_LEVEL:", repr(settings.LOG_LEVEL))
print("normalized:", _normalize_log_level(settings.LOG_LEVEL))

setup_logging()

logging.debug("this is debug")
logging.info("this is info")
logging.warning("this is warning")
logging.error("this is error")
