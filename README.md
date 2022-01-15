[comment]: # "Auto-generated SOAR connector documentation"
# Microsoft Teams

Publisher: Splunk  
Connector Version: 2\.3\.11  
Product Vendor: Microsoft  
Product Name: Teams  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 4\.9\.39220  

This app integrates with Microsoft Teams to support various generic and investigative actions

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2019-2022 Splunk Inc."
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
        URLs** from the Phantom asset that we will create below in the section titled "Configure the
        Microsoft Teams Phantom app asset".
    -   Under **API Permissions** , the following **Delegated Permissions** from **Microsoft Graph**
        needs to be added:
        -   Group.ReadWrite.All (https://graph.microsoft.com/Group.ReadWrite.All)
        -   offline_access (https://graph.microsoft.com/offline_access)
        -   User.ReadWrite.All (https://graph.microsoft.com/User.ReadWrite.All)

        After making these changes, click **Add permissions** at the bottom of the screen, then
        click **Grant admin consent for Phantom** .

## State file permissions

Please check the permissions for the state file as mentioned below.

#### State file path

-   For Non-NRI instance: /opt/phantom/local_data/app_states/\<appid>/\<asset_id>\_state.json
-   For NRI instance:
    /\<PHANTOM_HOME_DIRECTORY>/local_data/app_states/\<appid>/\<asset_id>\_state.json

#### State file permissions

-   File rights: rw-rw-r-- (664) (The phantom user should have read and write access for the state
    file)
-   File owner: Appropriate phantom user

## Configure the Microsoft Teams Phantom app asset

When creating an asset for the **Microsoft Teams** app, place the **Application Id** of the app in
the **Client ID** field and place the password generated during the app creation process in the
**Client Secret** field. Then, after filling out the **Tenant ID** field, click **SAVE** . Both the
Application/Client ID and the Tenant ID can be found in the **Overview** tab on your app's Azure
page.  
  
After saving, a new field will appear in the **Asset Settings** tab. Take the URL found in the
**POST incoming for Microsoft Teams to this location** field and place it in the **Redirect URLs**
field mentioned in a previous step. To this URL, add **/result** . After doing so the URL should
look something like:  
  

https://\<phantom_host>/rest/handler/microsoftteams_6ba1906f-5899-44df-bb65-1bee4df8ca3c/\<asset_name>/result

  
Once again, click Save at the bottom of the screen.  
  
Additionally, updating the Base URL in the Phantom Company Settings is also required. Navigate to
**Administration \> Company Settings \> Info** to configure the Base URL For Phantom Appliance.
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
    **https://\<phantom_host>/rest/handler/microsoftteams_6ba1906f-5899-44df-bb65-1bee4df8ca3c/\<asset_name>/admin_consent?asset_id=\<asset_id>**

      

    **Steps to fetch asset id**

    -   Open the asset on which the action is executed.

    -   URL for the asset will be in the following format:

          

        **https//\<phantom_host>/apps/\<app_id>/asset/\<asset_id>/**

    -   Take the asset id from the URL.

## Method to run test connectivity

After setting up the asset and user, click the **TEST CONNECTIVITY** button. A window should pop up
and display a URL. Navigate to this URL in a separate browser tab. This new tab will redirect to a
Microsoft login page. Log in to a Microsoft account. After logging in, review the requested
permissions listed, then click **Accept** . Finally, close that tab. The test connectivity window
should show a success message.  
  
The app should now be ready to be used.


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Teams asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**client\_id** |  required  | string | Client ID
**client\_secret** |  required  | password | Client Secret
**tenant\_id** |  required  | string | Tenant ID

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[get admin consent](#action-get-admin-consent) - Get the admin consent for a non\-admin user  
[list users](#action-list-users) - List all users  
[send message](#action-send-message) - Send a message to a channel of a group  
[list channels](#action-list-channels) - Lists all channels of a group  
[list groups](#action-list-groups) - List all Azure Groups  
[list teams](#action-list-teams) - List all Microsoft Teams  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

You first need admin consent if you're a non\-admin user\.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'get admin consent'
Get the admin consent for a non\-admin user

Type: **generic**  
Read only: **False**

Action <b>'get admin consent'</b> has to be run by an admin user to provide consent to a non\-admin user\.

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list users'
List all users

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data\.\*\.accountEnabled | boolean | 
action\_result\.data\.\*\.assignedLicenses\.\*\.disabledPlans | string | 
action\_result\.data\.\*\.assignedLicenses\.\*\.skuId | string | 
action\_result\.data\.\*\.assignedPlans\.\*\.assignedDateTime | string | 
action\_result\.data\.\*\.assignedPlans\.\*\.capabilityStatus | string | 
action\_result\.data\.\*\.assignedPlans\.\*\.service | string | 
action\_result\.data\.\*\.assignedPlans\.\*\.servicePlanId | string | 
action\_result\.data\.\*\.businessPhones | string | 
action\_result\.data\.\*\.city | string | 
action\_result\.data\.\*\.companyName | string | 
action\_result\.data\.\*\.country | string | 
action\_result\.data\.\*\.deletedDateTime | string | 
action\_result\.data\.\*\.department | string | 
action\_result\.data\.\*\.deviceKeys | string | 
action\_result\.data\.\*\.displayName | string |  `user name` 
action\_result\.data\.\*\.employeeId | string | 
action\_result\.data\.\*\.givenName | string |  `user name` 
action\_result\.data\.\*\.id | string | 
action\_result\.data\.\*\.imAddresses | string |  `email` 
action\_result\.data\.\*\.jobTitle | string | 
action\_result\.data\.\*\.legalAgeGroupClassification | string | 
action\_result\.data\.\*\.mail | string |  `email` 
action\_result\.data\.\*\.mailNickname | string |  `user name` 
action\_result\.data\.\*\.mobilePhone | string | 
action\_result\.data\.\*\.officeLocation | string | 
action\_result\.data\.\*\.onPremisesDomainName | string |  `domain` 
action\_result\.data\.\*\.onPremisesExtensionAttributes | string | 
action\_result\.data\.\*\.onPremisesImmutableId | string | 
action\_result\.data\.\*\.onPremisesLastSyncDateTime | string | 
action\_result\.data\.\*\.onPremisesProvisioningErrors | string | 
action\_result\.data\.\*\.onPremisesSamAccountName | string | 
action\_result\.data\.\*\.onPremisesSecurityIdentifier | string | 
action\_result\.data\.\*\.onPremisesSyncEnabled | string | 
action\_result\.data\.\*\.onPremisesUserPrincipalName | string | 
action\_result\.data\.\*\.passwordPolicies | string | 
action\_result\.data\.\*\.passwordProfile | string | 
action\_result\.data\.\*\.postalCode | string | 
action\_result\.data\.\*\.preferredDataLocation | string | 
action\_result\.data\.\*\.preferredLanguage | string | 
action\_result\.data\.\*\.provisionedPlans\.\*\.capabilityStatus | string | 
action\_result\.data\.\*\.provisionedPlans\.\*\.provisioningStatus | string | 
action\_result\.data\.\*\.provisionedPlans\.\*\.service | string | 
action\_result\.data\.\*\.proxyAddresses | string | 
action\_result\.data\.\*\.refreshTokensValidFromDateTime | string | 
action\_result\.data\.\*\.showInAddressList | string | 
action\_result\.data\.\*\.state | string | 
action\_result\.data\.\*\.streetAddress | string | 
action\_result\.data\.\*\.surname | string | 
action\_result\.data\.\*\.usageLocation | string | 
action\_result\.data\.\*\.userPrincipalName | string |  `email` 
action\_result\.data\.\*\.userType | string | 
action\_result\.summary\.total\_users | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'send message'
Send a message to a channel of a group

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group\_id** |  required  | ID of group | string |  `ms teams group id` 
**channel\_id** |  required  | ID of channel | string |  `ms teams channel id` 
**message** |  required  | Message to send \(HTML is supported\) | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.channel\_id | string |  `ms teams channel id` 
action\_result\.parameter\.group\_id | string |  `ms teams group id` 
action\_result\.parameter\.message | string | 
action\_result\.data\.\*\.\@odata\.context | string |  `url` 
action\_result\.data\.\*\.id | string | 
action\_result\.data\.\*\.body\.content | string | 
action\_result\.data\.\*\.body\.contentType | string | 
action\_result\.data\.\*\.etag | string | 
action\_result\.data\.\*\.from\.user\.id | string | 
action\_result\.data\.\*\.from\.user\.displayName | string | 
action\_result\.data\.\*\.from\.user\.userIdentityType | string | 
action\_result\.data\.\*\.from\.device | string | 
action\_result\.data\.\*\.from\.application | string | 
action\_result\.data\.\*\.from\.conversation | string | 
action\_result\.data\.\*\.locale | string | 
action\_result\.data\.\*\.webUrl | string | 
action\_result\.data\.\*\.subject | string | 
action\_result\.data\.\*\.summary | string | 
action\_result\.data\.\*\.replyToId | string | 
action\_result\.data\.\*\.importance | string | 
action\_result\.data\.\*\.messageType | string | 
action\_result\.data\.\*\.createdDateTime | string | 
action\_result\.data\.\*\.deletedDateTime | string | 
action\_result\.data\.\*\.policyViolation | string | 
action\_result\.data\.\*\.lastEditedDateTime | string | 
action\_result\.data\.\*\.lastModifiedDateTime | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list channels'
Lists all channels of a group

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group\_id** |  required  | ID of group | string |  `ms teams group id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.group\_id | string |  `ms teams group id` 
action\_result\.data\.\*\.description | string | 
action\_result\.data\.\*\.displayName | string | 
action\_result\.data\.\*\.id | string |  `ms teams channel id` 
action\_result\.data\.\*\.email | string | 
action\_result\.data\.\*\.webUrl | string | 
action\_result\.data\.\*\.membershipType | string | 
action\_result\.data\.\*\.isFavoriteByDefault | string | 
action\_result\.summary\.total\_channels | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list groups'
List all Azure Groups

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data\.\*\.classification | string | 
action\_result\.data\.\*\.createdDateTime | string | 
action\_result\.data\.\*\.deletedDateTime | string | 
action\_result\.data\.\*\.description | string | 
action\_result\.data\.\*\.displayName | string | 
action\_result\.data\.\*\.groupTypes | string | 
action\_result\.data\.\*\.id | string |  `ms teams group id` 
action\_result\.data\.\*\.mail | string |  `email` 
action\_result\.data\.\*\.mailEnabled | boolean | 
action\_result\.data\.\*\.mailNickname | string | 
action\_result\.data\.\*\.membershipRule | string | 
action\_result\.data\.\*\.membershipRuleProcessingState | string | 
action\_result\.data\.\*\.onPremisesLastSyncDateTime | string | 
action\_result\.data\.\*\.onPremisesProvisioningErrors | string | 
action\_result\.data\.\*\.onPremisesSecurityIdentifier | string | 
action\_result\.data\.\*\.onPremisesSyncEnabled | string | 
action\_result\.data\.\*\.preferredDataLocation | string | 
action\_result\.data\.\*\.preferredLanguage | string | 
action\_result\.data\.\*\.proxyAddresses | string | 
action\_result\.data\.\*\.renewedDateTime | string | 
action\_result\.data\.\*\.resourceBehaviorOptions | string | 
action\_result\.data\.\*\.resourceProvisioningOptions | string | 
action\_result\.data\.\*\.securityEnabled | boolean | 
action\_result\.data\.\*\.theme | string | 
action\_result\.data\.\*\.visibility | string | 
action\_result\.data\.\*\.expirationDateTime | string | 
action\_result\.data\.\*\.isAssignableToRole | string | 
action\_result\.data\.\*\.securityIdentifier | string | 
action\_result\.data\.\*\.onPremisesDomainName | string | 
action\_result\.data\.\*\.onPremisesNetBiosName | string | 
action\_result\.data\.\*\.onPremisesSamAccountName | string | 
action\_result\.summary\.total\_groups | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list teams'
List all Microsoft Teams

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data\.\*\.classification | string | 
action\_result\.data\.\*\.createdByAppId | string | 
action\_result\.data\.\*\.createdDateTime | string | 
action\_result\.data\.\*\.deletedDateTime | string | 
action\_result\.data\.\*\.description | string | 
action\_result\.data\.\*\.displayName | string | 
action\_result\.data\.\*\.expirationDateTime | string | 
action\_result\.data\.\*\.groupTypes\.\*\. | string | 
action\_result\.data\.\*\.id | string |  `ms teams group id` 
action\_result\.data\.\*\.isAssignableToRole | string | 
action\_result\.data\.\*\.mail | string |  `email` 
action\_result\.data\.\*\.mailEnabled | boolean | 
action\_result\.data\.\*\.mailNickname | string | 
action\_result\.data\.\*\.membershipRule | string | 
action\_result\.data\.\*\.membershipRuleProcessingState | string | 
action\_result\.data\.\*\.onPremisesDomainName | string |  `domain` 
action\_result\.data\.\*\.onPremisesLastSyncDateTime | string | 
action\_result\.data\.\*\.onPremisesNetBiosName | string | 
action\_result\.data\.\*\.onPremisesSamAccountName | string | 
action\_result\.data\.\*\.onPremisesSecurityIdentifier | string | 
action\_result\.data\.\*\.onPremisesSyncEnabled | string | 
action\_result\.data\.\*\.preferredDataLocation | string | 
action\_result\.data\.\*\.preferredLanguage | string | 
action\_result\.data\.\*\.proxyAddresses | string | 
action\_result\.data\.\*\.proxyAddresses\.\*\. | string | 
action\_result\.data\.\*\.renewedDateTime | string | 
action\_result\.data\.\*\.resourceProvisioningOptions\.\*\. | string | 
action\_result\.data\.\*\.securityEnabled | boolean | 
action\_result\.data\.\*\.securityIdentifier | string | 
action\_result\.data\.\*\.theme | string | 
action\_result\.data\.\*\.visibility | string | 
action\_result\.data\.\*\.isManagementRestricted | string | 
action\_result\.data\.\*\.writebackConfiguration\.isEnabled | string | 
action\_result\.data\.\*\.writebackConfiguration\.onPremisesGroupType | string | 
action\_result\.summary\.total\_teams | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 