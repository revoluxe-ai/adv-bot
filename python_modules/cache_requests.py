import os
import pickle
import requests
from datetime import datetime, timedelta
from hashlib import md5
from time import sleep
from json import JSONDecodeError
import logging

logger = logging.getLogger(__name__)



class ApiException(Exception):
    def __init__(self, message: str, method: str, server_response_code:int):
        super().__init__(message)
        self._message = message
        self._method = method
        self._server_code = server_response_code

    def __str__(self):
        return (f"""Код ответа: {self._server_code}, тело ответа: {self._message}, 
               метод: {self._method}
                """)





class CachedRequests:
    def __init__(self):
        module_dir = os.path.dirname(__file__)
        self.cache_dir = os.path.join(module_dir, 'requests_cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache_path(self, method, url, data):
        key = f"{method}_{url}_{data}"
        file_name = f"{md5(key.encode('utf-8')).hexdigest()}.pkl"
        return os.path.join(self.cache_dir, file_name)

    def _get_timestamp_path(self, url):
        url = url.split('?')[0]
        file_name = f"{md5(url.encode('utf-8')).hexdigest()}_timestamp.pkl"
        return os.path.join(self.cache_dir, file_name)

    def _is_cache_valid(self, cache_path, expire_after):
        if not os.path.exists(cache_path):
            return False
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - cache_time < expire_after

    def _is_time_sleep_valid(self, timestamp_path, time_sleep):
        # Проверяем, прошло ли достаточно времени с последнего запроса
        if not os.path.exists(timestamp_path) or time_sleep is None:
            return True
        with open(timestamp_path, 'rb') as f:
            last_request_time = pickle.load(f)
        return datetime.now() - last_request_time >= timedelta(seconds=time_sleep)

    def request(self, method, url, json_data, headers, time_sleep,
                expire_after: timedelta = timedelta(minutes=1)):
        serialized_data = pickle.dumps(json_data) if json_data else b''
        cache_path = self._get_cache_path(method, url, serialized_data)
        timestamp_path = self._get_timestamp_path(url)

        if self._is_cache_valid(cache_path, expire_after) and self._is_time_sleep_valid(timestamp_path, time_sleep):
            with open(cache_path, 'rb') as cache_file:
                response_data = pickle.load(cache_file)
        else:
            if not self._is_time_sleep_valid(timestamp_path, time_sleep):
                logger.debug(f'Плановая пауза между запросами: {time_sleep}')
                sleep(time_sleep)

            while True:
                 response = requests.request(method, url, json=json_data,
                                        headers=headers)
                 if response.text == '':
                     return None
                 try:
                     response_data = response.json()
                 except JSONDecodeError:
                     raise ApiException(f"Ошибка парсинга json. "
                                        f"text ответа: {response.text},"
                                        f"пауза между запросами: {round(time_sleep, 2)} сек.",
                                        url.split('?')[0],
                                        response.status_code)
                 if isinstance(response_data, dict):
                     if response_data.get('code') == 429:
                         logger.error(f'Много запросов, пауза, {time_sleep}')
                         sleep(time_sleep)
                         continue
                 break

            with open(cache_path, 'wb') as cache_file:
                pickle.dump(response_data, cache_file)
            with open(timestamp_path, 'wb') as f:
                pickle.dump(datetime.now(), f)

        return response_data
