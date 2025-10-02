from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_promotion_adverts_direction import (
    PostAdvV1PromotionAdvertsDirection,
)
from ...models.post_adv_v1_promotion_adverts_order import PostAdvV1PromotionAdvertsOrder
from ...models.post_adv_v1_promotion_adverts_response_401 import (
    PostAdvV1PromotionAdvertsResponse401,
)
from ...models.post_adv_v1_promotion_adverts_response_429 import (
    PostAdvV1PromotionAdvertsResponse429,
)
from ...models.post_adv_v1_promotion_adverts_status import (
    PostAdvV1PromotionAdvertsStatus,
)
from ...models.post_adv_v1_promotion_adverts_type import PostAdvV1PromotionAdvertsType
from ...models.response_info_advert import ResponseInfoAdvert
from ...models.response_info_advert_type_8 import ResponseInfoAdvertType8
from ...models.response_info_advert_type_9 import ResponseInfoAdvertType9
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: list[int],
    status: Union[Unset, PostAdvV1PromotionAdvertsStatus] = UNSET,
    type_: Union[Unset, PostAdvV1PromotionAdvertsType] = UNSET,
    order: PostAdvV1PromotionAdvertsOrder,
    direction: Union[Unset, PostAdvV1PromotionAdvertsDirection] = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    json_status: Union[Unset, int] = UNSET
    if not isinstance(status, Unset):
        json_status = status.value

    params["status"] = json_status

    json_type_: Union[Unset, int] = UNSET
    if not isinstance(type_, Unset):
        json_type_ = type_.value

    params["type"] = json_type_

    json_order = order.value
    params["order"] = json_order

    json_direction: Union[Unset, str] = UNSET
    if not isinstance(direction, Unset):
        json_direction = direction.value

    params["direction"] = json_direction

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/promotion/adverts",
        "params": params,
    }

    _kwargs["json"] = body

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any,
        PostAdvV1PromotionAdvertsResponse401,
        PostAdvV1PromotionAdvertsResponse429,
        list[
            Union[
                "ResponseInfoAdvert",
                "ResponseInfoAdvertType8",
                "ResponseInfoAdvertType9",
            ]
        ],
        str,
    ]
]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:

            def _parse_response_200_item(
                data: object,
            ) -> Union[
                "ResponseInfoAdvert",
                "ResponseInfoAdvertType8",
                "ResponseInfoAdvertType9",
            ]:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_0 = ResponseInfoAdvertType8.from_dict(data)

                    return response_200_item_type_0
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_1 = ResponseInfoAdvert.from_dict(data)

                    return response_200_item_type_1
                except:  # noqa: E722
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_item_type_2 = ResponseInfoAdvertType9.from_dict(data)

                return response_200_item_type_2

            response_200_item = _parse_response_200_item(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1PromotionAdvertsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 422:
        response_422 = response.text
        return response_422

    if response.status_code == 429:
        response_429 = PostAdvV1PromotionAdvertsResponse429.from_dict(response.json())

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
        PostAdvV1PromotionAdvertsResponse401,
        PostAdvV1PromotionAdvertsResponse429,
        list[
            Union[
                "ResponseInfoAdvert",
                "ResponseInfoAdvertType8",
                "ResponseInfoAdvertType9",
            ]
        ],
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
    status: Union[Unset, PostAdvV1PromotionAdvertsStatus] = UNSET,
    type_: Union[Unset, PostAdvV1PromotionAdvertsType] = UNSET,
    order: PostAdvV1PromotionAdvertsOrder,
    direction: Union[Unset, PostAdvV1PromotionAdvertsDirection] = UNSET,
) -> Response[
    Union[
        Any,
        PostAdvV1PromotionAdvertsResponse401,
        PostAdvV1PromotionAdvertsResponse429,
        list[
            Union[
                "ResponseInfoAdvert",
                "ResponseInfoAdvertType8",
                "ResponseInfoAdvertType9",
            ]
        ],
        str,
    ]
]:
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah po ih statusam, tipam i ID.
    <br><br>
    Dlja poluchenija informatsii o kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        status (Union[Unset, PostAdvV1PromotionAdvertsStatus]):
        type_ (Union[Unset, PostAdvV1PromotionAdvertsType]):
        order (PostAdvV1PromotionAdvertsOrder):
        direction (Union[Unset, PostAdvV1PromotionAdvertsDirection]):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostAdvV1PromotionAdvertsResponse401, PostAdvV1PromotionAdvertsResponse429, list[Union['ResponseInfoAdvert', 'ResponseInfoAdvertType8', 'ResponseInfoAdvertType9']], str]]
    """

    kwargs = _get_kwargs(
        body=body,
        status=status,
        type_=type_,
        order=order,
        direction=direction,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: list[int],
    status: Union[Unset, PostAdvV1PromotionAdvertsStatus] = UNSET,
    type_: Union[Unset, PostAdvV1PromotionAdvertsType] = UNSET,
    order: PostAdvV1PromotionAdvertsOrder,
    direction: Union[Unset, PostAdvV1PromotionAdvertsDirection] = UNSET,
) -> Optional[
    Union[
        Any,
        PostAdvV1PromotionAdvertsResponse401,
        PostAdvV1PromotionAdvertsResponse429,
        list[
            Union[
                "ResponseInfoAdvert",
                "ResponseInfoAdvertType8",
                "ResponseInfoAdvertType9",
            ]
        ],
        str,
    ]
]:
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah po ih statusam, tipam i ID.
    <br><br>
    Dlja poluchenija informatsii o kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        status (Union[Unset, PostAdvV1PromotionAdvertsStatus]):
        type_ (Union[Unset, PostAdvV1PromotionAdvertsType]):
        order (PostAdvV1PromotionAdvertsOrder):
        direction (Union[Unset, PostAdvV1PromotionAdvertsDirection]):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostAdvV1PromotionAdvertsResponse401, PostAdvV1PromotionAdvertsResponse429, list[Union['ResponseInfoAdvert', 'ResponseInfoAdvertType8', 'ResponseInfoAdvertType9']], str]
    """

    return sync_detailed(
        client=client,
        body=body,
        status=status,
        type_=type_,
        order=order,
        direction=direction,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: list[int],
    status: Union[Unset, PostAdvV1PromotionAdvertsStatus] = UNSET,
    type_: Union[Unset, PostAdvV1PromotionAdvertsType] = UNSET,
    order: PostAdvV1PromotionAdvertsOrder,
    direction: Union[Unset, PostAdvV1PromotionAdvertsDirection] = UNSET,
) -> Response[
    Union[
        Any,
        PostAdvV1PromotionAdvertsResponse401,
        PostAdvV1PromotionAdvertsResponse429,
        list[
            Union[
                "ResponseInfoAdvert",
                "ResponseInfoAdvertType8",
                "ResponseInfoAdvertType9",
            ]
        ],
        str,
    ]
]:
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah po ih statusam, tipam i ID.
    <br><br>
    Dlja poluchenija informatsii o kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        status (Union[Unset, PostAdvV1PromotionAdvertsStatus]):
        type_ (Union[Unset, PostAdvV1PromotionAdvertsType]):
        order (PostAdvV1PromotionAdvertsOrder):
        direction (Union[Unset, PostAdvV1PromotionAdvertsDirection]):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, PostAdvV1PromotionAdvertsResponse401, PostAdvV1PromotionAdvertsResponse429, list[Union['ResponseInfoAdvert', 'ResponseInfoAdvertType8', 'ResponseInfoAdvertType9']], str]]
    """

    kwargs = _get_kwargs(
        body=body,
        status=status,
        type_=type_,
        order=order,
        direction=direction,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: list[int],
    status: Union[Unset, PostAdvV1PromotionAdvertsStatus] = UNSET,
    type_: Union[Unset, PostAdvV1PromotionAdvertsType] = UNSET,
    order: PostAdvV1PromotionAdvertsOrder,
    direction: Union[Unset, PostAdvV1PromotionAdvertsDirection] = UNSET,
) -> Optional[
    Union[
        Any,
        PostAdvV1PromotionAdvertsResponse401,
        PostAdvV1PromotionAdvertsResponse429,
        list[
            Union[
                "ResponseInfoAdvert",
                "ResponseInfoAdvertType8",
                "ResponseInfoAdvertType9",
            ]
        ],
        str,
    ]
]:
    r"""Informatsija o kampanijah

     Metod vozvraschaet informatsiju o reklamnyh kampanijah po ih statusam, tipam i ID.
    <br><br>
    Dlja poluchenija informatsii o kampanijah s ruchnoj stavkoj ispol'zujte [otdel'nyj
    metod](/openapi/promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get).

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        status (Union[Unset, PostAdvV1PromotionAdvertsStatus]):
        type_ (Union[Unset, PostAdvV1PromotionAdvertsType]):
        order (PostAdvV1PromotionAdvertsOrder):
        direction (Union[Unset, PostAdvV1PromotionAdvertsDirection]):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, PostAdvV1PromotionAdvertsResponse401, PostAdvV1PromotionAdvertsResponse429, list[Union['ResponseInfoAdvert', 'ResponseInfoAdvertType8', 'ResponseInfoAdvertType9']], str]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            status=status,
            type_=type_,
            order=order,
            direction=direction,
        )
    ).parsed
