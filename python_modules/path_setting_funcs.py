import os

import aiofiles
import yaml


def get_document_by_key_name(file_path, key_name):
    with open(file_path, encoding='utf8') as file:
        doc = yaml.load_all(file, Loader=yaml.FullLoader)
        for dict_ in doc:
            if key_name in dict_:
                return dict_[key_name]
    raise Exception(f'Ключ {key_name} не найден в файле {file_path}')




async def get_document_by_key_name_async(file_path, key_name):
    async with aiofiles.open(file_path, encoding='utf8') as file:
        content = await file.read()
    doc = yaml.load_all(content, Loader=yaml.FullLoader)
    for dict_ in doc:
        if key_name in dict_:
            return dict_[key_name]
    raise Exception(f'Ключ {key_name} не найден в файле {file_path}')
def find_project_root(marker_filename='project_root.marker'):
    """
    Ищет корневую директорию проекта, содержащую файл-метку.
    Возвращает путь к корневой директории проекта.
    """
    current_path = os.path.abspath(os.path.dirname(__file__))
    while True:
        marker_path = os.path.join(current_path, marker_filename)
        if os.path.isfile(marker_path):
            return current_path
        new_path = os.path.abspath(os.path.join(current_path, '..'))
        if new_path == current_path:
            raise FileNotFoundError(f"Marker file '{marker_filename}' not found in any parent directory")
        current_path = new_path



def get_setting_path():
    # Получить абсолютный путь к текущему скрипту
    # current_script_path = os.path.abspath(__file__)
    # # Путь к файлу данных относительно текущего скрипта
    # current_path = os.path.dirname(current_script_path)
    # data_file_path = os.path.join(current_path, 'setting.yaml')
    root_path = find_project_root()
    return os.path.join(root_path,'setting.yaml')



async def get_alchemy_row_async():
    file_path = get_setting_path()
    postgres_dbname = await get_document_by_key_name_async(file_path, 'postgres-dbname')
    postgres_host = await get_document_by_key_name(file_path, 'postgres-host')
    postgres_password = await get_document_by_key_name(file_path, 'postgres-password')
    postgres_user = await get_document_by_key_name(file_path, 'postgres-user')
    db_connector = f'postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:5432/{postgres_dbname}'
    return db_connector



