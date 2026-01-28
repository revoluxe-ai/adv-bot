from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v1_budget_deposit_body import PostAdvV1BudgetDepositBody
from ...models.post_adv_v1_budget_deposit_response_400 import (
    PostAdvV1BudgetDepositResponse400,
)
from ...models.post_adv_v1_budget_deposit_response_401 import (
    PostAdvV1BudgetDepositResponse401,
)
from ...models.post_adv_v1_budget_deposit_response_429 import (
    PostAdvV1BudgetDepositResponse429,
)
from ...models.response_with_return import ResponseWithReturn
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1BudgetDepositBody,
    id: int,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/budget/deposit",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV1BudgetDepositResponse400
    | PostAdvV1BudgetDepositResponse401
    | PostAdvV1BudgetDepositResponse429
    | ResponseWithReturn
    | None
):
    if response.status_code == 200:
        response_200 = ResponseWithReturn.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = PostAdvV1BudgetDepositResponse400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV1BudgetDepositResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 429:
        response_429 = PostAdvV1BudgetDepositResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV1BudgetDepositResponse400
    | PostAdvV1BudgetDepositResponse401
    | PostAdvV1BudgetDepositResponse429
    | ResponseWithReturn
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
    body: PostAdvV1BudgetDepositBody,
    id: int,
) -> Response[
    PostAdvV1BudgetDepositResponse400
    | PostAdvV1BudgetDepositResponse401
    | PostAdvV1BudgetDepositResponse429
    | ResponseWithReturn
]:
    r"""Top-up of the Campaign Budget

     The method tops up the campaign [budget](/openapi/promotion#tag/Finance/paths/~1adv~1v1~1budget/get)
    in the status `11` — paused.<br>
    To launch the campaign after topping up the budget, use the [Launch
    campaign](/openapi/promotion#tag/Campaigns-Management/paths/~1adv~1v0~1start/get) method.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1BudgetDepositBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV1BudgetDepositResponse400 | PostAdvV1BudgetDepositResponse401 | PostAdvV1BudgetDepositResponse429 | ResponseWithReturn]
    """

    kwargs = _get_kwargs(
        body=body,
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1BudgetDepositBody,
    id: int,
) -> (
    PostAdvV1BudgetDepositResponse400
    | PostAdvV1BudgetDepositResponse401
    | PostAdvV1BudgetDepositResponse429
    | ResponseWithReturn
    | None
):
    r"""Top-up of the Campaign Budget

     The method tops up the campaign [budget](/openapi/promotion#tag/Finance/paths/~1adv~1v1~1budget/get)
    in the status `11` — paused.<br>
    To launch the campaign after topping up the budget, use the [Launch
    campaign](/openapi/promotion#tag/Campaigns-Management/paths/~1adv~1v0~1start/get) method.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1BudgetDepositBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV1BudgetDepositResponse400 | PostAdvV1BudgetDepositResponse401 | PostAdvV1BudgetDepositResponse429 | ResponseWithReturn
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1BudgetDepositBody,
    id: int,
) -> Response[
    PostAdvV1BudgetDepositResponse400
    | PostAdvV1BudgetDepositResponse401
    | PostAdvV1BudgetDepositResponse429
    | ResponseWithReturn
]:
    r"""Top-up of the Campaign Budget

     The method tops up the campaign [budget](/openapi/promotion#tag/Finance/paths/~1adv~1v1~1budget/get)
    in the status `11` — paused.<br>
    To launch the campaign after topping up the budget, use the [Launch
    campaign](/openapi/promotion#tag/Campaigns-Management/paths/~1adv~1v0~1start/get) method.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1BudgetDepositBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV1BudgetDepositResponse400 | PostAdvV1BudgetDepositResponse401 | PostAdvV1BudgetDepositResponse429 | ResponseWithReturn]
    """

    kwargs = _get_kwargs(
        body=body,
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1BudgetDepositBody,
    id: int,
) -> (
    PostAdvV1BudgetDepositResponse400
    | PostAdvV1BudgetDepositResponse401
    | PostAdvV1BudgetDepositResponse429
    | ResponseWithReturn
    | None
):
    r"""Top-up of the Campaign Budget

     The method tops up the campaign [budget](/openapi/promotion#tag/Finance/paths/~1adv~1v1~1budget/get)
    in the status `11` — paused.<br>
    To launch the campaign after topping up the budget, use the [Launch
    campaign](/openapi/promotion#tag/Campaigns-Management/paths/~1adv~1v0~1start/get) method.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Introduction/Rate-Limits\">Request limit</a> per one seller's
    account:

    | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- |
    | 1 second | 1 request | 1 second | 5 requests |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1BudgetDepositBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV1BudgetDepositResponse400 | PostAdvV1BudgetDepositResponse401 | PostAdvV1BudgetDepositResponse429 | ResponseWithReturn
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
