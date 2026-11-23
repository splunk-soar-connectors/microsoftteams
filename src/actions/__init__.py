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
"""Explicit SDK action registration for Microsoft Teams."""

from typing import TYPE_CHECKING

from .ask_question import AskQuestionOutput, AskQuestionParams, ask_question
from .create_meeting import (
    CreateMeetingOutput,
    CreateMeetingParams,
    create_meeting,
    display_meeting,
)
from .get_admin_consent import AdminConsentOutput, make_admin_consent_action
from .get_channel_message import (
    GetChannelMessageOutput,
    GetChannelMessageParams,
    get_channel_message,
)
from .get_chat_message import (
    GetChatMessageOutput,
    GetChatMessageParams,
    get_chat_message,
)
from .get_response import (
    GetResponseMessageOutput,
    GetResponseMessageParams,
    get_response,
)
from .list_channels import (
    ListChannelsOutput,
    ListChannelsParams,
    ListChannelsSummary,
    display_channels,
    list_channels,
)
from .list_chats import (
    ListChatsOutput,
    ListChatsParams,
    ListChatsSummary,
    list_chats,
)
from .list_groups import (
    ListGroupsOutput,
    ListGroupsSummary,
    list_groups,
)
from .list_teams import (
    ListTeamsOutput,
    ListTeamsSummary,
    list_teams,
)
from .list_users import (
    ListUsersOutput,
    ListUsersSummary,
    list_users,
)
from .send_channel_message import SendChannelMessageOutput, send_channel_message
from .send_chat_message import (
    SendChatMessageOutput,
    SendChatMessageParams,
    send_chat_message,
)
from .send_direct_message import (
    SendDirectMessageOutput,
    SendDirectMessageParams,
    send_direct_message,
)

if TYPE_CHECKING:
    from soar_sdk.app import App


def register_actions(app: "App") -> "App":
    """Register the ordinary actions and their published metadata."""
    app.register_action(
        action=make_admin_consent_action(lambda: app.get_webhook_url("oauth/callback")),
        name="get admin consent",
        identifier="get_admin_consent",
        description="Get the admin consent for a non-admin user",
        verbose=(
            "Action <b>'get admin consent'</b> has to be run by an admin user "
            "to provide consent to a non-admin user."
        ),
        action_type="generic",
        read_only=False,
        output_class=AdminConsentOutput,
        render_as="table",
    )
    app.register_action(
        action=list_users,
        name="list users",
        identifier="list_users",
        description="List all users",
        action_type="investigate",
        read_only=True,
        output_class=ListUsersOutput,
        render_as="table",
        summary_type=ListUsersSummary,
    )
    app.register_action(
        action=send_channel_message,
        name="send channel message",
        identifier="send_channel_message",
        description="Send a message to a channel of a group",
        action_type="generic",
        read_only=False,
        output_class=SendChannelMessageOutput,
        render_as="table",
    )
    app.register_action(
        action=ask_question,
        name="ask question",
        identifier="ask_question",
        description="Ask a question in a channel (DEPRECATED)",
        action_type="generic",
        read_only=False,
        params_class=AskQuestionParams,
        output_class=AskQuestionOutput,
        render_as="table",
    )
    app.register_action(
        action=list_chats,
        name="list chats",
        identifier="list_chats",
        description="List chats for authenticated user",
        action_type="investigate",
        read_only=True,
        params_class=ListChatsParams,
        output_class=ListChatsOutput,
        render_as="table",
        summary_type=ListChatsSummary,
    )
    app.register_action(
        action=send_direct_message,
        name="send direct message",
        identifier="send_direct_message",
        description="Send a direct message to a user",
        action_type="generic",
        read_only=False,
        params_class=SendDirectMessageParams,
        output_class=SendDirectMessageOutput,
        render_as="table",
    )
    app.register_action(
        action=send_chat_message,
        name="send chat message",
        identifier="send_chat_message",
        description="Send a message to specific chat",
        action_type="generic",
        read_only=False,
        params_class=SendChatMessageParams,
        output_class=SendChatMessageOutput,
        render_as="table",
    )
    app.register_action(
        action=list_channels,
        name="list channels",
        identifier="list_channels",
        description="Lists all channels of a group",
        action_type="investigate",
        read_only=True,
        params_class=ListChannelsParams,
        output_class=ListChannelsOutput,
        render_as="custom",
        view_handler=display_channels,
        view_template="channels.html",
        summary_type=ListChannelsSummary,
    )
    app.register_action(
        action=list_groups,
        name="list groups",
        identifier="list_groups",
        description="List all Azure Groups",
        action_type="investigate",
        read_only=True,
        output_class=ListGroupsOutput,
        render_as="table",
        summary_type=ListGroupsSummary,
    )
    app.register_action(
        action=list_teams,
        name="list teams",
        identifier="list_teams",
        description="List all Microsoft Teams",
        action_type="investigate",
        read_only=True,
        output_class=ListTeamsOutput,
        render_as="table",
        summary_type=ListTeamsSummary,
    )
    app.register_action(
        action=create_meeting,
        name="create meeting",
        identifier="create_meeting",
        description="Create a microsoft teams meeting",
        verbose=(
            "The <b>add_calendar_event</b> parameter can be used for creating a "
            "calender event for the given time and send the meeting invitation "
            "to all the attendees. If the value of that parameter is false, then "
            "apart from <b>subject</b>, rest of the parameters will be ignored "
            "and no event will be created in the calendar."
        ),
        action_type="generic",
        read_only=False,
        params_class=CreateMeetingParams,
        output_class=CreateMeetingOutput,
        render_as="custom",
        view_handler=display_meeting,
        view_template="meeting.html",
    )
    app.register_action(
        action=get_channel_message,
        name="get channel message",
        identifier="get_channel_message",
        description="Get message in a channel",
        action_type="investigate",
        read_only=True,
        params_class=GetChannelMessageParams,
        output_class=GetChannelMessageOutput,
        render_as="table",
    )
    app.register_action(
        action=get_chat_message,
        name="get chat message",
        identifier="get_chat_message",
        description="Get message in a chat",
        action_type="investigate",
        read_only=True,
        params_class=GetChatMessageParams,
        output_class=GetChatMessageOutput,
        render_as="table",
    )
    app.register_action(
        action=get_response,
        name="get response message",
        identifier="get_response",
        description="Get response on message in a chat",
        action_type="investigate",
        read_only=True,
        params_class=GetResponseMessageParams,
        output_class=GetResponseMessageOutput,
        render_as="table",
    )
    return app
