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


class SendDirectMessageParams(Params):
    user_id: str = Param(
        description="ID of the user to send direct message to",
        primary=True,
        cef_types=["ms teams user id"],
    )
    message: str = Param(description="Message content to send")


class UserOutput(ActionOutput):
    id: str | None = OutputField(cef_types=["ms teams user id"])
    displayName: str | None


class FromOutput(ActionOutput):
    user: UserOutput | None


class BodyOutput(ActionOutput):
    content: str | None
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


class SendDirectMessageOutput(ActionOutput):
    id: str | None = OutputField(cef_types=["ms teams message id"])
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


def send_direct_message(
    params: SendDirectMessageParams, soar: SOARClient, asset: Asset
) -> SendDirectMessageOutput:
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        auth = StaticTokenAuth(oauth_client.get_valid_token(auto_refresh=True))
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        with httpx.Client(headers=headers, timeout=30.0, verify=True) as client:
            response = client.get(graph_url("/me"), auth=auth)
            if graph_token_rejected(response):
                stored_token = oauth_client.get_stored_token()
                if stored_token is not None and stored_token.refresh_token:
                    auth = StaticTokenAuth(
                        oauth_client.refresh_token(stored_token.refresh_token)
                    )
                    response = client.get(graph_url("/me"), auth=auth)
            response.raise_for_status()
            current_user = response.json()
            current_user_id = current_user.get("id")
            if not current_user_id:
                return ActionResult(
                    False,
                    "Failed to retrieve current user ID",
                    params.model_dump(by_alias=True),
                )

            response = client.get(graph_url("/me/chats"), auth=auth)
            if graph_token_rejected(response):
                stored_token = oauth_client.get_stored_token()
                if stored_token is not None and stored_token.refresh_token:
                    auth = StaticTokenAuth(
                        oauth_client.refresh_token(stored_token.refresh_token)
                    )
                    response = client.get(graph_url("/me/chats"), auth=auth)
            response.raise_for_status()
            chats = response.json()
            chat_id = None
            for chat in chats.get("value", []):
                members = chat.get("members", [])
                if (
                    chat.get("chatType") == "oneOnOne"
                    and len(members) == 2
                    and any(
                        member.get("userId") == params.user_id for member in members
                    )
                ):
                    chat_id = chat.get("id")
                    break

            if not chat_id:
                response = client.post(
                    graph_url("/chats"),
                    auth=auth,
                    json={
                        "chatType": "oneOnOne",
                        "members": [
                            {
                                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                                "roles": ["owner"],
                                "user@odata.bind": (
                                    "https://graph.microsoft.com/v1.0/users/"
                                    f"{encode_graph_path_segment(current_user_id)}"
                                ),
                            },
                            {
                                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                                "roles": ["owner"],
                                "user@odata.bind": (
                                    "https://graph.microsoft.com/v1.0/users/"
                                    f"{encode_graph_path_segment(params.user_id)}"
                                ),
                            },
                        ],
                    },
                )
                if graph_token_rejected(response):
                    stored_token = oauth_client.get_stored_token()
                    if stored_token is not None and stored_token.refresh_token:
                        auth = StaticTokenAuth(
                            oauth_client.refresh_token(stored_token.refresh_token)
                        )
                        response = client.post(
                            graph_url("/chats"),
                            auth=auth,
                            json={
                                "chatType": "oneOnOne",
                                "members": [
                                    {
                                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                                        "roles": ["owner"],
                                        "user@odata.bind": (
                                            "https://graph.microsoft.com/v1.0/users/"
                                            f"{encode_graph_path_segment(current_user_id)}"
                                        ),
                                    },
                                    {
                                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                                        "roles": ["owner"],
                                        "user@odata.bind": (
                                            "https://graph.microsoft.com/v1.0/users/"
                                            f"{encode_graph_path_segment(params.user_id)}"
                                        ),
                                    },
                                ],
                            },
                        )
                response.raise_for_status()
                created = response.json()
                chat_id = created.get("id")

            if not chat_id:
                return ActionResult(
                    False,
                    "Microsoft Teams did not return a chat identifier",
                    params.model_dump(by_alias=True),
                )

            endpoint = graph_url(
                f"/chats/{encode_graph_path_segment(chat_id)}/messages"
            )
            body = {"body": {"contentType": "html", "content": params.message}}
            response = client.post(endpoint, auth=auth, json=body)
            if graph_token_rejected(response):
                stored_token = oauth_client.get_stored_token()
                if stored_token is not None and stored_token.refresh_token:
                    auth = StaticTokenAuth(
                        oauth_client.refresh_token(stored_token.refresh_token)
                    )
                    response = client.post(endpoint, auth=auth, json=body)
            response.raise_for_status()
            result = response.json()
        soar.set_message("Message sent to user successfully")
        return SendDirectMessageOutput(**result)
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
