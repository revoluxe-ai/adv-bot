import json
import aiofiles
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import asyncio
from app.utils.db.models import AdvKeyword, AdvSetting
from get_keyword_statistic import async_session_maker
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.ext.compiler import compiles
class json_array_length(FunctionElement):
    name = 'json_array_len'

@compiles(json_array_length)
def compile(element, compiler, **kw):
    return "json_array_length(%s)" % compiler.process(element.clauses)



sm = async_session_maker()


async def get_keyword_json() -> dict:
    # Запрос для получения всех активных настроек (AdvSetting) вместе с их ключевыми словами (AdvKeyword)
    stmt = select(AdvSetting).options(selectinload(AdvSetting.adv_keywords)).where(AdvSetting.bot_active == True)
    async with sm as session:
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.scalars().all() # Получаем все результаты запроса
        adv_data = {}
        for adv_setting in adv_settings:
            adv_data['nmid'] = adv_setting.nmids[0]
            adv_data['keywords'] = [keyword.text for keyword in adv_setting.adv_keywords]
            data = []
            data.append(adv_data)
            break

    # Преобразуем данные в формат JSON
    json_data = json.dumps(data, ensure_ascii=False, indent=4)

    # Записываем JSON данные в файл
    async with aiofiles.open('keyword.json', 'w', encoding='utf-8') as file:
        await file.write(json_data)


# Запуск асинхронной функции
if __name__ == '__main__':
    asyncio.run(get_keyword_json())