import asyncio
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db.session_maker import get_async_session_maker


async def main() -> None:
    async with get_async_session_maker(read_only=False) as s:  # type: AsyncSession
        res = await s.execute(text("SELECT version();"))
        print(res.scalar_one())


if __name__ == "__main__":
    asyncio.run(main())
