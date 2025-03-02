
async def check_all():
    from .shop_subscribes import manager
    await manager.check_all()
