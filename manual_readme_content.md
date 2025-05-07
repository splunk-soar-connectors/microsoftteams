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
