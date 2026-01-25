from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_api_v1_calendar_promotions_upload_body import (
    PostApiV1CalendarPromotionsUploadBody,
)
from ...models.post_api_v1_calendar_promotions_upload_response_200 import (
    PostApiV1CalendarPromotionsUploadResponse200,
)
from ...models.post_api_v1_calendar_promotions_upload_response_400 import (
    PostApiV1CalendarPromotionsUploadResponse400,
)
from ...models.post_api_v1_calendar_promotions_upload_response_401 import (
    PostApiV1CalendarPromotionsUploadResponse401,
)
from ...models.post_api_v1_calendar_promotions_upload_response_422 import (
    PostApiV1CalendarPromotionsUploadResponse422,
)
from ...models.post_api_v1_calendar_promotions_upload_response_429 import (
    PostApiV1CalendarPromotionsUploadResponse429,
)
from ...types import Response


def _get_kwargs(
    *,
    body: PostApiV1CalendarPromotionsUploadBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/calendar/promotions/upload",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostApiV1CalendarPromotionsUploadResponse200
    | PostApiV1CalendarPromotionsUploadResponse400
    | PostApiV1CalendarPromotionsUploadResponse401
    | PostApiV1CalendarPromotionsUploadResponse422
    | PostApiV1CalendarPromotionsUploadResponse429
    | None
):
    if response.status_code == 200:
        response_200 = PostApiV1CalendarPromotionsUploadResponse200.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 400:
        response_400 = PostApiV1CalendarPromotionsUploadResponse400.from_dict(
            response.json()
        )

        return response_400

    if response.status_code == 401:
        response_401 = PostApiV1CalendarPromotionsUploadResponse401.from_dict(
            response.json()
        )

        return response_401

    if response.status_code == 422:
        response_422 = PostApiV1CalendarPromotionsUploadResponse422.from_dict(
            response.json()
        )

        return response_422

    if response.status_code == 429:
        response_429 = PostApiV1CalendarPromotionsUploadResponse429.from_dict(
            response.json()
        )

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostApiV1CalendarPromotionsUploadResponse200
    | PostApiV1CalendarPromotionsUploadResponse400
    | PostApiV1CalendarPromotionsUploadResponse401
    | PostApiV1CalendarPromotionsUploadResponse422
    | PostApiV1CalendarPromotionsUploadResponse429
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: PostApiV1CalendarPromotionsUploadBody,
) -> Response[
    PostApiV1CalendarPromotionsUploadResponse200
    | PostApiV1CalendarPromotionsUploadResponse400
    | PostApiV1CalendarPromotionsUploadResponse401
    | PostApiV1CalendarPromotionsUploadResponse422
    | PostApiV1CalendarPromotionsUploadResponse429
]:
    r"""Dobavit' tovar v aktsiju

     Metod sozdaet zadanie na zagruzku tovara v [aktsiju](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get).<br>
    Sostojanie zagruzki mozhno proverit' s pomosch'ju [otdel'nyh metodov](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).

    <div class=\"description_important\">
      Dannyj metod neprimenim dlja avtoaktsij.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        body (PostApiV1CalendarPromotionsUploadBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiV1CalendarPromotionsUploadResponse200 | PostApiV1CalendarPromotionsUploadResponse400 | PostApiV1CalendarPromotionsUploadResponse401 | PostApiV1CalendarPromotionsUploadResponse422 | PostApiV1CalendarPromotionsUploadResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: PostApiV1CalendarPromotionsUploadBody,
) -> (
    PostApiV1CalendarPromotionsUploadResponse200
    | PostApiV1CalendarPromotionsUploadResponse400
    | PostApiV1CalendarPromotionsUploadResponse401
    | PostApiV1CalendarPromotionsUploadResponse422
    | PostApiV1CalendarPromotionsUploadResponse429
    | None
):
    r"""Dobavit' tovar v aktsiju

     Metod sozdaet zadanie na zagruzku tovara v [aktsiju](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get).<br>
    Sostojanie zagruzki mozhno proverit' s pomosch'ju [otdel'nyh metodov](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).

    <div class=\"description_important\">
      Dannyj metod neprimenim dlja avtoaktsij.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        body (PostApiV1CalendarPromotionsUploadBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiV1CalendarPromotionsUploadResponse200 | PostApiV1CalendarPromotionsUploadResponse400 | PostApiV1CalendarPromotionsUploadResponse401 | PostApiV1CalendarPromotionsUploadResponse422 | PostApiV1CalendarPromotionsUploadResponse429
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostApiV1CalendarPromotionsUploadBody,
) -> Response[
    PostApiV1CalendarPromotionsUploadResponse200
    | PostApiV1CalendarPromotionsUploadResponse400
    | PostApiV1CalendarPromotionsUploadResponse401
    | PostApiV1CalendarPromotionsUploadResponse422
    | PostApiV1CalendarPromotionsUploadResponse429
]:
    r"""Dobavit' tovar v aktsiju

     Metod sozdaet zadanie na zagruzku tovara v [aktsiju](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get).<br>
    Sostojanie zagruzki mozhno proverit' s pomosch'ju [otdel'nyh metodov](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).

    <div class=\"description_important\">
      Dannyj metod neprimenim dlja avtoaktsij.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        body (PostApiV1CalendarPromotionsUploadBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiV1CalendarPromotionsUploadResponse200 | PostApiV1CalendarPromotionsUploadResponse400 | PostApiV1CalendarPromotionsUploadResponse401 | PostApiV1CalendarPromotionsUploadResponse422 | PostApiV1CalendarPromotionsUploadResponse429]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostApiV1CalendarPromotionsUploadBody,
) -> (
    PostApiV1CalendarPromotionsUploadResponse200
    | PostApiV1CalendarPromotionsUploadResponse400
    | PostApiV1CalendarPromotionsUploadResponse401
    | PostApiV1CalendarPromotionsUploadResponse422
    | PostApiV1CalendarPromotionsUploadResponse429
    | None
):
    r"""Dobavit' tovar v aktsiju

     Metod sozdaet zadanie na zagruzku tovara v [aktsiju](/openapi/promotion#tag/Kalendar-
    akcij/paths/~1api~1v1~1calendar~1promotions~1details/get).<br>
    Sostojanie zagruzki mozhno proverit' s pomosch'ju [otdel'nyh metodov](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1tasks/get).

    <div class=\"description_important\">
      Dannyj metod neprimenim dlja avtoaktsij.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Kalendar' aktsij</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 10 zaprosov | 600 millisekund | 5 zaprosov |

    </div>

    Args:
        body (PostApiV1CalendarPromotionsUploadBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiV1CalendarPromotionsUploadResponse200 | PostApiV1CalendarPromotionsUploadResponse400 | PostApiV1CalendarPromotionsUploadResponse401 | PostApiV1CalendarPromotionsUploadResponse422 | PostApiV1CalendarPromotionsUploadResponse429
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
