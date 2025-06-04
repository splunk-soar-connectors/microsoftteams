# Copyright (c) 2025 Splunk Inc.
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
import asyncio
import json
from io import BytesIO
from pathlib import Path
from typing import Union
from zipfile import ZipFile

import phantom.app as phantom
from botbuilder.core import ActivityHandler, Bot, BotFrameworkAdapterSettings, CardFactory, TurnContext
from botbuilder.core.streaming import BotFrameworkHttpAdapterBase
from botbuilder.schema import Activity, Attachment
from phantom.app import ActionResult
from phantom.connector_result import ConnectorResult
from phantom.utils import get_list_from_string

from microsoftteams_consts import MSTEAMS_JSON_CHOICES, MSTEAMS_JSON_MSG


class SOARWebhookAdapter(BotFrameworkHttpAdapterBase):
    def __init__(self, settings: BotFrameworkAdapterSettings):
        super().__init__(settings)

        self._AUTH_HEADER_NAME = "Authorization"
        self._CHANNEL_ID_HEADER_NAME = "ChannelId"

    async def process(self, method: str, path: str, headers: dict[str, str], body: str, bot: Bot) -> dict:
        body_dict = json.loads(body)
        activity = Activity.deserialize(body_dict)
        auth_header = headers["Authorization"] if "Authorization" in headers else ""
        response = await self.process_activity(activity, auth_header, bot.on_turn)

        if response is not None:
            return {
                "status_code": response.status,
                "headers": response.headers,
                "content": response.body,
            }
        return {"status_code": 201, "headers": {}, "content": ""}


def create_question_card(question: str, choices: list[str]) -> Attachment:
    if choices:
        form = {
            "type": "Input.ChoiceSet",
            "id": "choice",
            "choices": [{"title": choice, "value": choice} for choice in choices],
            "placeholder": "Select an option",
            "style": "expanded",
        }
    else:
        form = {
            "type": "Input.Text",
            "id": "choice",
            "placeholder": "Enter your response",
        }

    return CardFactory.adaptive_card(
        {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Question from Splunk SOAR",
                    "wrap": True,
                    "style": "heading",
                },
                {
                    "type": "TextBlock",
                    "text": question,
                    "wrap": True,
                },
                form,
                {
                    "type": "ActionSet",
                    "actions": [{"type": "Action.Submit", "title": "Submit"}],
                },
            ],
        }
    )


def create_completed_question_card(question: str, choices: list[str], answer: str, answerer: str) -> Attachment:
    if choices:
        choice_bullets = []
        for choice in choices:
            if choice == answer:
                choice_bullets.append(f"- **{choice}** ✅")
            else:
                choice_bullets.append(f"- {choice}")
        answer_block = {
            "type": "TextBlock",
            "text": "\n".join(choice_bullets),
            "wrap": True,
        }
    else:
        answer_block = {
            "type": "TextBlock",
            "text": f"*{answer}*",
            "wrap": True,
        }
    return CardFactory.adaptive_card(
        {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Question from Splunk SOAR",
                    "wrap": True,
                    "style": "heading",
                },
                {
                    "type": "TextBlock",
                    "text": question,
                    "wrap": True,
                },
                answer_block,
                {
                    "type": "TextBlock",
                    "text": f"Answer submitted by **{answerer}**.",
                    "wrap": True,
                },
            ],
        }
    )


class SOARBot(ActivityHandler):
    def __init__(self, soar_rest_client):
        super(ActivityHandler, self).__init__()
        self.soar_rest_client = soar_rest_client

    async def on_message_activity(self, turn_context: TurnContext):
        if message_value := turn_context.activity.value:
            if choice := message_value.get("choice"):
                answerer = turn_context.activity.from_property.name
                original_activity_id = turn_context.activity.reply_to_id

                app_run = self.soar_rest_client.get_related_connector_run(original_activity_id)
                if not (isinstance(intermediate_results := app_run.get("result_data"), list) and intermediate_results):
                    raise ValueError(f"Could not find connector run for message {original_activity_id}")

                if not (isinstance(first_result := intermediate_results[0], dict)):
                    raise ValueError(f"Could not get intermediate connector run results for message {original_activity_id}")

                param = first_result.get("parameter", {})
                connector_result = ConnectorResult.from_dict(first_result)

                message = param[MSTEAMS_JSON_MSG]
                choices = param.get(MSTEAMS_JSON_CHOICES, "")

                choices_split = get_list_from_string(choices)

                result = ActionResult(param)
                result.set_status(phantom.APP_SUCCESS)
                result.add_data({"answer": choice, "answered_by": answerer})
                connector_result.add_item(result)
                connector_result.postprocess_action_results()
                self.soar_rest_client.finish_related_connector_run(original_activity_id, result=connector_result.get_dict())

                answer_card = create_completed_question_card(message, choices_split, choice, answerer)
                replacement_activity = Activity(type="message", id=original_activity_id, attachments=[answer_card])
                await turn_context.update_activity(replacement_activity)


def create_app_package(asset: dict) -> bytes:
    zip_bytes = BytesIO()
    with ZipFile(zip_bytes, mode="w") as zip_file:
        icons_path = Path(__file__).parent / "img" / "bot_icons"
        for icon_name in ["color.png", "outline.png"]:
            icon_path = icons_path / icon_name
            zip_file.write(icon_path, arcname=icon_name)

        manifest = {
            "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.9/MicrosoftTeams.schema.json",
            "manifestVersion": "1.19",
            "version": "1.0.0",
            "id": asset.get("client_id"),
            "developer": {
                "name": "Splunk",
                "websiteUrl": "https://www.splunk.com",
                "privacyUrl": "https://www.splunk.com/en_us/legal/privacy.html",
                "termsOfUseUrl": "https://www.splunk.com/en_us/legal/terms.html",
            },
            "name": {"short": "SOARBot", "full": "Splunk SOAR Bot"},
            "icons": {"color": "color.png", "outline": "outline.png"},
            "description": {
                "short": "Alerts and prompts from Splunk SOAR",
                "full": "This application allows you to view notifications and answer prompts from Splunk SOAR in Microsoft Teams.",
            },
            "accentColor": "#4FA484",
            "bots": [
                {
                    "botId": asset.get("client_id"),
                    "scopes": ["personal", "team", "groupChat"],
                    "supportsFiles": False,
                    "isNotificationOnly": False,
                }
            ],
        }
        zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_bytes.seek(0)
    return zip_bytes.read()


# Type alias that accepts both the string values provided by SOAR 6.x and the list values provided by SOAR 7.x
QueryParameters = dict[str, Union[str, list[str]]]


def handle_webhook(
    method: str, headers: dict[str, str], path_parts: list[str], query: QueryParameters, body: str, asset: dict, soar_rest_client
):
    if path_parts == ["app_package"]:
        return {
            "status_code": 200,
            "headers": [
                ("Content-Type", "application/zip"),
                ("Content-Disposition", 'attachment; filename="appPackage.zip"'),
            ],
            "content": create_app_package(asset),
        }

    bot = SOARBot(soar_rest_client)
    adapter = SOARWebhookAdapter(BotFrameworkAdapterSettings(asset.get("client_id"), app_password=asset.get("client_secret")))
    response_awaitable = adapter.process(method, path_parts, headers, body, bot)

    return asyncio.run(response_awaitable)
