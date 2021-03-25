# File: microsoftteams_consts.py
# Copyright (c) 2019-2021 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

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
MSTEAMS_MSGRAPH_SEND_MESSAGE_ENDPOINT = '/teams/{group_id}/channels/{channel_id}/messages'
MSTEAMS_TC_FILE = 'oauth_task.out'
MSTEAMS_TC_STATUS_SLEEP = 3
MSTEAMS_AUTHORIZE_WAIT_TIME = 15
MSTEAMS_REST_REQUEST_SCOPE = 'offline_access group.readwrite.all user.readwrite.all'
MSTEAMS_TOKEN_EXPIRED = 'Access token has expired'
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
MSTEAMS_AUTHORIZE_TROUBLESHOOT_MSG = 'If authorization URL fails to communicate with your Phantom instance, check whether you have:  '\
                                ' 1. Specified the Web Redirect URL of your App -- The Redirect URL should be <POST URL>/result . '\
                                ' 2. Configured the base URL of your Phantom Instance at Administration -> Company Settings -> Info'
MSTEAMS_CODE_RECEIVED_MSG = 'Code Received'
MSTEAMS_MAKING_CONNECTION_MSG = 'Making Connection...'
MSTEAMS_REST_URL_NOT_AVAILABLE_MSG = 'Rest URL not available. Error: {error}'
MSTEAMS_OAUTH_URL_MSG = 'Using OAuth URL:'
MSTEAMS_GENERATING_ACCESS_TOKEN_MSG = 'Generating access token'
MSTEAMS_CURRENT_USER_INFO_MSG = 'Getting info about the current user to verify token'
MSTEAMS_GOT_CURRENT_USER_INFO_MSG = 'Got current user info'
MSTEAMS_INVALID_CHANNEL_MSG = 'Channel {channel_id} does not belong to group {group_id}'
MSTEAMS_INVALID_MESSAGE_FORMAT_MSG = 'Message format: {message_format} is invalid. Must be one of: {valid_formats}'
MSTEAMS_MESSAGE_FORMAT_TEXT = 'text'
MSTEAMS_VALID_MESSAGE_FORMATS = [MSTEAMS_MESSAGE_FORMAT_TEXT, 'html']
MSTEAMS_JSON_GROUP_ID = 'group_id'
MSTEAMS_JSON_CHANNEL_ID = 'channel_id'
MSTEAMS_JSON_MESSAGE = 'message'
MSTEAMS_JSON_MESSAGE_FORMAT = 'message_format'
MSTEAMS_CONFIG_TENANT_ID = 'tenant_id'
MSTEAMS_CONFIG_CLIENT_ID = 'client_id'
MSTEAMS_TOKEN_STRING = 'token'
MSTEAMS_ACCESS_TOKEN_STRING = 'access_token'
MSTEAMS_REFRESH_TOKEN_STRING = 'refresh_token'
MSTEAMS_CONFIG_CLIENT_SECRET = 'client_secret'
MSTEAMS_NEXT_LINK_STRING = '@odata.nextLink'
