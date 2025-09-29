import asyncio
import logging
from pathlib import Path
from typing import Any

import aiofiles
import joblib

logger = logging.getLogger(__name__)

# Путь к pipeline модели
_MODEL_DIR = Path(__file__).parent / "model"  # predict_ctr_service/model/model
JOBLIB_PATH = _MODEL_DIR / "model.joblib"


def load_model(path: str) -> Any:
    """Загружает XGBRegressor модель из joblib файла."""
    logger.debug(f"Загрузка модели из {path}")

    if not Path(path).exists():
        raise FileNotFoundError(f"Файл модели не найден: {path}")

    try:
        model = joblib.load(str(path))
        logger.info(f"Модель успешно загружена из {path}")
        return model
    except Exception as e:
        logger.error(f"Ошибка загрузки модели из {path}: {e}")
        raise e


async def save_model(model: Any, time_stamp: str | None = None) -> None:
    """Сохраняет XGBRegressor модель в joblib."""
    JOBLIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(joblib.dump, model, str(JOBLIB_PATH))
    logger.info(f"Модель сохранена в {JOBLIB_PATH}")

    if time_stamp:
        timestamp_path = JOBLIB_PATH.parent / "time_stamp.txt"
        async with aiofiles.open(timestamp_path, "w") as file:
            await file.write(time_stamp)
        logger.debug(f"Временная метка сохранена в {timestamp_path}")


def save_model_sync(model: Any, time_stamp: str | None = None) -> None:
    """Синхронная оболочка при необходимости (не используется в legacy сервисе напрямую)."""
    asyncio.run(save_model(model, time_stamp))
