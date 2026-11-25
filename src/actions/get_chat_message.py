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


class GetChatMessageParams(Params):
    chat_id: str = Param(
        column_name="Chat ID",
        description="ID of chat",
        primary=True,
        cef_types=["ms teams chat id"],
    )
    message_id: str = Param(description="ID of message")


class OdataOutput(ActionOutput):
    type: str | None


class BodyOutput(ActionOutput):
    content: str | None = OutputField(example_values=["test message"])
    contentType: str | None = OutputField(example_values=["text"])


class UserOutput(ActionOutput):
    odata: OdataOutput | None
    displayName: str | None = OutputField(example_values=["Test User"])
    id: str | None = OutputField(
        example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"]
    )
    userIdentityType: str | None = OutputField(example_values=["aadUser"])
    tenantId: str | None = OutputField(example_values=["aadUser"])


class FromOutput(ActionOutput):
    application: str | None
    device: str | None
    user: UserOutput | None


class AttachmentsOutput(ActionOutput):
    id: str | None = OutputField(example_values=["1722330920100"])
    name: str | None
    content: str | None = OutputField(
        example_values=[
            '{"messageId":"1722330920117","messagePreview":"How are you?","messageSender":{"application":null,"device":null,"user":{"userIdentityType":"aadUser","tenantId":"149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0","id":"hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f","displayName":"Test User"}}}'
        ]
    )
    contentUrl: str | None
    teamsAppId: str | None
    contentType: str | None = OutputField(example_values=["messageReference"])
    thumbnailUrl: str | None


class GetChatMessageOutput(ActionOutput):
    id: str | None = OutputField(
        column_name="Message ID", example_values=["1517826451101"]
    )
    odata: OdataOutput | None
    body: BodyOutput | None
    createdDateTime: str | None = OutputField(
        example_values=["2021-03-12T06:02:01.352Z"]
    )
    deletedDateTime: str | None
    etag: str | None = OutputField(example_values=["1615528921765"])
    from_: FromOutput | None = OutputField(alias="from")
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
    chatId: str | None = OutputField(
        example_values=[
            "10:1c06006a-1885-401b-8dd2-b23e21dtest1_cbb6948d6abeeac89ae@unq.gbl.spaces"
        ]
    )
    attachments: list[AttachmentsOutput] | None
    eventDetail: str | None
    channelIdentity: str | None


def get_chat_message(
    params: GetChatMessageParams, soar: SOARClient, asset: Asset
) -> GetChatMessageOutput:
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        auth = StaticTokenAuth(oauth_client.get_valid_token(auto_refresh=True))
        endpoint = graph_url(
            f"/chats/{encode_graph_path_segment(params.chat_id)}/messages/"
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
            data = response.json()
        soar.set_message("Message successfully retrieved")
        return GetChatMessageOutput(**data)
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
