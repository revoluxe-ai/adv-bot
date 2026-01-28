from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v0_normquery_get_bids_response_401 import (
    PostAdvV0NormqueryGetBidsResponse401,
)
from ...models.post_adv_v0_normquery_get_bids_response_429 import (
    PostAdvV0NormqueryGetBidsResponse429,
)
from ...models.response_400 import Response400
from ...models.standardized_batch_error import StandardizedBatchError
from ...models.v0_get_norm_query_bids_request import V0GetNormQueryBidsRequest
from ...models.v0_get_norm_query_bids_response import V0GetNormQueryBidsResponse
from ...types import Response


def _get_kwargs(
    *,
    body: V0GetNormQueryBidsRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v0/normquery/get-bids",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostAdvV0NormqueryGetBidsResponse401
    | PostAdvV0NormqueryGetBidsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryBidsResponse
    | None
):
    if response.status_code == 200:
        response_200 = V0GetNormQueryBidsResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV0NormqueryGetBidsResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = StandardizedBatchError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostAdvV0NormqueryGetBidsResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostAdvV0NormqueryGetBidsResponse401
    | PostAdvV0NormqueryGetBidsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryBidsResponse
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: V0GetNormQueryBidsRequest,
) -> Response[
    PostAdvV0NormqueryGetBidsResponse401
    | PostAdvV0NormqueryGetBidsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryBidsResponse
]:
    r"""Spisok stavok poiskovyh klasterov

     Metod vozvraschaet spisok poiskovyh klasterov so stavkami po:
      - ID kampanij
      - artikulam WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0GetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV0NormqueryGetBidsResponse401 | PostAdvV0NormqueryGetBidsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryBidsResponse]
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
    client: AuthenticatedClient | Client,
    body: V0GetNormQueryBidsRequest,
) -> (
    PostAdvV0NormqueryGetBidsResponse401
    | PostAdvV0NormqueryGetBidsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryBidsResponse
    | None
):
    r"""Spisok stavok poiskovyh klasterov

     Metod vozvraschaet spisok poiskovyh klasterov so stavkami po:
      - ID kampanij
      - artikulam WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0GetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV0NormqueryGetBidsResponse401 | PostAdvV0NormqueryGetBidsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryBidsResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: V0GetNormQueryBidsRequest,
) -> Response[
    PostAdvV0NormqueryGetBidsResponse401
    | PostAdvV0NormqueryGetBidsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryBidsResponse
]:
    r"""Spisok stavok poiskovyh klasterov

     Metod vozvraschaet spisok poiskovyh klasterov so stavkami po:
      - ID kampanij
      - artikulam WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0GetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostAdvV0NormqueryGetBidsResponse401 | PostAdvV0NormqueryGetBidsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryBidsResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: V0GetNormQueryBidsRequest,
) -> (
    PostAdvV0NormqueryGetBidsResponse401
    | PostAdvV0NormqueryGetBidsResponse429
    | Response400
    | StandardizedBatchError
    | V0GetNormQueryBidsResponse
    | None
):
    r"""Spisok stavok poiskovyh klasterov

     Metod vozvraschaet spisok poiskovyh klasterov so stavkami po:
      - ID kampanij
      - artikulam WB

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0GetNormQueryBidsRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostAdvV0NormqueryGetBidsResponse401 | PostAdvV0NormqueryGetBidsResponse429 | Response400 | StandardizedBatchError | V0GetNormQueryBidsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
