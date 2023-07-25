# File: microsoftteams_connector.py
#
# Copyright (c) 2019-2023 Splunk Inc.
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
#
#
# Phantom App imports
import grp
import json
import os
import pwd
import sys
import time

import encryption_helper
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup, UnicodeDammit
from django.http import HttpResponse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from microsoftteams_consts import *

try:
    import urllib.parse as urllib
except ImportError:
    import urllib


def _handle_login_redirect(request, key):
    """ This function is used to redirect login request to microsoft login page.

    :param request: Data given to REST endpoint
    :param key: Key to search in state file
    :return: response authorization_url/admin_consent_url
    """

    asset_id = request.GET.get('asset_id')
    if not asset_id:
        return HttpResponse('ERROR: Asset ID not found in URL', content_type="text/plain", status=400)
    state = _load_app_state(asset_id)
    if not state:
        return HttpResponse('ERROR: Invalid asset_id', content_type="text/plain", status=400)
    url = state.get(key)
    if not url:
        return HttpResponse('App state is invalid, {key} not found.'.format(key=key), content_type="text/plain", status=400)
    response = HttpResponse(status=302)
    response['Location'] = url
    return response


def _handle_py_ver_compat_for_input_str(python_version, input_str, app_connector=None):
    """
    This method returns the encoded|original string based on the Python version.
    :param python_version: Python major version
    :param input_str: Input string to be processed
    :param app_connector: Object of app_connector class
    :return: input_str (Processed input string based on following logic 'input_str - Python 3; encoded input_str - Python 2')
    """
    try:
        if input_str and python_version == 2:
            input_str = UnicodeDammit(input_str).unicode_markup.encode('utf-8')
    except Exception:
        if app_connector:
            app_connector.debug_print("Error occurred while handling python 2to3 compatibility for the input string")

    return input_str


def _get_error_message_from_exception(self, e):
    """
    Get appropriate error message from the exception.
    :param e: Exception object
    :return: error message
    """

    error_code = None
    error_msg = ERROR_MSG_UNAVAILABLE

    self.error_print("Error occurred.", e)

    try:
        if hasattr(e, "args"):
            if len(e.args) > 1:
                error_code = e.args[0]
                error_msg = e.args[1]
            elif len(e.args) == 1:
                error_msg = e.args[0]
    except Exception as e:
        self.error_print("Error occurred while fetching exception information. Details: {}".format(str(e)))

    if not error_code:
        error_text = "Error Message: {}".format(error_msg)
    else:
        error_text = "Error Code: {}. Error Message: {}".format(error_code, error_msg)

    return error_text


def _load_app_state(asset_id, app_connector=None):
    """ This function is used to load the current state file.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: state: Current state file as a dictionary
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print('In _load_app_state: Invalid asset_id')
        return {}

    app_dir = os.path.dirname(os.path.abspath(__file__))
    state_file = '{0}/{1}_state.json'.format(app_dir, asset_id)
    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print('In _load_app_state: Invalid asset_id')
        return {}

    state = {}
    try:
        with open(real_state_file_path, 'r') as state_file_obj:
            state_file_data = state_file_obj.read()
            state = json.loads(state_file_data)
    except Exception as e:
        if app_connector:
            # Fetching the Python major version
            try:
                python_version = int(sys.version_info[0])
            except Exception:
                app_connector.debug_print("Error occurred while getting the Phantom server's Python major version.")
                return state

            error_text = _get_error_message_from_exception(python_version, e, app_connector)
            app_connector.debug_print('In _load_app_state: {}'.format(error_text))

    if app_connector:
        app_connector.debug_print('Loaded state: ', state)

    return state


def _save_app_state(state, asset_id, app_connector=None):
    """ This function is used to save current state in file.

    :param state: Dictionary which contains data to write in state file
    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS|phantom.APP_ERROR
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print('In _save_app_state: Invalid asset_id')
        return {}

    app_dir = os.path.split(__file__)[0]
    state_file = '{0}/{1}_state.json'.format(app_dir, asset_id)

    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print('In _save_app_state: Invalid asset_id')
        return {}

    if app_connector:
        app_connector.debug_print('Saving state: ', state)

    try:
        with open(real_state_file_path, 'w+') as state_file_obj:
            state_file_obj.write(json.dumps(state))
    except Exception as e:
        # Fetching the Python major version
        try:
            python_version = int(sys.version_info[0])
        except Exception:
            if app_connector:
                app_connector.debug_print("Error occurred while getting the Phantom server's Python major version.")
            return phantom.APP_ERROR

        error_text = _get_error_message_from_exception(python_version, e, app_connector)
        if app_connector:
            app_connector.debug_print('Unable to save state file: {}'.format(error_text))
        print('Unable to save state file: {}'.format(error_text))
        return phantom.APP_ERROR

    return phantom.APP_SUCCESS


