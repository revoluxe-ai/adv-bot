from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.request_with_campaign_id import RequestWithCampaignID
from ...models.request_with_date import RequestWithDate
from ...models.request_with_interval import RequestWithInterval
from ...models.response_adv_error_1 import ResponseAdvError1
from ...models.response_with_date_type_0_item import ResponseWithDateType0Item
from ...models.response_with_interval_item import ResponseWithIntervalItem
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: List[Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]],
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/fullstats",
    }

    _body = []
    for body_item_data in body:
        body_item: Dict[str, Any]
        if isinstance(body_item_data, RequestWithDate):
            body_item = body_item_data.to_dict()
        elif isinstance(body_item_data, RequestWithInterval):
            body_item = body_item_data.to_dict()
        else:
            body_item = body_item_data.to_dict()

        _body.append(body_item)

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any, ResponseAdvError1, Union[List["ResponseWithIntervalItem"], Union[List["ResponseWithDateType0Item"], None]]
    ]
]:
    if response.status_code == HTTPStatus.OK:

        def _parse_response_200(
            data: object
        ) -> Union[List["ResponseWithIntervalItem"], Union[List["ResponseWithDateType0Item"], None]]:
            def _parse_response_200_type_0(data: object) -> Union[List["ResponseWithDateType0Item"], None]:
                if data is None:
                    return data
                try:
                    if not isinstance(data, list):
                        raise TypeError()
                    componentsschemas_response_with_date_type_0 = UNSET
                    _componentsschemas_response_with_date_type_0 = data
                    for (
                        componentsschemas_response_with_date_type_0_item_data
                    ) in _componentsschemas_response_with_date_type_0:
                        componentsschemas_response_with_date_type_0_item = ResponseWithDateType0Item.from_dict(
                            componentsschemas_response_with_date_type_0_item_data
                        )

                        componentsschemas_response_with_date_type_0.append(
                            componentsschemas_response_with_date_type_0_item
                        )

                    return componentsschemas_response_with_date_type_0
                except:  # noqa: E722
                    pass
                return cast(Union[List["ResponseWithDateType0Item"], None], data)

            response_200_type_0 = _parse_response_200_type_0(data)

            return response_200_type_0
            if not isinstance(data, list):
                raise TypeError()
            response_200_type_1 = UNSET
            _response_200_type_1 = data
            for componentsschemas_response_with_interval_item_data in _response_200_type_1:
                componentsschemas_response_with_interval_item = ResponseWithIntervalItem.from_dict(
                    componentsschemas_response_with_interval_item_data
                )

                response_200_type_1.append(componentsschemas_response_with_interval_item)

            return response_200_type_1

        response_200 = _parse_response_200(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = ResponseAdvError1.from_dict(response.json())

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
) -> Response[
    Union[
        Any, ResponseAdvError1, Union[List["ResponseWithIntervalItem"], Union[List["ResponseWithDateType0Item"], None]]
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
    body: List[Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]],
) -> Response[
    Union[
        Any, ResponseAdvError1, Union[List["ResponseWithIntervalItem"], Union[List["ResponseWithDateType0Item"], None]]
    ]
]:
    r"""Statistika kampanij

     Metod budet otkljuchen 30 sentjabrja. Ispol'zujte [aktual'nyj
    metod](/openapi/promotion#tag/Statistika/paths/~1adv~1v3~1fullstats/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 5 zaprosov |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ResponseAdvError1, Union[List['ResponseWithIntervalItem'], Union[List['ResponseWithDateType0Item'], None]]]]
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
    body: List[Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]],
) -> Optional[
    Union[
        Any, ResponseAdvError1, Union[List["ResponseWithIntervalItem"], Union[List["ResponseWithDateType0Item"], None]]
    ]
]:
    r"""Statistika kampanij

     Metod budet otkljuchen 30 sentjabrja. Ispol'zujte [aktual'nyj
    metod](/openapi/promotion#tag/Statistika/paths/~1adv~1v3~1fullstats/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 5 zaprosov |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ResponseAdvError1, Union[List['ResponseWithIntervalItem'], Union[List['ResponseWithDateType0Item'], None]]]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: List[Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]],
) -> Response[
    Union[
        Any, ResponseAdvError1, Union[List["ResponseWithIntervalItem"], Union[List["ResponseWithDateType0Item"], None]]
    ]
]:
    r"""Statistika kampanij

     Metod budet otkljuchen 30 sentjabrja. Ispol'zujte [aktual'nyj
    metod](/openapi/promotion#tag/Statistika/paths/~1adv~1v3~1fullstats/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 5 zaprosov |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ResponseAdvError1, Union[List['ResponseWithIntervalItem'], Union[List['ResponseWithDateType0Item'], None]]]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: List[Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]],
) -> Optional[
    Union[
        Any, ResponseAdvError1, Union[List["ResponseWithIntervalItem"], Union[List["ResponseWithDateType0Item"], None]]
    ]
]:
    r"""Statistika kampanij

     Metod budet otkljuchen 30 sentjabrja. Ispol'zujte [aktual'nyj
    metod](/openapi/promotion#tag/Statistika/paths/~1adv~1v3~1fullstats/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 minuta | 1 zapros | 1 minuta | 5 zaprosov |
    </div>

    Args:
        body (List[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ResponseAdvError1, Union[List['ResponseWithIntervalItem'], Union[List['ResponseWithDateType0Item'], None]]]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
