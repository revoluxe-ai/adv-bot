from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_supplier_subjects_response_200_type_0_item import (
    GetAdvV1SupplierSubjectsResponse200Type0Item,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    payment_type: Union[Unset, str] = "cpm",
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["payment_type"] = payment_type

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/supplier/subjects",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[Any, Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None]]
]:
    if response.status_code == HTTPStatus.OK:

        def _parse_response_200(
            data: object,
        ) -> Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None]:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                response_200_type_0 = []
                _response_200_type_0 = data
                for response_200_type_0_item_data in _response_200_type_0:
                    response_200_type_0_item = (
                        GetAdvV1SupplierSubjectsResponse200Type0Item.from_dict(
                            response_200_type_0_item_data
                        )
                    )

                    response_200_type_0.append(response_200_type_0_item)

                return response_200_type_0
            except:  # noqa: E722
                pass
            return cast(
                Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None], data
            )

        response_200 = _parse_response_200(response.json())

        return response_200
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.NOT_FOUND:
        response_404 = cast(Any, None)
        return response_404
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[Any, Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None]]
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
    payment_type: Union[Unset, str] = "cpm",
) -> Response[
    Union[Any, Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None]]
]:
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 12 s | 1 request | 12 s | 5 requests |
    | Service | 12 s | 1 request | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        payment_type (Union[Unset, str]):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Union[List['GetAdvV1SupplierSubjectsResponse200Type0Item'], None]]]
    """

    kwargs = _get_kwargs(
        payment_type=payment_type,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    payment_type: Union[Unset, str] = "cpm",
) -> Optional[
    Union[Any, Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None]]
]:
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 12 s | 1 request | 12 s | 5 requests |
    | Service | 12 s | 1 request | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        payment_type (Union[Unset, str]):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Union[List['GetAdvV1SupplierSubjectsResponse200Type0Item'], None]]
    """

    return sync_detailed(
        client=client,
        payment_type=payment_type,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    payment_type: Union[Unset, str] = "cpm",
) -> Response[
    Union[Any, Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None]]
]:
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 12 s | 1 request | 12 s | 5 requests |
    | Service | 12 s | 1 request | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        payment_type (Union[Unset, str]):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Union[List['GetAdvV1SupplierSubjectsResponse200Type0Item'], None]]]
    """

    kwargs = _get_kwargs(
        payment_type=payment_type,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    payment_type: Union[Unset, str] = "cpm",
) -> Optional[
    Union[Any, Union[List["GetAdvV1SupplierSubjectsResponse200Type0Item"], None]]
]:
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 12 s | 1 request | 12 s | 5 requests |
    | Service | 12 s | 1 request | 12 s | 5 requests |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        payment_type (Union[Unset, str]):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Union[List['GetAdvV1SupplierSubjectsResponse200Type0Item'], None]]
    """

    return (
        await asyncio_detailed(
            client=client,
            payment_type=payment_type,
        )
    ).parsed
