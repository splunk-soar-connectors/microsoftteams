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
from soar_sdk.models.view import ViewContext
from soar_sdk.params import Param, Params
from ..asset import Asset


class CreateMeetingParams(Params):
    add_calendar_event: bool | None = Param(
        description="Create a calendar event for the meeting or not", default=False
    )
    subject: str | None = Param(description="Subject of the meeting")
    description: str | None = Param(description="Description of the meeting")
    start_time: str | None = Param(description="Date and Time to start the meeting")
    end_time: str | None = Param(description="Date and Time to end the meeting")
    attendees: str | None = Param(
        description="Email-id of the users to send the meeting invitation",
        primary=True,
        cef_types=["email"],
        allow_list=True,
    )


class OdataOutput(ActionOutput):
    context: str | None = OutputField(
        cef_types=["url"],
        example_values=[
            "https://graph.microsoft.com/v1.0/$metadata#users('hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f')/calendar/events/$entity",
            "https://graph.microsoft.com/v1.0/$metadata#users('hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f')/onlineMeetings/$entity",
        ],
    )
    etag: str | None = OutputField(
        example_values=['W/"07XhOkNngkCkqoNfY+k/jQAFHNmDaQ=="']
    )


class EmailaddressOutput(ActionOutput):
    address: str | None = OutputField(
        cef_types=["email"], example_values=["test@abc.com"]
    )
    name: str | None = OutputField(example_values=["Test User"])


class StatusOutput(ActionOutput):
    response: str | None = OutputField(example_values=["none"])
    time: str | None = OutputField(example_values=["0001-01-01T00:00:00Z"])


class AttendeesOutput(ActionOutput):
    emailAddress: EmailaddressOutput | None
    status: StatusOutput | None
    type: str | None = OutputField(example_values=["required"])


class BodyOutput(ActionOutput):
    content: str | None
    contentType: str | None = OutputField(example_values=["html"])


class EndOutput(ActionOutput):
    dateTime: str | None = OutputField(example_values=["2022-04-23T12:40:00.0000000"])
    timeZone: str | None = OutputField(example_values=["Pacific Standard Time"])


class LocationOutput(ActionOutput):
    displayName: str | None = OutputField(example_values=["Meeting Room1"])
    locationType: str | None = OutputField(example_values=["default"])
    uniqueIdType: str | None = OutputField(example_values=["unknown"])


class OnlinemeetingOutput(ActionOutput):
    joinUrl: str | None = OutputField(
        cef_types=["url"],
        example_values=[
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYThjNzMwNDc4NzZj%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d"
        ],
    )


class UserOutput(ActionOutput):
    id: str | None = OutputField(
        example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"]
    )
    tenantId: str | None = OutputField(
        example_values=["149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0"]
    )
    displayName: str | None
    registrantId: str | None
    identityProvider: str | None = OutputField(example_values=["AAD"])


class IdentityOutput(ActionOutput):
    user: UserOutput | None
    guest: str | None
    phone: str | None
    device: str | None
    acsUser: str | None
    encrypted: str | None
    spoolUser: str | None
    onPremises: str | None
    application: str | None
    applicationInstance: str | None
    acsApplicationInstance: str | None
    spoolApplicationInstance: str | None


class OrganizerOutput(ActionOutput):
    upn: str | None = OutputField(cef_types=["email"], example_values=["test@abc.com"])
    role: str | None = OutputField(example_values=["presenter"])
    identity: IdentityOutput | None


class ResponsestatusOutput(ActionOutput):
    response: str | None = OutputField(example_values=["organizer"])
    time: str | None = OutputField(example_values=["0001-01-01T00:00:00Z"])


class StartOutput(ActionOutput):
    dateTime: str | None = OutputField(example_values=["2022-04-23T12:30:00.0000000"])
    timeZone: str | None = OutputField(example_values=["Pacific Standard Time"])


class ChatinfoOutput(ActionOutput):
    threadId: str | None = OutputField(
        example_values=[
            "19:meeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm@thread.v2"
        ]
    )
    messageId: str | None = OutputField(example_values=["0"])
    replyChainMessageId: str | None


class ParticipantsOutput(ActionOutput):
    organizer: OrganizerOutput | None


class JoininformationOutput(ActionOutput):
    content: str | None
    contentType: str | None = OutputField(example_values=["html"])


class LobbybypasssettingsOutput(ActionOutput):
    scope: bool | None
    isDialInBypassEnabled: bool | None


