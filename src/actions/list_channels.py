# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from soar_sdk.abstract import SOARClient
import httpx
from soar_sdk.auth import StaticTokenAuth
from soar_sdk.models.view import ViewContext
from ._graph import (
    encode_graph_path_segment,
    graph_request_error,
    graph_token_rejected,
    graph_url,
)
from ..auth import oauth_token_client, validate_oauth_configuration
from soar_sdk.action_results import ActionOutput, ActionResult, OutputField
from soar_sdk.params import Param, Params
from ..asset import Asset


class ListChannelsParams(Params):
    group_id: str = Param(
        description="ID of group", primary=True, cef_types=["ms teams group id"]
    )


class ListChannelsOutput(ActionOutput):
    description: str | None = OutputField(example_values=["Test team"])
    displayName: str | None = OutputField(example_values=["General"])
    email: str | None
    tenantId: str | None = OutputField(
        example_values=["149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0"]
    )
    isArchived: bool | None
    createdDateTime: str | None = OutputField(
        example_values=["2020-07-13T12:39:21.573Z"]
    )
    id: str | None = OutputField(
        cef_types=["ms teams channel id"],
        example_values=["78f4a378-e7d3-49c8-a8a7-645b886752d9"],
    )
    isFavoriteByDefault: str | None
    membershipType: str | None = OutputField(example_values=["standard"])
    webUrl: str | None


def display_channels(
    context: ViewContext,
    outputs: list[ListChannelsOutput],
    params: list[ListChannelsParams],
) -> dict:
    return {
        "container_id": context.container,
        "results": [
            {
                "param": param.model_dump(by_alias=True),
                "data": [output.model_dump(by_alias=True)],
            }
            for output, param in zip(outputs, params, strict=True)
        ],
    }


class ListChannelsSummary(ActionOutput):
    total_channels: int


def list_channels(
    params: ListChannelsParams, soar: SOARClient, asset: Asset
) -> list[ListChannelsOutput]:
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        token = oauth_client.get_valid_token(auto_refresh=True)
        auth = StaticTokenAuth(token)
        channels: list[dict] = []
        endpoint = f"/teams/{encode_graph_path_segment(params.group_id)}/channels"
        seen_endpoints: set[str] = set()
        with httpx.Client(
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            verify=True,
        ) as client:
            for _ in range(1000):
                if endpoint in seen_endpoints:
                    return ActionResult(
                        False,
                        "Microsoft Graph returned a non-progressing nextLink",
                        params.model_dump(by_alias=True),
                    )
                seen_endpoints.add(endpoint)
                response = client.get(graph_url(endpoint), auth=auth)
                if graph_token_rejected(response):
                    stored_token = oauth_client.get_stored_token()
                    if stored_token is not None and stored_token.refresh_token:
                        auth = StaticTokenAuth(
                            oauth_client.refresh_token(stored_token.refresh_token)
                        )
                        response = client.get(graph_url(endpoint), auth=auth)
                response.raise_for_status()
                page = response.json()
                channels.extend(page.get("value", []))
                endpoint = page.get("@odata.nextLink")
                if not endpoint:
                    break
            else:
                return ActionResult(
                    False,
                    "Microsoft Graph pagination exceeded the 1000-page limit",
                    params.model_dump(by_alias=True),
                )
        soar.set_summary(ListChannelsSummary(total_channels=len(channels)))
        return [ListChannelsOutput(**channel) for channel in channels]
    except Exception as exc:
        message = graph_request_error(exc).replace("teamId", "'group_id'")
        return ActionResult(False, message, params.model_dump(by_alias=True))
