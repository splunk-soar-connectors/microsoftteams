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


class SendChatMessageParams(Params):
    chat_id: str = Param(
        description="ID of the chat to send message to",
        primary=True,
        cef_types=["ms teams chat id"],
    )
    message: str = Param(description="Message content to send")


class UserOutput(ActionOutput):
    id: str | None = OutputField(cef_types=["ms teams user id"])
    displayName: str | None


class FromOutput(ActionOutput):
    user: UserOutput | None


class BodyOutput(ActionOutput):
    content: str | None = OutputField(column_name="Message")
    contentType: str | None


class AttachmentsOutput(ActionOutput):
    content: str | None
    contentType: str | None
    contentUrl: str | None = OutputField(cef_types=["url"])
    id: str | None = OutputField(cef_types=["ms teams attachment id"])
    name: str | None
    teamsAppId: str | None
    thumbnailUrl: str | None = OutputField(cef_types=["url"])


class ChannelidentityOutput(ActionOutput):
    channelId: str | None = OutputField(cef_types=["ms teams channel id"])
    teamId: str | None = OutputField(cef_types=["ms teams team id"])


class SendChatMessageOutput(ActionOutput):
    id: str | None = OutputField(
        column_name="Message ID", cef_types=["ms teams message id"]
    )
    chatId: str | None = OutputField(cef_types=["ms teams chat id"])
    createdDateTime: str | None
    deletedDateTime: str | None
    lastModifiedDateTime: str | None
    lastEditedDateTime: str | None
    etag: str | None
    importance: str | None
    locale: str | None
    messageType: str | None
    replyToId: str | None = OutputField(cef_types=["ms teams message id"])
    subject: str | None
    summary: str | None
    webUrl: str | None = OutputField(cef_types=["url"])
    from_: FromOutput | None = OutputField(alias="from")
    body: BodyOutput | None
    attachments: list[AttachmentsOutput] | None
    channelIdentity: ChannelidentityOutput | None


def send_chat_message(
    params: SendChatMessageParams, soar: SOARClient, asset: Asset
) -> SendChatMessageOutput:
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        auth = StaticTokenAuth(oauth_client.get_valid_token(auto_refresh=True))
        endpoint = graph_url(
            f"/chats/{encode_graph_path_segment(params.chat_id)}/messages"
        )
        with httpx.Client(
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            verify=True,
        ) as client:
            response = client.post(
                endpoint,
                auth=auth,
                json={"body": {"contentType": "html", "content": params.message}},
            )
            if graph_token_rejected(response):
                stored_token = oauth_client.get_stored_token()
                if stored_token is not None and stored_token.refresh_token:
                    auth = StaticTokenAuth(
                        oauth_client.refresh_token(stored_token.refresh_token)
                    )
                    response = client.post(
                        endpoint,
                        auth=auth,
                        json={
                            "body": {"contentType": "html", "content": params.message}
                        },
                    )
            response.raise_for_status()
            data = response.json()
        soar.set_message("Message sent to chat successfully")
        return SendChatMessageOutput(**data)
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
