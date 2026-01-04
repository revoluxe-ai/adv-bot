import os
from pathlib import Path

import aiofiles
import yaml
from typing import Any


def get_document_by_key_name(file_path: str, key_name: str) -> Any:
    with open(file_path, encoding="utf8") as file:
        doc = yaml.load_all(file, Loader=yaml.FullLoader)
        for dict_ in doc:
            if key_name in dict_:
                return dict_[key_name]
    raise Exception(f"Ключ {key_name} не найден в файле {file_path}")


async def get_document_by_key_name_async(file_path: str, key_name: str) -> Any:
    async with aiofiles.open(file_path, encoding="utf8") as file:
        content = await file.read()
    doc = yaml.load_all(content, Loader=yaml.FullLoader)
    for dict_ in doc:
        if key_name in dict_:
            return dict_[key_name]
    raise Exception(f"Ключ {key_name} не найден в файле {file_path}")


def find_project_root(
    start: Path,
    marker_filename: str = "project_root.marker",
) -> Path:
    """
    Ищет корневую директорию проекта, содержащую файл-маркер.
    """
    current_path = start.resolve()

    for parent in (current_path, *current_path.parents):
        if (parent / marker_filename).is_file():
            return parent

    raise FileNotFoundError(
        f"Marker file '{marker_filename}' not found starting from {start}"
    )


def get_setting_path() -> str:
    # Получить абсолютный путь к текущему скрипту
    # current_script_path = os.path.abspath(__file__)
    # # Путь к файлу данных относительно текущего скрипта
    # current_path = os.path.dirname(current_script_path)
    # data_file_path = os.path.join(current_path, 'setting.yaml')
    root_path = find_project_root(Path(__file__).resolve().parent)
    return os.path.join(root_path, "setting.yaml")


async def get_alchemy_row_async() -> str:
    file_path: str = get_setting_path()
    postgres_dbname: Any = await get_document_by_key_name_async(
        file_path, "postgres-dbname"
    )
    postgres_host: Any = await get_document_by_key_name(file_path, "postgres-host")
    postgres_password: Any = await get_document_by_key_name(
        file_path, "postgres-password"
    )
    postgres_user: Any = await get_document_by_key_name(file_path, "postgres-user")
    db_connector: str = (
        f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:5432/{postgres_dbname}"
    )
    return db_connector
