from http import HTTPStatus
from typing import Any, Optional, Union, cast

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
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any,
        GetAdvV1SupplierSubjectsResponse401,
        GetAdvV1SupplierSubjectsResponse429,
        Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]],
    ]
]:
    if response.status_code == 200:

        def _parse_response_200(
            data: object,
        ) -> Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]]:
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
                Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]], data
            )

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
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        Any,
        GetAdvV1SupplierSubjectsResponse401,
        GetAdvV1SupplierSubjectsResponse429,
        Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]],
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
) -> Response[
    Union[
        Any,
        GetAdvV1SupplierSubjectsResponse401,
        GetAdvV1SupplierSubjectsResponse429,
        Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]],
    ]
]:
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAdvV1SupplierSubjectsResponse401, GetAdvV1SupplierSubjectsResponse429, Union[None, list['GetAdvV1SupplierSubjectsResponse200Type0Item']]]]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[
        Any,
        GetAdvV1SupplierSubjectsResponse401,
        GetAdvV1SupplierSubjectsResponse429,
        Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]],
    ]
]:
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAdvV1SupplierSubjectsResponse401, GetAdvV1SupplierSubjectsResponse429, Union[None, list['GetAdvV1SupplierSubjectsResponse200Type0Item']]]
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[
    Union[
        Any,
        GetAdvV1SupplierSubjectsResponse401,
        GetAdvV1SupplierSubjectsResponse429,
        Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]],
    ]
]:
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, GetAdvV1SupplierSubjectsResponse401, GetAdvV1SupplierSubjectsResponse429, Union[None, list['GetAdvV1SupplierSubjectsResponse200Type0Item']]]]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[
        Any,
        GetAdvV1SupplierSubjectsResponse401,
        GetAdvV1SupplierSubjectsResponse429,
        Union[None, list["GetAdvV1SupplierSubjectsResponse200Type0Item"]],
    ]
]:
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1adv~1v1~1promotion~1adverts/post).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, GetAdvV1SupplierSubjectsResponse401, GetAdvV1SupplierSubjectsResponse429, Union[None, list['GetAdvV1SupplierSubjectsResponse200Type0Item']]]
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