def _handle_login_response(request):
    """ This function is used to get the login response of authorization request from microsoft login page.

    :param request: Data given to REST endpoint
    :return: HttpResponse. The response displayed on authorization URL page
    """

    asset_id = request.GET.get('state')
    if not asset_id:
        return HttpResponse('ERROR: Asset ID not found in URL\n{}'.format(json.dumps(request.GET)), content_type="text/plain", status=400)

    # Check for error in URL
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    # If there is an error in response
    if error:
        message = 'Error: {0}'.format(error)
        if error_description:
            message = '{0} Details: {1}'.format(message, error_description)
        return HttpResponse('Server returned {0}'.format(message), content_type="text/plain", status=400)

    code = request.GET.get('code')
    admin_consent = request.GET.get('admin_consent')

    # If none of the code or admin_consent is available
    if not (code or admin_consent):
        return HttpResponse('Error while authenticating\n{0}'.format(json.dumps(request.GET)), content_type="text/plain", status=400)

    state = _load_app_state(asset_id)

    # If value of admin_consent is available
    if admin_consent:
        if admin_consent == 'True':
            admin_consent = True
        else:
            admin_consent = False

        state['admin_consent'] = admin_consent
        _save_app_state(state, asset_id, None)

        # If admin_consent is True
        if admin_consent:
            return HttpResponse('Admin Consent received. Please close this window.', content_type="text/plain")
        return HttpResponse('Admin Consent declined. Please close this window and try again later.', content_type="text/plain", status=400)

    # If value of admin_consent is not available, value of code is available
    state['code'] = code
    try:
        state['code'] = MicrosoftTeamConnector().encrypt_state(code, "code")
        state[MSTEAMS_STATE_IS_ENCRYPTED] = True
    except Exception as e:
        return HttpResponse("{}: {}".format(MSTEAMS_ENCRYPTION_ERROR, str(e)), content_type="text/plain", status=400)
    _save_app_state(state, asset_id, None)

    return HttpResponse('Code received. Please close this window, the action will continue to get new token.', content_type="text/plain")


def _handle_rest_request(request, path_parts):
    """ Handle requests for authorization.

    :param request: Data given to REST endpoint
    :param path_parts: parts of the URL passed
    :return: dictionary containing response parameters
    """

    if len(path_parts) < 2:
        return HttpResponse('error: True, message: Invalid REST endpoint request', content_type="text/plain", status=404)

    call_type = path_parts[1]

    # To handle admin_consent request in get_admin_consent action
    if call_type == 'admin_consent':
        return _handle_login_redirect(request, 'admin_consent_url')

    # To handle authorize request in test connectivity action
    if call_type == 'start_oauth':
        return _handle_login_redirect(request, 'authorization_url')

    # To handle response from microsoft login page
    if call_type == 'result':
        return_val = _handle_login_response(request)
        asset_id = request.GET.get('state')
        if asset_id and asset_id.isalnum():
            app_dir = os.path.dirname(os.path.abspath(__file__))
            auth_status_file_path = '{0}/{1}_{2}'.format(app_dir, asset_id, MSTEAMS_TC_FILE)
            real_auth_status_file_path = os.path.abspath(auth_status_file_path)
            if not os.path.dirname(real_auth_status_file_path) == app_dir:
                return HttpResponse("Error: Invalid asset_id", content_type="text/plain", status=400)
            open(auth_status_file_path, 'w').close()
            try:
                uid = pwd.getpwnam('apache').pw_uid
                gid = grp.getgrnam('phantom').gr_gid
                os.chown(auth_status_file_path, uid, gid)
                os.chmod(auth_status_file_path, '0664')
            except Exception:
                pass

        return return_val
    return HttpResponse('error: Invalid endpoint', content_type="text/plain", status=404)


def _get_dir_name_from_app_name(app_name):
    """ Get name of the directory for the app.

    :param app_name: Name of the application for which directory name is required
    :return: app_name: Name of the directory for the application
    """

    app_name = ''.join([x for x in app_name if x.isalnum()])
    app_name = app_name.lower()
    if not app_name:
        app_name = 'app_for_phantom'
    return app_name


class RetVal(tuple):

    def __new__(cls, val1, val2):

        return tuple.__new__(RetVal, (val1, val2))


