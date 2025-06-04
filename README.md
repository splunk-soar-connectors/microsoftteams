# Microsoft Teams

Publisher: Splunk \
Connector Version: 3.1.2 \
Product Vendor: Microsoft \
Product Name: Teams \
Minimum Product Version: 6.3.0

This app integrates with Microsoft Teams to support various generic and investigative actions

## Playbook Backward Compatibility

- With version 3.0.0 of the connector, the 'send message' action has been renamed to 'send channel message'. Please update any existing playbooks by modifying the action name accordingly.

## Note

- For an admin user, you can run the test connectivity directly.
- For a non-admin user, you need to get the admin consent first. This can be done by running the
  action **get_admin_consent** by an admin user.
- New in 3.1.0: there are now two ways to set up an asset: via Azure Active Directory, or via an Azure Bot. If you intend to use the "ask question" action, you must use the new Azure Bot method.

## Authentication (Azure Active Directory)

This app requires creating an app in the Azure Active Directory.

- Navigate to the <https://portal.azure.com> in a browser and log in with a Microsoft account

- Select **Azure Active Directory** from the left side menu

- From the left panel, select **App Registrations**

- At the top of the middle section, select **New registration**

- On the next page, give a name to your application and click **Register**

- Once the app is created, the below steps needs to be performed on the next page:

  - Under **Certificates & secrets** , select **New client secret** . Note this key somewhere
    secure, as it cannot be retrieved after closing the window.

  - Under **Authentication** , select **Add a platform** . In the **Add a platform** window,
    select **Web** . The **Redirect URLs** should be filled right here. We will get \*\*Redirect

    URLs\*\* from the Splunk SOAR asset that we will create below in the section titled "Configure the
    Microsoft Teams Splunk SOAR app asset".

  - Under **API Permissions** , the following minimum **Delegated Permissions** from **Microsoft Graph**
    needs to be added:

    | Permission | Action | Description | Admin Consent Required
    | :--------------- | :-------- | :------------ | :------------------- |
    | offline_access | test connectivity | Allows the app to read and update user data, even when they are not currently using the app. This permission is required to generate the refresh_token, if offline_access is not provided then Test connectivity action will fail and no other action will work. | No
    | User.ReadBasic.All | list users, get admin consent and test connectivity | Allows the app to read a basic set of profile properties of other users in your organization on behalf of the signed-in user. This includes display name, first and last name, email address, open extensions and photo. Also allows the app to read the full profile of the signed-in user | No
    | OnlineMeetings.ReadWrite | create meeting | Allows an app to create, read online meetings on behalf of the signed-in user. | No
    | Calendars.ReadWrite | create meeting (while add_calendar_event parameter is set to True) | Allows the app to create, read, update, and delete events in user calendars. | No
    | Channel.ReadBasic.All | list channels | Read channel names and channel descriptions, on behalf of the signed-in user. | No
    | ChannelMessage.Send | send channel message | Allows an app to send channel messages in Microsoft Teams, on behalf of the signed-in user. | No
    | Chat.Read, Chat.ReadWrite | get chat message | Read single message or message reply in chat, on behalf of the signed-in user. | No
    | ChatMessage.Send | send chat message | Allows an app to send new chat message in specified chat in Microsoft Teams, on behalf of the signed-in user. | No
    | GroupMember.Read.All | list groups, list teams | Allows the app to list groups, read basic group properties and read membership of all groups the signed-in user has access to. | Yes
    | Chat.ReadWrite | read and send chat messages | Allows the app to read and send messages in chats on behalf of the signed-in user. | No |

    After making these changes, click **Add permissions** at the bottom of the screen, then
    click **Grant admin consent for \<tenant_name>** .

## Authentication (Azure Bot)

The "ask question" action requires creating an Azure Bot. This method requires the following:

- Version 6.4.1 or later of the Splunk SOAR platform
- Version 3.1.0 or later of the Microsoft Teams app for Splunk SOAR
- The webhooks feature must be enabled in the SOAR administrative settings
- The webhooks port (default 3500) must be accessible from any IPv4 address (`0.0.0.0/0`)
- The webhooks port must have a valid TLS certificate that is trusted by a Root CA

To set up an Azure Bot:

- Navigate to <https://portal.azure.com> in a browser and log in with your Microsoft account.
- Type "Azure Bot" into the search bar, and select the "Azure Bot" item from the "Marketplace" section.
- On the "Create an Azure Bot" page, complete the form:
  - **Bot Handle**: Choose an appropriate name, such as `SOARBot`.
  - Select an Azure **Subscription** from your account, and select or create a **Resource group** to contain the bot.
  - **Data residency**: Most users can select `Global`. If you have stricter compliance needs, you can select `Regional` and choose either the `West Europe` or `Central India` region.
  - **Pricing tier**: Change to the `Free` plan. The Microsoft Teams app for Splunk SOAR does not use any paid features.
  - **Type of App**: `Multi Tenant`.
  - **Creation type**: `Create new Microsoft App ID`.
  - Leave the **Service management reference** blank.
  - Click **Review + create**, then **Create**. After your bot is created, click **Go to resource**. This brings you to your newly-created bot. Bookmark this page or open a second copy of it in a new tab, as you will need it again later.
- On the left side, under **Settings**, click **Configuration**. Next to the **Microsoft App ID** field, click **Manage Password**. This brings you to the Azure Active Directory role for your bot. We will now set up the permissions for your bot and retrieve its credentials:
  - On the **Certificates and Secrets** page, delete the existing client secret. This secret was created automatically, but we can't use it because we have no way of retrieving its secret value.
  - Click **New client secret**, and give the new secret whatever description and expiration date you like. Click **Add**. _**Before you leave this page, copy the value of the new client secret and make a note of it.**_ You won't be able to retrieve it again later, and you'll need it when configuring the SOAR asset in a future step.
  - On the left sidebar, click **API permissions**. Click **Add a permission**, then **Microsoft Graph**, then **Delegated permissions**. Add the following permissions:
    - `offline_access`
    - `User.ReadBasic.All`
    - `OnlineMeetings.ReadWrite`
    - `Calendars.ReadWrite`
    - `Channel.ReadBasic.All`
    - `ChannelMessage.Send`
    - `ChatMessage.Send`
    - `Chat.ReadWrite.All`
    - `GroupMember.ReadWrite.All`
  - Click **Add permissions**. Click **Grant admin consent**, then **Yes**.
  - On the left sidebar, click **Overview**. Copy the **Application (client) ID** and the **Directory (tenant) ID** and make a note of them for the next step. Leave this page open, as you will need it again soon.
