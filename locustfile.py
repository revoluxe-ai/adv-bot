from locust import HttpUser, between, task

key = '89779uoiugkftyeoilyeligoyuv'


class TelegramBotUser(HttpUser):
    host = 'https://tiriel.ru'
    wait_time = between(1, 5)  # Пользователи будут отправлять запрос каждые 1-5 секунд

    @task
    def send_message(self):
        headers = {'X-Telegram-Bot-Api-Secret-Token': '89779uoiugkftyeoilyeligoyuv'}
        self.client.post(f"/telegram_webhook", json={
            "update_id": 123456789,
            "message": {
                "message_id": 123,
                "from": {
                    "id": 373435337,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": 373435337,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1441645532,
                "text": "/start",
            }
        },
                         headers=headers
                         )