class MicrosoftTeamConnector(BaseConnector):

    def __init__(self):

        super(MicrosoftTeamConnector, self).__init__()

        self._state = None
        self._tenant = None
        self._client_id = None
        self._client_secret = None
        self._access_token = None
        self._refresh_token = None
        self.asset_id = self.get_asset_id()
        self._scope = None

    def encrypt_state(self, encrypt_var, token_name):
        """ Handle encryption of token.
        :param encrypt_var: Variable needs to be encrypted
        :return: encrypted variable
        """
        self.debug_print(MSTEAMS_ENCRYPT_TOKEN.format(token_name))   # nosemgrep
        return encryption_helper.encrypt(encrypt_var, self.asset_id)

    def decrypt_state(self, decrypt_var, token_name):
        """ Handle decryption of token.
        :param decrypt_var: Variable needs to be decrypted
        :return: decrypted variable
        """
        self.debug_print(MSTEAMS_DECRYPT_TOKEN.format(token_name))    # nosemgrep
        return encryption_helper.decrypt(decrypt_var, self.asset_id)

    def _process_empty_response(self, response, action_result):
        """ This function is used to process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # If response is OK or No-Content
        if response.status_code in [200, 204]:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Status code: {}. Empty response and no information in the header".format(
            response.status_code)), None)

    def _process_html_response(self, response, action_result):
        """ This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        error_text = _handle_py_ver_compat_for_input_str(self._python_version, error_text, self)
        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code,
                                                                      error_text)

        message = message.replace('{', '{{').replace('}', '}}')

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result):
        """ This function is used to process json response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            error_text = _get_error_message_from_exception(self._python_version, e, self)
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. {}".format(error_text)), None)

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        error_message = _handle_py_ver_compat_for_input_str(self._python_version, response.text.replace('{', '{{').replace('}', '}}'), self)
        message = "Error from server. Status Code: {0} Data from server: {1}".format(response.status_code, error_message)

        # Show only error message if available
        if isinstance(resp_json.get('error', {}), dict) and resp_json.get('error', {}).get('message'):
            error_message = _handle_py_ver_compat_for_input_str(self._python_version, resp_json['error']['message'], self)
            message = "Error from server. Status Code: {0} Data from server: {1}".format(response.status_code, error_message)

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        """ This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': response.status_code})
            action_result.add_debug_data({'r_text': response.text})
            action_result.add_debug_data({'r_headers': response.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in response.headers.get('Content-Type', ''):
            return self._process_json_response(response, action_result)

        if 'text/javascript' in response.headers.get('Content-Type', ''):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the API talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in response.headers.get('Content-Type', ''):
            return self._process_html_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        error_message = _handle_py_ver_compat_for_input_str(self._python_version, response.text.replace('{', '{{').replace('}', '}}'), self)
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            response.status_code, error_message)

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _update_request(self, action_result, endpoint, headers=None, params=None, data=None, method='get'):
        """ This function is used to update the headers with access_token before making REST call.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        # In pagination, URL of next page contains complete URL
        # So no need to modify them
        if endpoint.startswith(MSTEAMS_MSGRAPH_TEAMS_ENDPOINT):
            endpoint = '{0}{1}'.format(MSTEAMS_MSGRAPH_BETA_API_BASE_URL, endpoint)
        elif not endpoint.startswith(MSTEAMS_MSGRAPH_API_BASE_URL):
            endpoint = '{0}{1}'.format(MSTEAMS_MSGRAPH_API_BASE_URL, endpoint)

        if headers is None:
            headers = {}

        self._client_id = urllib.quote(self._client_id)
        self._tenant = urllib.quote(self._tenant)
        token_data = {
            'client_id': self._client_id,
            'scope': self._scope,
            'client_secret': self._client_secret,
            'grant_type': MSTEAMS_REFRESH_TOKEN_STRING,
            'refresh_token': self._refresh_token
        }

        if not self._access_token:
            if not self._refresh_token:
                # If none of the access_token and refresh_token is available
                return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_TOKEN_NOT_AVAILABLE_MSG), None

            # If refresh_token is available and access_token is not available, generate new access_token
            status = self._generate_new_access_token(action_result=action_result, data=token_data)

            if phantom.is_fail(status):
                return action_result.get_status(), None

        headers.update({'Authorization': 'Bearer {0}'.format(self._access_token),
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'})

        ret_val, resp_json = self._make_rest_call(action_result=action_result, endpoint=endpoint, headers=headers,
                                                  params=params, data=data, method=method)

        # If token is expired, generate new token
        if MSTEAMS_TOKEN_EXPIRED in action_result.get_message():
            status = self._generate_new_access_token(action_result=action_result, data=token_data)

            if phantom.is_fail(status):
                return action_result.get_status(), None

            headers.update({'Authorization': 'Bearer {0}'.format(self._access_token)})

            ret_val, resp_json = self._make_rest_call(action_result=action_result, endpoint=endpoint, headers=headers,
                                                      params=params, data=data, method=method)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get", verify=True):
        """ Function that makes the REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param verify: verify server certificate (Default True)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)), resp_json)
        try:
            r = request_func(endpoint, data=data, headers=headers, verify=verify, params=params, timeout=MSTEAMS_DEFAULT_TIMEOUT)
        except Exception as e:
            error_text = _get_error_message_from_exception(self._python_version, e, self)
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Error connecting to server. {}".format(error_text)), resp_json)

        return self._process_response(r, action_result)

    def _get_asset_name(self, action_result):
        """ Get name of the asset using Phantom URL.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), asset name
        """

        asset_id = self.get_asset_id()
        rest_endpoint = MSTEAMS_PHANTOM_ASSET_INFO_URL.format(asset_id=asset_id)
        url = '{}{}'.format(self.get_phantom_base_url() + 'rest', rest_endpoint)
        ret_val, resp_json = self._make_rest_call(action_result=action_result, endpoint=url, verify=False)

        if phantom.is_fail(ret_val):
            return ret_val, None

        asset_name = resp_json.get('name')
        if not asset_name:
            return action_result.set_status(phantom.APP_ERROR, 'Asset Name for id: {0} not found.'.format(asset_id),
                                            None)
        return phantom.APP_SUCCESS, asset_name

    def _get_phantom_base_url_ms(self, action_result):
        """ Get base url of phantom.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        base url of phantom
        """
        url = '{}{}'.format(self.get_phantom_base_url() + 'rest', MSTEAMS_PHANTOM_SYS_INFO_URL)
        ret_val, resp_json = self._make_rest_call(action_result=action_result, endpoint=url, verify=False)
        if phantom.is_fail(ret_val):
            return ret_val, None

        phantom_base_url = resp_json.get('base_url')
        if not phantom_base_url:
            return action_result.set_status(phantom.APP_ERROR, MSTEAMS_BASE_URL_NOT_FOUND_MSG), None

        phantom_base_url = phantom_base_url.strip("/")

        return phantom.APP_SUCCESS, phantom_base_url

    def _get_app_rest_url(self, action_result):
        """ Get URL for making rest calls.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        URL to make rest calls
        """

        ret_val, phantom_base_url = self._get_phantom_base_url_ms(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        ret_val, asset_name = self._get_asset_name(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        self.save_progress('Using Phantom base URL as: {0}'.format(phantom_base_url))
        app_json = self.get_app_json()
        app_name = app_json['name']

        app_dir_name = _get_dir_name_from_app_name(app_name)
        url_to_app_rest = '{0}/rest/handler/{1}_{2}/{3}'.format(phantom_base_url, app_dir_name, app_json['appid'],
                                                                asset_name)
        return phantom.APP_SUCCESS, url_to_app_rest

    def _generate_new_access_token(self, action_result, data):
        """ This function is used to generate new access token using the code obtained on authorization.

        :param action_result: object of ActionResult class
        :param data: Data to send in REST call
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS
        """

        req_url = '{}{}'.format(MSTEAMS_LOGIN_BASE_URL, MSTEAMS_SERVER_TOKEN_URL.format(tenant_id=self._tenant))

        ret_val, resp_json = self._make_rest_call(action_result=action_result, endpoint=req_url,
                                                  data=urllib.urlencode(data), method="post")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self._access_token = resp_json[MSTEAMS_ACCESS_TOKEN_STRING]
        self._refresh_token = resp_json[MSTEAMS_REFRESH_TOKEN_STRING]

        try:
            encrypted_access_token = self.encrypt_state(resp_json[MSTEAMS_ACCESS_TOKEN_STRING], "access")
        except Exception as e:
            self.debug_print("{}: {}".format(MSTEAMS_ENCRYPTION_ERROR, _get_error_message_from_exception(self._python_version, e, self)))
            return action_result.set_status(phantom.APP_ERROR, MSTEAMS_ENCRYPTION_ERROR)

        try:
            encrypted_refresh_token = self.encrypt_state(resp_json[MSTEAMS_REFRESH_TOKEN_STRING], "refresh")
        except Exception as e:
            self.debug_print("{}: {}".format(MSTEAMS_ENCRYPTION_ERROR, _get_error_message_from_exception(self._python_version, e, self)))
            return action_result.set_status(phantom.APP_ERROR, MSTEAMS_ENCRYPTION_ERROR)

        resp_json[MSTEAMS_ACCESS_TOKEN_STRING] = encrypted_access_token
        resp_json[MSTEAMS_REFRESH_TOKEN_STRING] = encrypted_refresh_token

        self._state[MSTEAMS_TOKEN_STRING] = resp_json
        self._state[MSTEAMS_STATE_IS_ENCRYPTED] = True
        self.save_state(self._state)
        _save_app_state(self._state, self.get_asset_id(), self)

        self._state = self.load_state()
        # Scenario -
        #
        # If the corresponding state file doesn't have correct owner, owner group or permissions,
        # the newly generated token is not being saved to state file and automatic workflow for token has been stopped.
        # So we have to check that token from response and token which are saved to state file
        # after successful generation of new token are same or not.

        try:
            if self._access_token != self.decrypt_state(self._state.get(MSTEAMS_TOKEN_STRING, {}).get
                    (MSTEAMS_ACCESS_TOKEN_STRING), "access") or self._refresh_token != self.decrypt_state(self._state.get
                    (MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_REFRESH_TOKEN_STRING), "refresh"):
                message = "Error occurred while saving the newly generated access or "
                message += "refresh token (in place of the expired token) in the state file."
                message += " Please check the owner, owner group, and the permissions of the state file. The Phantom "
                message += "user should have the correct access rights and "
                message += "ownership for the corresponding state file (refer to readme file for more information)."
                return action_result.set_status(phantom.APP_ERROR, message)
        except Exception as e:
            self.debug_print("{}: {}".format(MSTEAMS_DECRYPTION_ERROR, _get_error_message_from_exception(self._python_version, e, self)))
            return action_result.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)

        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        """ Testing of given credentials and obtaining authorization/admin consent for all other actions.

        :param param: (not used in this method)
        :return: status success/failure
        """
        app_state = {}
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(MSTEAMS_MAKING_CONNECTION_MSG)

        # Get initial REST URL
        ret_val, app_rest_url = self._get_app_rest_url(action_result)
        if phantom.is_fail(ret_val):
            self.save_progress(MSTEAMS_REST_URL_NOT_AVAILABLE_MSG.format(error=action_result.get_message()))
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)

        # Append /result to create redirect_uri
        redirect_uri = '{0}/result'.format(app_rest_url)
        app_state['redirect_uri'] = redirect_uri

        self.save_progress(MSTEAMS_OAUTH_URL_MSG)
        self.save_progress(redirect_uri)

        # Authorization URL used to make request for getting code which is used to generate access token
        self._client_id = urllib.quote(self._client_id)
        self._tenant = urllib.quote(self._tenant)
        authorization_url = MSTEAMS_AUTHORIZE_URL.format(tenant_id=self._tenant, client_id=self._client_id,
                                                         redirect_uri=redirect_uri, state=self.get_asset_id(),
                                                         response_type='code',
                                                         scope=self._scope)
        authorization_url = '{}{}'.format(MSTEAMS_LOGIN_BASE_URL, authorization_url)

        app_state['authorization_url'] = authorization_url

        # URL which would be shown to the user
        url_for_authorize_request = '{0}/start_oauth?asset_id={1}&'.format(app_rest_url, self.get_asset_id())
        _save_app_state(app_state, self.get_asset_id(), self)

        self.save_progress(MSTEAMS_AUTHORIZE_USER_MSG)
        self.save_progress(url_for_authorize_request)   # nosemgrep
        self.save_progress(MSTEAMS_AUTHORIZE_TROUBLESHOOT_MSG)
        self.save_progress(MSTEAMS_AUTHORIZE_WAIT_MSG)

        time.sleep(MSTEAMS_AUTHORIZE_WAIT_TIME)

        # Wait for some while user login to Microsoft
        status = self._wait(action_result=action_result)

        if phantom.is_fail(status):
            self.save_progress(MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.get_status()

        # Empty message to override last message of waiting
        self.send_progress('')
        self.save_progress(MSTEAMS_CODE_RECEIVED_MSG)
        self._state = _load_app_state(self.get_asset_id(), self)

        # if code is not available in the state file
        if not self._state or not self._state.get('code'):
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)

        if self._state.get(MSTEAMS_STATE_IS_ENCRYPTED):
            try:
                current_code = self.decrypt_state(self._state['code'], "code")
            except Exception as e:
                self.debug_print("{}: {}".format(MSTEAMS_DECRYPTION_ERROR, _get_error_message_from_exception(self._python_version, e, self)))
                return action_result.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)
        self.save_state(self._state)
        _save_app_state(self._state, self.get_asset_id(), self)
        self.save_progress(MSTEAMS_GENERATING_ACCESS_TOKEN_MSG)

        data = {
            'client_id': self._client_id,
            'scope': self._scope,
            'client_secret': self._client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code': current_code
        }
        # for first time access, new access token is generated
        ret_val = self._generate_new_access_token(action_result=action_result, data=data)

        if phantom.is_fail(ret_val):
            self.save_progress(MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.get_status()

        self.save_progress(MSTEAMS_CURRENT_USER_INFO_MSG)

        url = '{}{}'.format(MSTEAMS_MSGRAPH_API_BASE_URL, MSTEAMS_MSGRAPH_SELF_ENDPOINT)
        ret_val, response = self._update_request(action_result=action_result, endpoint=url)

        if phantom.is_fail(ret_val):
            self.save_progress(MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.get_status()

        self.save_progress(MSTEAMS_GOT_CURRENT_USER_INFO_MSG)
        self.save_progress(MSTEAMS_TEST_CONNECTIVITY_PASSED_MSG)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _wait(self, action_result):
        """ This function is used to hold the action till user login.

        :param action_result: Object of ActionResult class
        :return: status (success/failed)
        """

        app_dir = os.path.dirname(os.path.abspath(__file__))
        # file to check whether the request has been granted or not
        auth_status_file_path = '{0}/{1}_{2}'.format(app_dir, self.get_asset_id(), MSTEAMS_TC_FILE)
        time_out = False

        # wait-time while request is being granted
        for i in range(0, 35):
            if os.path.isfile(auth_status_file_path):
                time_out = True
                os.unlink(auth_status_file_path)
                break
            time.sleep(MSTEAMS_TC_STATUS_SLEEP)

        if not time_out:
            return action_result.set_status(phantom.APP_ERROR, status_message='Timeout. Please try again later.')
        self.send_progress('Authenticated')
        return phantom.APP_SUCCESS

    def _handle_get_admin_consent(self, param):
        """ This function is used to get the consent from admin.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, app_rest_url = self._get_app_rest_url(action_result)
        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR,
                                            status_message="Unable to get the URL to the app's REST Endpoint. "
                                                           "Error: {0}".format(action_result.get_message()))
        redirect_uri = '{0}/result'.format(app_rest_url)

        # Store admin_consent_url to state file so that we can access it from _handle_rest_request
        self._client_id = urllib.quote(self._client_id)
        self._tenant = urllib.quote(self._tenant)
        admin_consent_url = MSTEAMS_ADMIN_CONSENT_URL.format(tenant_id=self._tenant, client_id=self._client_id,
                                                             redirect_uri=redirect_uri, state=self.get_asset_id())
        admin_consent_url = '{}{}'.format(MSTEAMS_LOGIN_BASE_URL, admin_consent_url)
        self._state['admin_consent_url'] = admin_consent_url

        url_to_show = '{0}/admin_consent?asset_id={1}&'.format(app_rest_url, self.get_asset_id())
        _save_app_state(self._state, self.get_asset_id(), self)

        self.save_progress('Waiting to receive the admin consent')
        self.debug_print('Waiting to receive the admin consent')

        self.save_progress('{0}{1}'.format(MSTEAMS_ADMIN_CONSENT_MSG, url_to_show))
        self.debug_print('{0}{1}'.format(MSTEAMS_ADMIN_CONSENT_MSG, url_to_show))

        time.sleep(MSTEAMS_AUTHORIZE_WAIT_TIME)

        # Wait till authorization is given or timeout occurred
        status = self._wait(action_result=action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        self._state = _load_app_state(self.get_asset_id(), self)

        if not self._state or not self._state.get('admin_consent'):
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_ADMIN_CONSENT_FAILED_MSG)

        return action_result.set_status(phantom.APP_SUCCESS, status_message=MSTEAMS_ADMIN_CONSENT_PASSED_MSG)

    def _handle_list_users(self, param):
        """ This function is used to list all the users.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = MSTEAMS_MSGRAPH_LIST_USERS_ENDPOINT

        while True:

            # make rest call
            ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            for user in response.get('value', []):
                action_result.add_data(user)

            if not response.get(MSTEAMS_NEXT_LINK_STRING):
                break

            endpoint = response[MSTEAMS_NEXT_LINK_STRING]

        summary = action_result.update_summary({})
        summary['total_users'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _verify_parameters(self, group_id, channel_id, action_result):
        """ This function is used to verify that the provided group_id is valid and channel_id belongs
        to that group_id.

        :param group_id: ID of group
        :param channel_id: ID of channel
        :param action_result: Object of ActionResult class
        :return: status (success/failed)
        """

        endpoint = MSTEAMS_MSGRAPH_LIST_CHANNELS_ENDPOINT.format(group_id=group_id)
        channel_list = []

        while True:
            # make rest call
            ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            for channel in response.get('value', []):
                channel_list.append(channel['id'])

            if not response.get(MSTEAMS_NEXT_LINK_STRING):
                break

            endpoint = response[MSTEAMS_NEXT_LINK_STRING]

        if channel_id not in channel_list:
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_INVALID_CHANNEL_MSG.format(
                channel_id=channel_id, group_id=group_id))

        return phantom.APP_SUCCESS

    def _handle_send_message(self, param):
        """ This function is used to send the message in a group.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = _handle_py_ver_compat_for_input_str(self._python_version, param[MSTEAMS_JSON_GROUP_ID], self)
        channel_id = _handle_py_ver_compat_for_input_str(self._python_version, param[MSTEAMS_JSON_CHANNEL_ID], self)
        message = param[MSTEAMS_JSON_MSG]

        status = self._verify_parameters(group_id=group_id, channel_id=channel_id, action_result=action_result)

        if phantom.is_fail(status):
            error_message = action_result.get_message()
            if 'teamId' in error_message:
                error_message = error_message.replace('teamId', "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        endpoint = MSTEAMS_MSGRAPH_SEND_MSG_ENDPOINT.format(group_id=group_id, channel_id=channel_id)

        data = {
            "body": {
                "contentType": "html",
                "content": message
            }
        }

        # make rest call
        ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result, method='post',
                                                 data=json.dumps(data))

        if phantom.is_fail(ret_val):
            error_message = action_result.get_message()
            if 'teamId' in error_message:
                error_message = error_message.replace('teamId', "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message='Message sent')

    def _handle_list_channels(self, param):
        """ This function is used to list all the channels of the particular group.

        :param param: Dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = _handle_py_ver_compat_for_input_str(self._python_version, param[MSTEAMS_JSON_GROUP_ID], self)

        endpoint = MSTEAMS_MSGRAPH_LIST_CHANNELS_ENDPOINT.format(group_id=group_id)

        while True:

            # make rest call
            ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result)

            if phantom.is_fail(ret_val):
                error_message = action_result.get_message()
                if 'teamId' in error_message:
                    error_message = error_message.replace('teamId', "'group_id'")
                return action_result.set_status(phantom.APP_ERROR, error_message)

            for channel in response.get('value', []):
                action_result.add_data(channel)

            if not response.get(MSTEAMS_NEXT_LINK_STRING):
                break

            endpoint = response[MSTEAMS_NEXT_LINK_STRING]

        summary = action_result.update_summary({})
        summary['total_channels'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_groups(self, param):
        """ This function is used to list all the groups for Microsoft Team.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = MSTEAMS_MSGRAPH_GROUPS_ENDPOINT

        while True:

            # make rest call using refresh token
            ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            for group in response.get('value', []):
                action_result.add_data(group)

            if not response.get(MSTEAMS_NEXT_LINK_STRING):
                break

            endpoint = response[MSTEAMS_NEXT_LINK_STRING]

        summary = action_result.update_summary({})
        summary['total_groups'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_teams(self, param):
        """ This function is used to list all the teams for Microsoft Team.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = MSTEAMS_MSGRAPH_TEAMS_ENDPOINT

        while True:

            # make rest call using refresh token
            ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            for team in response.get('value', []):
                action_result.add_data(team)

            if not response.get(MSTEAMS_NEXT_LINK_STRING):
                break

            endpoint = response[MSTEAMS_NEXT_LINK_STRING]

        summary = action_result.update_summary({})
        summary['total_teams'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_meeting(self, param):
        """ This function is used to create meeting for Microsoft Teams.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        use_calendar = param.get(MSTEAMS_JSON_CALENDAR, False)
        subject = param.get(MSTEAMS_JSON_SUBJECT)
        data = {}
        if subject:
            data.update({
                "subject": subject
            })
        if not use_calendar:
            endpoint = MSTEAMS_MSGRAPH_ONLINE_MEETING_ENDPOINT
        else:
            endpoint = MSTEAMS_MSGRAPH_CALENDER_EVENT_ENDPOINT
            description = param.get(MSTEAMS_JSON_DESCRIPTION)
            start_time = param.get(MSTEAMS_JSON_START_TIME)
            end_time = param.get(MSTEAMS_JSON_END_TIME)
            attendees = param.get(MSTEAMS_JSON_ATTENDEES)
            attendees_list = []
            if attendees:
                attendees = [value.strip() for value in attendees.split(",")]
                attendees = list(filter(None, attendees))
                for attendee in attendees:
                    attendee_dict = {"emailAddress": {
                        "address": attendee
                    }}
                    attendees_list.append(attendee_dict)
            data.update({ "isOnlineMeeting": True })
            if description:
                data.update({
                    "body": {
                        "content": description
                    }
                })
            if start_time:
                data.update({
                    "start": {
                        "dateTime": start_time,
                        "timeZone": self._timezone
                    }
                })
            if end_time:
                data.update({
                    "end": {
                        "dateTime": end_time,
                        "timeZone": self._timezone
                    }
                })
            if attendees_list:
                data.update({
                    "attendees": attendees_list
                })
        # make rest call
        ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result, method='post',
                                                 data=json.dumps(data))

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message='Meeting Created Successfully')

    def handle_action(self, param):
        """ This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        self.debug_print("action_id", self.get_action_identifier())

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            'test_connectivity': self._handle_test_connectivity,
            'send_message': self._handle_send_message,
            'list_groups': self._handle_list_groups,
            'list_teams': self._handle_list_teams,
            'list_users': self._handle_list_users,
            'list_channels': self._handle_list_channels,
            'get_admin_consent': self._handle_get_admin_consent,
            'create_meeting': self._handle_create_meeting
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in action_mapping.keys():
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

    def initialize(self):
        """ This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, MSTEAMS_STATE_FILE_CORRUPT_ERROR)

        # Fetching the Python major version
        try:
            self._python_version = int(sys.version_info[0])
        except Exception:
            return self.set_status(phantom.APP_ERROR, "Error occurred while getting the Phantom server's Python major version.")

        # get the asset config
        config = self.get_config()

        self._tenant = _handle_py_ver_compat_for_input_str(self._python_version, config[MSTEAMS_CONFIG_TENANT_ID], self)
        self._client_id = _handle_py_ver_compat_for_input_str(self._python_version, config[MSTEAMS_CONFIG_CLIENT_ID], self)
        self._client_secret = config[MSTEAMS_CONFIG_CLIENT_SECRET]
        self._access_token = self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_ACCESS_TOKEN_STRING)
        self._refresh_token = self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_REFRESH_TOKEN_STRING)
        self._scope = config[MSTEAMS_CONFIG_SCOPE]
        if self._state.get(MSTEAMS_STATE_IS_ENCRYPTED):
            try:
                if self._access_token:
                    self._access_token = self.decrypt_state(self._access_token, "access")
            except Exception as e:
                self.debug_print("{}: {}".format(MSTEAMS_DECRYPTION_ERROR, _get_error_message_from_exception(self._python_version, e, self)))
                return self.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)

            try:
                if self._refresh_token:
                    self._refresh_token = self.decrypt_state(self._refresh_token, "refresh")
            except Exception as e:
                self.debug_print("{}: {}".format(MSTEAMS_DECRYPTION_ERROR, _get_error_message_from_exception(self._python_version, e, self)))
                return self.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)
        self._timezone = config.get(MSTEAMS_CONFIG_TIMEZONE)
        return phantom.APP_SUCCESS

    def finalize(self):
        """ This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices, etc.

        :return: status (success/failure)
        """
        try:
            if self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_ACCESS_TOKEN_STRING):
                self._state[MSTEAMS_TOKEN_STRING][MSTEAMS_ACCESS_TOKEN_STRING] = self.encrypt_state(self._access_token, "access")
        except Exception as e:
            self.debug_print("{}: {}".format(MSTEAMS_ENCRYPTION_ERROR, self._get_error_message_from_exception(e)))
            return self.set_status(phantom.APP_ERROR, MSTEAMS_ENCRYPTION_ERROR)

        try:
            if self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_REFRESH_TOKEN_STRING):
                self._state[MSTEAMS_TOKEN_STRING][MSTEAMS_REFRESH_TOKEN_STRING] = self.encrypt_state(self._refresh_token, "refresh")
        except Exception as e:
            self.debug_print("{}: {}".format(MSTEAMS_ENCRYPTION_ERROR, self._get_error_message_from_exception(e)))
            return self.set_status(phantom.APP_ERROR, MSTEAMS_ENCRYPTION_ERROR)
        self._state[MSTEAMS_STATE_IS_ENCRYPTED] = True
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        _save_app_state(self._state, self.get_asset_id(), self)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            print("Accessing the Login page")
            r = requests.get(BaseConnector._get_phantom_base_url() + "login", verify=verify, timeout=MSTEAMS_DEFAULT_TIMEOUT)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken={}'.format(csrftoken)
            headers['Referer'] = BaseConnector._get_phantom_base_url() + 'login'

            print("Logging into Platform to get the session id")
            r2 = requests.post(BaseConnector._get_phantom_base_url() + "login", verify=verify, data=data,
                headers=headers, timeout=MSTEAMS_DEFAULT_TIMEOUT)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: {}".format(str(e)))
            sys.exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MicrosoftTeamConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
