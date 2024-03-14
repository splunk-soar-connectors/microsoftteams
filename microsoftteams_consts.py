# File: microsoftteams_consts.py
#
# Copyright (c) 2019-2024 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
MSTEAMS_PHANTOM_SYS_INFO_URL = '/system_info'
MSTEAMS_PHANTOM_ASSET_INFO_URL = '/asset/{asset_id}'
MSTEAMS_LOGIN_BASE_URL = 'https://login.microsoftonline.com'
MSTEAMS_SERVER_TOKEN_URL = '/{tenant_id}/oauth2/v2.0/token'
MSTEAMS_AUTHORIZE_URL = '/{tenant_id}/oauth2/v2.0/authorize?client_id={client_id}&redirect_uri={redirect_uri}' \
                       '&response_type={response_type}&state={state}&scope={scope}'
MSTEAMS_ADMIN_CONSENT_URL = '/{tenant_id}/adminconsent?client_id={client_id}&redirect_uri={redirect_uri}&state={state}'
MSTEAMS_MSGRAPH_API_BASE_URL = 'https://graph.microsoft.com/v1.0'
MSTEAMS_MSGRAPH_BETA_API_BASE_URL = 'https://graph.microsoft.com/beta'
MSTEAMS_MSGRAPH_SELF_ENDPOINT = '/me'
MSTEAMS_MSGRAPH_GROUPS_ENDPOINT = '/groups'
MSTEAMS_MSGRAPH_TEAMS_ENDPOINT = '/groups?$filter=resourceProvisioningOptions/Any(x:x eq \'Team\')'
MSTEAMS_MSGRAPH_LIST_USERS_ENDPOINT = '/users'
MSTEAMS_MSGRAPH_LIST_CHANNELS_ENDPOINT = '/teams/{group_id}/channels'
MSTEAMS_MSGRAPH_SEND_MSG_ENDPOINT = '/teams/{group_id}/channels/{channel_id}/messages'
MSTEAMS_MSGRAPH_CALENDER_EVENT_ENDPOINT = '/me/calendar/events'
MSTEAMS_MSGRAPH_ONLINE_MEETING_ENDPOINT = '/me/onlineMeetings'
MSTEAMS_TC_FILE = 'oauth_task.out'
MSTEAMS_TC_STATUS_SLEEP = 3
MSTEAMS_AUTHORIZE_WAIT_TIME = 15
MSTEAMS_TOKEN_NOT_AVAILABLE_MSG = 'Token not available. Please run test connectivity first.'
MSTEAMS_BASE_URL_NOT_FOUND_MSG = 'Phantom Base URL not found in System Settings. ' \
                                'Please specify this value in System Settings.'
MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG = 'Test connectivity failed'
MSTEAMS_TEST_CONNECTIVITY_PASSED_MSG = 'Test connectivity passed'
MSTEAMS_ADMIN_CONSENT_MSG = 'Please hit the mentioned URL in another tab of browser to authorize the user and provide the admin consent: '
MSTEAMS_ADMIN_CONSENT_FAILED_MSG = 'Admin consent not received'
MSTEAMS_ADMIN_CONSENT_PASSED_MSG = 'Admin consent Received'
MSTEAMS_AUTHORIZE_USER_MSG = 'Please authorize user in a separate tab using URL'
MSTEAMS_AUTHORIZE_WAIT_MSG = 'Waiting for authorization to complete'
MSTEAMS_AUTHORIZE_TROUBLESHOOT_MSG = 'If authorization URL fails to communicate with your SOAR instance, check whether you have:  '\
                                ' 1. Specified the Web Redirect URL of your App -- The Redirect URL should be <POST URL>/result . '\
                                ' 2. Configured the base URL of your SOAR Instance at Administration -> Company Settings -> Info'
MSTEAMS_CODE_RECEIVED_MSG = 'Code Received'
MSTEAMS_MAKING_CONNECTION_MSG = 'Making Connection...'
MSTEAMS_REST_URL_NOT_AVAILABLE_MSG = 'Rest URL not available. Error: {error}'
MSTEAMS_OAUTH_URL_MSG = 'Using OAuth URL:'
MSTEAMS_GENERATING_ACCESS_TOKEN_MSG = 'Generating access token'
MSTEAMS_CURRENT_USER_INFO_MSG = 'Getting info about the current user to verify token'
MSTEAMS_GOT_CURRENT_USER_INFO_MSG = 'Got current user info'
MSTEAMS_INVALID_CHANNEL_MSG = 'Channel {channel_id} does not belongs to group {group_id}'
MSTEAMS_STATE_FILE_CORRUPT_ERROR = "Error occurred while loading the state file due to it's unexpected format. " \
    "Resetting the state file with the default format. Please test the connectivity."
MSTEAMS_JSON_GROUP_ID = 'group_id'
MSTEAMS_JSON_CHANNEL_ID = 'channel_id'
MSTEAMS_JSON_MSG = 'message'
MSTEAMS_JSON_SUBJECT = 'subject'
MSTEAMS_JSON_CALENDAR = 'add_calendar_event'
MSTEAMS_JSON_DESCRIPTION = 'description'
MSTEAMS_JSON_START_TIME = 'start_time'
MSTEAMS_JSON_END_TIME = 'end_time'
MSTEAMS_JSON_ATTENDEES = 'attendees'
MSTEAMS_CONFIG_TENANT_ID = 'tenant_id'
MSTEAMS_CONFIG_CLIENT_ID = 'client_id'
MSTEAMS_TOKEN_STRING = 'token'
MSTEAMS_STATE_IS_ENCRYPTED = 'is_encrypted'
MSTEAMS_ACCESS_TOKEN_STRING = 'access_token'
MSTEAMS_REFRESH_TOKEN_STRING = 'refresh_token'
MSTEAMS_CONFIG_CLIENT_SECRET = 'client_secret'  # pragma: allowlist secret
MSTEAMS_CONFIG_TIMEZONE = 'timezone'
MSTEAMS_CONFIG_SCOPE = 'scope'
MSTEAMS_NEXT_LINK_STRING = '@odata.nextLink'
MSTEAMS_DEFAULT_TIMEOUT = 30

# For encryption and decryption
MSTEAMS_ENCRYPT_TOKEN = "Encrypting the {} token"
MSTEAMS_DECRYPT_TOKEN = "Decrypting the {} token"
MSTEAMS_ENCRYPTION_ERROR = "Error occurred while encrypting the state file"
MSTEAMS_DECRYPTION_ERROR = "Error occurred while decrypting the state file"

# Constants relating to '_get_error_message_from_exception'
ERROR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
