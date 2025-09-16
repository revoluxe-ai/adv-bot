import sys

if sys.platform != "win32":
    import uvloop

    uvloop.install()


async def run() -> None:
    while True:
        try:
            await app.run()
        except AdvBotMainLoopCriticalError:
            logge
