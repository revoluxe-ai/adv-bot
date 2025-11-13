from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.field_400_response import Field400Response
from ...models.post_adv_v1_auto_set_excluded_body import PostAdvV1AutoSetExcludedBody
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    params: Dict[str, Any] = {}

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": "/adv/v1/auto/set-excluded",
        "params": params,
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, Field400Response]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = cast(Any, None)
        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = Field400Response.from_dict(response.json())

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
) -> Response[Union[Any, Field400Response]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> Response[Union[Any, Field400Response]]:
    r"""Ustanovka/udalenie minus-fraz dlja kampanii s edinoj stavkoj

     Metod ustanavlivaet i udaljaet minus-frazy dlja kampanii s [edinoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v1~1save-ad/post).<br>

    Dannye frazy mozhno vybrat' iz spiska zaprosov, po kotorym pokupateli nahodili vash tovar.
    Spisok zaprosov mozhno poluchit' v [statistike po kljuchevym
    frazam](/openapi/promotion#tag/Statistika/paths/~1adv~1v0~1stats~1keywords/get).<br>

    Otpravka pustogo massiva udaljaet vse minus-frazy iz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 1 zapros | 6 sekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Field400Response]]
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
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> Optional[Union[Any, Field400Response]]:
    r"""Ustanovka/udalenie minus-fraz dlja kampanii s edinoj stavkoj

     Metod ustanavlivaet i udaljaet minus-frazy dlja kampanii s [edinoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v1~1save-ad/post).<br>

    Dannye frazy mozhno vybrat' iz spiska zaprosov, po kotorym pokupateli nahodili vash tovar.
    Spisok zaprosov mozhno poluchit' v [statistike po kljuchevym
    frazam](/openapi/promotion#tag/Statistika/paths/~1adv~1v0~1stats~1keywords/get).<br>

    Otpravka pustogo massiva udaljaet vse minus-frazy iz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 1 zapros | 6 sekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Field400Response]
    """

    return sync_detailed(
        client=client,
        body=body,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> Response[Union[Any, Field400Response]]:
    r"""Ustanovka/udalenie minus-fraz dlja kampanii s edinoj stavkoj

     Metod ustanavlivaet i udaljaet minus-frazy dlja kampanii s [edinoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v1~1save-ad/post).<br>

    Dannye frazy mozhno vybrat' iz spiska zaprosov, po kotorym pokupateli nahodili vash tovar.
    Spisok zaprosov mozhno poluchit' v [statistike po kljuchevym
    frazam](/openapi/promotion#tag/Statistika/paths/~1adv~1v0~1stats~1keywords/get).<br>

    Otpravka pustogo massiva udaljaet vse minus-frazy iz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 1 zapros | 6 sekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Field400Response]]
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
    body: PostAdvV1AutoSetExcludedBody,
    id: int,
) -> Optional[Union[Any, Field400Response]]:
    r"""Ustanovka/udalenie minus-fraz dlja kampanii s edinoj stavkoj

     Metod ustanavlivaet i udaljaet minus-frazy dlja kampanii s [edinoj
    stavkoj](/openapi/promotion#tag/Sozdanie-kampanij/paths/~1adv~1v1~1save-ad/post).<br>

    Dannye frazy mozhno vybrat' iz spiska zaprosov, po kotorym pokupateli nahodili vash tovar.
    Spisok zaprosov mozhno poluchit' v [statistike po kljuchevym
    frazam](/openapi/promotion#tag/Statistika/paths/~1adv~1v0~1stats~1keywords/get).<br>

    Otpravka pustogo massiva udaljaet vse minus-frazy iz kampanii.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sekund | 1 zapros | 6 sekund | 5 zaprosov |
    </div>

    Args:
        id (int):  Example: 1234567.
        body (PostAdvV1AutoSetExcludedBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Field400Response]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            id=id,
        )
    ).parsed
