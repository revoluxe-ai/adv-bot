# set_shop_id_for_all_wbtokens.py
# Добавляем настройку пути к корню проекта
try:
    # Пытаемся импортировать напрямую, если скрипт запускается из директории scripts
    from set_path import add_project_root_to_path
except ImportError:
    # Если не получается, пробуем импортировать с использованием полного пути
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv

dotenv.load_dotenv()
from sqlalchemy import select

# Импортируем исключение для обработки ошибки невалидного токена
from app.core.wb_api.exceptions import NotValidTokenError
from app.modules.common_slaves.wildberries.models import WBToken
from app.utils.db.session_maker import get_async_session_maker as sm


async def set_shop_id_for_all_wbtokens():
    """
    Устанавливает shop_id для всех токенов WB, которые его не имеют.
    """
    tokens_processed = 0
    tokens_updated = 0
    tokens_invalid = 0

    async with sm() as session:
        stmt = select(WBToken)
        result = await session.execute(stmt)
        wb_tokens: list[WBToken] = result.scalars().all()
        print(f"Найдено токенов: {len(wb_tokens)}")

        for token in wb_tokens:
            tokens_processed += 1
            if token.shop_id:
                continue
            try:
                shop_id = token.get_shop_id_from_token()
                token.shop_id = shop_id
                await session.commit()
                tokens_updated += 1
                print(f"Обновлен токен: {token.id}, shop_id: {shop_id}")
            except NotValidTokenError:
                tokens_invalid += 1
                print(f"Невалидный токен: {token.id}")
                continue
            except Exception as e:
                print(f"Ошибка при обработке токена {token.id}: {e}")
                continue

    print("\nИтоги:")
    print(f"Обработано токенов: {tokens_processed}")
    print(f"Обновлено токенов: {tokens_updated}")
    print(f"Невалидных токенов: {tokens_invalid}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(set_shop_id_for_all_wbtokens())
