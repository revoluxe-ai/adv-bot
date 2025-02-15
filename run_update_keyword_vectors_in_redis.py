from app.utils.NeoDataScience.driver import DataScience
import asyncio



gds = DataScience()



if __name__ == '__main__':
    asyncio.run(gds.update_vectors_in_redis())