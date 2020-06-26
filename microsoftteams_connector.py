# File: microsoftteams_connector.py
# Copyright (c) 2019-2020 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.


# Phantom App imports
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

from microsoftteams_consts import *
import requests
from django.http import HttpResponse
import json
import os
import time
import pwd
import grp
from bs4 import BeautifulSoup

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
        return HttpResponse('ERROR: Asset ID not found in URL')
    state = _load_app_state(asset_id)
    url = state.get(key)
    if not url:
        return HttpResponse('App state is invalid, {key} not found.'.format(key=key))
    response = HttpResponse(status=302)
    response['Location'] = url
    return response


def _load_app_state(asset_id, app_connector=None):
    """ This function is used to load the current state file.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: state: Current state file as a dictionary
    """

    dirpath = os.path.split(__file__)[0]
    state_file = '{0}/{1}_state.json'.format(dirpath, asset_id)
    state = {}
    try:
        with open(state_file, 'r') as state_file_obj:
            state_file_data = state_file_obj.read()
            state = json.loads(state_file_data)
    except Exception as e:
        if app_connector:
            app_connector.debug_print('In _load_app_state: Exception: {0}'.format(str(e)))

    if app_connector:
        app_connector.debug_print('Loaded state: ', state)
    return state


def _save_app_state(state, asset_id, app_connector):
    """ This functions is used to save current state in file.

    :param state: Dictionary which contains data to write in state file
    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS
    """

    dirpath = os.path.split(__file__)[0]
    state_file = '{0}/{1}_state.json'.format(dirpath, asset_id)

    if app_connector:
        app_connector.debug_print('Saving state: ', state)

    try:
        with open(state_file, 'w+') as state_file_obj:
            state_file_obj.write(json.dumps(state))
    except Exception as e:
        print('Unable to save state file: {0}'.format(str(e)))

    return phantom.APP_SUCCESS


def _handle_login_response(request):
    """ This function is used to get the login response of authorization request from microsoft login page.

    :param request: Data given to REST endpoint
    :return: HttpResponse. The response displayed on authorization URL page
    """

    asset_id = request.GET.get('state')
    if not asset_id:
        return HttpResponse('ERROR: Asset ID not found in URL\n{}'.format(json.dumps(request.GET)))

    # Check for error in URL
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    # If there is an error in response
    if error:
        message = 'Error: {0}'.format(error)
        if error_description:
            message = '{0} Details: {1}'.format(message, error_description)
        return HttpResponse('Server returned {0}'.format(message))

    code = request.GET.get('code')
    admin_consent = request.GET.get('admin_consent')

    # If none of the code or admin_consent is available
    if not (code or admin_consent):
        return HttpResponse('Error while authenticating\n{0}'.format(json.dumps(request.GET)))

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
            return HttpResponse('Admin Consent received. Please close this window.')
        return HttpResponse('Admin Consent declined. Please close this window and try again later.')

    # If value of admin_consent is not available, value of code is available
    state['code'] = code
    _save_app_state(state, asset_id, None)

    return HttpResponse('Code received. Please close this window, the action will continue to get new token.')


