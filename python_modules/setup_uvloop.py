import asyncio
import platform

def setup_uvloop() -> None:
    """Настройка uvloop для Linux систем"""
    system = platform.system()
    if system == "Linux":
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return None
