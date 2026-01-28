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
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    payment_type: str | Unset = "cpm",
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["payment_type"] = payment_type

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/adv/v1/supplier/subjects",
        "params": params,
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
    payment_type: str | Unset = "cpm",
) -> Response[
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
]:
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Args:
        payment_type (str | Unset):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None]
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
    payment_type: str | Unset = "cpm",
) -> (
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
    | None
):
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Args:
        payment_type (str | Unset):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None
    """

    return sync_detailed(
        client=client,
        payment_type=payment_type,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    payment_type: str | Unset = "cpm",
) -> Response[
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
]:
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Args:
        payment_type (str | Unset):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None]
    """

    kwargs = _get_kwargs(
        payment_type=payment_type,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    payment_type: str | Unset = "cpm",
) -> (
    Any
    | GetAdvV1SupplierSubjectsResponse401
    | GetAdvV1SupplierSubjectsResponse429
    | list[GetAdvV1SupplierSubjectsResponse200Type0Item]
    | None
    | None
):
    r"""Predmety dlja kampanij

     Metod vozvraschaet spisok [predmetov](/openapi/work-with-products#tag/Kategorii-predmety-i-
    harakteristiki/paths/~1content~1v2~1object~1all/get), kotorye mozhno dobavit' v reklamnuju
    [kampaniju](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 12 sekund | 1 zapros | 12 sekund | 5 zaprosov |
    </div>

    Args:
        payment_type (str | Unset):  Default: 'cpm'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GetAdvV1SupplierSubjectsResponse401 | GetAdvV1SupplierSubjectsResponse429 | list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None
    """

    return (
        await asyncio_detailed(
            client=client,
            payment_type=payment_type,
        )
    ).parsed
