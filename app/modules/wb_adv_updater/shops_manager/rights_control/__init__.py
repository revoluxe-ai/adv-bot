from .shop_subscribes import manager


async def check_all():
    await manager.check_all()
