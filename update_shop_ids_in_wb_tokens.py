from app.core.wb_api.exceptions import NotValidTokenError
from app.modules.common_slaves.wildberries.models import WBToken
from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select, delete


async def update_shop_ids_in_wb_tokens() -> None:
    async with sm() as session:
        stmt = select(WBToken)
        result = await session.execute(stmt)
        tokens: list[WBToken] = result.scalars().all()

        for token in tokens:
            shop_id = token.shop_id
            if shop_id:
                print(f"Token {token.api_key} already has shop_id {shop_id}")
                continue
            try:
                shop_id = token.get_shop_id_from_token()
                token.shop_id = shop_id
            except NotValidTokenError:
                print(f"Token {token.api_key} is not valid")
                session.delete(token)
                continue
            finally:
                print(f"Token {token.api_key} shop_id updated to {token.shop_id}")
                await session.commit()


if __name__ == '__main__':
    import asyncio
    asyncio.run(update_shop_ids_in_wb_tokens())


