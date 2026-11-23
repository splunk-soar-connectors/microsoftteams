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
import re

from soar_sdk.abstract import SOARClient
import httpx
from soar_sdk.auth import StaticTokenAuth
from src.actions._graph import graph_request_error, graph_token_rejected, graph_url, encode_graph_path_segment
from src.auth import oauth_token_client, validate_oauth_configuration
from soar_sdk.action_results import ActionOutput, ActionResult, OutputField
from soar_sdk.params import Param, Params
from src.asset import Asset


class GetResponseMessageParams(Params):
    chat_id: str = Param(
        description="ID of chat", primary=True, cef_types=["ms teams chat id"]
    )
    message_id: str = Param(description="The ID of the message to be replied to")


class OdataOutput(ActionOutput):
    type: str | None


class BodyOutput(ActionOutput):
    content: str | None = OutputField(example_values=["test message"])
    contentType: str | None = OutputField(example_values=["text"])
    message_reply: str | None = OutputField(example_values=["try it"])


class UserOutput(ActionOutput):
    odata: OdataOutput | None
    displayName: str | None = OutputField(example_values=["Test User"])
    id: str | None = OutputField(example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"])
    userIdentityType: str | None = OutputField(example_values=["aadUser"])
    tenantId: str | None = OutputField(example_values=["aadUser"])


class FromOutput(ActionOutput):
    application: str | None
    device: str | None
    user: UserOutput | None


class AttachmentsOutput(ActionOutput):
    id: str | None = OutputField(example_values=["1722330920117"])
    name: str | None
    content: str | None = OutputField(
        example_values=[
            '{"messageId":"1722330920117","messagePreview":"How are you?","messageSender":{"application":null,"device":null,"user":{"userIdentityType":"aadUser","tenantId":"149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0","id":"eeb3645f-df19-47a1-8e8c-fcd234cbuste","displayName":"Test User"}}}'
        ]
    )
    contentUrl: str | None
    teamsAppId: str | None
    contentType: str | None = OutputField(example_values=["messageReference"])
    thumbnailUrl: str | None


class GetResponseMessageOutput(ActionOutput):
    odata: OdataOutput | None
    body: BodyOutput | None
    createdDateTime: str | None = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    deletedDateTime: str | None
    etag: str | None = OutputField(example_values=["1615528921100"])
    from_: FromOutput | None = OutputField(alias="from")
    id: str | None = OutputField(example_values=["1517826451101"])
    importance: str | None = OutputField(example_values=["normal"])
    contain_attachment: str | None
    lastEditedDateTime: str | None
    lastModifiedDateTime: str | None = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
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


def get_response(
    params: GetResponseMessageParams, soar: SOARClient, asset: Asset
) -> list[GetResponseMessageOutput]:
    endpoint = (
        f"/chats/{encode_graph_path_segment(params.chat_id)}/messages"
        "?$orderby=createdDateTime+desc&$top=50"
    )
    seen_endpoints = {endpoint}
    matched_replies = []
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        auth = StaticTokenAuth(oauth_client.get_valid_token(auto_refresh=True))
        with httpx.Client(
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            verify=True,
        ) as client:
            for page_count in range(1, 1001):
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
                replies = page.get("value", [])
                if not replies:
                    return ActionResult(
                        False,
                        f"get response action did not find reply for {params.message_id} message",
                        params.model_dump(by_alias=True),
                    )
                parent_found = False
                for reply in replies:
                    if reply.get("id") == params.message_id:
                        parent_found = True
                    attachments = reply.get("attachments", [])
                    attachment_ids = [attachment.get("id") for attachment in attachments]
                    if params.message_id in attachment_ids:
                        reply["contain_attachment"] = "Yes" if len(attachments) > 1 else "No"
                        matched_replies.append(reply)
                if parent_found:
                    break
                next_endpoint = page.get("@odata.nextLink")
                if not next_endpoint:
                    break
                if page_count >= 1000:
                    return ActionResult(
                        False,
                        "Microsoft Graph pagination exceeded the 1000-page limit",
                        params.model_dump(by_alias=True),
                    )
                if next_endpoint in seen_endpoints:
                    return ActionResult(
                        False,
                        "Microsoft Graph returned a non-progressing nextLink",
                        params.model_dump(by_alias=True),
                    )
                seen_endpoints.add(next_endpoint)
                endpoint = next_endpoint

        if not matched_replies:
            return ActionResult(
                False,
                f"get response action did not find reply for {params.message_id} message",
                params.model_dump(by_alias=True),
            )
        for reply in matched_replies:
            body = reply.get("body")
            if body is None or body.get("content") is None:
                continue
            match = re.findall(r"</attachment>\n(.*?)\n<p>", body["content"])
            body["message_reply"] = "".join(match).strip()
        soar.set_message("Successfully found a reply to the message")
        return [GetResponseMessageOutput(**reply) for reply in matched_replies]
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