- In a new tab, open Splunk SOAR. Navigate to **Apps**, find **Microsoft Teams**, and click **Configure New Asset**. We will now configure the SOAR asset:
  - On the **Asset Info** tab, assign whatever name, description, and tags you like. Assign an Automation Broker, if needed.
  - On the **Asset Settings** tab, paste in the **Client ID**, **Client Secret**, and **Tenant ID** you copied earlier. Set **Microsoft Teams' timezone** to your local timezone. Copy the value of the **POST incoming for Microsoft Teams to this location** field, and make a note of it for later.
  - On the **Webhook Settings** tab, ensure that **Enable webhooks for this asset** is checked. Leave all the other settings at their defaults, and click **Save**. Copy the value of the new **URL for this webhook** field, and note it for later. Leave this page open, you'll need it again soon.
- Return to the Azure Active Directory page:
  - Click **Add a Redirect URI**, then **Add a platform**, then **Web**.
  - For the **Redirect URI**, paste in the **POST incoming** URL you copied earlier, and add `/result` to the end. Click **Configure**.
  - You can now close this tab.
- Return to the Azure Bot page:
  - On the left sidebar, under **Settings**, click **Configuration**. For the **Messaging endpoint**, paste in the **Webhook URL** you copied earlier. Click **Apply**.
  - On the left sidebar, under **Settings**, click **Channels**. Click **Microsoft Teams** and agree to the Terms of Service. Under **Messaging**, select **Microsoft Teams Commercial**, then click **Apply**.
  - You can now close this tab.
- Return to the Splunk SOAR Asset Configuration page.
  - Under **Asset Settings**, click **Test Connectivity**. Follow the instructions that appear for authorizing the app. After the connectivity check succeeds, click **Close**.
  - Copy the **URL for this webhook** again, and paste it into your browser's address bar. Add `/app_package` to the end, and hit enter. Your browser will download an `appPackage.zip` file, which you will use in the next step.
  - You can now close the SOAR asset page, if you like.
- Open the Microsoft Teams app on your desktop or web browser, and log in as a user with administrative privileges. We will now install the SOARBot app in your Teams workspace:
  - On the left sidebar, click **Apps**. In the middle pane, click **Manage your apps**.
  - On the top bar, click **Upload an app**, then **Upload a custom app**. Select the `appPackage.zip` you downloaded previously. Click **Add**.

The app is now configured successfully. Please note that due to a Microsoft limitation, it may take up to 24 hours for your Azure Bot to be fully provisioned. During this time, users may receive an error when trying to submit responses to the `ask question` action.

## Method to revoke permission

