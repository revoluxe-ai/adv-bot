import datetime
from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_upd_response_200_item import GetAdvV1UpdResponse200Item
from ...models.get_adv_v1_upd_response_401 import GetAdvV1UpdResponse401
from ...models.get_adv_v1_upd_response_429 import GetAdvV1UpdResponse429
from ...types import UNSET, Response


def _get_kwargs(
    *,
    from_: datetime.date,
    to: datetime.date,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_from_ = from_.isoformat()
    params["from"] = json_from_

    json_to = to.isoformat()
    params["to"] = json_to

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/upd",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    GetAdvV1UpdResponse401
    | GetAdvV1UpdResponse429
    | list[GetAdvV1UpdResponse200Item]
    | str
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = GetAdvV1UpdResponse200Item.from_dict(
                response_200_item_data
            )

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = GetAdvV1UpdResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = GetAdvV1UpdResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    GetAdvV1UpdResponse401
    | GetAdvV1UpdResponse429
    | list[GetAdvV1UpdResponse200Item]
    | str
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
    from_: datetime.date,
    to: datetime.date,
) -> Response[
    GetAdvV1UpdResponse401
    | GetAdvV1UpdResponse429
    | list[GetAdvV1UpdResponse200Item]
    | str
]:
    r"""Poluchenie istorii zatrat

     Metod formiruet spisok fakticheskih zatrat na reklamnye kampanii za zadannyj period.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        from_ (datetime.date):  Example: 2023-07-31.
        to (datetime.date):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1UpdResponse401 | GetAdvV1UpdResponse429 | list[GetAdvV1UpdResponse200Item] | str]
    """

    kwargs = _get_kwargs(
        from_=from_,
        to=to,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    from_: datetime.date,
    to: datetime.date,
) -> (
    GetAdvV1UpdResponse401
    | GetAdvV1UpdResponse429
    | list[GetAdvV1UpdResponse200Item]
    | str
    | None
):
    r"""Poluchenie istorii zatrat

     Metod formiruet spisok fakticheskih zatrat na reklamnye kampanii za zadannyj period.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        from_ (datetime.date):  Example: 2023-07-31.
        to (datetime.date):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1UpdResponse401 | GetAdvV1UpdResponse429 | list[GetAdvV1UpdResponse200Item] | str
    """

    return sync_detailed(
        client=client,
        from_=from_,
        to=to,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    from_: datetime.date,
    to: datetime.date,
) -> Response[
    GetAdvV1UpdResponse401
    | GetAdvV1UpdResponse429
    | list[GetAdvV1UpdResponse200Item]
    | str
]:
    r"""Poluchenie istorii zatrat

     Metod formiruet spisok fakticheskih zatrat na reklamnye kampanii za zadannyj period.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        from_ (datetime.date):  Example: 2023-07-31.
        to (datetime.date):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAdvV1UpdResponse401 | GetAdvV1UpdResponse429 | list[GetAdvV1UpdResponse200Item] | str]
    """

    kwargs = _get_kwargs(
        from_=from_,
        to=to,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    from_: datetime.date,
    to: datetime.date,
) -> (
    GetAdvV1UpdResponse401
    | GetAdvV1UpdResponse429
    | list[GetAdvV1UpdResponse200Item]
    | str
    | None
):
    r"""Poluchenie istorii zatrat

     Metod formiruet spisok fakticheskih zatrat na reklamnye kampanii za zadannyj period.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 1 zapros | 1 sekunda | 5 zaprosov |
    </div>

    Args:
        from_ (datetime.date):  Example: 2023-07-31.
        to (datetime.date):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAdvV1UpdResponse401 | GetAdvV1UpdResponse429 | list[GetAdvV1UpdResponse200Item] | str
    """

    return (
        await asyncio_detailed(
            client=client,
            from_=from_,
            to=to,
        )
    ).parsed
