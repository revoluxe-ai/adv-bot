from app import KeywordUpdateRunner, client_bot
import asyncio
from threading import Thread

async def main_loop():
    await asyncio.gather(
        KeywordUpdateRunner().run(False),
        client_bot.run()
    )



def run_all():
    asyncio.run(main_loop())



if __name__ == '__main__':
    run_all()
