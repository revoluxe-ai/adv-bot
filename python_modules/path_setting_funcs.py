import aiofiles
import yaml
import os

def get_document_by_key_name(file_path, key_name):
    with open(file_path, 'r', encoding='utf8') as file:
        doc = yaml.load_all(file, Loader=yaml.FullLoader)
        for dict_ in doc:
            if key_name in dict_:
                return dict_[key_name]
    raise Exception(f'Ключ {key_name} не найден в файле {file_path}')




async def get_document_by_key_name_async(file_path, key_name):
    async with aiofiles.open(file_path, 'r', encoding='utf8') as file:
        content = await file.read()
    doc = yaml.load_all(content, Loader=yaml.FullLoader)
    for dict_ in doc:
        if key_name in dict_:
            return dict_[key_name]
    raise Exception(f'Ключ {key_name} не найден в файле {file_path}')




def get_setting_path():
    # Получить абсолютный путь к текущему скрипту
    # current_script_path = os.path.abspath(__file__)
    # # Путь к файлу данных относительно текущего скрипта
    # current_path = os.path.dirname(current_script_path)
    # data_file_path = os.path.join(current_path, 'setting.yaml')
    return 'setting.yaml'



def get_alchemy_row():
    file_path = get_setting_path()
    postgres_dbname = get_document_by_key_name(file_path, 'postgres-dbname')
    postgres_host = get_document_by_key_name(file_path, 'postgres-host')
    postgres_password = get_document_by_key_name(file_path, 'postgres-password')
    postgres_user = get_document_by_key_name(file_path, 'postgres-user')
    db_connector = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:5432/{postgres_dbname}'
    return db_connector



async def get_alchemy_row_async():
    file_path = get_setting_path()
    postgres_dbname = await get_document_by_key_name_async(file_path, 'postgres-dbname')
    postgres_host = await get_document_by_key_name(file_path, 'postgres-host')
    postgres_password = await get_document_by_key_name(file_path, 'postgres-password')
    postgres_user = await get_document_by_key_name(file_path, 'postgres-user')
    db_connector = f'postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:5432/{postgres_dbname}'
    return db_connector



