import contextvars
import typing


class UniversalTokenManager:
    """
    Универсальный менеджер токенов WB для разных разделов и магазинов.
    Хранит токены в ContextVar с ключом (section, shop_id).
    Предполагает, что токен — объект с полем api_key.
    """
    _tokens_ctx: contextvars.ContextVar = contextvars.ContextVar("universal_tokens_ctx", default={})

    @classmethod
    async def get_tokens(
            cls,
            section: str,
            shop_id: str,
            fetch_tokens_func: typing.Callable[[str], typing.Awaitable[typing.List]],
    ) -> typing.List:
        ctx = cls._tokens_ctx.get()
        key = (section, shop_id)
        if key in ctx:
            return ctx[key]
        tokens = await fetch_tokens_func(shop_id)
        ctx[key] = tokens
        cls._tokens_ctx.set(ctx)
        return tokens

    @classmethod
    async def mark_token_invalid(
            cls,
            section: str,
            shop_id: str,
            token,
    ):
        ctx = cls._tokens_ctx.get()
        key = (section, shop_id)
        tokens = ctx.get(key, [])
        tokens = [t for t in tokens if getattr(t, 'api_key', None) != getattr(token, 'api_key', None)]
        ctx[key] = tokens
        cls._tokens_ctx.set(ctx)

    @classmethod
    async def refresh_tokens(
            cls,
            section: str,
            shop_id: str,
            fetch_tokens_func: typing.Callable[[str], typing.Awaitable[typing.List]],
    ) -> typing.List:
        tokens = await fetch_tokens_func(shop_id)
        ctx = cls._tokens_ctx.get()
        key = (section, shop_id)
        ctx[key] = tokens
        cls._tokens_ctx.set(ctx)
        return tokens

    @classmethod
    async def get_token(
            cls,
            section: str,
            shop_id: str,
            fetch_tokens_func: typing.Callable[[str], typing.Awaitable[typing.List]],
    ) -> typing.Any:
        tokens = await cls.get_tokens(section, shop_id, fetch_tokens_func)
        if not tokens:
            return None
        # Здесь можно реализовать более сложную логику выбора токена
        return tokens[0]
