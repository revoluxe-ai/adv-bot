import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_payments_response_200_item import (
    GetAdvV1PaymentsResponse200Item,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    from_: Union[Unset, datetime.date] = UNSET,
    to: Union[Unset, datetime.date] = UNSET,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    json_from_: Union[Unset, str] = UNSET
    if not isinstance(from_, Unset):
        json_from_ = from_.isoformat()
    params["from"] = json_from_

    json_to: Union[Unset, str] = UNSET
    if not isinstance(to, Unset):
        json_to = to.isoformat()
    params["to"] = json_to

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/payments",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, List["GetAdvV1PaymentsResponse200Item"], str]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = GetAdvV1PaymentsResponse200Item.from_dict(
                response_200_item_data
            )

            response_200.append(response_200_item)

        return response_200
    if response.status_code == HTTPStatus.NO_CONTENT:
        response_204 = cast(Any, None)
        return response_204
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = cast(str, response.json())
        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[Any, List["GetAdvV1PaymentsResponse200Item"], str]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    from_: Union[Unset, datetime.date] = UNSET,
    to: Union[Unset, datetime.date] = UNSET,
) -> Response[Union[Any, List["GetAdvV1PaymentsResponse200Item"], str]]:
    r"""Receiving the History of Account Top-ups

     The method allows you to get a history of top-ups.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 5 requests |
    </div>

    Args:
        from_ (Union[Unset, datetime.date]):  Example: 2023-07-31.
        to (Union[Unset, datetime.date]):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List['GetAdvV1PaymentsResponse200Item'], str]]
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
    from_: Union[Unset, datetime.date] = UNSET,
    to: Union[Unset, datetime.date] = UNSET,
) -> Optional[Union[Any, List["GetAdvV1PaymentsResponse200Item"], str]]:
    r"""Receiving the History of Account Top-ups

     The method allows you to get a history of top-ups.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 5 requests |
    </div>

    Args:
        from_ (Union[Unset, datetime.date]):  Example: 2023-07-31.
        to (Union[Unset, datetime.date]):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List['GetAdvV1PaymentsResponse200Item'], str]
    """

    return sync_detailed(
        client=client,
        from_=from_,
        to=to,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    from_: Union[Unset, datetime.date] = UNSET,
    to: Union[Unset, datetime.date] = UNSET,
) -> Response[Union[Any, List["GetAdvV1PaymentsResponse200Item"], str]]:
    r"""Receiving the History of Account Top-ups

     The method allows you to get a history of top-ups.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 5 requests |
    </div>

    Args:
        from_ (Union[Unset, datetime.date]):  Example: 2023-07-31.
        to (Union[Unset, datetime.date]):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, List['GetAdvV1PaymentsResponse200Item'], str]]
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
    from_: Union[Unset, datetime.date] = UNSET,
    to: Union[Unset, datetime.date] = UNSET,
) -> Optional[Union[Any, List["GetAdvV1PaymentsResponse200Item"], str]]:
    r"""Receiving the History of Account Top-ups

     The method allows you to get a history of top-ups.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 s | 1 request | 1 s | 5 requests |
    </div>

    Args:
        from_ (Union[Unset, datetime.date]):  Example: 2023-07-31.
        to (Union[Unset, datetime.date]):  Example: 2023-08-02.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, List['GetAdvV1PaymentsResponse200Item'], str]
    """

    return (
        await asyncio_detailed(
            client=client,
            from_=from_,
            to=to,
        )
    ).parsed
