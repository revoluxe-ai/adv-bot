from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.field_4_xx_response import Field4XxResponse
from ...models.get_api_v1_acceptance_report_tasks_task_id_download_response_200_item import (
    GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item,
)
from ...types import Response


def _get_kwargs(
    task_id: str,
) -> Dict[str, Any]:

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/acceptance_report/tasks/{task_id}/download".format(
            task_id=task_id,
        ),
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        Any,
        Field4XxResponse,
        List["GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item"],
    ]
]:
    if response.status_code == HTTPStatus.OK:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = (
                GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item.from_dict(
                    response_200_item_data
                )
            )

            response_200.append(response_200_item)

        return response_200
    if response.status_code == HTTPStatus.NO_CONTENT:
        response_204 = cast(Any, None)
        return response_204
    if response.status_code == HTTPStatus.BAD_REQUEST:
        response_400 = Field4XxResponse.from_dict(response.json())

        return response_400
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        response_401 = cast(Any, None)
        return response_401
    if response.status_code == HTTPStatus.PAYMENT_REQUIRED:
        response_402 = cast(Any, None)
        return response_402
    if response.status_code == HTTPStatus.NOT_FOUND:
        response_404 = Field4XxResponse.from_dict(response.json())

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
) -> Response[
    Union[
        Any,
        Field4XxResponse,
        List["GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item"],
    ]
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[
    Union[
        Any,
        Field4XxResponse,
        List["GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item"],
    ]
]:
    r"""Get the Report

     Returns the report by task ID

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        task_id (str):  Example: 06e06887-9d9f-491f-b16a-bb1766fcb8d2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Field4XxResponse, List['GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item']]]
    """

    kwargs = _get_kwargs(
        task_id=task_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    task_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[
        Any,
        Field4XxResponse,
        List["GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item"],
    ]
]:
    r"""Get the Report

     Returns the report by task ID

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        task_id (str):  Example: 06e06887-9d9f-491f-b16a-bb1766fcb8d2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Field4XxResponse, List['GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item']]
    """

    return sync_detailed(
        task_id=task_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    task_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[
    Union[
        Any,
        Field4XxResponse,
        List["GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item"],
    ]
]:
    r"""Get the Report

     Returns the report by task ID

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        task_id (str):  Example: 06e06887-9d9f-491f-b16a-bb1766fcb8d2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, Field4XxResponse, List['GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item']]]
    """

    kwargs = _get_kwargs(
        task_id=task_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    task_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[
    Union[
        Any,
        Field4XxResponse,
        List["GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item"],
    ]
]:
    r"""Get the Report

     Returns the report by task ID

    <div class=\"description_limit\">
    <a href=\"/openapi/api-information#tag/introduction/Rate-Limits\">Request limit</a> per one seller
    account:


    | Type | Period | Limit | Interval | Burst |
    | --- | --- | --- | --- | --- |
    | Personal | 1 min | 1 request | 1 min | 1 request |
    | Service | 1 min | 1 request | 1 min | 1 request |
    | Base with secret | 1 min | 1 request | 1 min | 1 request |
    | Base | 1 h | 2 requests | 30 min | 1 request |
    </div>

    Args:
        task_id (str):  Example: 06e06887-9d9f-491f-b16a-bb1766fcb8d2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, Field4XxResponse, List['GetApiV1AcceptanceReportTasksTaskIdDownloadResponse200Item']]
    """

    return (
        await asyncio_detailed(
            task_id=task_id,
            client=client,
        )
    ).parsed
