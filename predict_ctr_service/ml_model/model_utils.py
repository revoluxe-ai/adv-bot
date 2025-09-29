import asyncio
import logging
from pathlib import Path

import aiofiles
import joblib
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)

# Путь к pipeline модели
_MODEL_DIR = Path(__file__).parent / "model"  # predict_ctr_service/model/model
JOBLIB_PATH = _MODEL_DIR / "model.joblib"


async def load_model() -> joblib.Booster:
    """Загружает XGBRegressor модель из joblib файла."""
    logger.debug(f"Загрузка модели из {JOBLIB_PATH}")

    if not JOBLIB_PATH.exists():
        raise FileNotFoundError(f"Файл модели не найден: {JOBLIB_PATH}")

    try:
        model = await asyncio.to_thread(joblib.load, str(JOBLIB_PATH))
        logger.info(f"XGBRegressor модель успешно загружена из {JOBLIB_PATH}")
        return model
    except Exception as e:
        logger.error(f"Ошибка загрузки модели из {JOBLIB_PATH}: {e}")
        raise e


async def save_model(model: XGBRegressor, time_stamp: str | None = None) -> None:
    """Сохраняет XGBRegressor модель в joblib."""
    JOBLIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(joblib.dump, model, str(JOBLIB_PATH))
    logger.info(f"Модель сохранена в {JOBLIB_PATH}")

    if time_stamp:
        timestamp_path = JOBLIB_PATH.parent / "time_stamp.txt"
        async with aiofiles.open(timestamp_path, "w") as file:
            await file.write(time_stamp)
        logger.debug(f"Временная метка сохранена в {timestamp_path}")
