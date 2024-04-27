import asyncio
import platform

from selenium import webdriver
from selenium.webdriver.chrome.service import Service


async def get_selenium():
    chrome_driver_path = 'D:/chrome_driver/chromedriver.exe'
    chrome_binary_path = None

    chrome_options = webdriver.ChromeOptions()

    if platform.system() != 'Windows':
        chrome_options.add_argument("--headless")  # Запуск в безголовом режиме
        # Обход проблемы с безопасностью
        chrome_options.add_argument("--no-sandbox")
        # Отключение использования /dev/shm
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Указание виртуального дисплея
        chrome_options.add_argument("--display=:99")

    if chrome_binary_path:
        chrome_options.binary_location = chrome_binary_path
    service = Service(chrome_driver_path)
    driver = await asyncio.to_thread(lambda: webdriver.Chrome(service=service,
                                                                       options=chrome_options))
    return driver