- For revoking the permissions, please refer [this](https://learn.microsoft.com/en-gb/azure/active-directory/manage-apps/manage-application-permissions?pivots=ms-graph) documentation.

- After removing the permissions from the Azure app, it might still be visible in the state file as those permissions aren’t fully revoked.

- To verify the permissions are revoked or not, follow the below steps:

  - Navigate to the https://portal.azure.com in a browser and log in with a Microsoft account

  - Select **Azure Active Directory** from the left side menu

  - From the left panel, select **Enterprise applications**

  - Select the application used in the asset

  - From the left hand side select **Permissions**

  - In the **Permissions** page go to **user consent**

  - If any extra permissions are present in the user consent, then it should be removed.

  - To remove the permissions visible in the **user consent** please refer [this](https://learn.microsoft.com/en-gb/azure/active-directory/manage-apps/manage-application-permissions?pivots=ms-graph) documentation.

    Note: Following the given steps will remove consent for all the permissions

## State file permissions

Please check the permissions for the state file as mentioned below.

#### State file path

- For unprivileged instance:
  /\<PHANTOM_HOME_DIRECTORY>/local_data/app_states/\<appid>/\<asset_id>\_state.json

#### State file permissions

- File rights: rw-rw-r-- (664) (The phantom user should have read and write access for the state
  file)
- File owner: Appropriate phantom user

## Configure the Microsoft Teams Splunk SOAR app asset

When creating an asset for the **Microsoft Teams** app, place the **Application Id** of the app in
the **Client ID** field and place the password generated during the app creation process in the
**Client Secret** field. Then, after filling out the **Tenant ID** field, click **SAVE** . Both the
Application/Client ID and the Tenant ID can be found in the **Overview** tab on your app's Azure
page.

The **Scope** configuration parameter's default value is the minimum required scopes. You can add/delete scopes as needed. The scopes added in this parameter should be consistent with those used to create the application on the Azure portal

After saving, a new field will appear in the **Asset Settings** tab. Take the URL found in the
**POST incoming for Microsoft Teams to this location** field and place it in the **Redirect URLs**
field mentioned in a previous step. To this URL, add **/result** . After doing so the URL should
look something like:

https://\<splunk_soar_host>/rest/handler/microsoftteams_6ba1906f-5899-44df-bb65-1bee4df8ca3c/\<asset_name>/result

Once again, click Save at the bottom of the screen.

Additionally, updating the Base URL in the Company Settings is also required. Navigate to
**Administration > Company Settings > Info** to configure the Base URL For Splunk SOAR Appliance.
Then, select **Save Changes.**

## Method to run get admin consent

Run **get_admin_consent** action. It will display an URL in spawn.logs file. Navigate to this URL in a separate browser
tab. This new tab will redirect to a Microsoft login page. Log in to a Microsoft account with
administrator privileges. After logging in, review the requested permissions listed, then click
**Accept** . Finally, close that tab. Action should show a success message.

**Note:** To user can get the URL while running the **get_admin_consent** action via following ways:

1. User can find the URL in 'spawn.log' file. Search for the line starting with "Please hit the mentioned URL in another tab of browser to authorize the user and provide the admin consent". It should contain the URL.

1. If not via spawn.log, user can also manually generate the URL and navigate to the URL in a separate browser tab. The URL format is:
   **https://\<splunk_soar_host>/rest/handler/microsoftteams_6ba1906f-5899-44df-bb65-1bee4df8ca3c/\<asset_name>/admin_consent?asset_id=\<asset_id>**

   User needs to replace splunk_soar_host, asset_name and asset_id with it's corrosponding values in the above mentioned URL.

   **Steps to fetch splunk_soar_host, asset_id and asset_name**

   - Open the asset on which the action is executed.

   - URL for the asset will be in the following format:

     **https://\<splunk_soar_host>/apps/\<app_id>/asset/\<asset_id>/**

   - For example, the splunk_soar_host, app_id and asset_id as highlighted below.

     - After replacing splunk_soar_host, asset_id and asset_name with it's corresponding values the redirect URL would be,

       **https://splunk_soar_test/rest/handler/microsoftteams_6ba1906f-5899-44df-bb65-1bee4df8ca3c/microsoft_teams/admin_consent?asset_id=6**

   [![](img/microsoftteams_asset.png)](img/microsoftteams_asset.png)

## Method to run test connectivity

After setting up the asset and user, click the **TEST CONNECTIVITY** button. A window should pop up
and display a URL. Navigate to this URL in a separate browser tab. This new tab will redirect to a
Microsoft login page. Log in to a Microsoft account. After logging in, review the requested
permissions listed, then click **Accept** . Finally, close that tab. The test connectivity window
should show a success message.

The app should now be ready to be used.

## Important points to be considered for 'Create Meeting' action

- The **timezone** configuration parameter will only be used for **Create Meeting** action, when
  the user wants to provide **start_time** and **end_time** of the meeting.
- The **timezone** parameter can be configured using the timezone of the microsoft teams calender.
  If not provided, by default the **UTC** timezone will be considered for scheduling the meetings.
- In case of add_calendar_event = true, if the user wants to provide schedule time for the
  meeting, **start_time** and **end_time** both the parameters are required.

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the Microsoft Teams Server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Microsoft Teams. These variables are specified when configuring a Teams asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**client_id** | required | string | Client ID |
**client_secret** | required | password | Client Secret |
**tenant_id** | required | string | Tenant ID |
**timezone** | optional | timezone | Microsoft Teams' timezone |
**scope** | required | string | Scopes to access (space-separated) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[get admin consent](#action-get-admin-consent) - Get the admin consent for a non-admin user \
[list users](#action-list-users) - List all users \
[send channel message](#action-send-channel-message) - Send a message to a channel of a group \
[ask question](#action-ask-question) - Ask a question in a channel \
[list chats](#action-list-chats) - List chats for authenticated user \
[send direct message](#action-send-direct-message) - Send a direct message to a user \
[send chat message](#action-send-chat-message) - Send a message to specific chat \
[list channels](#action-list-channels) - Lists all channels of a group \
[list groups](#action-list-groups) - List all Azure Groups \
[list teams](#action-list-teams) - List all Microsoft Teams \
[create meeting](#action-create-meeting) - Create a microsoft teams meeting \
[get channel message](#action-get-channel-message) - Get message in a channel \
[get chat message](#action-get-chat-message) - Get message in a chat \
[get response message](#action-get-response-message) - Get response on message in a chat

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

You first need admin consent if you're a non-admin user.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get admin consent'

Get the admin consent for a non-admin user

Type: **generic** \
Read only: **False**

Action <b>'get admin consent'</b> has to be run by an admin user to provide consent to a non-admin user.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Admin consent Received |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list users'

List all users

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.accountEnabled | boolean | | True False |
action_result.data.\*.assignedLicenses.\*.disabledPlans | string | | |
action_result.data.\*.assignedLicenses.\*.skuId | string | | 6fd2c87f-b296-42f0-b197-1e91e994b900 |
action_result.data.\*.assignedPlans.\*.assignedDateTime | string | | 2018-01-24T11:17:21Z |
action_result.data.\*.assignedPlans.\*.capabilityStatus | string | | Enabled |
action_result.data.\*.assignedPlans.\*.service | string | | exchange |
action_result.data.\*.assignedPlans.\*.servicePlanId | string | | efb87545-963c-4e0d-99df-69c6916d9eb0 |
action_result.data.\*.businessPhones | string | | 22211156 |
action_result.data.\*.city | string | | |
action_result.data.\*.companyName | string | | |
action_result.data.\*.country | string | | US |
action_result.data.\*.deletedDateTime | string | | 2018-01-24T11:16:50Z |
action_result.data.\*.department | string | | |
action_result.data.\*.deviceKeys | string | | |
action_result.data.\*.displayName | string | `user name` | Test User |
action_result.data.\*.employeeId | string | | |
action_result.data.\*.givenName | string | `user name` | User |
action_result.data.\*.id | string | | a1a6d0a2-b0f6-46c1-b49e-98a9ddabac09 |
action_result.data.\*.imAddresses | string | `email` | test@abc.com |
action_result.data.\*.jobTitle | string | | |
action_result.data.\*.legalAgeGroupClassification | string | | |
action_result.data.\*.mail | string | `email` | test.user@abc.com |
action_result.data.\*.mailNickname | string | `user name` | User |
action_result.data.\*.mobilePhone | string | | |
action_result.data.\*.officeLocation | string | | |
action_result.data.\*.onPremisesDomainName | string | `domain` | |
action_result.data.\*.onPremisesExtensionAttributes | string | | |
action_result.data.\*.onPremisesImmutableId | string | | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | 2018-01-24T11:16:50Z |
action_result.data.\*.onPremisesProvisioningErrors | string | | |
action_result.data.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.onPremisesSyncEnabled | string | | |
action_result.data.\*.onPremisesUserPrincipalName | string | | |
action_result.data.\*.passwordPolicies | string | | |
action_result.data.\*.passwordProfile | string | | |
action_result.data.\*.postalCode | string | | |
action_result.data.\*.preferredDataLocation | string | | |
action_result.data.\*.preferredLanguage | string | | en |
action_result.data.\*.provisionedPlans.\*.capabilityStatus | string | | Enabled |
action_result.data.\*.provisionedPlans.\*.provisioningStatus | string | | Success |
action_result.data.\*.provisionedPlans.\*.service | string | | exchange |
action_result.data.\*.proxyAddresses | string | | SMTP:test@abc.com |
action_result.data.\*.refreshTokensValidFromDateTime | string | | 2018-01-24T11:16:50Z |
action_result.data.\*.showInAddressList | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.streetAddress | string | | |
action_result.data.\*.surname | string | | User |
action_result.data.\*.usageLocation | string | | US |
action_result.data.\*.userPrincipalName | string | `email` | test.user@abc.com |
action_result.data.\*.userType | string | | Member |
action_result.summary.total_users | numeric | | 5 |
action_result.message | string | | Total users: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'send channel message'

Send a message to a channel of a group

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | ID of group | string | `ms teams group id` |
**channel_id** | required | ID of channel | string | `ms teams channel id` |
**message** | required | Message to send (HTML is supported) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.channel_id | string | `ms teams channel id` | 10:2daiuhf4c29f6d7041eca70b67979r245437@thread.v2 |
action_result.parameter.group_id | string | `ms teams group id` | caf444a0-0e0e-426b-98ea-db67ff6b0b25 |
action_result.parameter.message | string | | This is a test message |
action_result.data.\*.@odata.context | string | `url` | https://test.link.com/beta/$metadata#chatThreads/$entity |
action_result.data.\*.body.content | string | | test message |
action_result.data.\*.body.contentType | string | | text |
action_result.data.\*.createdDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.etag | string | | 1615528921352 |
action_result.data.\*.from.application | string | | |
action_result.data.\*.from.conversation | string | | |
action_result.data.\*.from.device | string | | |
action_result.data.\*.from.user.displayName | string | | Test User |
action_result.data.\*.from.user.id | string | | hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f |
action_result.data.\*.from.user.userIdentityType | string | | aadUser |
action_result.data.\*.id | string | | 1517826451101 |
action_result.data.\*.importance | string | | normal |
action_result.data.\*.lastEditedDateTime | string | | |
action_result.data.\*.lastModifiedDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.locale | string | | |
action_result.data.\*.messageType | string | | message |
action_result.data.\*.policyViolation | string | | |
action_result.data.\*.replyToId | string | | |
action_result.data.\*.from.user.tenantId | string | | 149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0 |
action_result.data.\*.from.user.@odata.type | string | | #microsoft.graph.teamworkUserIdentity |
action_result.data.\*.chatId | string | | |
action_result.data.\*.eventDetail | string | | |
action_result.data.\*.channelIdentity.teamId | string | | hfyr6hdhyr6s-d42a-452b-9155-379764077e25 |
action_result.data.\*.channelIdentity.channelId | string | | 19:391631e7f5984005811c658217ea8f23@thread.tacv2 |
action_result.data.\*.subject | string | | |
action_result.data.\*.summary | string | | |
action_result.data.\*.webUrl | string | | |
action_result.summary | string | | |
action_result.message | string | | Message sent |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ask question'

Ask a question in a channel

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | ID of group | string | `ms teams group id` |
**channel_id** | required | ID of channel | string | `ms teams channel id` |
**message** | required | Question text (Markdown is supported) | string | |
**choices** | optional | Comma-separated list of possible answers (leave blank for a short-answer question) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_id | string | `ms teams group id` | caf444a0-0e0e-426b-98ea-db67ff6b0b25 |
action_result.parameter.channel_id | string | `ms teams channel id` | 10:2daiuhf4c29f6d7041eca70b67979r245437@thread.v2 |
action_result.parameter.message | string | | What is your favorite color? |
action_result.parameter.choices | string | | Red,Green,Blue |
action_result.data.\*.answer | string | | Green |
action_result.data.\*.answered_by | string | | John Smith |
action_result.summary | string | | |
action_result.message | string | | Message sent |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list chats'

List chats for authenticated user

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user** | optional | Filter chats containing specific user (by email or user id) | string | |
**chat_type** | optional | Filter chats by type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.user | string | | |
action_result.parameter.chat_type | string | | |
action_result.data.\*.id | string | `ms teams chat id` | |
action_result.data.\*.topic | string | | |
action_result.data.\*.createdDateTime | string | | |
action_result.data.\*.lastUpdatedDateTime | string | | |
action_result.data.\*.chatType | string | | |
action_result.data.\*.webUrl | string | `url` | |
action_result.data.\*.tenantId | string | | |
action_result.data.\*.viewpoint.isHidden | boolean | | |
action_result.data.\*.viewpoint.lastMessageReadDateTime | string | | |
action_result.data.\*.onlineMeetingInfo.joinWebUrl | string | `url` | |
action_result.data.\*.onlineMeetingInfo.conferenceId | string | | |
action_result.data.\*.onlineMeetingInfo.joinUrl | string | `url` | |
action_result.data.\*.onlineMeetingInfo.phones | string | | |
action_result.data.\*.onlineMeetingInfo.quickDial | string | | |
action_result.data.\*.onlineMeetingInfo.tollFreeNumbers | string | | |
action_result.data.\*.onlineMeetingInfo.tollNumber | string | | |
action_result.summary.total_chats | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'send direct message'

Send a direct message to a user

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | ID of the user to send direct message to | string | `ms teams user id` |
**message** | required | Message content to send | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.user_id | string | `ms teams user id` | |
action_result.parameter.message | string | | |
action_result.data.\*.id | string | `ms teams message id` | |
action_result.data.\*.chatId | string | `ms teams chat id` | |
action_result.data.\*.createdDateTime | string | | |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.lastModifiedDateTime | string | | |
action_result.data.\*.lastEditedDateTime | string | | |
action_result.data.\*.etag | string | | |
action_result.data.\*.importance | string | | |
action_result.data.\*.locale | string | | |
action_result.data.\*.messageType | string | | |
action_result.data.\*.replyToId | string | `ms teams message id` | |
action_result.data.\*.subject | string | | |
action_result.data.\*.summary | string | | |
action_result.data.\*.webUrl | string | `url` | |
action_result.data.\*.from.user.id | string | `ms teams user id` | |
action_result.data.\*.from.user.displayName | string | | |
action_result.data.\*.body.content | string | | |
action_result.data.\*.body.contentType | string | | |
action_result.data.\*.attachments.\*.content | string | | |
action_result.data.\*.attachments.\*.contentType | string | | |
action_result.data.\*.attachments.\*.contentUrl | string | `url` | |
action_result.data.\*.attachments.\*.id | string | `ms teams attachment id` | |
action_result.data.\*.attachments.\*.name | string | | |
action_result.data.\*.attachments.\*.teamsAppId | string | | |
action_result.data.\*.attachments.\*.thumbnailUrl | string | `url` | |
action_result.data.\*.channelIdentity.channelId | string | `ms teams channel id` | |
action_result.data.\*.channelIdentity.teamId | string | `ms teams team id` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'send chat message'

Send a message to specific chat

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**chat_id** | required | ID of the chat to send message to | string | `ms teams chat id` |
**message** | required | Message content to send | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.chat_id | string | `ms teams chat id` | |
action_result.parameter.message | string | | |
action_result.data.\*.id | string | `ms teams message id` | |
action_result.data.\*.chatId | string | `ms teams chat id` | |
action_result.data.\*.createdDateTime | string | | |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.lastModifiedDateTime | string | | |
action_result.data.\*.lastEditedDateTime | string | | |
action_result.data.\*.etag | string | | |
action_result.data.\*.importance | string | | |
action_result.data.\*.locale | string | | |
action_result.data.\*.messageType | string | | |
action_result.data.\*.replyToId | string | `ms teams message id` | |
action_result.data.\*.subject | string | | |
action_result.data.\*.summary | string | | |
action_result.data.\*.webUrl | string | `url` | |
action_result.data.\*.from.user.id | string | `ms teams user id` | |
action_result.data.\*.from.user.displayName | string | | |
action_result.data.\*.body.content | string | | |
action_result.data.\*.body.contentType | string | | |
action_result.data.\*.attachments.\*.content | string | | |
action_result.data.\*.attachments.\*.contentType | string | | |
action_result.data.\*.attachments.\*.contentUrl | string | `url` | |
action_result.data.\*.attachments.\*.id | string | `ms teams attachment id` | |
action_result.data.\*.attachments.\*.name | string | | |
action_result.data.\*.attachments.\*.teamsAppId | string | | |
action_result.data.\*.attachments.\*.thumbnailUrl | string | `url` | |
action_result.data.\*.channelIdentity.channelId | string | `ms teams channel id` | |
action_result.data.\*.channelIdentity.teamId | string | `ms teams team id` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list channels'

Lists all channels of a group

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | ID of group | string | `ms teams group id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_id | string | `ms teams group id` | caf444a0-0e0e-426b-98ea-db67ff6b0b25 |
action_result.data.\*.description | string | | Test team |
action_result.data.\*.displayName | string | | General |
action_result.data.\*.email | string | | |
action_result.data.\*.tenantId | string | | 149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0 |
action_result.data.\*.isArchived | boolean | | True False |
action_result.data.\*.createdDateTime | string | | 2020-07-13T12:39:21.573Z |
action_result.data.\*.id | string | `ms teams channel id` | 78f4a378-e7d3-49c8-a8a7-645b886752d9 |
action_result.data.\*.isFavoriteByDefault | string | | |
action_result.data.\*.membershipType | string | | standard |
action_result.data.\*.webUrl | string | | |
action_result.summary.total_channels | numeric | | 1 |
action_result.message | string | | Total channels: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list groups'

List all Azure Groups

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.classification | string | | classification |
action_result.data.\*.createdDateTime | string | | 2018-01-30T09:43:13Z |
action_result.data.\*.deletedDateTime | string | | 2018-01-30T09:43:13Z |
action_result.data.\*.description | string | | team2 |
action_result.data.\*.displayName | string | | team2 |
action_result.data.\*.uniqueName | string | | |
action_result.data.\*.expirationDateTime | string | | |
action_result.data.\*.groupTypes | string | | DynamicMembership |
action_result.data.\*.id | string | `ms teams group id` | 594101ba-1fde-482d-8e24-3bbab23a3ca8 |
action_result.data.\*.isAssignableToRole | boolean | | |
action_result.data.\*.mail | string | `email` | team2@test.com |
action_result.data.\*.mailEnabled | boolean | | True False |
action_result.data.\*.mailNickname | string | | team2 |
action_result.data.\*.membershipRule | string | | user.department -eq "Marketing" |
action_result.data.\*.membershipRuleProcessingState | string | | on |
action_result.data.\*.onPremisesDomainName | string | | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | 2018-01-30T09:43:13Z |
action_result.data.\*.onPremisesNetBiosName | string | | |
action_result.data.\*.onPremisesProvisioningErrors | string | | |
action_result.data.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.onPremisesSyncEnabled | boolean | | |
action_result.data.\*.preferredDataLocation | string | | |
action_result.data.\*.preferredLanguage | string | | |
action_result.data.\*.proxyAddresses | string | | SMTP : team2@test.com |
action_result.data.\*.renewedDateTime | string | | 2018-01-30T09:43:13Z |
action_result.data.\*.resourceBehaviorOptions | string | | |
action_result.data.\*.resourceProvisioningOptions | string | | |
action_result.data.\*.securityEnabled | boolean | | True False |
action_result.data.\*.securityIdentifier | string | | S-2-22-2-123456789-1234567890-123456789-1234567890 |
action_result.data.\*.theme | string | | |
action_result.data.\*.visibility | string | | Private |
action_result.summary.total_groups | numeric | | 4 |
action_result.message | string | | Total groups: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list teams'

List all Microsoft Teams

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.classification | string | | |
action_result.data.\*.createdByAppId | string | | |
action_result.data.\*.createdDateTime | string | | 2018-02-05T21:42:33Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.description | string | | TeamOne |
action_result.data.\*.displayName | string | | TeamOne |
action_result.data.\*.expirationDateTime | string | | |
action_result.data.\*.groupTypes.\*. | string | | Unified |
action_result.data.\*.id | string | `ms teams group id` | a84b973e-ad51-4248-9a3e-df054415f026 |
action_result.data.\*.isAssignableToRole | string | | |
action_result.data.\*.isManagementRestricted | string | | |
action_result.data.\*.mail | string | `email` | test@test.com |
action_result.data.\*.mailEnabled | boolean | | True False |
action_result.data.\*.mailNickname | string | | TeamOne |
action_result.data.\*.membershipRule | string | | |
action_result.data.\*.membershipRuleProcessingState | string | | |
action_result.data.\*.onPremisesDomainName | string | `domain` | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | |
action_result.data.\*.onPremisesNetBiosName | string | | |
action_result.data.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.onPremisesSyncEnabled | string | | |
action_result.data.\*.preferredDataLocation | string | | |
action_result.data.\*.preferredLanguage | string | | |
action_result.data.\*.proxyAddresses | string | | SMTP:test@test.com |
action_result.data.\*.proxyAddresses.\*. | string | | SPO:SPO_2e56f4be-737f-418d-8dee-7d01911b91df@SPO_a417c578-c7ee-480d-a225-d48057e74df5 |
action_result.data.\*.renewedDateTime | string | | 2018-02-05T21:42:33Z |
action_result.data.\*.resourceProvisioningOptions.\*. | string | | Team |
action_result.data.\*.securityEnabled | boolean | | True False |
action_result.data.\*.securityIdentifier | string | | S-1-12-1-2823526206-1112059217-98516634-653268292 |
action_result.data.\*.theme | string | | |
action_result.data.\*.visibility | string | | Public |
action_result.data.\*.writebackConfiguration.isEnabled | string | | |
action_result.data.\*.writebackConfiguration.onPremisesGroupType | string | | |
action_result.summary.total_teams | numeric | | 1 |
action_result.message | string | | Total teams: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create meeting'

Create a microsoft teams meeting

Type: **generic** \
Read only: **False**

The <b>add_calendar_event</b> parameter can be used for creating a calender event for the given time and send the meeting invitation to all the attendees. If the value of that parameter is false, then apart from <b>subject</b>, rest of the parameters will be ignored and no event will be created in the calendar.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**add_calendar_event** | optional | Create a calendar event for the meeting or not | boolean | |
**subject** | optional | Subject of the meeting | string | |
**description** | optional | Description of the meeting | string | |
**start_time** | optional | Date and Time to start the meeting | string | |
**end_time** | optional | Date and Time to end the meeting | string | |
**attendees** | optional | Email-id of the users to send the meeting invitation | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.add_calendar_event | boolean | | False True |
action_result.parameter.attendees | string | `email` | test@abc.com, testuser@abc.com |
action_result.parameter.description | string | | Test |
action_result.parameter.end_time | string | | 2017-04-15T12:30:00 24 April, 2022 4:30 am |
action_result.parameter.start_time | string | | 2017-04-15T12:00:00 24 April, 2022 4 am |
action_result.parameter.subject | string | | Let's go for lunch |
action_result.data.\*.@odata.context | string | `url` | https://graph.microsoft.com/v1.0/$metadata#users('hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f')/calendar/events/$entity https://graph.microsoft.com/v1.0/$metadata#users('hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f')/onlineMeetings/$entity |
action_result.data.\*.@odata.etag | string | | W/"07XhOkNngkCkqoNfY+k/jQAFHNmDaQ==" |
action_result.data.\*.allowNewTimeProposals | boolean | | True False |
action_result.data.\*.attendees.\*.emailAddress.address | string | `email` | test@abc.com |
action_result.data.\*.attendees.\*.emailAddress.name | string | `email` | test@abc.com |
action_result.data.\*.attendees.\*.status.response | string | | none |
action_result.data.\*.attendees.\*.status.time | string | | 0001-01-01T00:00:00Z |
action_result.data.\*.attendees.\*.type | string | | required |
action_result.data.\*.body.content | string | | |
action_result.data.\*.body.contentType | string | | html |
action_result.data.\*.bodyPreview | string | | .........................................................................................................................................\\r\\nJoin Teams Meeting\\r\\nen-US\\r\\nhttps://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYT |
action_result.data.\*.changeKey | string | | 07XhOkNngkCkqoNfY+k/jQAFHNmDaQ== |
action_result.data.\*.createdDateTime | string | | 2022-04-22T10:51:54.9092527Z |
action_result.data.\*.end.dateTime | string | | 2022-04-23T12:40:00.0000000 |
action_result.data.\*.end.timeZone | string | | Pacific Standard Time |
action_result.data.\*.hasAttachments | boolean | | True False |
action_result.data.\*.hideAttendees | numeric | | False |
action_result.data.\*.iCalUId | string | | 040000008200E00074C5B7101A82E00800000000A3FE23FB3656D80100000000000000001000000045D024D0A24F814DA4CBB362A95DD153 |
action_result.data.\*.id | string | | AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY_k-jQAAAgENAAAA07XhOkNngkCkqoNfY_k-jQAFHbOt_AAAAA== |
action_result.data.\*.importance | string | | normal |
action_result.data.\*.isAllDay | boolean | | True False |
action_result.data.\*.isCancelled | boolean | | True False |
action_result.data.\*.isDraft | boolean | | True False |
action_result.data.\*.isOnlineMeeting | boolean | | True False |
action_result.data.\*.isOrganizer | boolean | | True False |
action_result.data.\*.isReminderOn | boolean | | True False |
action_result.data.\*.lastModifiedDateTime | string | | 2022-04-22T10:51:56.5665393Z |
action_result.data.\*.location.displayName | string | | Meeting Room1 |
action_result.data.\*.location.locationType | string | | default |
action_result.data.\*.location.uniqueIdType | string | | unknown |
action_result.data.\*.occurrenceId | string | | |
action_result.data.\*.onlineMeeting.joinUrl | string | `url` | https://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYThjNzMwNDc4NzZj%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d |
action_result.data.\*.onlineMeetingProvider | string | | teamsForBusiness |
action_result.data.\*.onlineMeetingUrl | string | | |
action_result.data.\*.organizer.emailAddress.address | string | `email` | test@abc.com |
action_result.data.\*.organizer.emailAddress.name | string | | Test User |
action_result.data.\*.originalEndTimeZone | string | | Pacific Standard Time |
action_result.data.\*.originalStartTimeZone | string | | Pacific Standard Time |
action_result.data.\*.recurrence | string | | |
action_result.data.\*.reminderMinutesBeforeStart | numeric | | 15 |
action_result.data.\*.responseRequested | boolean | | True False |
action_result.data.\*.responseStatus.response | string | | organizer |
action_result.data.\*.responseStatus.time | string | | 0001-01-01T00:00:00Z |
action_result.data.\*.sensitivity | string | | normal |
action_result.data.\*.seriesMasterId | string | | |
action_result.data.\*.showAs | string | | busy |
action_result.data.\*.start.dateTime | string | | 2022-04-23T12:30:00.0000000 |
action_result.data.\*.start.timeZone | string | | Pacific Standard Time |
action_result.data.\*.subject | string | | My Code Review |
action_result.data.\*.transactionId | string | | |
action_result.data.\*.type | string | | singleInstance |
action_result.data.\*.webLink | string | `url` | https://outlook.office365.com/owa/?itemid=AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY%2Bk%2FjQAAAgENAAAA07XhOkNngkCkqoNfY%2Bk%2FjQAFHbOt%2BAAAAA%3D%3D&exvsurl=1&path=/calendar/item |
action_result.data.\*.joinUrl | string | `url` | https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d |
action_result.data.\*.chatInfo.threadId | string | | 19:meeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm@thread.v2 |
action_result.data.\*.chatInfo.messageId | string | | 0 |
action_result.data.\*.chatInfo.replyChainMessageId | string | | |
action_result.data.\*.externalId | string | | |
action_result.data.\*.joinWebUrl | string | `url` | https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d |
action_result.data.\*.endDateTime | string | | 2022-04-28T13:11:55.0940461Z |
action_result.data.\*.isBroadcast | numeric | | False |
action_result.data.\*.meetingCode | string | | 230408462435 |
action_result.data.\*.meetingInfo | string | | |
action_result.data.\*.participants.organizer.upn | string | `email` | test@abc.com |
action_result.data.\*.participants.organizer.role | string | | presenter |
action_result.data.\*.participants.organizer.identity.user.id | string | | hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f |
action_result.data.\*.participants.organizer.identity.user.tenantId | string | | 149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0 |
action_result.data.\*.participants.organizer.identity.user.displayName | string | | |
action_result.data.\*.participants.organizer.identity.user.registrantId | string | | |
action_result.data.\*.participants.organizer.identity.user.identityProvider | string | | AAD |
action_result.data.\*.participants.organizer.identity.guest | string | | |
action_result.data.\*.participants.organizer.identity.phone | string | | |
action_result.data.\*.participants.organizer.identity.device | string | | |
action_result.data.\*.participants.organizer.identity.acsUser | string | | |
action_result.data.\*.participants.organizer.identity.encrypted | string | | |
action_result.data.\*.participants.organizer.identity.spoolUser | string | | |
action_result.data.\*.participants.organizer.identity.onPremises | string | | |
action_result.data.\*.participants.organizer.identity.application | string | | |
action_result.data.\*.participants.organizer.identity.applicationInstance | string | | |
action_result.data.\*.participants.organizer.identity.acsApplicationInstance | string | | |
action_result.data.\*.participants.organizer.identity.spoolApplicationInstance | string | | |
action_result.data.\*.startDateTime | string | | 2022-04-28T12:11:55.0940461Z |
action_result.data.\*.joinInformation.content | string | | |
action_result.data.\*.joinInformation.contentType | string | | html |
action_result.data.\*.allowMeetingChat | string | | enabled |
action_result.data.\*.creationDateTime | string | | 2022-04-28T12:11:55.7803555Z |
action_result.data.\*.allowedPresenters | string | | everyone |
action_result.data.\*.audioConferencing | string | | |
action_result.data.\*.autoAdmittedUsers | string | | everyoneInCompany |
action_result.data.\*.broadcastSettings | string | | |
action_result.data.\*.lobbyBypassSettings.scope | boolean | | True False |
action_result.data.\*.lobbyBypassSettings.isDialInBypassEnabled | boolean | | True False |
action_result.data.\*.recordAutomatically | boolean | | True False |
action_result.data.\*.isEntryExitAnnounced | boolean | | True False |
action_result.data.\*.joinMeetingIdSettings | string | | |
action_result.data.\*.videoTeleconferenceId | string | | |
action_result.data.\*.allowTeamworkReactions | boolean | | True False |
action_result.data.\*.allowAttendeeToEnableMic | boolean | | True False |
action_result.data.\*.allowAttendeeToEnableCamera | boolean | | True False |
action_result.data.\*.outerMeetingAutoAdmittedUsers | string | | |
action_result.summary | string | | |
action_result.message | string | | Meeting Created Successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get channel message'

Get message in a channel

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | ID of group | string | `ms teams group id` |
**channel_id** | required | ID of channel | string | `ms teams channel id` |
**message_id** | required | ID of message | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.channel_id | string | `ms teams channel id` | 10:2daiuhf4c29f6d7041eca70b67979r245437@thread.v2 |
action_result.parameter.group_id | string | `ms teams group id` | caf444a0-0e0e-426b-98ea-db67ff6b0b25 |
action_result.parameter.message_id | string | | 1688719160710 |
action_result.data.\*.@odata.context | string | `url` | https://test.link.com/beta/$metadata#chatThreads/$entity |
action_result.data.\*.body.content | string | | test message |
action_result.data.body.\*.contentType | string | | text |
action_result.data.\*.createdDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.etag | string | | 1615528921352 |
action_result.data.\*.eventDetail.@odata.type | string | | |
action_result.data.\*.eventDetail.visibleHistoryStartDateTime | string | | 0001-01-01T00:00:00Z |
action_result.data.\*.eventDetail.members.\*.id | string | | |
action_result.data.\*.eventDetail.members.\*.displayName | string | | |
action_result.data.\*.eventDetail.members.\*.userIdentityType | string | | |
action_result.data.\*.eventDetail.members.\*.tenantId | string | | |
action_result.data.\*.eventDetail.initiator.device | string | | |
action_result.data.\*.eventDetail.initiator.user | string | | |
action_result.data.\*.eventDetail.initiator.application | string | | |
action_result.data.\*.eventDetail.initiator.application.@odata.type | string | | |
action_result.data.\*.eventDetail.initiator.application.id | string | | |
action_result.data.\*.eventDetail.initiator.application.displayName | string | | |
action_result.data.\*.eventDetail.initiator.application.applicationIdentityType | string | | |
action_result.data.\*.from.user.tenantId | string | | 149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0 |
action_result.data.\*.from.user.@odata.type | string | | #microsoft.graph.teamworkUserIdentity |
action_result.data.\*.chatId | string | | |
action_result.data.\*.eventDetail | string | | |
action_result.data.\*.channelIdentity.teamId | string | | hfyr6hdhyr6s-d42a-452b-9155-379764077e25 |
action_result.data.\*.channelIdentity.channelId | string | | 10:2daiuhf4c29f6d7041eca70b67979r245437@thread.v2 |
action_result.data.\*.id | string | | 1517826451101 |
action_result.data.\*.importance | string | | normal |
action_result.data.\*.lastEditedDateTime | string | | |
action_result.data.\*.lastModifiedDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.locale | string | | |
action_result.data.\*.messageType | string | | message |
action_result.data.\*.policyViolation | string | | |
action_result.data.\*.replyToId | string | | |
action_result.data.\*.subject | string | | |
action_result.data.\*.summary | string | | |
action_result.data.\*.webUrl | string | | |
action_result.data.\*.body.contentType | string | | html |
action_result.data.\*.from.user.id | string | | hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f |
action_result.data.\*.from.user.tenantId | string | | 149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0 |
action_result.data.\*.from.user.@odata.type | string | | #microsoft.graph.teamworkUserIdentity |
action_result.data.\*.from.user.displayName | string | | Test User |
action_result.data.\*.from.user.userIdentityType | string | | aadUser |
action_result.data.\*.from.device | string | | |
action_result.data.\*.from.application | string | | |
action_result.data.\*.chatId | string | | |
action_result.data.\*.eventDetail | string | | |
action_result.data.\*.channelIdentity.teamId | string | | hfyr6hdhyr6s-d42a-452b-9155-379764077e25 |
action_result.data.\*.channelIdentity.channelId | string | | 10:2daiuhf4c29f6d7041eca70b67979r245437@thread.v2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Message sent |

## action: 'get chat message'

Get message in a chat

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**chat_id** | required | ID of chat | string | `ms teams chat id` |
**message_id** | required | ID of message | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.chat_id | string | `ms teams chat id` | 10:1c06006a-1885-401b-8dd2-b23e21dtest1_cbb6948d6abeeac89ae@unq.gbl.spaces |
action_result.parameter.message_id | string | | 1688719160100 |
action_result.data.\*.@odata.context | string | `url` | https://test.link.com/beta/$metadata#chatThreads/$entity |
action_result.data.\*.body.content | string | | test message |
action_result.data.\*.body.contentType | string | | text |
action_result.data.\*.createdDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.etag | string | | 1615528921765 |
action_result.data.\*.from.application | string | | |
action_result.data.\*.from.device | string | | |
action_result.data.\*.from.user.@odata.type | string | | |
action_result.data.\*.from.user.displayName | string | | Test User |
action_result.data.\*.from.user.id | string | | hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f |
action_result.data.\*.from.user.userIdentityType | string | | aadUser |
action_result.data.\*.from.user.tenantId | string | | aadUser |
action_result.data.\*.id | string | | 1517826451101 |
action_result.data.\*.importance | string | | normal |
action_result.data.\*.lastEditedDateTime | string | | |
action_result.data.\*.lastModifiedDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.locale | string | | |
action_result.data.\*.messageType | string | | message |
action_result.data.\*.policyViolation | string | | |
action_result.data.\*.replyToId | string | | |
action_result.data.\*.subject | string | | |
action_result.data.\*.summary | string | | |
action_result.data.\*.webUrl | string | | |
action_result.data.\*.chatId | string | | 10:1c06006a-1885-401b-8dd2-b23e21dtest1_cbb6948d6abeeac89ae@unq.gbl.spaces |
action_result.data.\*.attachments.\*.id | string | | 1722330920100 |
action_result.data.\*.attachments.\*.name | string | | |
action_result.data.\*.attachments.\*.content | string | | {"messageId":"1722330920117","messagePreview":"How are you?","messageSender":{"application":null,"device":null,"user":{"userIdentityType":"aadUser","tenantId":"149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0","id":"hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f","displayName":"Test User"}}} |
action_result.data.\*.attachments.\*.contentUrl | string | | |
action_result.data.\*.attachments.\*.teamsAppId | string | | |
action_result.data.\*.attachments.\*.contentType | string | | messageReference |
action_result.data.\*.attachments.\*.thumbnailUrl | string | | |
action_result.data.\*.eventDetail | string | | |
action_result.data.\*.channelIdentity | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Message sent |

## action: 'get response message'

Get response on message in a chat

Type: **investigate** \
Read only: **True**

Get response action retrieves replies from chat message. It can only find replies if they exist in the most recent 50 messages.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**chat_id** | required | ID of chat | string | `ms teams chat id` |
**message_id** | required | The ID of the message to be replied to | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.chat_id | string | `ms teams chat id` | 10:1c06006a-1885-401b-8dd2-b23e21dtest1_cbb6948d6abeeac89ae@unq.gbl.spaces |
action_result.parameter.message_id | string | | 1688719160711 |
action_result.data.\*.@odata.context | string | `url` | https://test.link.com/beta/$metadata#chatThreads/$entity |
action_result.data.\*.body.content | string | | test message |
action_result.data.\*.body.contentType | string | | text |
action_result.data.\*.body.message_reply | string | | try it |
action_result.data.\*.createdDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.etag | string | | 1615528921100 |
action_result.data.\*.from.application | string | | |
action_result.data.\*.from.device | string | | |
action_result.data.\*.from.user.@odata.type | string | | |
action_result.data.\*.from.user.displayName | string | | Test User |
action_result.data.\*.from.user.id | string | | hu45nfhf-df19-47a1-8e8c-fcd234cb5f6f |
action_result.data.\*.from.user.userIdentityType | string | | aadUser |
action_result.data.\*.from.user.tenantId | string | | aadUser |
action_result.data.\*.id | string | | 1517826451101 |
action_result.data.\*.importance | string | | normal |
action_result.data.\*.contain_attachment | string | | |
action_result.data.\*.lastEditedDateTime | string | | |
action_result.data.\*.lastModifiedDateTime | string | | 2021-03-12T06:02:01.352Z |
action_result.data.\*.locale | string | | |
action_result.data.\*.messageType | string | | message |
action_result.data.\*.policyViolation | string | | |
action_result.data.\*.replyToId | string | | |
action_result.data.\*.subject | string | | |
action_result.data.\*.summary | string | | |
action_result.data.\*.webUrl | string | | |
action_result.data.\*.chatId | string | | 10:1c06006a-1885-401b-8dd2-b23e21dtest1_cbb6948d6abeeac89ae@unq.gbl.spaces |
action_result.data.\*.attachments.\*.id | string | | 1722330920117 |
action_result.data.\*.attachments.\*.name | string | | |
action_result.data.\*.attachments.\*.content | string | | {"messageId":"1722330920117","messagePreview":"How are you?","messageSender":{"application":null,"device":null,"user":{"userIdentityType":"aadUser","tenantId":"149y9r6d-819d-4b6d-b7ef-1c0a827792970f4f0","id":"eeb3645f-df19-47a1-8e8c-fcd234cbuste","displayName":"Test User"}}} |
action_result.data.\*.attachments.\*.contentUrl | string | | |
action_result.data.\*.attachments.\*.teamsAppId | string | | |
action_result.data.\*.attachments.\*.contentType | string | | messageReference |
action_result.data.\*.attachments.\*.thumbnailUrl | string | | |
action_result.data.\*.eventDetail | string | | |
action_result.data.\*.channelIdentity | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Message sent |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
