
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .tools import get_selenium


class SeleniumMaster:
    async def __aenter__(self):

        self._selenium_driver = await get_selenium()

        return self

    async  def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:  # Если возникло исключение
            logger.error (f"Exception handled: {exc_val}")  # Обрабатываем исключение
        self._selenium_driver.quit()

    async def get_image_url(self, nmid):
        driver = self._selenium_driver
        url = f'https://www.wildberries.ru/catalog/{nmid}/detail.aspx?targetUrl=WR'
        driver.get(url)

        wait = WebDriverWait(driver,10)
        try:
            element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "photo-zoom__preview")))
        except TimeoutException:
            try:
                element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "content404")))
            except:
                Exception('Неизвестная ошибка!!! Проверить')

        url = driver.find_elements(By.CLASS_NAME, "photo-zoom__preview")[0].get_attribute('src')

        return url


