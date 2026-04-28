import pytest

from app.modules.common_slaves.wildberries.models import WBToken

pytestmark = pytest.mark.unit


# Токены из файла CSV пользователя. Валидным считается только первый.
TOKENS = [
    # (token, is_expected_valid)
    (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjkwODNmNDU2LWJiZGEtNDczOS1hMGYxLTMwMzRiZDhjMDczNCIsInMiOjEwMiwic2lkIjoiOTRhM2YwY2QtOGFjMS00Mjk2LTliNmUtYmE4NmNiNTQ2NGNiIiwiZXhwIjoyMDExODMwMzIwLCJhY2MiOjEsInQiOmZhbHNlfQ.QeUqgoxsjJEWrJpdsFxLOsqa15EBfGkNZwf690qlUko",
        True,
    ),
    (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjA4NTI5ZThkLTYwODAtNDA0ZC05NjM2LTBjZmU4YzM0NDAwNyIsInMiOjEwNzM3NDE5MjYsInNpZCI6ImUyYWUzMmM3LTM4ODYtNDA1Mi1iNzc2LTE3NGFmMTczYjY4MyIsImV4cCI6MTc2Mzg0MTc5OSwiYWNjIjoxLCJ0IjpmYWxzZX0.y-paYj698-YI_IpoExYuws8Q5YU9zbdmdSAe96EtSBA",
        False,
    ),
    (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjkxY2YxZGExLTc3MDQtNDU1Ny1iMGRkLWUzN2Y1Y2M1NjM2NyIsInMiOjcwLCJzaWQiOiJkMDk3MDlhOC1jOTMyLTRjYTktOWE2My01NGNmMzg3ZGIwNDEiLCJleHAiOjE3NjM4NDE3OTksImFjY2I6MSwidCI6ZmFsc2V9.uwA4BD79C4Zvq40_9SIof60KrIs79xLxC6IyRSC6ce4",
        False,
    ),
    (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImU3NjFmZmNkLTczZWItNDQwNi04ZjViLTJjOTVjNjVjYTRiMSIsInMiOjEwMiwic2lkIjoiM2MxMTRhNGItZTUxOC00YWYwLTgzYjctOWY1Nzc5ZmNhNjVjIiwiZXhwIjoxNzYxMTYzMzk5LCJhY2MiOjEsInQiOmZhbHNlfQ.g_CLlPsuiiRvFzA0T-xCsKuBnDCkkaoF9XrMank_m20",
        False,
    ),
]


@pytest.mark.parametrize("token, expected", TOKENS)
def test_token_validity_simple(token: str, expected: bool) -> None:
    t = WBToken(api_key=token)
    # Критерий валидности: корректный JWT, не read_only, не просрочен, и есть право "Статистика"
    is_valid = (
        t.check_valid()
        and (not t.read_only)
        and (not t.is_expired)
        and ("Статистика" in t.categories)
    )
    assert is_valid == expected
