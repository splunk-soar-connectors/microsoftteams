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
from zoneinfo import ZoneInfo
from soar_sdk.abstract import SOARClient
from soar_sdk.app import App
from soar_sdk.params import Param, Params
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.asset import BaseAsset, AssetField
from soar_sdk.logging import getLogger

logger = getLogger()


class Asset(BaseAsset):
    client_id: str = AssetField(description="Client ID")
    client_secret: str = AssetField(description="Client Secret")
    tenant_id: str = AssetField(description="Tenant ID")
    timezone: ZoneInfo | None = AssetField(
        description="Microsoft Teams' timezone", default=ZoneInfo("UTC")
    )
    scope: str = AssetField(
        description="Scopes to access (space-separated)",
        default="offline_access calendars.readwrite onlinemeetings.readwrite channelmessage.send user.readbasic.all channel.readbasic.all groupmember.read.all",
    )


app = App(
    name="microsoftteams",
    app_type="information",
    logo="logo_microsoftteams.svg",
    logo_dark="logo_microsoftteams_dark.svg",
    product_vendor="Microsoft",
    product_name="Teams",
    publisher="Splunk",
    appid="6ba1906f-5899-44df-bb65-1bee4df8ca3c",
    fips_compliant=True,
    encrypt_cache_state=True,
    encrypt_ingest_state=True,
    asset_cls=Asset,
)


@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    raise NotImplementedError()


@app.action(
    description="Get the admin consent for a non-admin user",
    action_type="generic",
    read_only=False,
    verbose="Action <b>'get admin consent'</b> has to be run by an admin user to provide consent to a non-admin user.",
)
def get_admin_consent(params: Params, soar: SOARClient, asset: Asset) -> ActionOutput:
    raise NotImplementedError()


class AssignedlicensesOutput(ActionOutput):
    disabledPlans: str
    skuId: str = OutputField(example_values=["6fd2c87f-b296-42f0-b197-1e91e994b900"])


class AssignedplansOutput(ActionOutput):
    assignedDateTime: str = OutputField(example_values=["2018-01-24T11:17:21Z"])
    capabilityStatus: str = OutputField(example_values=["Enabled"])
    service: str = OutputField(example_values=["exchange"])
    servicePlanId: str = OutputField(
        example_values=["efb87545-963c-4e0d-99df-69c6916d9eb0"]
    )


class ProvisionedplansOutput(ActionOutput):
    capabilityStatus: str = OutputField(example_values=["Enabled"])
    provisioningStatus: str = OutputField(example_values=["Success"])
    service: str = OutputField(example_values=["exchange"])


class ListUsersOutput(ActionOutput):
    accountEnabled: bool
    assignedLicenses: list[AssignedlicensesOutput]
    assignedPlans: list[AssignedplansOutput]
    businessPhones: str = OutputField(example_values=["22211156"])
    city: str
    companyName: str
    country: str = OutputField(example_values=["US"])
    deletedDateTime: str = OutputField(example_values=["2018-01-24T11:16:50Z"])
    department: str
    deviceKeys: str
    displayName: str = OutputField(
        cef_types=["user name"], example_values=["Test User"]
    )
    employeeId: str
    givenName: str = OutputField(cef_types=["user name"], example_values=["User"])
    id: str = OutputField(example_values=["a1a6d0a2-b0f6-46c1-b49e-98a9ddabac09"])
    imAddresses: str = OutputField(cef_types=["email"], example_values=["test@abc.com"])
    jobTitle: str
    legalAgeGroupClassification: str
    mail: str = OutputField(cef_types=["email"], example_values=["test.user@abc.com"])
    mailNickname: str = OutputField(cef_types=["user name"], example_values=["User"])
    mobilePhone: str
    officeLocation: str
    onPremisesDomainName: str = OutputField(cef_types=["domain"])
    onPremisesExtensionAttributes: str
    onPremisesImmutableId: str
    onPremisesLastSyncDateTime: str = OutputField(
        example_values=["2018-01-24T11:16:50Z"]
    )
    onPremisesProvisioningErrors: str
    onPremisesSamAccountName: str
    onPremisesSecurityIdentifier: str
    onPremisesSyncEnabled: str
    onPremisesUserPrincipalName: str
    passwordPolicies: str
    passwordProfile: str
    postalCode: str
    preferredDataLocation: str
    preferredLanguage: str = OutputField(example_values=["en"])
    provisionedPlans: list[ProvisionedplansOutput]
    proxyAddresses: str = OutputField(example_values=["SMTP:test@abc.com"])
    refreshTokensValidFromDateTime: str = OutputField(
        example_values=["2018-01-24T11:16:50Z"]
    )
    showInAddressList: str
    state: str
    streetAddress: str
    surname: str = OutputField(example_values=["User"])
    usageLocation: str = OutputField(example_values=["US"])
    userPrincipalName: str = OutputField(
        cef_types=["email"], example_values=["test.user@abc.com"]
    )
    userType: str = OutputField(example_values=["Member"])


