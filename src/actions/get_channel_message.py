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
from ._graph import (
    graph_request_error,
    graph_token_rejected,
    graph_url,
    encode_graph_path_segment,
)
from ..auth import oauth_token_client, validate_oauth_configuration
from soar_sdk.action_results import ActionOutput, ActionResult, OutputField
from soar_sdk.params import Param, Params
from ..asset import Asset


class GetChannelMessageParams(Params):
    group_id: str = Param(
        description="ID of group", primary=True, cef_types=["ms teams group id"]
    )
    channel_id: str = Param(
        description="ID of channel", primary=True, cef_types=["ms teams channel id"]
    )
    message_id: str = Param(description="ID of message")


class OdataOutput(ActionOutput):
    type: str | None = OutputField(
        example_values=["#microsoft.graph.teamworkUserIdentity"]
    )


class BodyOutput(ActionOutput):
    content: str | None = OutputField(example_values=["test message"])
    contentType: str | None = OutputField(example_values=["html"])


class UserOutput(ActionOutput):
    id: str | None = OutputField(
        example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"]
    )
    tenantId: str | None = OutputField(
        example_values=["149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0"]
    )
    odata: OdataOutput | None
    displayName: str | None = OutputField(example_values=["Test User"])
    userIdentityType: str | None = OutputField(example_values=["aadUser"])


class FromOutput(ActionOutput):
    user: UserOutput | None
    device: str | None
    application: str | None


class ChannelidentityOutput(ActionOutput):
    teamId: str | None = OutputField(
        example_values=["hfyr6hdhyr6s-d42a-452b-9155-379764077e25"]
    )
    channelId: str | None = OutputField(
        example_values=["10:2daiuhf4c29f6d7041eca70b67979r245437@thread.v2"]
    )


class GetChannelMessageOutput(ActionOutput):
    odata: OdataOutput | None
    body: BodyOutput | None
    createdDateTime: str | None = OutputField(
        example_values=["2021-03-12T06:02:01.352Z"]
    )
    deletedDateTime: str | None
    etag: str | None = OutputField(example_values=["1615528921352"])
    eventDetail: str | None
    id: str | None = OutputField(example_values=["1517826451101"])
    importance: str | None = OutputField(example_values=["normal"])
    lastEditedDateTime: str | None
    lastModifiedDateTime: str | None = OutputField(
        example_values=["2021-03-12T06:02:01.352Z"]
    )
    locale: str | None
    messageType: str | None = OutputField(example_values=["message"])
    policyViolation: str | None
    replyToId: str | None
    subject: str | None
    summary: str | None
    webUrl: str | None
    from_: FromOutput | None = OutputField(alias="from")
    chatId: str | None
    channelIdentity: ChannelidentityOutput | None


def get_channel_message(
    params: GetChannelMessageParams, soar: SOARClient, asset: Asset
) -> GetChannelMessageOutput:
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        auth = StaticTokenAuth(oauth_client.get_valid_token(auto_refresh=True))
        group_id = encode_graph_path_segment(params.group_id)
        channel_id = encode_graph_path_segment(params.channel_id)
        channels: list[dict] = []
        endpoint = f"/teams/{group_id}/channels"
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
        if not any(channel.get("id") == params.channel_id for channel in channels):
            return ActionResult(
                False,
                f"Channel {params.channel_id} does not belongs to group {params.group_id}",
                params.model_dump(by_alias=True),
            )
        endpoint = graph_url(
            f"/teams/{group_id}/channels/{channel_id}/messages/"
            f"{encode_graph_path_segment(params.message_id)}"
        )
        with httpx.Client(
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            verify=True,
        ) as client:
            response = client.get(endpoint, auth=auth)
            if graph_token_rejected(response):
                stored_token = oauth_client.get_stored_token()
                if stored_token is not None and stored_token.refresh_token:
                    auth = StaticTokenAuth(
                        oauth_client.refresh_token(stored_token.refresh_token)
                    )
                    response = client.get(endpoint, auth=auth)
            response.raise_for_status()
            result = response.json()
        soar.set_message("Message successfully retrieved")
        return GetChannelMessageOutput(**result)
    except Exception as exc:
        message = graph_request_error(exc).replace("teamId", "'group_id'")
        return ActionResult(False, message, params.model_dump(by_alias=True))
