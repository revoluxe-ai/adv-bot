import datetime
from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.v0_keywords_statistics_response import V0KeywordsStatisticsResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["advert_id"] = advert_id

    json_from_ = from_.isoformat()
    params["from"] = json_from_

    json_to = to.isoformat()
    params["to"] = json_to

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/adv/v0/stats/keywords",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = V0KeywordsStatisticsResponse.from_dict(response.json())

        return response_200
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = ErrorResponse.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.NOT_FOUND:
        response_404 = ErrorResponse.from_dict(response.json())

        return response_404
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        response_429 = cast(Any, None)
        return response_429
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> Response[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]:
    r"""Statistika po kljuchevym frazam

     Metod formiruet statistiku po kljuchevym frazam iz poiskovoj stroki: kolichestvo prosmotrov tovara i
    zatraty po odnoj kljuchevoj fraze. Podhodit dlja kampanij c edinoj i ruchnoj stavkoj.
    <br><br>
    Statistika formiruetsja za kazhdyj den', kogda kampanija byla aktivna. V odnom zaprose mozhno
    poluchit' dannye maksimum za 7 dnej.
    <br>
    Dannye obnovljajutsja kazhdyj chas.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]
    """

    kwargs = _get_kwargs(
        advert_id=advert_id,
        from_=from_,
        to=to,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> Optional[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]:
    r"""Statistika po kljuchevym frazam

     Metod formiruet statistiku po kljuchevym frazam iz poiskovoj stroki: kolichestvo prosmotrov tovara i
    zatraty po odnoj kljuchevoj fraze. Podhodit dlja kampanij c edinoj i ruchnoj stavkoj.
    <br><br>
    Statistika formiruetsja za kazhdyj den', kogda kampanija byla aktivna. V odnom zaprose mozhno
    poluchit' dannye maksimum za 7 dnej.
    <br>
    Dannye obnovljajutsja kazhdyj chas.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]
    """

    return sync_detailed(
        client=client,
        advert_id=advert_id,
        from_=from_,
        to=to,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> Response[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]:
    r"""Statistika po kljuchevym frazam

     Metod formiruet statistiku po kljuchevym frazam iz poiskovoj stroki: kolichestvo prosmotrov tovara i
    zatraty po odnoj kljuchevoj fraze. Podhodit dlja kampanij c edinoj i ruchnoj stavkoj.
    <br><br>
    Statistika formiruetsja za kazhdyj den', kogda kampanija byla aktivna. V odnom zaprose mozhno
    poluchit' dannye maksimum za 7 dnej.
    <br>
    Dannye obnovljajutsja kazhdyj chas.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]
    """

    kwargs = _get_kwargs(
        advert_id=advert_id,
        from_=from_,
        to=to,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    advert_id: int,
    from_: datetime.date,
    to: datetime.date,
) -> Optional[Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]]:
    r"""Statistika po kljuchevym frazam

     Metod formiruet statistiku po kljuchevym frazam iz poiskovoj stroki: kolichestvo prosmotrov tovara i
    zatraty po odnoj kljuchevoj fraze. Podhodit dlja kampanij c edinoj i ruchnoj stavkoj.
    <br><br>
    Statistika formiruetsja za kazhdyj den', kogda kampanija byla aktivna. V odnom zaprose mozhno
    poluchit' dannye maksimum za 7 dnej.
    <br>
    Dannye obnovljajutsja kazhdyj chas.

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/Vvedenie/Limity-zaprosov\">Limit zaprosov</a> na odin akkaunt
    prodavtsa:

    | Period | Limit | Interval | Vsplesk |
    | --- | --- | --- | --- |
    | 1 sekunda | 4 zaprosa | 250 millisekund | 4 zaprosa |
    </div>

    Args:
        advert_id (int):
        from_ (datetime.date):
        to (datetime.date):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorResponse, V0KeywordsStatisticsResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            advert_id=advert_id,
            from_=from_,
            to=to,
        )
    ).parsed
