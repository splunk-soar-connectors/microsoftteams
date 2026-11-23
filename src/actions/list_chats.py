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
from ._graph import graph_request_error, graph_token_rejected, graph_url
from ..auth import oauth_token_client, validate_oauth_configuration
from soar_sdk.action_results import ActionOutput, ActionResult, OutputField
from soar_sdk.params import Param, Params
from ..asset import Asset


class ListChatsParams(Params):
    user: str | None = Param(
        description="Filter chats containing specific user (by email or user id)"
    )
    chat_type: str | None = Param(
        description="Filter chats by type",
        value_list=["oneOnOne", "group", "meeting", "unknownFutureValue"],
    )


class ViewpointOutput(ActionOutput):
    isHidden: bool | None
    lastMessageReadDateTime: str | None


class OnlinemeetinginfoOutput(ActionOutput):
    joinWebUrl: str | None = OutputField(cef_types=["url"])
    conferenceId: str | None
    joinUrl: str | None = OutputField(cef_types=["url"])
    phones: str | None
    quickDial: str | None
    tollFreeNumbers: str | None
    tollNumber: str | None


class ListChatsOutput(ActionOutput):
    id: str | None = OutputField(cef_types=["ms teams chat id"])
    topic: str | None
    createdDateTime: str | None
    lastUpdatedDateTime: str | None
    chatType: str | None
    webUrl: str | None = OutputField(cef_types=["url"])
    tenantId: str | None
    viewpoint: ViewpointOutput | None
    onlineMeetingInfo: OnlinemeetinginfoOutput | None


class ListChatsSummary(ActionOutput):
    total_chats: int


def list_chats(
    params: ListChatsParams, soar: SOARClient, asset: Asset
) -> list[ListChatsOutput]:
    if params.chat_type and params.chat_type not in {
        "oneOnOne",
        "group",
        "meeting",
        "unknownFutureValue",
    }:
        return ActionResult(
            False,
            "Invalid chat type filter",
            params.model_dump(by_alias=True),
        )
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        auth = StaticTokenAuth(oauth_client.get_valid_token(auto_refresh=True))
        chats: list[dict] = []
        endpoint = "/me/chats"
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
                chats.extend(page.get("value", []))
                endpoint = page.get("@odata.nextLink")
                if not endpoint:
                    break
            else:
                return ActionResult(
                    False,
                    "Microsoft Graph pagination exceeded the 1000-page limit",
                    params.model_dump(by_alias=True),
                )
        selected = []
        for chat in chats:
            if params.chat_type and params.chat_type != chat.get("chatType", ""):
                continue
            if params.user and not any(
                params.user in member.get("userId", "")
                or params.user in member.get("email", "")
                for member in chat.get("members", [])
            ):
                continue
            selected.append(ListChatsOutput(**chat))
        soar.set_summary(ListChatsSummary(total_chats=len(selected)))
        return selected
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
