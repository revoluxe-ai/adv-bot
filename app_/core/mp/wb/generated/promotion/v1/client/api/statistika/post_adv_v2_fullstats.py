from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v2_fullstats_response_401 import PostAdvV2FullstatsResponse401
from ...models.post_adv_v2_fullstats_response_429 import PostAdvV2FullstatsResponse429
from ...models.request_with_campaign_id import RequestWithCampaignID
from ...models.request_with_date import RequestWithDate
from ...models.request_with_interval import RequestWithInterval
from ...models.response_adv_error_1 import ResponseAdvError1
from ...models.response_with_date_type_0_item import ResponseWithDateType0Item
from ...models.response_with_interval_item import ResponseWithIntervalItem
from ...types import Response


def _get_kwargs(
    *,
    body: list[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v2/fullstats",
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item: dict[str, Any]
        if isinstance(body_item_data, RequestWithDate):
            body_item = body_item_data.to_dict()
        elif isinstance(body_item_data, RequestWithInterval):
            body_item = body_item_data.to_dict()
        else:
            body_item = body_item_data.to_dict()

        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        PostAdvV2FullstatsResponse401,
        PostAdvV2FullstatsResponse429,
        ResponseAdvError1,
        Union[
            None, list["ResponseWithDateType0Item"], list["ResponseWithIntervalItem"]
        ],
    ]
]:
    if response.status_code == 200:

        def _parse_response_200(
            data: object,
        ) -> Union[
            None, list["ResponseWithDateType0Item"], list["ResponseWithIntervalItem"]
        ]:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                componentsschemas_response_with_date_type_0 = []
                _componentsschemas_response_with_date_type_0 = data
                for (
                    componentsschemas_response_with_date_type_0_item_data
                ) in _componentsschemas_response_with_date_type_0:
                    componentsschemas_response_with_date_type_0_item = (
                        ResponseWithDateType0Item.from_dict(
                            componentsschemas_response_with_date_type_0_item_data
                        )
                    )

                    componentsschemas_response_with_date_type_0.append(
                        componentsschemas_response_with_date_type_0_item
                    )

                return componentsschemas_response_with_date_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                response_200_type_1 = []
                _response_200_type_1 = data
                for (
                    componentsschemas_response_with_interval_item_data
                ) in _response_200_type_1:
                    componentsschemas_response_with_interval_item = (
                        ResponseWithIntervalItem.from_dict(
                            componentsschemas_response_with_interval_item_data
                        )
                    )

                    response_200_type_1.append(
                        componentsschemas_response_with_interval_item
                    )

                return response_200_type_1
            except:  # noqa: E722
                pass
            return cast(
                Union[
                    None,
                    list["ResponseWithDateType0Item"],
                    list["ResponseWithIntervalItem"],
                ],
                data,
            )

        response_200 = _parse_response_200(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ResponseAdvError1.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV2FullstatsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV2FullstatsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        PostAdvV2FullstatsResponse401,
        PostAdvV2FullstatsResponse429,
        ResponseAdvError1,
        Union[
            None, list["ResponseWithDateType0Item"], list["ResponseWithIntervalItem"]
        ],
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
    body: list[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Response[
    Union[
        PostAdvV2FullstatsResponse401,
        PostAdvV2FullstatsResponse429,
        ResponseAdvError1,
        Union[
            None, list["ResponseWithDateType0Item"], list["ResponseWithIntervalItem"]
        ],
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
        body (list[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV2FullstatsResponse401, PostAdvV2FullstatsResponse429, ResponseAdvError1, Union[None, list['ResponseWithDateType0Item'], list['ResponseWithIntervalItem']]]]
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
    body: list[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Optional[
    Union[
        PostAdvV2FullstatsResponse401,
        PostAdvV2FullstatsResponse429,
        ResponseAdvError1,
        Union[
            None, list["ResponseWithDateType0Item"], list["ResponseWithIntervalItem"]
        ],
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
        body (list[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV2FullstatsResponse401, PostAdvV2FullstatsResponse429, ResponseAdvError1, Union[None, list['ResponseWithDateType0Item'], list['ResponseWithIntervalItem']]]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: list[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Response[
    Union[
        PostAdvV2FullstatsResponse401,
        PostAdvV2FullstatsResponse429,
        ResponseAdvError1,
        Union[
            None, list["ResponseWithDateType0Item"], list["ResponseWithIntervalItem"]
        ],
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
        body (list[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[PostAdvV2FullstatsResponse401, PostAdvV2FullstatsResponse429, ResponseAdvError1, Union[None, list['ResponseWithDateType0Item'], list['ResponseWithIntervalItem']]]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: list[
        Union["RequestWithCampaignID", "RequestWithDate", "RequestWithInterval"]
    ],
) -> Optional[
    Union[
        PostAdvV2FullstatsResponse401,
        PostAdvV2FullstatsResponse429,
        ResponseAdvError1,
        Union[
            None, list["ResponseWithDateType0Item"], list["ResponseWithIntervalItem"]
        ],
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
        body (list[Union['RequestWithCampaignID', 'RequestWithDate', 'RequestWithInterval']]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[PostAdvV2FullstatsResponse401, PostAdvV2FullstatsResponse429, ResponseAdvError1, Union[None, list['ResponseWithDateType0Item'], list['ResponseWithIntervalItem']]]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
