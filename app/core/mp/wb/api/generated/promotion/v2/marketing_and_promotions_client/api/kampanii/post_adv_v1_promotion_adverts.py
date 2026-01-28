from http import HTTPStatus
from typing import Any, cast

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
from ...models.response_info_advert_type_8 import ResponseInfoAdvertType8
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: list[int],
    status: PostAdvV1PromotionAdvertsStatus | Unset = UNSET,
    type_: PostAdvV1PromotionAdvertsType | Unset = UNSET,
    order: PostAdvV1PromotionAdvertsOrder | Unset = UNSET,
    direction: PostAdvV1PromotionAdvertsDirection | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    json_status: int | Unset = UNSET
    if not isinstance(status, Unset):
        json_status = status.value

    params["status"] = json_status

    json_type_: int | Unset = UNSET
    if not isinstance(type_, Unset):
        json_type_ = type_.value

    params["type"] = json_type_

    json_order: str | Unset = UNSET
    if not isinstance(order, Unset):
        json_order = order.value

    params["order"] = json_order

    json_direction: str | Unset = UNSET
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
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | PostAdvV1PromotionAdvertsResponse401
    | PostAdvV1PromotionAdvertsResponse429
    | list[ResponseInfoAdvertType8]
    | str
    | None
):
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = ResponseInfoAdvertType8.from_dict(
                response_200_item_data
            )

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
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | PostAdvV1PromotionAdvertsResponse401
    | PostAdvV1PromotionAdvertsResponse429
    | list[ResponseInfoAdvertType8]
    | str
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
    status: PostAdvV1PromotionAdvertsStatus | Unset = UNSET,
    type_: PostAdvV1PromotionAdvertsType | Unset = UNSET,
    order: PostAdvV1PromotionAdvertsOrder | Unset = UNSET,
    direction: PostAdvV1PromotionAdvertsDirection | Unset = UNSET,
) -> Response[
    Any
    | PostAdvV1PromotionAdvertsResponse401
    | PostAdvV1PromotionAdvertsResponse429
    | list[ResponseInfoAdvertType8]
    | str
]:
    """Informatsija o kampanijah

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        status (PostAdvV1PromotionAdvertsStatus | Unset):
        type_ (PostAdvV1PromotionAdvertsType | Unset):
        order (PostAdvV1PromotionAdvertsOrder | Unset):
        direction (PostAdvV1PromotionAdvertsDirection | Unset):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV1PromotionAdvertsResponse401 | PostAdvV1PromotionAdvertsResponse429 | list[ResponseInfoAdvertType8] | str]
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
    status: PostAdvV1PromotionAdvertsStatus | Unset = UNSET,
    type_: PostAdvV1PromotionAdvertsType | Unset = UNSET,
    order: PostAdvV1PromotionAdvertsOrder | Unset = UNSET,
    direction: PostAdvV1PromotionAdvertsDirection | Unset = UNSET,
) -> (
    Any
    | PostAdvV1PromotionAdvertsResponse401
    | PostAdvV1PromotionAdvertsResponse429
    | list[ResponseInfoAdvertType8]
    | str
    | None
):
    """Informatsija o kampanijah

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        status (PostAdvV1PromotionAdvertsStatus | Unset):
        type_ (PostAdvV1PromotionAdvertsType | Unset):
        order (PostAdvV1PromotionAdvertsOrder | Unset):
        direction (PostAdvV1PromotionAdvertsDirection | Unset):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV1PromotionAdvertsResponse401 | PostAdvV1PromotionAdvertsResponse429 | list[ResponseInfoAdvertType8] | str
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
    status: PostAdvV1PromotionAdvertsStatus | Unset = UNSET,
    type_: PostAdvV1PromotionAdvertsType | Unset = UNSET,
    order: PostAdvV1PromotionAdvertsOrder | Unset = UNSET,
    direction: PostAdvV1PromotionAdvertsDirection | Unset = UNSET,
) -> Response[
    Any
    | PostAdvV1PromotionAdvertsResponse401
    | PostAdvV1PromotionAdvertsResponse429
    | list[ResponseInfoAdvertType8]
    | str
]:
    """Informatsija o kampanijah

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        status (PostAdvV1PromotionAdvertsStatus | Unset):
        type_ (PostAdvV1PromotionAdvertsType | Unset):
        order (PostAdvV1PromotionAdvertsOrder | Unset):
        direction (PostAdvV1PromotionAdvertsDirection | Unset):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV1PromotionAdvertsResponse401 | PostAdvV1PromotionAdvertsResponse429 | list[ResponseInfoAdvertType8] | str]
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
    status: PostAdvV1PromotionAdvertsStatus | Unset = UNSET,
    type_: PostAdvV1PromotionAdvertsType | Unset = UNSET,
    order: PostAdvV1PromotionAdvertsOrder | Unset = UNSET,
    direction: PostAdvV1PromotionAdvertsDirection | Unset = UNSET,
) -> (
    Any
    | PostAdvV1PromotionAdvertsResponse401
    | PostAdvV1PromotionAdvertsResponse429
    | list[ResponseInfoAdvertType8]
    | str
    | None
):
    """Informatsija o kampanijah

     Dannyj metod ustarel. On budet udalen [2 fevralja](https://dev.wildberries.ru/release-notes?id=388)

    Args:
        status (PostAdvV1PromotionAdvertsStatus | Unset):
        type_ (PostAdvV1PromotionAdvertsType | Unset):
        order (PostAdvV1PromotionAdvertsOrder | Unset):
        direction (PostAdvV1PromotionAdvertsDirection | Unset):
        body (list[int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV1PromotionAdvertsResponse401 | PostAdvV1PromotionAdvertsResponse429 | list[ResponseInfoAdvertType8] | str
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
