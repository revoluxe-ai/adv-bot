from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_api_v2_upload_task_body import PostApiV2UploadTaskBody
from ...models.post_api_v2_upload_task_response_401 import (
    PostApiV2UploadTaskResponse401,
)
from ...models.post_api_v2_upload_task_response_429 import (
    PostApiV2UploadTaskResponse429,
)
from ...models.request_already_exists_error import RequestAlreadyExistsError
from ...models.response_error import ResponseError
from ...models.task_created import TaskCreated
from ...types import Response


def _get_kwargs(
    *,
    body: PostApiV2UploadTaskBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/upload/task",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostApiV2UploadTaskResponse401
    | PostApiV2UploadTaskResponse429
    | RequestAlreadyExistsError
    | ResponseError
    | TaskCreated
    | None
):
    if response.status_code == 200:
        response_200 = TaskCreated.from_dict(response.json())

        return response_200

    if response.status_code == 208:
        response_208 = RequestAlreadyExistsError.from_dict(response.json())

        return response_208

    if response.status_code == 400:
        response_400 = ResponseError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostApiV2UploadTaskResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseError.from_dict(response.json())

        return response_403

    if response.status_code == 422:
        response_422 = ResponseError.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = PostApiV2UploadTaskResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostApiV2UploadTaskResponse401
    | PostApiV2UploadTaskResponse429
    | RequestAlreadyExistsError
    | ResponseError
    | TaskCreated
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
    body: PostApiV2UploadTaskBody,
) -> Response[
    PostApiV2UploadTaskResponse401
    | PostApiV2UploadTaskResponse429
    | RequestAlreadyExistsError
    | ResponseError
    | TaskCreated
]:
    r"""Ustanovit' tseny i skidki

     Metod ustanavlivaet tseny i skidki dlja tovarov.
    <br><br>
    Chtoby ustanovit' tseny dlja razmerov tovara, ispol'zujte [otdel'nyj metod](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1size/post).

    <div class=\"description_important\">
      Poluchit' informatsiju o protsesse ustanovki tsen i skidok mozhno s pomosch'ju metodov <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1history~1tasks/get\">sostojanija</a> i <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1goods~1task/get\">detalizatsii</a> obrabotannoj
    zagruzki.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        body (PostApiV2UploadTaskBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiV2UploadTaskResponse401 | PostApiV2UploadTaskResponse429 | RequestAlreadyExistsError | ResponseError | TaskCreated]
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
    body: PostApiV2UploadTaskBody,
) -> (
    PostApiV2UploadTaskResponse401
    | PostApiV2UploadTaskResponse429
    | RequestAlreadyExistsError
    | ResponseError
    | TaskCreated
    | None
):
    r"""Ustanovit' tseny i skidki

     Metod ustanavlivaet tseny i skidki dlja tovarov.
    <br><br>
    Chtoby ustanovit' tseny dlja razmerov tovara, ispol'zujte [otdel'nyj metod](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1size/post).

    <div class=\"description_important\">
      Poluchit' informatsiju o protsesse ustanovki tsen i skidok mozhno s pomosch'ju metodov <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1history~1tasks/get\">sostojanija</a> i <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1goods~1task/get\">detalizatsii</a> obrabotannoj
    zagruzki.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        body (PostApiV2UploadTaskBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiV2UploadTaskResponse401 | PostApiV2UploadTaskResponse429 | RequestAlreadyExistsError | ResponseError | TaskCreated
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: PostApiV2UploadTaskBody,
) -> Response[
    PostApiV2UploadTaskResponse401
    | PostApiV2UploadTaskResponse429
    | RequestAlreadyExistsError
    | ResponseError
    | TaskCreated
]:
    r"""Ustanovit' tseny i skidki

     Metod ustanavlivaet tseny i skidki dlja tovarov.
    <br><br>
    Chtoby ustanovit' tseny dlja razmerov tovara, ispol'zujte [otdel'nyj metod](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1size/post).

    <div class=\"description_important\">
      Poluchit' informatsiju o protsesse ustanovki tsen i skidok mozhno s pomosch'ju metodov <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1history~1tasks/get\">sostojanija</a> i <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1goods~1task/get\">detalizatsii</a> obrabotannoj
    zagruzki.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        body (PostApiV2UploadTaskBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostApiV2UploadTaskResponse401 | PostApiV2UploadTaskResponse429 | RequestAlreadyExistsError | ResponseError | TaskCreated]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: PostApiV2UploadTaskBody,
) -> (
    PostApiV2UploadTaskResponse401
    | PostApiV2UploadTaskResponse429
    | RequestAlreadyExistsError
    | ResponseError
    | TaskCreated
    | None
):
    r"""Ustanovit' tseny i skidki

     Metod ustanavlivaet tseny i skidki dlja tovarov.
    <br><br>
    Chtoby ustanovit' tseny dlja razmerov tovara, ispol'zujte [otdel'nyj metod](/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1upload~1task~1size/post).

    <div class=\"description_important\">
      Poluchit' informatsiju o protsesse ustanovki tsen i skidok mozhno s pomosch'ju metodov <a
    href=\"/openapi/work-with-products#tag/Ceny-i-
    skidki/paths/~1api~1v2~1history~1tasks/get\">sostojanija</a> i <a href=\"/openapi/work-with-
    products#tag/Ceny-i-skidki/paths/~1api~1v2~1history~1goods~1task/get\">detalizatsii</a> obrabotannoj
    zagruzki.
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa dlja vseh metodov kategorii <strong>Tseny i skidki</strong>:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 6 sek | 10 zaprosov | 600 ms | 5 zaprosov |

    </div>

    Args:
        body (PostApiV2UploadTaskBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostApiV2UploadTaskResponse401 | PostApiV2UploadTaskResponse429 | RequestAlreadyExistsError | ResponseError | TaskCreated
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
