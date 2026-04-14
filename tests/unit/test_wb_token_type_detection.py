import datetime

import jwt
import pytest

from app.modules.common_slaves.wildberries.models.models import WBToken, WBTokenType

pytestmark = pytest.mark.unit


def _build_token(*, acc: int, for_field: str | None, t: bool) -> str:
    payload: dict[str, object] = {
        "id": "test",
        "s": 102,
        "sid": "shop_test",
        "exp": int((datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)).timestamp()),
        "acc": acc,
        "t": t,
    }
    if for_field is not None:
        payload["for"] = for_field
    return jwt.encode(payload, "secret", algorithm="HS256")


@pytest.mark.parametrize(
    ("token", "expected_type"),
    [
        (_build_token(acc=1, for_field=None, t=False), WBTokenType.BASE),
        (_build_token(acc=2, for_field=None, t=True), WBTokenType.TEST),
        (_build_token(acc=3, for_field="self", t=False), WBTokenType.PERSONAL),
        (_build_token(acc=4, for_field="asid:123", t=False), WBTokenType.SERVICE),
        (_build_token(acc=3, for_field=None, t=False), WBTokenType.UNKNOWN),
    ],
)
def test_detect_wb_token_type(token: str, expected_type: WBTokenType) -> None:
    wb_token = WBToken(api_key=token)
    assert wb_token.detect_wb_token_type() == expected_type
    assert wb_token.token_type == expected_type


def test_is_personal_true_only_for_personal_type() -> None:
    personal = WBToken(api_key=_build_token(acc=3, for_field="self", t=False))
    base = WBToken(api_key=_build_token(acc=1, for_field=None, t=False))

    assert personal.is_personal is True
    assert base.is_personal is False
