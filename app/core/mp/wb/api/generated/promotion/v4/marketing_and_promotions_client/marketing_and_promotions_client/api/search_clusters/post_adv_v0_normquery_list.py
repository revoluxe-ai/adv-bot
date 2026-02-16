from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.response_400 import Response400
from ...models.v0_get_norm_query_list_request import V0GetNormQueryListRequest
from ...models.v0_get_norm_query_list_response import V0GetNormQueryListResponse
from ...types import Response


def _get_kwargs(
    *,
    body: V0GetNormQueryListRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/adv/v0/normquery/list",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, Response400, V0GetNormQueryListResponse]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = V0GetNormQueryListResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = Response400.from_dict(response.json())

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
) -> Response[Union[Any, Response400, V0GetNormQueryListResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: V0GetNormQueryListRequest,
) -> Response[Union[Any, Response400, V0GetNormQueryListResponse]]:
    """Active and Inactive Search Cluster Lists

     Returns lists of active and inactive search clusters with at least 100 views.

    Args:
        body (V0GetNormQueryListRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Response400, V0GetNormQueryListResponse]]
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
    body: V0GetNormQueryListRequest,
) -> Optional[Union[Any, Response400, V0GetNormQueryListResponse]]:
    """Active and Inactive Search Cluster Lists

     Returns lists of active and inactive search clusters with at least 100 views.

    Args:
        body (V0GetNormQueryListRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Response400, V0GetNormQueryListResponse]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: V0GetNormQueryListRequest,
) -> Response[Union[Any, Response400, V0GetNormQueryListResponse]]:
    """Active and Inactive Search Cluster Lists

     Returns lists of active and inactive search clusters with at least 100 views.

    Args:
        body (V0GetNormQueryListRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Response400, V0GetNormQueryListResponse]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: V0GetNormQueryListRequest,
) -> Optional[Union[Any, Response400, V0GetNormQueryListResponse]]:
    """Active and Inactive Search Cluster Lists

     Returns lists of active and inactive search clusters with at least 100 views.

    Args:
        body (V0GetNormQueryListRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Response400, V0GetNormQueryListResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