@app.action(description="List all users", action_type="investigate")
def list_users(params: Params, soar: SOARClient, asset: Asset) -> ListUsersOutput:
    raise NotImplementedError()


class SendChannelMessageParams(Params):
    group_id: str = Param(
        description="ID of group", primary=True, cef_types=["ms teams group id"]
    )
    channel_id: str = Param(
        description="ID of channel", primary=True, cef_types=["ms teams channel id"]
    )
    message: str = Param(description="Message to send (HTML is supported)")


class OdataOutput(ActionOutput):
    type: str = OutputField(example_values=["#microsoft.graph.teamworkUserIdentity"])


class BodyOutput(ActionOutput):
    content: str = OutputField(example_values=["test message"])
    contentType: str = OutputField(example_values=["text"])


class UserOutput(ActionOutput):
    displayName: str = OutputField(example_values=["Test User"])
    id: str = OutputField(example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"])
    userIdentityType: str = OutputField(example_values=["aadUser"])
    tenantId: str = OutputField(
        example_values=["149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0"]
    )
    odata: OdataOutput


class FromOutput(ActionOutput):
    application: str
    conversation: str
    device: str
    user: UserOutput


class ChannelidentityOutput(ActionOutput):
    teamId: str = OutputField(
        example_values=["hfyr6hdhyr6s-d42a-452b-9155-379764077e25"]
    )
    channelId: str = OutputField(
        example_values=["19:391631e7f5984005811c658217ea8f23@thread.tacv2"]
    )


class SendChannelMessageOutput(ActionOutput):
    odata: OdataOutput
    body: BodyOutput
    createdDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    deletedDateTime: str
    etag: str = OutputField(example_values=["1615528921352"])
    from_: FromOutput
    id: str = OutputField(example_values=["1517826451101"])
    importance: str = OutputField(example_values=["normal"])
    lastEditedDateTime: str
    lastModifiedDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    locale: str
    messageType: str = OutputField(example_values=["message"])
    policyViolation: str
    replyToId: str
    chatId: str
    eventDetail: str
    channelIdentity: ChannelidentityOutput
    subject: str
    summary: str
    webUrl: str


@app.action(
    description="Send a message to a channel of a group",
    action_type="generic",
    read_only=False,
)
def send_channel_message(
    params: SendChannelMessageParams, soar: SOARClient, asset: Asset
) -> SendChannelMessageOutput:
    raise NotImplementedError()


class AskQuestionParams(Params):
    group_id: str = Param(
        description="ID of group", primary=True, cef_types=["ms teams group id"]
    )
    channel_id: str = Param(
        description="ID of channel", primary=True, cef_types=["ms teams channel id"]
    )
    message: str = Param(description="Question text (Markdown is supported)")
    choices: str | None = Param(
        description="Comma-separated list of possible answers (leave blank for a short-answer question)"
    )


class AskQuestionOutput(ActionOutput):
    answer: str = OutputField(example_values=["Green"])
    answered_by: str = OutputField(example_values=["John Smith"])


@app.action(
    description="Ask a question in a channel (DEPRECATED)",
    action_type="generic",
    read_only=False,
)
def ask_question(
    params: AskQuestionParams, soar: SOARClient, asset: Asset
) -> AskQuestionOutput:
    raise NotImplementedError()


class ListChatsParams(Params):
    user: str | None = Param(
        description="Filter chats containing specific user (by email or user id)"
    )
    chat_type: str | None = Param(
        description="Filter chats by type",
        value_list=["oneOnOne", "group", "meeting", "unknownFutureValue"],
    )


class ViewpointOutput(ActionOutput):
    isHidden: bool
    lastMessageReadDateTime: str


class OnlinemeetinginfoOutput(ActionOutput):
    joinWebUrl: str = OutputField(cef_types=["url"])
    conferenceId: str
    joinUrl: str = OutputField(cef_types=["url"])
    phones: str
    quickDial: str
    tollFreeNumbers: str
    tollNumber: str


class ListChatsOutput(ActionOutput):
    id: str = OutputField(cef_types=["ms teams chat id"])
    topic: str
    createdDateTime: str
    lastUpdatedDateTime: str
    chatType: str
    webUrl: str = OutputField(cef_types=["url"])
    tenantId: str
    viewpoint: ViewpointOutput
    onlineMeetingInfo: OnlinemeetinginfoOutput


@app.action(description="List chats for authenticated user", action_type="investigate")
def list_chats(
    params: ListChatsParams, soar: SOARClient, asset: Asset
) -> ListChatsOutput:
    raise NotImplementedError()


class SendDirectMessageParams(Params):
    user_id: str = Param(
        description="ID of the user to send direct message to",
        primary=True,
        cef_types=["ms teams user id"],
    )
    message: str = Param(description="Message content to send")


class UserOutput(ActionOutput):
    id: str = OutputField(cef_types=["ms teams user id"])
    displayName: str


class FromOutput(ActionOutput):
    user: UserOutput


class BodyOutput(ActionOutput):
    content: str
    contentType: str


class AttachmentsOutput(ActionOutput):
    content: str
    contentType: str
    contentUrl: str = OutputField(cef_types=["url"])
    id: str = OutputField(cef_types=["ms teams attachment id"])
    name: str
    teamsAppId: str
    thumbnailUrl: str = OutputField(cef_types=["url"])


class ChannelidentityOutput(ActionOutput):
    channelId: str = OutputField(cef_types=["ms teams channel id"])
    teamId: str = OutputField(cef_types=["ms teams team id"])


class SendDirectMessageOutput(ActionOutput):
    id: str = OutputField(cef_types=["ms teams message id"])
    chatId: str = OutputField(cef_types=["ms teams chat id"])
    createdDateTime: str
    deletedDateTime: str
    lastModifiedDateTime: str
    lastEditedDateTime: str
    etag: str
    importance: str
    locale: str
    messageType: str
    replyToId: str = OutputField(cef_types=["ms teams message id"])
    subject: str
    summary: str
    webUrl: str = OutputField(cef_types=["url"])
    from_: FromOutput
    body: BodyOutput
    attachments: list[AttachmentsOutput]
    channelIdentity: ChannelidentityOutput


@app.action(
    description="Send a direct message to a user",
    action_type="generic",
    read_only=False,
)
def send_direct_message(
    params: SendDirectMessageParams, soar: SOARClient, asset: Asset
) -> SendDirectMessageOutput:
    raise NotImplementedError()


class SendChatMessageParams(Params):
    chat_id: str = Param(
        description="ID of the chat to send message to",
        primary=True,
        cef_types=["ms teams chat id"],
    )
    message: str = Param(description="Message content to send")


class UserOutput(ActionOutput):
    id: str = OutputField(cef_types=["ms teams user id"])
    displayName: str


class FromOutput(ActionOutput):
    user: UserOutput


class BodyOutput(ActionOutput):
    content: str
    contentType: str


class AttachmentsOutput(ActionOutput):
    content: str
    contentType: str
    contentUrl: str = OutputField(cef_types=["url"])
    id: str = OutputField(cef_types=["ms teams attachment id"])
    name: str
    teamsAppId: str
    thumbnailUrl: str = OutputField(cef_types=["url"])


class ChannelidentityOutput(ActionOutput):
    channelId: str = OutputField(cef_types=["ms teams channel id"])
    teamId: str = OutputField(cef_types=["ms teams team id"])


class SendChatMessageOutput(ActionOutput):
    id: str = OutputField(cef_types=["ms teams message id"])
    chatId: str = OutputField(cef_types=["ms teams chat id"])
    createdDateTime: str
    deletedDateTime: str
    lastModifiedDateTime: str
    lastEditedDateTime: str
    etag: str
    importance: str
    locale: str
    messageType: str
    replyToId: str = OutputField(cef_types=["ms teams message id"])
    subject: str
    summary: str
    webUrl: str = OutputField(cef_types=["url"])
    from_: FromOutput
    body: BodyOutput
    attachments: list[AttachmentsOutput]
    channelIdentity: ChannelidentityOutput


@app.action(
    description="Send a message to specific chat",
    action_type="generic",
    read_only=False,
)
def send_chat_message(
    params: SendChatMessageParams, soar: SOARClient, asset: Asset
) -> SendChatMessageOutput:
    raise NotImplementedError()


class ListChannelsParams(Params):
    group_id: str = Param(
        description="ID of group", primary=True, cef_types=["ms teams group id"]
    )


class ListChannelsOutput(ActionOutput):
    description: str = OutputField(example_values=["Test team"])
    displayName: str = OutputField(example_values=["General"])
    email: str
    tenantId: str = OutputField(
        example_values=["149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0"]
    )
    isArchived: bool
    createdDateTime: str = OutputField(example_values=["2020-07-13T12:39:21.573Z"])
    id: str = OutputField(
        cef_types=["ms teams channel id"],
        example_values=["78f4a378-e7d3-49c8-a8a7-645b886752d9"],
    )
    isFavoriteByDefault: str
    membershipType: str = OutputField(example_values=["standard"])
    webUrl: str


@app.action(description="Lists all channels of a group", action_type="investigate")
def list_channels(
    params: ListChannelsParams, soar: SOARClient, asset: Asset
) -> ListChannelsOutput:
    raise NotImplementedError()


class ListGroupsOutput(ActionOutput):
    classification: str = OutputField(example_values=["classification"])
    createdDateTime: str = OutputField(example_values=["2018-01-30T09:43:13Z"])
    deletedDateTime: str = OutputField(example_values=["2018-01-30T09:43:13Z"])
    description: str = OutputField(example_values=["team2"])
    displayName: str = OutputField(example_values=["team2"])
    uniqueName: str
    expirationDateTime: str
    groupTypes: str = OutputField(example_values=["DynamicMembership"])
    id: str = OutputField(
        cef_types=["ms teams group id"],
        example_values=["594101ba-1fde-482d-8e24-3bbab23a3ca8"],
    )
    isAssignableToRole: bool
    mail: str = OutputField(cef_types=["email"], example_values=["team2@test.com"])
    mailEnabled: bool
    mailNickname: str = OutputField(example_values=["team2"])
    membershipRule: str = OutputField(
        example_values=['user.department -eq "Marketing"']
    )
    membershipRuleProcessingState: str = OutputField(example_values=["on"])
    onPremisesDomainName: str
    onPremisesLastSyncDateTime: str = OutputField(
        example_values=["2018-01-30T09:43:13Z"]
    )
    onPremisesNetBiosName: str
    onPremisesProvisioningErrors: str
    onPremisesSamAccountName: str
    onPremisesSecurityIdentifier: str
    onPremisesSyncEnabled: bool
    preferredDataLocation: str
    preferredLanguage: str
    proxyAddresses: str = OutputField(example_values=["SMTP : team2@test.com"])
    renewedDateTime: str = OutputField(example_values=["2018-01-30T09:43:13Z"])
    resourceBehaviorOptions: str
    resourceProvisioningOptions: str
    securityEnabled: bool
    securityIdentifier: str = OutputField(
        example_values=["S-2-22-2-123456789-1234567890-123456789-1234567890"]
    )
    theme: str
    visibility: str = OutputField(example_values=["Private"])


@app.action(description="List all Azure Groups", action_type="investigate")
def list_groups(params: Params, soar: SOARClient, asset: Asset) -> ListGroupsOutput:
    raise NotImplementedError()


class WritebackconfigurationOutput(ActionOutput):
    isEnabled: str
    onPremisesGroupType: str


class ListTeamsOutput(ActionOutput):
    classification: str
    createdByAppId: str
    createdDateTime: str = OutputField(example_values=["2018-02-05T21:42:33Z"])
    deletedDateTime: str
    description: str = OutputField(example_values=["TeamOne"])
    displayName: str = OutputField(example_values=["TeamOne"])
    expirationDateTime: str
    groupTypes: list[str] = OutputField(example_values=["Unified"])
    id: str = OutputField(
        cef_types=["ms teams group id"],
        example_values=["a84b973e-ad51-4248-9a3e-df054415f026"],
    )
    isAssignableToRole: str
    isManagementRestricted: str
    mail: str = OutputField(cef_types=["email"], example_values=["test@test.com"])
    mailEnabled: bool
    mailNickname: str = OutputField(example_values=["TeamOne"])
    membershipRule: str
    membershipRuleProcessingState: str
    onPremisesDomainName: str = OutputField(cef_types=["domain"])
    onPremisesLastSyncDateTime: str
    onPremisesNetBiosName: str
    onPremisesSamAccountName: str
    onPremisesSecurityIdentifier: str
    onPremisesSyncEnabled: str
    preferredDataLocation: str
    preferredLanguage: str
    proxyAddresses: list[str] = OutputField(
        example_values=[
            "SPO:SPO_2e56f4be-737f-418d-8dee-7d01911b91df@SPO_a417c578-c7ee-480d-a225-d48057e74df5"
        ]
    )
    renewedDateTime: str = OutputField(example_values=["2018-02-05T21:42:33Z"])
    resourceProvisioningOptions: list[str] = OutputField(example_values=["Team"])
    securityEnabled: bool
    securityIdentifier: str = OutputField(
        example_values=["S-1-12-1-2823526206-1112059217-98516634-653268292"]
    )
    theme: str
    visibility: str = OutputField(example_values=["Public"])
    writebackConfiguration: WritebackconfigurationOutput


@app.action(description="List all Microsoft Teams", action_type="investigate")
def list_teams(params: Params, soar: SOARClient, asset: Asset) -> ListTeamsOutput:
    raise NotImplementedError()


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
    context: str = OutputField(
        cef_types=["url"],
        example_values=[
            "https://graph.microsoft.com/v1.0/$metadata#users('hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f')/calendar/events/$entity",
            "https://graph.microsoft.com/v1.0/$metadata#users('hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f')/onlineMeetings/$entity",
        ],
    )
    etag: str = OutputField(example_values=['W/"07XhOkNngkCkqoNfY+k/jQAFHNmDaQ=="'])


class EmailaddressOutput(ActionOutput):
    address: str = OutputField(cef_types=["email"], example_values=["test@abc.com"])
    name: str = OutputField(example_values=["Test User"])


class StatusOutput(ActionOutput):
    response: str = OutputField(example_values=["none"])
    time: str = OutputField(example_values=["0001-01-01T00:00:00Z"])


class AttendeesOutput(ActionOutput):
    emailAddress: EmailaddressOutput
    status: StatusOutput
    type: str = OutputField(example_values=["required"])


class BodyOutput(ActionOutput):
    content: str
    contentType: str = OutputField(example_values=["html"])


class EndOutput(ActionOutput):
    dateTime: str = OutputField(example_values=["2022-04-23T12:40:00.0000000"])
    timeZone: str = OutputField(example_values=["Pacific Standard Time"])


class LocationOutput(ActionOutput):
    displayName: str = OutputField(example_values=["Meeting Room1"])
    locationType: str = OutputField(example_values=["default"])
    uniqueIdType: str = OutputField(example_values=["unknown"])


class OnlinemeetingOutput(ActionOutput):
    joinUrl: str = OutputField(
        cef_types=["url"],
        example_values=[
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYThjNzMwNDc4NzZj%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d"
        ],
    )


class OrganizerOutput(ActionOutput):
    upn: str = OutputField(cef_types=["email"], example_values=["test@abc.com"])
    role: str = OutputField(example_values=["presenter"])
    identity: IdentityOutput


class ResponsestatusOutput(ActionOutput):
    response: str = OutputField(example_values=["organizer"])
    time: str = OutputField(example_values=["0001-01-01T00:00:00Z"])


class StartOutput(ActionOutput):
    dateTime: str = OutputField(example_values=["2022-04-23T12:30:00.0000000"])
    timeZone: str = OutputField(example_values=["Pacific Standard Time"])


class ChatinfoOutput(ActionOutput):
    threadId: str = OutputField(
        example_values=[
            "19:meeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm@thread.v2"
        ]
    )
    messageId: str = OutputField(example_values=["0"])
    replyChainMessageId: str


class UserOutput(ActionOutput):
    id: str = OutputField(example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"])
    tenantId: str = OutputField(
        example_values=["149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0"]
    )
    displayName: str
    registrantId: str
    identityProvider: str = OutputField(example_values=["AAD"])


class IdentityOutput(ActionOutput):
    user: UserOutput
    guest: str
    phone: str
    device: str
    acsUser: str
    encrypted: str
    spoolUser: str
    onPremises: str
    application: str
    applicationInstance: str
    acsApplicationInstance: str
    spoolApplicationInstance: str


class ParticipantsOutput(ActionOutput):
    organizer: OrganizerOutput


class JoininformationOutput(ActionOutput):
    content: str
    contentType: str = OutputField(example_values=["html"])


class LobbybypasssettingsOutput(ActionOutput):
    scope: bool
    isDialInBypassEnabled: bool


class CreateMeetingOutput(ActionOutput):
    odata: OdataOutput
    allowNewTimeProposals: bool
    attendees: list[AttendeesOutput]
    body: BodyOutput
    bodyPreview: str = OutputField(
        example_values=[
            ".........................................................................................................................................\\r\\nJoin Teams Meeting\\r\\nen-US\\r\\nhttps://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYT"
        ]
    )
    changeKey: str = OutputField(example_values=["07XhOkNngkCkqoNfY+k/jQAFHNmDaQ=="])
    createdDateTime: str = OutputField(example_values=["2022-04-22T10:51:54.9092527Z"])
    end: EndOutput
    hasAttachments: bool
    hideAttendees: float = OutputField(example_values=[False])
    iCalUId: str = OutputField(
        example_values=[
            "040000008200E00074C5B7101A82E00800000000A3FE23FB3656D80100000000000000001000000045D024D0A24F814DA4CBB362A95DD153"
        ]
    )
    id: str = OutputField(
        example_values=[
            "AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY_k-jQAAAgENAAAA07XhOkNngkCkqoNfY_k-jQAFHbOt_AAAAA=="
        ]
    )
    importance: str = OutputField(example_values=["normal"])
    isAllDay: bool
    isCancelled: bool
    isDraft: bool
    isOnlineMeeting: bool
    isOrganizer: bool
    isReminderOn: bool
    lastModifiedDateTime: str = OutputField(
        example_values=["2022-04-22T10:51:56.5665393Z"]
    )
    location: LocationOutput
    occurrenceId: str
    onlineMeeting: OnlinemeetingOutput
    onlineMeetingProvider: str = OutputField(example_values=["teamsForBusiness"])
    onlineMeetingUrl: str
    organizer: OrganizerOutput
    originalEndTimeZone: str = OutputField(example_values=["Pacific Standard Time"])
    originalStartTimeZone: str = OutputField(example_values=["Pacific Standard Time"])
    recurrence: str
    reminderMinutesBeforeStart: float = OutputField(example_values=[15])
    responseRequested: bool
    responseStatus: ResponsestatusOutput
    sensitivity: str = OutputField(example_values=["normal"])
    seriesMasterId: str
    showAs: str = OutputField(example_values=["busy"])
    start: StartOutput
    subject: str = OutputField(example_values=["My Code Review"])
    transactionId: str
    type: str = OutputField(example_values=["singleInstance"])
    webLink: str = OutputField(
        cef_types=["url"],
        example_values=[
            "https://outlook.office365.com/owa/?itemid=AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY%2Bk%2FjQAAAgENAAAA07XhOkNngkCkqoNfY%2Bk%2FjQAFHbOt%2BAAAAA%3D%3D&exvsurl=1&path=/calendar/item"
        ],
    )
    joinUrl: str = OutputField(
        cef_types=["url"],
        example_values=[
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d"
        ],
    )
    chatInfo: ChatinfoOutput
    externalId: str
    joinWebUrl: str = OutputField(
        cef_types=["url"],
        example_values=[
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d"
        ],
    )
    endDateTime: str = OutputField(example_values=["2022-04-28T13:11:55.0940461Z"])
    isBroadcast: float = OutputField(example_values=[False])
    meetingCode: str = OutputField(example_values=["230408462435"])
    meetingInfo: str
    participants: ParticipantsOutput
    startDateTime: str = OutputField(example_values=["2022-04-28T12:11:55.0940461Z"])
    joinInformation: JoininformationOutput
    allowMeetingChat: str = OutputField(example_values=["enabled"])
    creationDateTime: str = OutputField(example_values=["2022-04-28T12:11:55.7803555Z"])
    allowedPresenters: str = OutputField(example_values=["everyone"])
    audioConferencing: str
    autoAdmittedUsers: str = OutputField(example_values=["everyoneInCompany"])
    broadcastSettings: str
    lobbyBypassSettings: LobbybypasssettingsOutput
    recordAutomatically: bool
    isEntryExitAnnounced: bool
    joinMeetingIdSettings: str
    videoTeleconferenceId: str
    allowTeamworkReactions: bool
    allowAttendeeToEnableMic: bool
    allowAttendeeToEnableCamera: bool
    outerMeetingAutoAdmittedUsers: str


@app.action(
    description="Create a microsoft teams meeting",
    action_type="generic",
    read_only=False,
    verbose="The <b>add_calendar_event</b> parameter can be used for creating a calender event for the given time and send the meeting invitation to all the attendees. If the value of that parameter is false, then apart from <b>subject</b>, rest of the parameters will be ignored and no event will be created in the calendar.",
)
def create_meeting(
    params: CreateMeetingParams, soar: SOARClient, asset: Asset
) -> CreateMeetingOutput:
    raise NotImplementedError()


class GetChannelMessageParams(Params):
    group_id: str = Param(
        description="ID of group", primary=True, cef_types=["ms teams group id"]
    )
    channel_id: str = Param(
        description="ID of channel", primary=True, cef_types=["ms teams channel id"]
    )
    message_id: str = Param(description="ID of message")


class OdataOutput(ActionOutput):
    type: str = OutputField(example_values=["#microsoft.graph.teamworkUserIdentity"])


class BodyOutput(ActionOutput):
    content: str = OutputField(example_values=["test message"])
    contentType: str = OutputField(example_values=["html"])


class UserOutput(ActionOutput):
    id: str = OutputField(example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"])
    tenantId: str = OutputField(
        example_values=["149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0"]
    )
    odata: OdataOutput
    displayName: str = OutputField(example_values=["Test User"])
    userIdentityType: str = OutputField(example_values=["aadUser"])


class FromOutput(ActionOutput):
    user: UserOutput
    device: str
    application: str


class ChannelidentityOutput(ActionOutput):
    teamId: str = OutputField(
        example_values=["hfyr6hdhyr6s-d42a-452b-9155-379764077e25"]
    )
    channelId: str = OutputField(
        example_values=["10:2daiuhf4c29f6d7041eca70b67979r245437@thread.v2"]
    )


class GetChannelMessageOutput(ActionOutput):
    odata: OdataOutput
    body: BodyOutput
    createdDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    deletedDateTime: str
    etag: str = OutputField(example_values=["1615528921352"])
    eventDetail: str
    id: str = OutputField(example_values=["1517826451101"])
    importance: str = OutputField(example_values=["normal"])
    lastEditedDateTime: str
    lastModifiedDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    locale: str
    messageType: str = OutputField(example_values=["message"])
    policyViolation: str
    replyToId: str
    subject: str
    summary: str
    webUrl: str
    from_: FromOutput
    chatId: str
    channelIdentity: ChannelidentityOutput


@app.action(description="Get message in a channel", action_type="investigate")
def get_channel_message(
    params: GetChannelMessageParams, soar: SOARClient, asset: Asset
) -> GetChannelMessageOutput:
    raise NotImplementedError()


class GetChatMessageParams(Params):
    chat_id: str = Param(
        description="ID of chat", primary=True, cef_types=["ms teams chat id"]
    )
    message_id: str = Param(description="ID of message")


class OdataOutput(ActionOutput):
    type: str


class BodyOutput(ActionOutput):
    content: str = OutputField(example_values=["test message"])
    contentType: str = OutputField(example_values=["text"])


class UserOutput(ActionOutput):
    odata: OdataOutput
    displayName: str = OutputField(example_values=["Test User"])
    id: str = OutputField(example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"])
    userIdentityType: str = OutputField(example_values=["aadUser"])
    tenantId: str = OutputField(example_values=["aadUser"])


class FromOutput(ActionOutput):
    application: str
    device: str
    user: UserOutput


class AttachmentsOutput(ActionOutput):
    id: str = OutputField(example_values=["1722330920100"])
    name: str
    content: str = OutputField(
        example_values=[
            '{"messageId":"1722330920117","messagePreview":"How are you?","messageSender":{"application":null,"device":null,"user":{"userIdentityType":"aadUser","tenantId":"149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0","id":"hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f","displayName":"Test User"}}}'
        ]
    )
    contentUrl: str
    teamsAppId: str
    contentType: str = OutputField(example_values=["messageReference"])
    thumbnailUrl: str


class GetChatMessageOutput(ActionOutput):
    odata: OdataOutput
    body: BodyOutput
    createdDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    deletedDateTime: str
    etag: str = OutputField(example_values=["1615528921765"])
    from_: FromOutput
    id: str = OutputField(example_values=["1517826451101"])
    importance: str = OutputField(example_values=["normal"])
    lastEditedDateTime: str
    lastModifiedDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    locale: str
    messageType: str = OutputField(example_values=["message"])
    policyViolation: str
    replyToId: str
    subject: str
    summary: str
    webUrl: str
    chatId: str = OutputField(
        example_values=[
            "10:1c06006a-1885-401b-8dd2-b23e21dtest1_cbb6948d6abeeac89ae@unq.gbl.spaces"
        ]
    )
    attachments: list[AttachmentsOutput]
    eventDetail: str
    channelIdentity: str


@app.action(description="Get message in a chat", action_type="investigate")
def get_chat_message(
    params: GetChatMessageParams, soar: SOARClient, asset: Asset
) -> GetChatMessageOutput:
    raise NotImplementedError()


class GetResponseMessageParams(Params):
    chat_id: str = Param(
        description="ID of chat", primary=True, cef_types=["ms teams chat id"]
    )
    message_id: str = Param(description="The ID of the message to be replied to")


class OdataOutput(ActionOutput):
    type: str


class BodyOutput(ActionOutput):
    content: str = OutputField(example_values=["test message"])
    contentType: str = OutputField(example_values=["text"])
    message_reply: str = OutputField(example_values=["try it"])


class UserOutput(ActionOutput):
    odata: OdataOutput
    displayName: str = OutputField(example_values=["Test User"])
    id: str = OutputField(example_values=["hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f"])
    userIdentityType: str = OutputField(example_values=["aadUser"])
    tenantId: str = OutputField(example_values=["aadUser"])


class FromOutput(ActionOutput):
    application: str
    device: str
    user: UserOutput


class AttachmentsOutput(ActionOutput):
    id: str = OutputField(example_values=["1722330920117"])
    name: str
    content: str = OutputField(
        example_values=[
            '{"messageId":"1722330920117","messagePreview":"How are you?","messageSender":{"application":null,"device":null,"user":{"userIdentityType":"aadUser","tenantId":"149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0","id":"eeb3645f-df19-47a1-8e8c-fcd234cbuste","displayName":"Test User"}}}'
        ]
    )
    contentUrl: str
    teamsAppId: str
    contentType: str = OutputField(example_values=["messageReference"])
    thumbnailUrl: str


class GetResponseMessageOutput(ActionOutput):
    odata: OdataOutput
    body: BodyOutput
    createdDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    deletedDateTime: str
    etag: str = OutputField(example_values=["1615528921100"])
    from_: FromOutput
    id: str = OutputField(example_values=["1517826451101"])
    importance: str = OutputField(example_values=["normal"])
    contain_attachment: str
    lastEditedDateTime: str
    lastModifiedDateTime: str = OutputField(example_values=["2021-03-12T06:02:01.352Z"])
    locale: str
    messageType: str = OutputField(example_values=["message"])
    policyViolation: str
    replyToId: str
    subject: str
    summary: str
    webUrl: str
    chatId: str = OutputField(
        example_values=[
            "10:1c06006a-1885-401b-8dd2-b23e21dtest1_cbb6948d6abeeac89ae@unq.gbl.spaces"
        ]
    )
    attachments: list[AttachmentsOutput]
    eventDetail: str
    channelIdentity: str


@app.action(
    description="Get response on message in a chat",
    action_type="investigate",
    verbose="Get response action retrieves replies from chat message. It can only find replies if they exist in the most recent 50 messages.",
)
def get_response(
    params: GetResponseMessageParams, soar: SOARClient, asset: Asset
) -> GetResponseMessageOutput:
    raise NotImplementedError()


if __name__ == "__main__":
    app.cli()
