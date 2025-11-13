from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import Response


def _get_kwargs() -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/calendar/promotions/upload",
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Any]:
    if response.status_code == HTTPStatus.OK:
        return None
    if response.status_code == HTTPStatus.BAD_REQUEST:
        return None
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        return None
    if response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
        return None
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return None
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Any]:
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

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Any]:
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

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
