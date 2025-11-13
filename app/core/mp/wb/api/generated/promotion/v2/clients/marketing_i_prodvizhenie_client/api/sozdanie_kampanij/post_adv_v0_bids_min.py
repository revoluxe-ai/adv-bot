from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v0_bids_min_body import PostAdvV0BidsMinBody
from ...models.post_adv_v0_bids_min_response_200 import PostAdvV0BidsMinResponse200
from ...models.standardized_batch_error import StandardizedBatchError
from ...types import Response


def _get_kwargs(
    *,
    body: PostAdvV0BidsMinBody,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/adv/v0/bids/min",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PostAdvV0BidsMinResponse200.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = StandardizedBatchError.from_dict(response.json())

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
) -> Response[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PostAdvV0BidsMinBody,
) -> Response[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov po tipu oplaty i mestam razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]
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
    client: Union[AuthenticatedClient, Client],
    body: PostAdvV0BidsMinBody,
) -> Optional[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov po tipu oplaty i mestam razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PostAdvV0BidsMinBody,
) -> Response[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov po tipu oplaty i mestam razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PostAdvV0BidsMinBody,
) -> Optional[Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]]:
    r"""Minimal'nye stavki dlja kartochek tovarov

     Metod vozvraschaet minimal'nye stavki dlja kartochek tovarov po tipu oplaty i mestam razmeschenija.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 20 zaprosov | 3 sekundy | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0BidsMinBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostAdvV0BidsMinResponse200, StandardizedBatchError]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
