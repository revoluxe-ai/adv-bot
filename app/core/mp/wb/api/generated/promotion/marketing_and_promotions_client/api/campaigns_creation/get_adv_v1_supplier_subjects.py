from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_adv_v1_supplier_subjects_response_200_type_0_item import (
    GetAdvV1SupplierSubjectsResponse200Type0Item,
)
from ...models.get_adv_v1_supplier_subjects_response_401 import (
    GetAdvV1SupplierSubjectsResponse401,
)
from ...models.get_adv_v1_supplier_subjects_response_429 import (
    GetAdvV1SupplierSubjectsResponse429,
)
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/supplier/subjects",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
    | None
):
    if response.status_code == 200:

        def _parse_response_200(
            data: object,
        ) -> list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None:
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
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None, data)

        response_200 = _parse_response_200(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = GetAdvV1SupplierSubjectsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 404:
        response_404 = cast(Any, None)
        return response_404

    if response.status_code == 429:
        response_429 = GetAdvV1SupplierSubjectsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
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
) -> Response[
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
]:
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 12 seconds | 1 request | 12 seconds | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> (
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
    | None
):
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 12 seconds | 1 request | 12 seconds | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
]:
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 12 seconds | 1 request | 12 seconds | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> (
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
    | None
):
    r"""Subjects for Campaigns

     Returns subjects product cards from which are available for all campaigns

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 12 seconds | 1 request | 12 seconds | 5 requests |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
