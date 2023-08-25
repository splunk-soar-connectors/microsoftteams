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

        After removing the permissions from the Azure app, it might still be visible in the state file as those permissions aren’t fully revoked.

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


The **Scope** configuration parameter's default value is the minimum required scopes. You can add/delete scopes as needed. The scopes added in this parameter should be consistent with those used to create the application on the Azure portal

  
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
