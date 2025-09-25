import pytest

from app.core.mp.wb.tokens.token_manager import TokenManager, TokenManagerFactory


@pytest.mark.asyncio
async def test_token_rotation_and_mark_invalid():
    tm = TokenManager(shop_id="shop1", tokens=["t1", "t2", "t3"])

    # initial token should be t1
    t = await tm.get_token("promotion")
    assert t == "t1"

    # mark current invalid -> should rotate to t2
    tm.mark_invalid("promotion")
    t = await tm.get_token("promotion")
    assert t == "t2"

    # mark t2 invalid by explicit token -> rotate to t3
    tm.mark_invalid("promotion", token="t2")
    t = await tm.get_token("promotion")
    assert t == "t3"

    # mark remaining tokens invalid -> expect RuntimeError on get
    tm.mark_invalid("promotion", token="t1")
    tm.mark_invalid("promotion", token="t3")
    with pytest.raises(RuntimeError):
        await tm.get_token("promotion")


def test_token_manager_factory_cache():
    f = TokenManagerFactory()
    m1 = f.get_manager("shopA")
    m2 = f.get_manager("shopA")
    assert m1 is m2


