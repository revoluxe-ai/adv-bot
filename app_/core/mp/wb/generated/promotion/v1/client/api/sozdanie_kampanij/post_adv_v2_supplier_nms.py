from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v2_supplier_nms_response_200_item import (
    PostAdvV2SupplierNmsResponse200Item,
)
from ...models.post_adv_v2_supplier_nms_response_401 import (
    PostAdvV2SupplierNmsResponse401,
)
from ...models.post_adv_v2_supplier_nms_response_429 import (
    PostAdvV2SupplierNmsResponse429,
)
from ...types import Response


def _get_kwargs(
    *,
    body: list[int],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/supplier/nms",
    }

    _kwargs["json"] = body

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        PostAdvV2SupplierNmsResponse401,
        PostAdvV2SupplierNmsResponse429,
        list["PostAdvV2SupplierNmsResponse200Item"],
        str,
    ]
]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = PostAdvV2SupplierNmsResponse200Item.from_dict(
                response_200_item_data
            )

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV2SupplierNmsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV2SupplierNmsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        PostAdvV2SupplierNmsResponse401,
        PostAdvV2SupplierNmsResponse429,
        list["PostAdvV2SupplierNmsResponse200Item"],
        str,
    ]
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
    body: list[int],
) -> Response[
    Union[
        PostAdvV2SupplierNmsResponse401,
        PostAdvV2SupplierNmsResponse429,
        list["PostAdvV2SupplierNmsResponse200Item"],
        str,
    ]
]:
    r"""Kartochki tovarov dlja kampanij

     Metod vozvraschaet spisok [kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post). Dlja
    poluchenija kartochek neobhodimy ID [predmetov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v1~1supplier~1subjects/get), takzhe dostupnyh dlja dobavlenija v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV2SupplierNmsResponse401, PostAdvV2SupplierNmsResponse429, list['PostAdvV2SupplierNmsResponse200Item'], str]]
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
    body: list[int],
) -> Optional[
    Union[
        PostAdvV2SupplierNmsResponse401,
        PostAdvV2SupplierNmsResponse429,
        list["PostAdvV2SupplierNmsResponse200Item"],
        str,
    ]
]:
    r"""Kartochki tovarov dlja kampanij

     Metod vozvraschaet spisok [kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post). Dlja
    poluchenija kartochek neobhodimy ID [predmetov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v1~1supplier~1subjects/get), takzhe dostupnyh dlja dobavlenija v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV2SupplierNmsResponse401, PostAdvV2SupplierNmsResponse429, list['PostAdvV2SupplierNmsResponse200Item'], str]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: list[int],
) -> Response[
    Union[
        PostAdvV2SupplierNmsResponse401,
        PostAdvV2SupplierNmsResponse429,
        list["PostAdvV2SupplierNmsResponse200Item"],
        str,
    ]
]:
    r"""Kartochki tovarov dlja kampanij

     Metod vozvraschaet spisok [kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post). Dlja
    poluchenija kartochek neobhodimy ID [predmetov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v1~1supplier~1subjects/get), takzhe dostupnyh dlja dobavlenija v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV2SupplierNmsResponse401, PostAdvV2SupplierNmsResponse429, list['PostAdvV2SupplierNmsResponse200Item'], str]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: list[int],
) -> Optional[
    Union[
        PostAdvV2SupplierNmsResponse401,
        PostAdvV2SupplierNmsResponse429,
        list["PostAdvV2SupplierNmsResponse200Item"],
        str,
    ]
]:
    r"""Kartochki tovarov dlja kampanij

     Metod vozvraschaet spisok [kartochek tovarov](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1get~1cards~1list/post), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post). Dlja
    poluchenija kartochek neobhodimy ID [predmetov](/openapi/promotion#tag/Sozdanie-
    kampanij/paths/~1adv~1v1~1supplier~1subjects/get), takzhe dostupnyh dlja dobavlenija v kampaniju.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 5 zaprosov | 12 sekund | 5 zaprosov |
    </div>

    Args:
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV2SupplierNmsResponse401, PostAdvV2SupplierNmsResponse429, list['PostAdvV2SupplierNmsResponse200Item'], str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
