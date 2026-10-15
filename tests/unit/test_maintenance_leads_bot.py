"""Offline regression tests. No network access or production API writes."""
import unittest

from maintenance_leads_bot import MaintenanceBot, normalize_phone


class FakeAPI:
    def __init__(self, fail_admin=False):
        self.calls = []
        self.fail_admin = fail_admin

    def call(self, method, **kwargs):
        if method == "sendMessage" and self.fail_admin and kwargs["chat_id"] == 9911:
            raise RuntimeError("admin unavailable")
        self.calls.append((method, kwargs))
        return True


def message_update(text=None, contact=None, chat_type="private"):
    m = {
        "chat": {"id": 123, "type": chat_type},
        "from": {"id": 123, "first_name": "Тест", "username": "seller"},
    }
    if text is not None:
        m["text"] = text
    if contact is not None:
        m["contact"] = contact
    return {"update_id": 77, "message": m}


class MaintenanceTests(unittest.TestCase):
    def test_phone_validation(self):
        self.assertEqual(normalize_phone("8 (999) 123-45-67"), "+79991234567")
        self.assertEqual(normalize_phone("9991234567"), "+79991234567")
        self.assertEqual(normalize_phone("+41 79 123 45 67"), "+41791234567")
        self.assertIsNone(normalize_phone("+7 abc123"))
        self.assertIsNone(normalize_phone("123"))

    def test_start_and_cta_never_create_lead(self):
        api = FakeAPI()
        bot = MaintenanceBot(api, 9911)
        bot.handle(message_update("/start"))
        bot.handle(message_update("📩 Оставить заявку"))
        self.assertEqual(
            [kwargs["chat_id"] for m, kwargs in api.calls if m == "sendMessage"],
            [123, 123],
        )
        self.assertTrue(
            api.calls[-1][1]["reply_markup"]["keyboard"][0][0]["request_contact"]
        )

    def test_valid_phone_admin_receives_first(self):
        api = FakeAPI()
        bot = MaintenanceBot(api, 9911)
        bot.handle(message_update("+7 (999) 123-45-67"))
        self.assertEqual([kwargs["chat_id"] for _, kwargs in api.calls], [9911, 123])
        self.assertIn("+79991234567", api.calls[0][1]["text"])
        self.assertIn("Update ID: 77", api.calls[0][1]["text"])

    def test_valid_self_contact(self):
        api = FakeAPI()
        MaintenanceBot(api, 9911).handle(
            message_update(contact={"user_id": 123, "phone_number": "89991234567"})
        )
        self.assertEqual(api.calls[0][1]["chat_id"], 9911)

    def test_third_party_contact_rejected(self):
        api = FakeAPI()
        MaintenanceBot(api, 9911).handle(
            message_update(contact={"user_id": 999, "phone_number": "89991234567"})
        )
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0][1]["chat_id"], 123)

    def test_no_success_if_admin_delivery_fails(self):
        api = FakeAPI(fail_admin=True)
        with self.assertRaises(RuntimeError):
            MaintenanceBot(api, 9911).handle(message_update("+79991234567"))
        self.assertEqual(api.calls, [])

    def test_ignore_group_messages(self):
        api = FakeAPI()
        MaintenanceBot(api, 9911).handle(
            message_update("+79991234567", chat_type="group")
        )
        self.assertEqual(api.calls, [])


if __name__ == "__main__":
    unittest.main()
