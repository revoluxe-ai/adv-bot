from locust import HttpUser, task, between


from python_modules import path_setting_funcs


setting_path = path_setting_funcs.get_setting_path()

key =


class TelegramBotUser(HttpUser):
    wait_time = between(1, 5)  # Пользователи будут отправлять запрос каждые 1-5 секунд

    @task
    def send_message(self):
        self.client.post("'https://tiriel.ru/telegram_webhook?key=", json={
            "update_id": 123456789,
            "message": {
                "message_id": 123,
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": 123456789,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1441645532,
                "text": "/start",
            }
        })