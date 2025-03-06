import asyncio
import json

from botbuilder.core import ActivityHandler, Bot, BotFrameworkAdapterSettings, CardFactory, TurnContext
from botbuilder.core.streaming import BotFrameworkHttpAdapterBase
from botbuilder.schema import Activity, Attachment, ChannelAccount


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


class SOARBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        print(turn_context.activity.serialize())
        if message_value := turn_context.activity.value:
            if choice := message_value.get("choice"):
                answerer = turn_context.activity.from_property.name
                await turn_context.send_activity(f"Answer recorded: _{choice}_ by **{answerer}**")
                return
        await turn_context.send_activity(f"I heard {turn_context.activity.text}")

    async def on_members_added_activity(self, members_added: list[ChannelAccount], turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    Activity(
                        type="message",
                        text="Hello!",
                        attachments=[create_question_card("What is your favorite color?", ["Red", "Green", "Blue"])],
                    )
                )


def handle_webhook(
    method: str,
    headers: dict[str, str],
    path_parts: list[str],
    query: dict[str, str],
    body: str,
    asset: dict,
):
    bot = SOARBot()
    adapter = SOARWebhookAdapter(BotFrameworkAdapterSettings(asset.get("client_id"), app_password=asset.get("client_secret")))
    response_awaitable = adapter.process(method, path_parts, headers, body, bot)

    return asyncio.run(response_awaitable)
