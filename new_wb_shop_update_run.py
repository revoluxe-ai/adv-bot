import dotenv
dotenv.load_dotenv()
from app.modules.shop_runner import run_process_func
from python_modules.logger import setup_logging

setup_logging()

if __name__ == '__main__':
    run_process_func.run()