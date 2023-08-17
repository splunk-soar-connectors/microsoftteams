[comment]: # "Auto-generated SOAR connector documentation"
# Microsoft Teams

Publisher: Splunk  
Connector Version: 2.5.0  
Product Vendor: Microsoft  
Product Name: Teams  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.0.2  

This app integrates with Microsoft Teams to support various generic and investigative actions

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2019-2023 Splunk Inc."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
## Note

-   For an admin user, you can run the test connectivity directly.
-   For a non-admin user, you need to get the admin consent first. This can be done by running the
    action **get_admin_consent** by an admin user.

## Authentication

This app requires creating an app in the Azure Active Directory.

-   Navigate to the <https://portal.azure.com> in a browser and log in with a Microsoft account

-   Select **Azure Active Directory** from the left side menu

-   From the left panel, select **App Registrations**

-   At the top of the middle section, select **New registration**

-   On the next page, give a name to your application and click **Register**

-   Once the app is created, the below steps needs to be performed on the next page:



    -   Under **Certificates & secrets** , select **New client secret** . Note this key somewhere
        secure, as it cannot be retrieved after closing the window.
    -   Under **Authentication** , select **Add a platform** . In the **Add a platform** window,
        select **Web** . The **Redirect URLs** should be filled right here. We will get **Redirect
        URLs** from the Splunk SOAR asset that we will create below in the section titled "Configure the
        Microsoft Teams Splunk SOAR app asset".
    -   Under **API Permissions** , the following minimum **Delegated Permissions** from **Microsoft Graph**
        needs to be added:
        -   **OnlineMeetings.ReadWrite** (https://graph.microsoft.com/OnlineMeetings.ReadWrite): Allows an app to create, read online meetings on behalf of the signed-in user. Required to run the **create meeting** action.
        -   **Calendars.ReadWrite** (https://graph.microsoft.com/Calendars.ReadWrite): Allows the app to create, read, update, and delete events in user calendars. Required to run the **create meeting** action with **add_calendar_event** set to true.
        -   **offline_access** (https://graph.microsoft.com/offline_access): Allows the app to read and update user data, even when they are not currently using the app. This permission is required for all actions.
        -   **Channel.ReadBasic.All** (https://graph.microsoft.com/Channel.ReadBasic.All): Read channel names and channel descriptions, on behalf of the signed-in user. This permission is required for 'list channels' action. Required to run the **list channels** action.
        -   **User.ReadBasic.All** (https://graph.microsoft.com/User.ReadBasic.All): Allows the app to read a basic set of profile properties of other users in your organization on behalf of the signed-in user. This includes display name, first and last name, email address, open extensions and photo. Also allows the app to read the full profile of the signed-in user. Required to run the **list users, get admin consent and test connectivity action** action. To run the test connectivity and get admin consent action, User.read scope is sufficient
        -  **ChannelMessage.Send** (https://graph.microsoft.com/ChannelMessage.Send): Allows an app to send channel messages in Microsoft Teams, on behalf of the signed-in user. Required to run the **send message** action
        - **GroupMember.Read.All** (https://graph.microsoft.com/GroupMember.Read.All): Allows the app to list groups, read basic group properties and read membership of all groups the signed-in user has access to. Required to run the **list groups** and **list teams** action

        After making these changes, click **Add permissions** at the bottom of the screen, then
        click **Grant admin consent for <tenant_name>** .

        For revoking the permissions, please refer [this](https://learn.microsoft.com/en-gb/azure/active-directory/manage-apps/manage-application-permissions?pivots=ms-graph) documentation.

        It might happen sometimes that after removing the permissions from the azure app, it might be still visible in the state file as those permissions aren’t fully revoked.

        To verify the permissions are revoked or not, follow the below steps:
        - Navigate to the https://portal.azure.com in a browser and log in with a Microsoft account
        - Select **Azure Active Directory** from the left side menu
        - From the left panel, select **Enterprise applications**
        - Select the application used in the asset
        - From the left hand side select **Permissions**
        - In the **Permissions** page go to **user consent**

        If any extra permissions are present in the user consent, then it should be removed.\
        To remove the permissions visible in the **user consent** please refer [this](https://learn.microsoft.com/en-gb/azure/active-directory/manage-apps/manage-application-permissions?pivots=ms-graph) documentation.

        Note: Following the given steps will remove consent for all the permissions

## State file permissions

Please check the permissions for the state file as mentioned below.

#### State file path


-   For unprivileged instance:
    /\<PHANTOM_HOME_DIRECTORY>/local_data/app_states/\<appid>/\<asset_id>\_state.json

#### State file permissions

-   File rights: rw-rw-r-- (664) (The phantom user should have read and write access for the state
    file)
-   File owner: Appropriate phantom user

## Configure the Microsoft Teams Splunk SOAR app asset

When creating an asset for the **Microsoft Teams** app, place the **Application Id** of the app in
the **Client ID** field and place the password generated during the app creation process in the
**Client Secret** field. Then, after filling out the **Tenant ID** field, click **SAVE** . Both the
Application/Client ID and the Tenant ID can be found in the **Overview** tab on your app's Azure
page.  

Added a new **Scope** configuration parameter with minimum required scopes as the default value, and you can add/delete the scopes from the value according to the requirement. The scopes added in this parameter should be same as added while creating the application on azure portal
  
After saving, a new field will appear in the **Asset Settings** tab. Take the URL found in the
**POST incoming for Microsoft Teams to this location** field and place it in the **Redirect URLs**
field mentioned in a previous step. To this URL, add **/result** . After doing so the URL should
look something like:  
  

https://\<splunk_soar_host>/rest/handler/microsoftteams_6ba1906f-5899-44df-bb65-1bee4df8ca3c/\<asset_name>/result

  
Once again, click Save at the bottom of the screen.  
  
Additionally, updating the Base URL in the Company Settings is also required. Navigate to
**Administration \> Company Settings \> Info** to configure the Base URL For Splunk SOAR Appliance.
Then, select **Save Changes.**  

## Method to run get admin consent

Run **get_admin_consent** action. It will display an URL. Navigate to this URL in a separate browser
tab. This new tab will redirect to a Microsoft login page. Log in to a Microsoft account with
administrator privileges. After logging in, review the requested permissions listed, then click
**Accept** . Finally, close that tab. Action should show a success message.

**Note:** If the URL is not displayed while running the **get_admin_consent** action, the user can
get the URL from the following ways:

-   User can find the URL in 'spawn.log' file.

-   User needs to manually navigate to the URL in a separate browser tab. The URL format is:
    **https://\<splunk_soar_host>/rest/handler/microsoftteams_6ba1906f-5899-44df-bb65-1bee4df8ca3c/\<asset_name>/admin_consent?asset_id=\<asset_id>**

      

    **Steps to fetch asset id**

    -   Open the asset on which the action is executed.

    -   URL for the asset will be in the following format:

          

        **https//\<splunk_soar_host>/apps/\<app_id>/asset/\<asset_id>/**

    -   Take the asset id from the URL.

## Method to run test connectivity

After setting up the asset and user, click the **TEST CONNECTIVITY** button. A window should pop up
and display a URL. Navigate to this URL in a separate browser tab. This new tab will redirect to a
Microsoft login page. Log in to a Microsoft account. After logging in, review the requested
permissions listed, then click **Accept** . Finally, close that tab. The test connectivity window
should show a success message.  
  
The app should now be ready to be used.

## Important points to be considered for 'Create Meeting' action

-   The **timezone** configuration parameter will only be used for **Create Meeting** action, when
    the user wants to provide **start_time** and **end_time** of the meeting.
-   The **timezone** parameter can be configured using the timezone of the microsoft teams calender.
    If not provided, by default the **UTC** timezone will be considered for scheduling the meetings.
-   In case of add_calendar_event = true, if the user wants to provide schedule time for the
    meeting, **start_time** and **end_time** both the parameters are required.

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the Microsoft Teams Server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http         | tcp                | 80   |
| https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Teams asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**client_id** |  required  | string | Client ID
**client_secret** |  required  | password | Client Secret
**tenant_id** |  required  | string | Tenant ID
**timezone** |  optional  | timezone | Microsoft Teams' timezone
**scope** |  required  | string | Scopes to access (space-separated)

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[get admin consent](#action-get-admin-consent) - Get the admin consent for a non-admin user  
[list users](#action-list-users) - List all users  
[send message](#action-send-message) - Send a message to a channel of a group  
[list channels](#action-list-channels) - Lists all channels of a group  
[list groups](#action-list-groups) - List all Azure Groups  
[list teams](#action-list-teams) - List all Microsoft Teams  
[create meeting](#action-create-meeting) - Create a microsoft teams meeting  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

You first need admin consent if you're a non-admin user.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'get admin consent'
Get the admin consent for a non-admin user

Type: **generic**  
Read only: **False**

Action <b>'get admin consent'</b> has to be run by an admin user to provide consent to a non-admin user.

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.data | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |   Admin consent Received 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'list users'
List all users

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.data.\*.accountEnabled | boolean |  |   True  False 
action_result.data.\*.assignedLicenses.\*.disabledPlans | string |  |  
action_result.data.\*.assignedLicenses.\*.skuId | string |  |   6fd2c87f-b296-42f0-b197-1e91e994b900 
action_result.data.\*.assignedPlans.\*.assignedDateTime | string |  |   2018-01-24T11:17:21Z 
action_result.data.\*.assignedPlans.\*.capabilityStatus | string |  |   Enabled 
action_result.data.\*.assignedPlans.\*.service | string |  |   exchange 
action_result.data.\*.assignedPlans.\*.servicePlanId | string |  |   efb87545-963c-4e0d-99df-69c6916d9eb0 
action_result.data.\*.businessPhones | string |  |   22211156 
action_result.data.\*.city | string |  |  
action_result.data.\*.companyName | string |  |  
action_result.data.\*.country | string |  |   US 
action_result.data.\*.deletedDateTime | string |  |   2018-01-24T11:16:50Z 
action_result.data.\*.department | string |  |  
action_result.data.\*.deviceKeys | string |  |  
action_result.data.\*.displayName | string |  `user name`  |   Test User 
action_result.data.\*.employeeId | string |  |  
action_result.data.\*.givenName | string |  `user name`  |   User 
action_result.data.\*.id | string |  |   a1a6d0a2-b0f6-46c1-b49e-98a9ddabac09 
action_result.data.\*.imAddresses | string |  `email`  |   test@abc.com 
action_result.data.\*.jobTitle | string |  |  
action_result.data.\*.legalAgeGroupClassification | string |  |  
action_result.data.\*.mail | string |  `email`  |   test.user@abc.com 
action_result.data.\*.mailNickname | string |  `user name`  |   User 
action_result.data.\*.mobilePhone | string |  |  
action_result.data.\*.officeLocation | string |  |  
action_result.data.\*.onPremisesDomainName | string |  `domain`  |  
action_result.data.\*.onPremisesExtensionAttributes | string |  |  
action_result.data.\*.onPremisesImmutableId | string |  |  
action_result.data.\*.onPremisesLastSyncDateTime | string |  |   2018-01-24T11:16:50Z 
action_result.data.\*.onPremisesProvisioningErrors | string |  |  
action_result.data.\*.onPremisesSamAccountName | string |  |  
action_result.data.\*.onPremisesSecurityIdentifier | string |  |  
action_result.data.\*.onPremisesSyncEnabled | string |  |  
action_result.data.\*.onPremisesUserPrincipalName | string |  |  
action_result.data.\*.passwordPolicies | string |  |  
action_result.data.\*.passwordProfile | string |  |  
action_result.data.\*.postalCode | string |  |  
action_result.data.\*.preferredDataLocation | string |  |  
action_result.data.\*.preferredLanguage | string |  |   en 
action_result.data.\*.provisionedPlans.\*.capabilityStatus | string |  |   Enabled 
action_result.data.\*.provisionedPlans.\*.provisioningStatus | string |  |   Success 
action_result.data.\*.provisionedPlans.\*.service | string |  |   exchange 
action_result.data.\*.proxyAddresses | string |  |   SMTP:test@abc.com 
action_result.data.\*.refreshTokensValidFromDateTime | string |  |   2018-01-24T11:16:50Z 
action_result.data.\*.showInAddressList | string |  |  
action_result.data.\*.state | string |  |  
action_result.data.\*.streetAddress | string |  |  
action_result.data.\*.surname | string |  |   User 
action_result.data.\*.usageLocation | string |  |   US 
action_result.data.\*.userPrincipalName | string |  `email`  |   test.user@abc.com 
action_result.data.\*.userType | string |  |   Member 
action_result.summary.total_users | numeric |  |   5 
action_result.message | string |  |   Total users: 5 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'send message'
Send a message to a channel of a group

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** |  required  | ID of group | string |  `ms teams group id` 
**channel_id** |  required  | ID of channel | string |  `ms teams channel id` 
**message** |  required  | Message to send (HTML is supported) | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.channel_id | string |  `ms teams channel id`  |   cd6f5efb-39f8-492e-80cd-c228c211cf17 
action_result.parameter.group_id | string |  `ms teams group id`  |   594101ba-1fde-482d-8e24-3bbab23a3ca8 
action_result.parameter.message | string |  |   This is a test message  <a href="https://www.google.com"> Test link </a> 
action_result.data.\*.@odata.context | string |  `url`  |   https://test.link.com/beta/$metadata#chatThreads/$entity 
action_result.data.\*.body.content | string |  |   test message 
action_result.data.\*.body.contentType | string |  |   text 
action_result.data.\*.createdDateTime | string |  |   2021-03-12T06:02:01.352Z 
action_result.data.\*.deletedDateTime | string |  |  
action_result.data.\*.etag | string |  |   1615528921352 
action_result.data.\*.from.application | string |  |  
action_result.data.\*.from.conversation | string |  |  
action_result.data.\*.from.device | string |  |  
action_result.data.\*.from.user.displayName | string |  |   Test User 
action_result.data.\*.from.user.id | string |  |   eeb3645f-df19-47a1-8e8c-fcd234cb5f6f 
action_result.data.\*.from.user.userIdentityType | string |  |   aadUser 
action_result.data.\*.id | string |  |   1517826451101 
action_result.data.\*.importance | string |  |   normal 
action_result.data.\*.lastEditedDateTime | string |  |  
action_result.data.\*.lastModifiedDateTime | string |  |   2021-03-12T06:02:01.352Z 
action_result.data.\*.locale | string |  |  
action_result.data.\*.messageType | string |  |   message 
action_result.data.\*.policyViolation | string |  |  
action_result.data.\*.replyToId | string |  |  
action_result.data.\*.subject | string |  |  
action_result.data.\*.summary | string |  |  
action_result.data.\*.webUrl | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |   Message sent 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'list channels'
Lists all channels of a group

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** |  required  | ID of group | string |  `ms teams group id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.group_id | string |  `ms teams group id`  |   caf444a0-0e0e-426b-98ea-db67ff6b0b25 
action_result.data.\*.description | string |  |   Test team 
action_result.data.\*.displayName | string |  |   General 
action_result.data.\*.email | string |  |  
action_result.data.\*.id | string |  `ms teams channel id`  |   78f4a378-e7d3-49c8-a8a7-645b886752d9 
action_result.data.\*.isFavoriteByDefault | string |  |  
action_result.data.\*.membershipType | string |  |   standard 
action_result.data.\*.webUrl | string |  |  
action_result.summary.total_channels | numeric |  |   1 
action_result.message | string |  |   Total channels: 3 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'list groups'
List all Azure Groups

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.data.\*.classification | string |  |   classification 
action_result.data.\*.createdDateTime | string |  |   2018-01-30T09:43:13Z 
action_result.data.\*.deletedDateTime | string |  |   2018-01-30T09:43:13Z 
action_result.data.\*.description | string |  |   team2 
action_result.data.\*.displayName | string |  |   team2 
action_result.data.\*.expirationDateTime | string |  |  
action_result.data.\*.groupTypes | string |  |   DynamicMembership 
action_result.data.\*.id | string |  `ms teams group id`  |   594101ba-1fde-482d-8e24-3bbab23a3ca8 
action_result.data.\*.isAssignableToRole | string |  |  
action_result.data.\*.mail | string |  `email`  |   team2@test.com 
action_result.data.\*.mailEnabled | boolean |  |   True  False 
action_result.data.\*.mailNickname | string |  |   team2 
action_result.data.\*.membershipRule | string |  |   user.department -eq "Marketing" 
action_result.data.\*.membershipRuleProcessingState | string |  |   on 
action_result.data.\*.onPremisesDomainName | string |  |  
action_result.data.\*.onPremisesLastSyncDateTime | string |  |   2018-01-30T09:43:13Z 
action_result.data.\*.onPremisesNetBiosName | string |  |  
action_result.data.\*.onPremisesProvisioningErrors | string |  |  
action_result.data.\*.onPremisesSamAccountName | string |  |  
action_result.data.\*.onPremisesSecurityIdentifier | string |  |  
action_result.data.\*.onPremisesSyncEnabled | string |  |  
action_result.data.\*.preferredDataLocation | string |  |  
action_result.data.\*.preferredLanguage | string |  |  
action_result.data.\*.proxyAddresses | string |  |   SMTP : team2@test.com 
action_result.data.\*.renewedDateTime | string |  |   2018-01-30T09:43:13Z 
action_result.data.\*.resourceBehaviorOptions | string |  |  
action_result.data.\*.resourceProvisioningOptions | string |  |  
action_result.data.\*.securityEnabled | boolean |  |   True  False 
action_result.data.\*.securityIdentifier | string |  |   S-2-22-2-123456789-1234567890-123456789-1234567890 
action_result.data.\*.theme | string |  |  
action_result.data.\*.visibility | string |  |   Private 
action_result.summary.total_groups | numeric |  |   4 
action_result.message | string |  |   Total groups: 3 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'list teams'
List all Microsoft Teams

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.data.\*.classification | string |  |  
action_result.data.\*.createdByAppId | string |  |  
action_result.data.\*.createdDateTime | string |  |   2018-02-05T21:42:33Z 
action_result.data.\*.deletedDateTime | string |  |  
action_result.data.\*.description | string |  |   TeamOne 
action_result.data.\*.displayName | string |  |   TeamOne 
action_result.data.\*.expirationDateTime | string |  |  
action_result.data.\*.groupTypes.\*. | string |  |   Unified 
action_result.data.\*.id | string |  `ms teams group id`  |   a84b973e-ad51-4248-9a3e-df054415f026 
action_result.data.\*.isAssignableToRole | string |  |  
action_result.data.\*.isManagementRestricted | string |  |  
action_result.data.\*.mail | string |  `email`  |   test@test.com 
action_result.data.\*.mailEnabled | boolean |  |   True  False 
action_result.data.\*.mailNickname | string |  |   TeamOne 
action_result.data.\*.membershipRule | string |  |  
action_result.data.\*.membershipRuleProcessingState | string |  |  
action_result.data.\*.onPremisesDomainName | string |  `domain`  |  
action_result.data.\*.onPremisesLastSyncDateTime | string |  |  
action_result.data.\*.onPremisesNetBiosName | string |  |  
action_result.data.\*.onPremisesSamAccountName | string |  |  
action_result.data.\*.onPremisesSecurityIdentifier | string |  |  
action_result.data.\*.onPremisesSyncEnabled | string |  |  
action_result.data.\*.preferredDataLocation | string |  |  
action_result.data.\*.preferredLanguage | string |  |  
action_result.data.\*.proxyAddresses | string |  |   SMTP:test@test.com 
action_result.data.\*.proxyAddresses.\*. | string |  |   SPO:SPO_2e56f4be-737f-418d-8dee-7d01911b91df@SPO_a417c578-c7ee-480d-a225-d48057e74df5 
action_result.data.\*.renewedDateTime | string |  |   2018-02-05T21:42:33Z 
action_result.data.\*.resourceProvisioningOptions.\*. | string |  |   Team 
action_result.data.\*.securityEnabled | boolean |  |   True  False 
action_result.data.\*.securityIdentifier | string |  |   S-1-12-1-2823526206-1112059217-98516634-653268292 
action_result.data.\*.theme | string |  |  
action_result.data.\*.visibility | string |  |   Public 
action_result.data.\*.writebackConfiguration.isEnabled | string |  |  
action_result.data.\*.writebackConfiguration.onPremisesGroupType | string |  |  
action_result.summary.total_teams | numeric |  |   1 
action_result.message | string |  |   Total teams: 1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'create meeting'
Create a microsoft teams meeting

Type: **generic**  
Read only: **False**

The <b>add_calendar_event</b> parameter can be used for creating a calender event for the given time and send the meeting invitation to all the attendees. If the value of that parameter is false, then apart from <b>subject</b>, rest of the parameters will be ignored and no event will be created in the calendar.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**add_calendar_event** |  optional  | Create a calendar event for the meeting or not | boolean | 
**subject** |  optional  | Subject of the meeting | string | 
**description** |  optional  | Description of the meeting | string | 
**start_time** |  optional  | Date and Time to start the meeting | string | 
**end_time** |  optional  | Date and Time to end the meeting | string | 
**attendees** |  optional  | Email-id of the users to send the meeting invitation | string |  `email` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.add_calendar_event | boolean |  |   False  True 
action_result.parameter.attendees | string |  `email`  |   test@abc.com, testuser@abc.com 
action_result.parameter.description | string |  |   Test 
action_result.parameter.end_time | string |  |   2017-04-15T12:30:00  24 April, 2022 4:30 am 
action_result.parameter.start_time | string |  |   2017-04-15T12:00:00  24 April, 2022 4 am 
action_result.parameter.subject | string |  |   Let's go for lunch 
action_result.data.\*.@odata.context | string |  `url`  |   https://graph.microsoft.com/v1.0/$metadata#users('eeb3645f-df19-47a1-8e8c-fcd234cb5f6f')/calendar/events/$entity  https://graph.microsoft.com/v1.0/$metadata#users('eeb3645f-df19-47a1-8e8c-fcd234cb5f6f')/onlineMeetings/$entity 
action_result.data.\*.@odata.etag | string |  |   W/"07XhOkNngkCkqoNfY+k/jQAFHNmDaQ==" 
action_result.data.\*.allowNewTimeProposals | boolean |  |   True  False 
action_result.data.\*.attendees.\*.emailAddress.address | string |  `email`  |   test@abc.com 
action_result.data.\*.attendees.\*.emailAddress.name | string |  `email`  |   test@abc.com 
action_result.data.\*.attendees.\*.status.response | string |  |   none 
action_result.data.\*.attendees.\*.status.time | string |  |   0001-01-01T00:00:00Z 
action_result.data.\*.attendees.\*.type | string |  |   required 
action_result.data.\*.body.content | string |  |  
action_result.data.\*.body.contentType | string |  |   html 
action_result.data.\*.bodyPreview | string |  |   .........................................................................................................................................\\r\\nJoin Teams Meeting\\r\\nen-US\\r\\nhttps://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYT 
action_result.data.\*.changeKey | string |  |   07XhOkNngkCkqoNfY+k/jQAFHNmDaQ== 
action_result.data.\*.createdDateTime | string |  |   2022-04-22T10:51:54.9092527Z 
action_result.data.\*.end.dateTime | string |  |   2022-04-23T12:40:00.0000000 
action_result.data.\*.end.timeZone | string |  |   Pacific Standard Time 
action_result.data.\*.hasAttachments | boolean |  |   True  False 
action_result.data.\*.hideAttendees | numeric |  |   False 
action_result.data.\*.iCalUId | string |  |   040000008200E00074C5B7101A82E00800000000A3FE23FB3656D80100000000000000001000000045D024D0A24F814DA4CBB362A95DD153 
action_result.data.\*.id | string |  |   AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY_k-jQAAAgENAAAA07XhOkNngkCkqoNfY_k-jQAFHbOt_AAAAA== 
action_result.data.\*.importance | string |  |   normal 
action_result.data.\*.isAllDay | boolean |  |   True  False 
action_result.data.\*.isCancelled | boolean |  |   True  False 
action_result.data.\*.isDraft | boolean |  |   True  False 
action_result.data.\*.isOnlineMeeting | boolean |  |   True  False 
action_result.data.\*.isOrganizer | boolean |  |   True  False 
action_result.data.\*.isReminderOn | boolean |  |   True  False 
action_result.data.\*.lastModifiedDateTime | string |  |   2022-04-22T10:51:56.5665393Z 
action_result.data.\*.location.displayName | string |  |   Meeting Room1 
action_result.data.\*.location.locationType | string |  |   default 
action_result.data.\*.location.uniqueIdType | string |  |   unknown 
action_result.data.\*.occurrenceId | string |  |  
action_result.data.\*.onlineMeeting.joinUrl | string |  `url`  |   https://teams.microsoft.com/l/meetup-join/19%3ameeting_ZDljMDhjMDAtNWI2Yy00MGUxLWExYjUtYThjNzMwNDc4NzZj%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d 
action_result.data.\*.onlineMeetingProvider | string |  |   teamsForBusiness 
action_result.data.\*.onlineMeetingUrl | string |  |  
action_result.data.\*.organizer.emailAddress.address | string |  `email`  |   test@abc.com 
action_result.data.\*.organizer.emailAddress.name | string |  |   Test User 
action_result.data.\*.originalEndTimeZone | string |  |   Pacific Standard Time 
action_result.data.\*.originalStartTimeZone | string |  |   Pacific Standard Time 
action_result.data.\*.recurrence | string |  |  
action_result.data.\*.reminderMinutesBeforeStart | numeric |  |   15 
action_result.data.\*.responseRequested | boolean |  |   True  False 
action_result.data.\*.responseStatus.response | string |  |   organizer 
action_result.data.\*.responseStatus.time | string |  |   0001-01-01T00:00:00Z 
action_result.data.\*.sensitivity | string |  |   normal 
action_result.data.\*.seriesMasterId | string |  |  
action_result.data.\*.showAs | string |  |   busy 
action_result.data.\*.start.dateTime | string |  |   2022-04-23T12:30:00.0000000 
action_result.data.\*.start.timeZone | string |  |   Pacific Standard Time 
action_result.data.\*.subject | string |  |   My Code Review 
action_result.data.\*.transactionId | string |  |  
action_result.data.\*.type | string |  |   singleInstance 
action_result.data.\*.webLink | string |  `url`  |   https://outlook.office365.com/owa/?itemid=AQMkAGYxNGJmOWQyLTlhMjctNGRiOS1iODU0LTA1ZWE3ZmQ3NDU3MQBGAAADeDDJKaEf4EihMWU6SZgKbAcA07XhOkNngkCkqoNfY%2Bk%2FjQAAAgENAAAA07XhOkNngkCkqoNfY%2Bk%2FjQAFHbOt%2BAAAAA%3D%3D&exvsurl=1&path=/calendar/item 
action_result.data.\*.joinUrl | string |  `url`  |   https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d 
action_result.data.\*.chatInfo.threadId | string |  |   19:meeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm@thread.v2 
action_result.data.\*.chatInfo.messageId | string |  |   0 
action_result.data.\*.chatInfo.replyChainMessageId | string |  |  
action_result.data.\*.externalId | string |  |  
action_result.data.\*.joinWebUrl | string |  `url`  |   https://teams.microsoft.com/l/meetup-join/19%3ameeting_MjViZWE2ODItM2UyNi00YjdhLWJhOGUtN2FmYWQwM2NkOTJm%40thread.v2/0?context=%7b%22Tid%22%3a%22140fe46d-819d-4b6d-b7ef-1c0a8270f4f0%22%2c%22Oid%22%3a%22eeb3645f-df19-47a1-8e8c-fcd234cb5f6f%22%7d 
action_result.data.\*.endDateTime | string |  |   2022-04-28T13:11:55.0940461Z 
action_result.data.\*.isBroadcast | numeric |  |   False 
action_result.data.\*.meetingCode | string |  |   230408462435 
action_result.data.\*.meetingInfo | string |  |  
action_result.data.\*.participants.organizer.upn | string |  `email`  |   test@abc.com 
action_result.data.\*.participants.organizer.role | string |  |   presenter 
action_result.data.\*.participants.organizer.identity.user.id | string |  |   eeb3645f-df19-47a1-8e8c-fcd234cb5f6f 
action_result.data.\*.participants.organizer.identity.user.tenantId | string |  |   140fe46d-819d-4b6d-b7ef-1c0a8270f4f0 
action_result.data.\*.participants.organizer.identity.user.displayName | string |  |  
action_result.data.\*.participants.organizer.identity.user.registrantId | string |  |  
action_result.data.\*.participants.organizer.identity.user.identityProvider | string |  |   AAD 
action_result.data.\*.participants.organizer.identity.guest | string |  |  
action_result.data.\*.participants.organizer.identity.phone | string |  |  
action_result.data.\*.participants.organizer.identity.device | string |  |  
action_result.data.\*.participants.organizer.identity.acsUser | string |  |  
action_result.data.\*.participants.organizer.identity.encrypted | string |  |  
action_result.data.\*.participants.organizer.identity.spoolUser | string |  |  
action_result.data.\*.participants.organizer.identity.onPremises | string |  |  
action_result.data.\*.participants.organizer.identity.application | string |  |  
action_result.data.\*.participants.organizer.identity.applicationInstance | string |  |  
action_result.data.\*.participants.organizer.identity.acsApplicationInstance | string |  |  
action_result.data.\*.participants.organizer.identity.spoolApplicationInstance | string |  |  
action_result.data.\*.startDateTime | string |  |   2022-04-28T12:11:55.0940461Z 
action_result.data.\*.joinInformation.content | string |  |  
action_result.data.\*.joinInformation.contentType | string |  |   html 
action_result.data.\*.allowMeetingChat | string |  |   enabled 
action_result.data.\*.creationDateTime | string |  |   2022-04-28T12:11:55.7803555Z 
action_result.data.\*.allowedPresenters | string |  |   everyone 
action_result.data.\*.audioConferencing | string |  |  
action_result.data.\*.autoAdmittedUsers | string |  |   everyoneInCompany 
action_result.data.\*.broadcastSettings | string |  |  
action_result.data.\*.lobbyBypassSettings.scope | boolean |  |   True  False 
action_result.data.\*.lobbyBypassSettings.isDialInBypassEnabled | boolean |  |   True  False 
action_result.data.\*.recordAutomatically | boolean |  |   True  False 
action_result.data.\*.isEntryExitAnnounced | boolean |  |   True  False 
action_result.data.\*.joinMeetingIdSettings | string |  |  
action_result.data.\*.videoTeleconferenceId | string |  |  
action_result.data.\*.allowTeamworkReactions | boolean |  |   True  False 
action_result.data.\*.allowAttendeeToEnableMic | boolean |  |   True  False 
action_result.data.\*.allowAttendeeToEnableCamera | boolean |  |   True  False 
action_result.data.\*.outerMeetingAutoAdmittedUsers | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |   Meeting Created Successfully 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 