class CreateMeetingOutput(ActionOutput):
    odata: OdataOutput | None
    allowNewTimeProposals: bool | None
    attendees: list[AttendeesOutput] | None
    body: BodyOutput | None
    bodyPreview: str | None = OutputField(
        example_values=[
            ".........................................................................................................................................\\r\\nJoin Teams Meeting\\r\\nen-US\\r\\nhttps://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYT"
        ]
    )
    changeKey: str | None = OutputField(
        example_values=["07XhOkNngkCkqoNfY+k/jQAFHNmDaQ=="]
    )
    createdDateTime: str | None = OutputField(
        example_values=["2022-04-22T10:51:54.9092527Z"]
    )
    end: EndOutput | None
    hasAttachments: bool | None
    hideAttendees: float | None = OutputField(example_values=[False])
    iCalUId: str | None = OutputField(
        example_values=[
            "040000008200E00074C5B7101A82E00800000000A3FE23FB3656D80100000000000000001000000045D024D0A24F814DA4CBB362A95DD153"
        ]
    )
    id: str | None = OutputField(
        example_values=[
            "AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY_k-jQAAAgENAAAA07XhOkNngkCkqoNfY_k-jQAFHbOt_AAAAA=="
        ]
    )
    importance: str | None = OutputField(example_values=["normal"])
    isAllDay: bool | None
    isCancelled: bool | None
    isDraft: bool | None
    isOnlineMeeting: bool | None
    isOrganizer: bool | None
    isReminderOn: bool | None
    lastModifiedDateTime: str | None = OutputField(
        example_values=["2022-04-22T10:51:56.5665393Z"]
    )
    location: LocationOutput | None
    occurrenceId: str | None
    onlineMeeting: OnlinemeetingOutput | None
    onlineMeetingProvider: str | None = OutputField(example_values=["teamsForBusiness"])
    onlineMeetingUrl: str | None
    organizer: OrganizerOutput | None
    originalEndTimeZone: str | None = OutputField(
        example_values=["Pacific Standard Time"]
    )
    originalStartTimeZone: str | None = OutputField(
        example_values=["Pacific Standard Time"]
    )
    recurrence: str | None
    reminderMinutesBeforeStart: float | None = OutputField(example_values=[15])
    responseRequested: bool | None
    responseStatus: ResponsestatusOutput | None
    sensitivity: str | None = OutputField(example_values=["normal"])
    seriesMasterId: str | None
    showAs: str | None = OutputField(example_values=["busy"])
    start: StartOutput | None
    subject: str | None = OutputField(example_values=["My Code Review"])
    transactionId: str | None
    type: str | None = OutputField(example_values=["singleInstance"])
    webLink: str | None = OutputField(
        cef_types=["url"],
        example_values=[
            "https://outlook.office365.com/owa/?itemid=AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY%2Bk%2FjQAAAgENAAAA07XhOkNngkCkqoNfY%2Bk%2FjQAFHbOt%2BAAAAA%3D%3D&exvsurl=1&path=/calendar/item"
        ],
    )
    joinUrl: str | None = OutputField(
        cef_types=["url"],
        example_values=[
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d"
        ],
    )
    chatInfo: ChatinfoOutput | None
    externalId: str | None
    joinWebUrl: str | None = OutputField(
        cef_types=["url"],
        example_values=[
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d"
        ],
    )
    endDateTime: str | None = OutputField(
        example_values=["2022-04-28T13:11:55.0940461Z"]
    )
    isBroadcast: float | None = OutputField(example_values=[False])
    meetingCode: str | None = OutputField(example_values=["230408462435"])
    meetingInfo: str | None
    participants: ParticipantsOutput | None
    startDateTime: str | None = OutputField(
        example_values=["2022-04-28T12:11:55.0940461Z"]
    )
    joinInformation: JoininformationOutput | None
    allowMeetingChat: str | None = OutputField(example_values=["enabled"])
    creationDateTime: str | None = OutputField(
        example_values=["2022-04-28T12:11:55.7803555Z"]
    )
    allowedPresenters: str | None = OutputField(example_values=["everyone"])
    audioConferencing: str | None
    autoAdmittedUsers: str | None = OutputField(example_values=["everyoneInCompany"])
    broadcastSettings: str | None
    lobbyBypassSettings: LobbybypasssettingsOutput | None
    recordAutomatically: bool | None
    isEntryExitAnnounced: bool | None
    joinMeetingIdSettings: str | None
    videoTeleconferenceId: str | None
    allowTeamworkReactions: bool | None
    allowAttendeeToEnableMic: bool | None
    allowAttendeeToEnableCamera: bool | None
    outerMeetingAutoAdmittedUsers: str | None


def display_meeting(
    context: ViewContext,
    outputs: list[CreateMeetingOutput],
    params: list[CreateMeetingParams],
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


def create_meeting(
    params: CreateMeetingParams, soar: SOARClient, asset: Asset
) -> CreateMeetingOutput:
    data: dict = {}
    if params.subject:
        data["subject"] = params.subject
    if params.add_calendar_event:
        endpoint = "/me/calendar/events"
        data["isOnlineMeeting"] = True
        if params.description:
            data["body"] = {"content": params.description}
        timezone = asset.timezone.key if asset.timezone else "UTC"
        if params.start_time:
            data["start"] = {"dateTime": params.start_time, "timeZone": timezone}
        if params.end_time:
            data["end"] = {"dateTime": params.end_time, "timeZone": timezone}
        attendees = [
            value.strip()
            for value in (params.attendees or "").split(",")
            if value.strip()
        ]
        if attendees:
            data["attendees"] = [
                {"emailAddress": {"address": attendee}} for attendee in attendees
            ]
    else:
        endpoint = "/me/onlineMeetings"
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        auth = StaticTokenAuth(oauth_client.get_valid_token(auto_refresh=True))
        endpoint = graph_url(endpoint)
        with httpx.Client(
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            verify=True,
        ) as client:
            response = client.post(endpoint, auth=auth, json=data)
            if graph_token_rejected(response):
                stored_token = oauth_client.get_stored_token()
                if stored_token is not None and stored_token.refresh_token:
                    auth = StaticTokenAuth(
                        oauth_client.refresh_token(stored_token.refresh_token)
                    )
                    response = client.post(endpoint, auth=auth, json=data)
            response.raise_for_status()
            result = response.json()
        soar.set_message("Meeting Created Successfully")
        return CreateMeetingOutput(**result)
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
