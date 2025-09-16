import dotenv

dotenv.load_dotenv()
import asyncio

from app.modules.payment_compensation import main

if __name__ == "__main__":
    asyncio.run(main())