def _handle_rest_request(request, path_parts):
    """ Handle requests for authorization.

    :param request: Data given to REST endpoint
    :param path_parts: parts of the URL passed
    :return: dictionary containing response parameters
    """

    if len(path_parts) < 2:
        return HttpResponse('error: True, message: Invalid REST endpoint request')

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
        if asset_id:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            auth_status_file_path = '{0}/{1}_{2}'.format(app_dir, asset_id, MSTEAMS_TC_FILE)
            open(auth_status_file_path, 'w').close()
            try:
                uid = pwd.getpwnam('apache').pw_uid
                gid = grp.getgrnam('phantom').gr_gid
                os.chown(auth_status_file_path, uid, gid)
                os.chmod(auth_status_file_path, '0664')
            except:
                pass

        return return_val
    return HttpResponse('error: Invalid endpoint')


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

    def _process_empty_reponse(self, response, action_result):
        """ This function is used to process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
                      None)

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
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

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
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".
                                                   format(str(e))), None)

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = "Error from server. Status Code: {0} Data from server: {1}".format(response.status_code,
                                                                                     response.text.replace('{', '{{')
                                                                                     .replace('}', '}}'))

        # Show only error message if available
        if isinstance(resp_json.get('error', {}), dict) and resp_json.get('error', {}).get('message'):
            message = "Error from server. Status Code: {0} Data from server: {1}".format(response.status_code,
                                                                                         resp_json['error']['message'])

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
            return self._process_empty_reponse(response, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            response.status_code, response.text.replace('{', '{{').replace('}', '}}'))

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
        if not endpoint.startswith(MSTEAMS_MSGRAPH_API_BASE_URL):
            endpoint = '{0}{1}'.format(MSTEAMS_MSGRAPH_API_BASE_URL, endpoint)

        if headers is None:
            headers = {}

        token_data = {
            'client_id': self._client_id,
            'scope': MSTEAMS_REST_REQUEST_SCOPE,
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
            r = request_func(endpoint, data=data, headers=headers, verify=verify, params=params)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Error Connecting to server. Details: {0}"
                                                   .format(str(e))), resp_json)

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

        self._state[MSTEAMS_TOKEN_STRING] = resp_json
        self._access_token = resp_json[MSTEAMS_ACCESS_TOKEN_STRING]
        self._refresh_token = resp_json[MSTEAMS_REFRESH_TOKEN_STRING]
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        """ Testing of given credentials and obtaining authorization/admin consent for all other actions.

        :param param: (not used in this method)
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(MSTEAMS_MAKING_CONNECTION_MSG)

        # Get initial REST URL
        ret_val, app_rest_url = self._get_app_rest_url(action_result)
        if phantom.is_fail(ret_val):
            self.save_progress(MSTEAMS_REST_URL_NOT_AVAILABLE_MSG.format(error=action_result.get_message()))
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)

        # Append /result to create redirect_uri
        redirect_uri = '{0}/result'.format(app_rest_url)
        self._state['redirect_uri'] = redirect_uri

        self.save_progress(MSTEAMS_OAUTH_URL_MSG)
        self.save_progress(redirect_uri)

        # Authorization URL used to make request for getting code which is used to generate access token
        authorization_url = MSTEAMS_AUTHORIZE_URL.format(tenant_id=self._tenant, client_id=self._client_id,
                                                         redirect_uri=redirect_uri, state=self.get_asset_id(),
                                                         response_type='code',
                                                         scope=MSTEAMS_REST_REQUEST_SCOPE)
        authorization_url = '{}{}'.format(MSTEAMS_LOGIN_BASE_URL, authorization_url)

        self._state['authorization_url'] = authorization_url

        # URL which would be shown to the user
        url_for_authorize_request = '{0}/start_oauth?asset_id={1}&'.format(app_rest_url, self.get_asset_id())
        _save_app_state(self._state, self.get_asset_id(), self)

        self.save_progress(MSTEAMS_AUTHORIZE_USER_MSG)
        self.save_progress(url_for_authorize_request)

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

        current_code = self._state['code']
        self.save_state(self._state)

        self.save_progress(MSTEAMS_GENERATING_ACCESS_TOKEN_MSG)

        data = {
            'client_id': self._client_id,
            'scope': MSTEAMS_REST_REQUEST_SCOPE,
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
            self._state = _load_app_state(self.get_asset_id(), self)
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
        admin_consent_url = MSTEAMS_ADMIN_CONSENT_URL.format(tenant_id=self._tenant, client_id=self._client_id,
                                                             redirect_uri=redirect_uri, state=self.get_asset_id())
        admin_consent_url = '{}{}'.format(MSTEAMS_LOGIN_BASE_URL, admin_consent_url)
        self._state['admin_consent_url'] = admin_consent_url

        url_to_show = '{0}/admin_consent?asset_id={1}&'.format(app_rest_url, self.get_asset_id())
        _save_app_state(self._state, self.get_asset_id(), self)
        self.save_progress('Waiting to receive the admin consent')
        self.save_progress('{0}{1}'.format(MSTEAMS_ADMIN_CONSENT_MSG, url_to_show))

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

        group_id = param[MSTEAMS_JSON_GROUP_ID]
        channel_id = param[MSTEAMS_JSON_CHANNEL_ID]
        message = param[MSTEAMS_JSON_MESSAGE]

        status = self._verify_parameters(group_id=group_id, channel_id=channel_id, action_result=action_result)

        if phantom.is_fail(status):
            return action_result.get_status()

        endpoint = MSTEAMS_MSGRAPH_SEND_MESSAGE_ENDPOINT.format(group_id=group_id, channel_id=channel_id)

        data = {
            "rootMessage": {
                "body": {
                    "contentType": 1,
                    "content": message
                }
            }
        }

        # make rest call
        ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result, method='post',
                                                 data=json.dumps(data))

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message='Message sent')

    def _handle_list_channels(self, param):
        """ This function is used to list all channels of particular group.

        :param param: Dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = param[MSTEAMS_JSON_GROUP_ID]

        endpoint = MSTEAMS_MSGRAPH_LIST_CHANNELS_ENDPOINT.format(group_id=group_id)

        while True:

            # make rest call
            ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            for channel in response.get('value', []):
                action_result.add_data(channel)

            if not response.get(MSTEAMS_NEXT_LINK_STRING):
                break

            endpoint = response[MSTEAMS_NEXT_LINK_STRING]

        summary = action_result.update_summary({})
        summary['total_channels'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_groups(self, param):
        """ This function is used to list all the groups fo Microsoft Team.

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
            'list_users': self._handle_list_users,
            'list_channels': self._handle_list_channels,
            'get_admin_consent': self._handle_get_admin_consent
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

        # get the asset config
        config = self.get_config()

        self._tenant = config[MSTEAMS_CONFIG_TENANT_ID]
        self._client_id = config[MSTEAMS_CONFIG_CLIENT_ID]
        self._client_secret = config[MSTEAMS_CONFIG_CLIENT_SECRET]
        self._access_token = self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_ACCESS_TOKEN_STRING)
        self._refresh_token = self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_REFRESH_TOKEN_STRING)

        return phantom.APP_SUCCESS

    def finalize(self):
        """ This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.

        :return: status (success/failure)
        """

        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import sys
    import pudb
    import argparse

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            print ("Accessing the Login page")
            r = requests.get(BaseConnector._get_phantom_base_url() + "login", verify=False)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken={}'.format(csrftoken)
            headers['Referer'] = BaseConnector._get_phantom_base_url() + 'login'

            print ("Logging into Platform to get the session id")
            r2 = requests.post(BaseConnector._get_phantom_base_url() + "login", verify=False, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print ("Unable to get session id from the platfrom. Error: {}".format(str(e)))
            exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MicrosoftTeamConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print (json.dumps(json.loads(ret_val), indent=4))

    exit(0)
