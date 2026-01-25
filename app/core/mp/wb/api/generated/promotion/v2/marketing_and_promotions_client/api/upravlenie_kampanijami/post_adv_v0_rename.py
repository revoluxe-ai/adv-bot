from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_adv_v0_rename_body import PostAdvV0RenameBody
from ...models.post_adv_v0_rename_response_401 import PostAdvV0RenameResponse401
from ...models.post_adv_v0_rename_response_429 import PostAdvV0RenameResponse429
from ...types import Response


def _get_kwargs(
    *,
    body: PostAdvV0RenameBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/adv/v0/rename",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str | None:
    if response.status_code == 200:
        response_200 = cast(Any, None)
        return response_200

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = PostAdvV0RenameResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 422:
        response_422 = response.text
        return response_422

    if response.status_code == 429:
        response_429 = PostAdvV0RenameResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV0RenameBody,
) -> Response[Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str]:
    r"""Pereimenovanie kampanii

     Metod menjaet nazvanie
    [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get). Eto mozhno sdelat'
    v ljuboj moment suschestvovanija kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0RenameBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str]
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
    body: PostAdvV0RenameBody,
) -> Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str | None:
    r"""Pereimenovanie kampanii

     Metod menjaet nazvanie
    [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get). Eto mozhno sdelat'
    v ljuboj moment suschestvovanija kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0RenameBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV0RenameBody,
) -> Response[Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str]:
    r"""Pereimenovanie kampanii

     Metod menjaet nazvanie
    [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get). Eto mozhno sdelat'
    v ljuboj moment suschestvovanija kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0RenameBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostAdvV0RenameBody,
) -> Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str | None:
    r"""Pereimenovanie kampanii

     Metod menjaet nazvanie
    [kampanii](/openapi/promotion#tag/Kampanii/paths/~1api~1advert~1v2~1adverts/get). Eto mozhno sdelat'
    v ljuboj moment suschestvovanija kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 5 zaprosov | 200 millisekund | 5 zaprosov |
    </div>

    Args:
        body (PostAdvV0RenameBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PostAdvV0RenameResponse401 | PostAdvV0RenameResponse429 | str
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
