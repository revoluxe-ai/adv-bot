from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v0_normquery_set_minus_response_401 import (
    PostAdvV0NormquerySetMinusResponse401,
)
from ...models.post_adv_v0_normquery_set_minus_response_429 import (
    PostAdvV0NormquerySetMinusResponse429,
)
from ...models.response_400 import Response400
from ...models.standardized_batch_error import StandardizedBatchError
from ...models.v0_set_minus_norm_query_request import V0SetMinusNormQueryRequest
from ...types import Response


def _get_kwargs(
    *,
    body: V0SetMinusNormQueryRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v0/normquery/set-minus",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    Any
    | PostAdvV0NormquerySetMinusResponse401
    | PostAdvV0NormquerySetMinusResponse429
    | Response400
    | StandardizedBatchError
    | None
):
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = Response400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV0NormquerySetMinusResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = StandardizedBatchError.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostAdvV0NormquerySetMinusResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    Any
    | PostAdvV0NormquerySetMinusResponse401
    | PostAdvV0NormquerySetMinusResponse429
    | Response400
    | StandardizedBatchError
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
    body: V0SetMinusNormQueryRequest,
) -> Response[
    Any
    | PostAdvV0NormquerySetMinusResponse401
    | PostAdvV0NormquerySetMinusResponse429
    | Response400
    | StandardizedBatchError
]:
    r"""Ustanovka i udalenie minus-fraz

     Metod ustanavlivaet i udaljaet minus-frazy v kampanijah c:
      - ruchnoj stavkoj
      - model'ju oplaty `cpm` — za pokazy

    <div class=\"description_important\">
      Otpravka pustogo massiva udaljaet vse minus-frazy
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0SetMinusNormQueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV0NormquerySetMinusResponse401 | PostAdvV0NormquerySetMinusResponse429 | Response400 | StandardizedBatchError]
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
    body: V0SetMinusNormQueryRequest,
) -> (
    Any
    | PostAdvV0NormquerySetMinusResponse401
    | PostAdvV0NormquerySetMinusResponse429
    | Response400
    | StandardizedBatchError
    | None
):
    r"""Ustanovka i udalenie minus-fraz

     Metod ustanavlivaet i udaljaet minus-frazy v kampanijah c:
      - ruchnoj stavkoj
      - model'ju oplaty `cpm` — za pokazy

    <div class=\"description_important\">
      Otpravka pustogo massiva udaljaet vse minus-frazy
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0SetMinusNormQueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV0NormquerySetMinusResponse401 | PostAdvV0NormquerySetMinusResponse429 | Response400 | StandardizedBatchError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: V0SetMinusNormQueryRequest,
) -> Response[
    Any
    | PostAdvV0NormquerySetMinusResponse401
    | PostAdvV0NormquerySetMinusResponse429
    | Response400
    | StandardizedBatchError
]:
    r"""Ustanovka i udalenie minus-fraz

     Metod ustanavlivaet i udaljaet minus-frazy v kampanijah c:
      - ruchnoj stavkoj
      - model'ju oplaty `cpm` — za pokazy

    <div class=\"description_important\">
      Otpravka pustogo massiva udaljaet vse minus-frazy
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0SetMinusNormQueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV0NormquerySetMinusResponse401 | PostAdvV0NormquerySetMinusResponse429 | Response400 | StandardizedBatchError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: V0SetMinusNormQueryRequest,
) -> (
    Any
    | PostAdvV0NormquerySetMinusResponse401
    | PostAdvV0NormquerySetMinusResponse429
    | Response400
    | StandardizedBatchError
    | None
):
    r"""Ustanovka i udalenie minus-fraz

     Metod ustanavlivaet i udaljaet minus-frazy v kampanijah c:
      - ruchnoj stavkoj
      - model'ju oplaty `cpm` — za pokazy

    <div class=\"description_important\">
      Otpravka pustogo massiva udaljaet vse minus-frazy
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 10 zaprosov |
    </div>

    Args:
        body (V0SetMinusNormQueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV0NormquerySetMinusResponse401 | PostAdvV0NormquerySetMinusResponse429 | Response400 | StandardizedBatchError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
