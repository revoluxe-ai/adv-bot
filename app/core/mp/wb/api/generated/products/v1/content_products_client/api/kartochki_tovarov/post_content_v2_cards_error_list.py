from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.post_content_v2_cards_error_list_response_401 import (
    PostContentV2CardsErrorListResponse401,
)
from ...models.post_content_v2_cards_error_list_response_429 import (
    PostContentV2CardsErrorListResponse429,
)
from ...models.request_public_viewer_public_errors_table_list_v2 import (
    RequestPublicViewerPublicErrorsTableListV2,
)
from ...models.response_body_content_error_400 import ResponseBodyContentError400
from ...models.response_body_content_error_403 import ResponseBodyContentError403
from ...models.response_public_viewer_public_errors_table_list_v2 import (
    ResponsePublicViewerPublicErrorsTableListV2,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: RequestPublicViewerPublicErrorsTableListV2,
    locale: str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["locale"] = locale

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/content/v2/cards/error/list",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    PostContentV2CardsErrorListResponse401
    | PostContentV2CardsErrorListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponsePublicViewerPublicErrorsTableListV2
    | None
):
    if response.status_code == 200:
        response_200 = ResponsePublicViewerPublicErrorsTableListV2.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 400:
        response_400 = ResponseBodyContentError400.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = PostContentV2CardsErrorListResponse401.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ResponseBodyContentError403.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = PostContentV2CardsErrorListResponse429.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[
    PostContentV2CardsErrorListResponse401
    | PostContentV2CardsErrorListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponsePublicViewerPublicErrorsTableListV2
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
    body: RequestPublicViewerPublicErrorsTableListV2,
    locale: str | Unset = UNSET,
) -> Response[
    PostContentV2CardsErrorListResponse401
    | PostContentV2CardsErrorListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponsePublicViewerPublicErrorsTableListV2
]:
    r"""Spisok nesozdannyh kartochek tovarov s oshibkami

     Metod vozvraschaet spisok kartochek tovarov ([chernovikov](https://seller.wildberries.ru/new-
    goods/error-cards)), pri sozdanii ili redaktirovanii kotoryh proizoshli oshibki, s opisaniem etih
    oshibok.
    <br><br>
    Dannye v otvete vozvraschajutsja paketami `batch`. Odin paket soderzhit:
      - vse oshibki po odnomu massivu `variants` odnogo zaprosa pri [sozdanii](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post) kartochek tovarov
      - vse oshibki odnogo zaprosa pri [sozdanii s prisoedineniem](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload~1add/post) ili
    [redaktirovanii](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post) kartochek tovarov
    <br><br>
    Chtoby poluchit' bolee 100 paketov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"cursor\": {
                \"limit\": 100
              },
              \"order\": {
                \"ascending\": true
              }
            }</pre>
      2. Skopirujte `\"updatedAt\":\"***\",\"batchUUID\":\"***\" `iz `cursor` otveta i vstav'te v
    `cursor` zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka ne poluchite v otvete `\"next\":false`. Eto budet oznachat',
    chto vy poluchili vse pakety.

    <div class=\"description_important\">
      Chtoby udalit' kartochku tovara iz spiska, sdelajte esche odin zapros na sozdanie, sozdanie s
    prisoedineniem ili redaktirovanie kartochki tovara s ispravlennymi oshibkami
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        locale (str | Unset):  Example: en.
        body (RequestPublicViewerPublicErrorsTableListV2):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsErrorListResponse401 | PostContentV2CardsErrorListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponsePublicViewerPublicErrorsTableListV2]
    """

    kwargs = _get_kwargs(
        body=body,
        locale=locale,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: RequestPublicViewerPublicErrorsTableListV2,
    locale: str | Unset = UNSET,
) -> (
    PostContentV2CardsErrorListResponse401
    | PostContentV2CardsErrorListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponsePublicViewerPublicErrorsTableListV2
    | None
):
    r"""Spisok nesozdannyh kartochek tovarov s oshibkami

     Metod vozvraschaet spisok kartochek tovarov ([chernovikov](https://seller.wildberries.ru/new-
    goods/error-cards)), pri sozdanii ili redaktirovanii kotoryh proizoshli oshibki, s opisaniem etih
    oshibok.
    <br><br>
    Dannye v otvete vozvraschajutsja paketami `batch`. Odin paket soderzhit:
      - vse oshibki po odnomu massivu `variants` odnogo zaprosa pri [sozdanii](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post) kartochek tovarov
      - vse oshibki odnogo zaprosa pri [sozdanii s prisoedineniem](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload~1add/post) ili
    [redaktirovanii](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post) kartochek tovarov
    <br><br>
    Chtoby poluchit' bolee 100 paketov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"cursor\": {
                \"limit\": 100
              },
              \"order\": {
                \"ascending\": true
              }
            }</pre>
      2. Skopirujte `\"updatedAt\":\"***\",\"batchUUID\":\"***\" `iz `cursor` otveta i vstav'te v
    `cursor` zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka ne poluchite v otvete `\"next\":false`. Eto budet oznachat',
    chto vy poluchili vse pakety.

    <div class=\"description_important\">
      Chtoby udalit' kartochku tovara iz spiska, sdelajte esche odin zapros na sozdanie, sozdanie s
    prisoedineniem ili redaktirovanie kartochki tovara s ispravlennymi oshibkami
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        locale (str | Unset):  Example: en.
        body (RequestPublicViewerPublicErrorsTableListV2):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsErrorListResponse401 | PostContentV2CardsErrorListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponsePublicViewerPublicErrorsTableListV2
    """

    return sync_detailed(
        client=client,
        body=body,
        locale=locale,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: RequestPublicViewerPublicErrorsTableListV2,
    locale: str | Unset = UNSET,
) -> Response[
    PostContentV2CardsErrorListResponse401
    | PostContentV2CardsErrorListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponsePublicViewerPublicErrorsTableListV2
]:
    r"""Spisok nesozdannyh kartochek tovarov s oshibkami

     Metod vozvraschaet spisok kartochek tovarov ([chernovikov](https://seller.wildberries.ru/new-
    goods/error-cards)), pri sozdanii ili redaktirovanii kotoryh proizoshli oshibki, s opisaniem etih
    oshibok.
    <br><br>
    Dannye v otvete vozvraschajutsja paketami `batch`. Odin paket soderzhit:
      - vse oshibki po odnomu massivu `variants` odnogo zaprosa pri [sozdanii](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post) kartochek tovarov
      - vse oshibki odnogo zaprosa pri [sozdanii s prisoedineniem](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload~1add/post) ili
    [redaktirovanii](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post) kartochek tovarov
    <br><br>
    Chtoby poluchit' bolee 100 paketov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"cursor\": {
                \"limit\": 100
              },
              \"order\": {
                \"ascending\": true
              }
            }</pre>
      2. Skopirujte `\"updatedAt\":\"***\",\"batchUUID\":\"***\" `iz `cursor` otveta i vstav'te v
    `cursor` zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka ne poluchite v otvete `\"next\":false`. Eto budet oznachat',
    chto vy poluchili vse pakety.

    <div class=\"description_important\">
      Chtoby udalit' kartochku tovara iz spiska, sdelajte esche odin zapros na sozdanie, sozdanie s
    prisoedineniem ili redaktirovanie kartochki tovara s ispravlennymi oshibkami
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        locale (str | Unset):  Example: en.
        body (RequestPublicViewerPublicErrorsTableListV2):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PostContentV2CardsErrorListResponse401 | PostContentV2CardsErrorListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponsePublicViewerPublicErrorsTableListV2]
    """

    kwargs = _get_kwargs(
        body=body,
        locale=locale,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: RequestPublicViewerPublicErrorsTableListV2,
    locale: str | Unset = UNSET,
) -> (
    PostContentV2CardsErrorListResponse401
    | PostContentV2CardsErrorListResponse429
    | ResponseBodyContentError400
    | ResponseBodyContentError403
    | ResponsePublicViewerPublicErrorsTableListV2
    | None
):
    r"""Spisok nesozdannyh kartochek tovarov s oshibkami

     Metod vozvraschaet spisok kartochek tovarov ([chernovikov](https://seller.wildberries.ru/new-
    goods/error-cards)), pri sozdanii ili redaktirovanii kotoryh proizoshli oshibki, s opisaniem etih
    oshibok.
    <br><br>
    Dannye v otvete vozvraschajutsja paketami `batch`. Odin paket soderzhit:
      - vse oshibki po odnomu massivu `variants` odnogo zaprosa pri [sozdanii](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload/post) kartochek tovarov
      - vse oshibki odnogo zaprosa pri [sozdanii s prisoedineniem](/openapi/work-with-
    products#tag/Sozdanie-kartochek-tovarov/paths/~1content~1v2~1cards~1upload~1add/post) ili
    [redaktirovanii](/openapi/work-with-products#tag/Kartochki-
    tovarov/paths/~1content~1v2~1cards~1update/post) kartochek tovarov
    <br><br>
    Chtoby poluchit' bolee 100 paketov, ispol'zujte paginatsiju:
      1. Sdelajte pervyj zapros: <br>
          <pre style=\"background-color: rgb(38 50 56 / 5%); color: #e53935\">
            {
              \"cursor\": {
                \"limit\": 100
              },
              \"order\": {
                \"ascending\": true
              }
            }</pre>
      2. Skopirujte `\"updatedAt\":\"***\",\"batchUUID\":\"***\" `iz `cursor` otveta i vstav'te v
    `cursor` zaprosa.
      3. Povtorite zapros.
      4. Povtorjajte punkty 2 i 3, poka ne poluchite v otvete `\"next\":false`. Eto budet oznachat',
    chto vy poluchili vse pakety.

    <div class=\"description_important\">
      Chtoby udalit' kartochku tovara iz spiska, sdelajte esche odin zapros na sozdanie, sozdanie s
    prisoedineniem ili redaktirovanie kartochki tovara s ispravlennymi oshibkami
    </div>

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 min | 10 zaprosov | 6 sek | 5 zaprosov |
    </div>

    Args:
        locale (str | Unset):  Example: en.
        body (RequestPublicViewerPublicErrorsTableListV2):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PostContentV2CardsErrorListResponse401 | PostContentV2CardsErrorListResponse429 | ResponseBodyContentError400 | ResponseBodyContentError403 | ResponsePublicViewerPublicErrorsTableListV2
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            locale=locale,
        )
    ).parsed
