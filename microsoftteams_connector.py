# File: microsoftteams_connector.py
#
# Copyright (c) 2019-2026 Splunk Inc.
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
import asyncio
import grp
import hashlib
import hmac
import json
import os
import pwd
import re
import secrets
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import encryption_helper
import phantom.app as phantom
import requests
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ConversationParameters, ConversationReference
from botbuilder.schema.teams import ChannelInfo, TeamInfo, TeamsChannelAccount, TeamsChannelData, TenantInfo
from bs4 import BeautifulSoup
from django.http import HttpResponse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.utils import get_list_from_string

from microsoftteams_consts import *
from microsoftteams_reactions import (
    create_reaction_approval_card,
    describe_reaction_decision,
    finalize_reaction_card,
    normalize_reaction,
    parse_reactions,
    reaction_decision_blocks,
    reaction_expired_blocks,
)
from microsoftteams_webhook import create_question_card


try:
    import urllib.parse as urllib
except ImportError:
    import urllib


def _encode_graph_path_segment(value):
    raw_value = str(value)
    canonical_value = raw_value
    for _ in range(5):
        decoded_value = urllib.unquote(canonical_value)
        if decoded_value == canonical_value:
            break
        canonical_value = decoded_value
    if canonical_value in {".", ".."}:
        raise ValueError("Microsoft Graph path identifiers must not be dot segments")
    return urllib.quote(raw_value, safe="")


def _handle_login_redirect(request, key):
    """This function is used to redirect login request to microsoft login page.

    :param request: Data given to REST endpoint
    :param key: Key to search in state file
    :return: response authorization_url/admin_consent_url
    """

    asset_id = request.GET.get("asset_id")
    if not asset_id:
        return HttpResponse("ERROR: Asset ID not found in URL", content_type="text/plain", status=400)
    state = _load_app_state(asset_id)
    if not state:
        return HttpResponse("ERROR: Invalid asset_id", content_type="text/plain", status=400)
    nonce_key = "admin_consent_state_nonce" if key == "admin_consent_url" else "oauth_state_nonce"
    presented_nonce = request.GET.get("state_nonce", "")
    stored_nonce = state.get(nonce_key, "")
    if not stored_nonce or not hmac.compare_digest(stored_nonce, presented_nonce):
        return HttpResponse("ERROR: Invalid OAuth state", content_type="text/plain", status=400)
    url = state.get(key)
    if not url:
        return HttpResponse(f"App state is invalid, {key} not found.", content_type="text/plain", status=400)
    response = HttpResponse(status=302)
    response["Location"] = url
    return response


def _get_error_message_from_exception(e, app_connector):
    """
    Get appropriate error message from the exception.
    :param e: Exception object
    :return: error message
    """

    error_code = None
    error_message = ERROR_MSG_UNAVAILABLE

    app_connector.error_print("Error occurred.", e)

    try:
        if hasattr(e, "args"):
            if len(e.args) > 1:
                error_code = e.args[0]
                error_message = e.args[1]
            elif len(e.args) == 1:
                error_message = e.args[0]
    except Exception as e:
        app_connector.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

    if not error_code:
        error_text = f"Error Message: {error_message}"
    else:
        error_text = f"Error Code: {error_code}. Error Message: {error_message}"

    return error_text


def _load_app_state(asset_id, app_connector=None):
    """This function is used to load the current state file.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: state: Current state file as a dictionary
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print("In _load_app_state: Invalid asset_id")
        return {}

    app_dir = os.path.dirname(os.path.abspath(__file__))
    state_file = f"{app_dir}/{asset_id}_state.json"
    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print("In _load_app_state: Invalid asset_id")
        return {}

    state = {}
    try:
        with open(real_state_file_path) as state_file_obj:
            state_file_data = state_file_obj.read()
            state = json.loads(state_file_data)
    except Exception as e:
        if app_connector:
            error_text = _get_error_message_from_exception(e, app_connector)
            app_connector.debug_print(f"In _load_app_state: {error_text}")

    if app_connector:
        app_connector.debug_print("Loaded state: ", state)

    return state


def _save_app_state(state, asset_id, app_connector=None):
    """This function is used to save current state in file.

    :param state: Dictionary which contains data to write in state file
    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS|phantom.APP_ERROR
    """

    asset_id = str(asset_id)
    if not asset_id or not asset_id.isalnum():
        if app_connector:
            app_connector.debug_print("In _save_app_state: Invalid asset_id")
        return {}

    app_dir = os.path.split(__file__)[0]
    state_file = f"{app_dir}/{asset_id}_state.json"

    real_state_file_path = os.path.abspath(state_file)
    if not os.path.dirname(real_state_file_path) == app_dir:
        if app_connector:
            app_connector.debug_print("In _save_app_state: Invalid asset_id")
        return {}

    if app_connector:
        app_connector.debug_print("Saving state: ", state)

    try:
        with open(real_state_file_path, "w+") as state_file_obj:
            state_file_obj.write(json.dumps(state))
    except Exception as e:
        error_text = _get_error_message_from_exception(e, app_connector)
        if app_connector:
            app_connector.debug_print(f"Unable to save state file: {error_text}")
        print(f"Unable to save state file: {error_text}")
        return phantom.APP_ERROR

    return phantom.APP_SUCCESS


def _handle_login_response(request):
    """This function is used to get the login response of authorization request from microsoft login page.

    :param request: Data given to REST endpoint
    :return: HttpResponse. The response displayed on authorization URL page
    """

    oauth_state = request.GET.get("state")
    if not oauth_state or ":" not in oauth_state:
        return HttpResponse(f"ERROR: Asset ID not found in URL\n{json.dumps(request.GET)}", content_type="text/plain", status=400)

    asset_id, presented_nonce = oauth_state.split(":", 1)
    if not asset_id.isalnum():
        return HttpResponse("ERROR: Invalid OAuth state", content_type="text/plain", status=400)

    state = _load_app_state(asset_id)
    nonce_key = "admin_consent_state_nonce" if request.GET.get("admin_consent") is not None else "oauth_state_nonce"
    stored_nonce = state.get(nonce_key, "")
    if not stored_nonce or not hmac.compare_digest(stored_nonce, presented_nonce):
        return HttpResponse("ERROR: Invalid OAuth state", content_type="text/plain", status=400)
    state.pop(nonce_key, None)

    # Check for error in URL
    error = request.GET.get("error")
    error_description = request.GET.get("error_description")

    # If there is an error in response
    if error:
        _save_app_state(state, asset_id, None)
        message = f"Error: {error}"
        if error_description:
            message = f"{message} Details: {error_description}"
        return HttpResponse(f"Server returned {message}", content_type="text/plain", status=400)

    code = request.GET.get("code")
    admin_consent = request.GET.get("admin_consent")

    # If none of the code or admin_consent is available
    if not (code or admin_consent):
        _save_app_state(state, asset_id, None)
        return HttpResponse(f"Error while authenticating\n{json.dumps(request.GET)}", content_type="text/plain", status=400)

    # If value of admin_consent is available
    if admin_consent:
        if admin_consent == "True":
            admin_consent = True
        else:
            admin_consent = False

        state["admin_consent"] = admin_consent
        _save_app_state(state, asset_id, None)

        # If admin_consent is True
        if admin_consent:
            return HttpResponse("Admin Consent received. Please close this window.", content_type="text/plain")
        return HttpResponse("Admin Consent declined. Please close this window and try again later.", content_type="text/plain", status=400)

    # If value of admin_consent is not available, value of code is available
    state["code"] = code
    try:
        state["code"] = MicrosoftTeamConnector().encrypt_state(code, "code")
        state[MSTEAMS_STATE_IS_ENCRYPTED] = True
    except Exception as e:
        return HttpResponse(f"{MSTEAMS_ENCRYPTION_ERROR}: {e!s}", content_type="text/plain", status=400)
    _save_app_state(state, asset_id, None)

    return HttpResponse("Code received. Please close this window, the action will continue to get new token.", content_type="text/plain")


def _handle_rest_request(request, path_parts):
    """Handle requests for authorization.

    :param request: Data given to REST endpoint
    :param path_parts: parts of the URL passed
    :return: dictionary containing response parameters
    """

    if len(path_parts) < 2:
        return HttpResponse("error: True, message: Invalid REST endpoint request", content_type="text/plain", status=404)

    call_type = path_parts[1]

    # To handle admin_consent request in get_admin_consent action
    if call_type == "admin_consent":
        return _handle_login_redirect(request, "admin_consent_url")

    # To handle authorize request in test connectivity action
    if call_type == "start_oauth":
        return _handle_login_redirect(request, "authorization_url")

    # To handle response from microsoft login page
    if call_type == "result":
        return_val = _handle_login_response(request)
        oauth_state = request.GET.get("state", "")
        asset_id = oauth_state.split(":", 1)[0]
        if return_val.status_code < 400 and asset_id and asset_id.isalnum():
            app_dir = os.path.dirname(os.path.abspath(__file__))
            auth_status_file_path = f"{app_dir}/{asset_id}_{MSTEAMS_TC_FILE}"
            real_auth_status_file_path = os.path.abspath(auth_status_file_path)
            if not os.path.dirname(real_auth_status_file_path) == app_dir:
                return HttpResponse("Error: Invalid asset_id", content_type="text/plain", status=400)
            open(auth_status_file_path, "w").close()
            try:
                uid = pwd.getpwnam("apache").pw_uid
                gid = grp.getgrnam("phantom").gr_gid
                os.chown(auth_status_file_path, uid, gid)
                os.chmod(auth_status_file_path, "0664")
            except Exception:
                pass

        return return_val
    return HttpResponse("error: Invalid endpoint", content_type="text/plain", status=404)


def _get_dir_name_from_app_name(app_name):
    """Get name of the directory for the app.

    :param app_name: Name of the application for which directory name is required
    :return: app_name: Name of the directory for the application
    """

    app_name = "".join([x for x in app_name if x.isalnum()])
    app_name = app_name.lower()
    if not app_name:
        app_name = "app_for_phantom"
    return app_name


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class MicrosoftTeamConnector(BaseConnector):
    def __init__(self):
        super().__init__()

        self._state = None
        self._tenant = None
        self._client_id = None
        self._client_secret = None
        self._access_token = None
        self._refresh_token = None
        self.asset_id = self.get_asset_id()
        self._scope = None

    def encrypt_state(self, encrypt_var, token_name):
        """Handle encryption of token.
        :param encrypt_var: Variable needs to be encrypted
        :return: encrypted variable
        """
        self.debug_print(MSTEAMS_ENCRYPT_TOKEN.format(token_name))  # nosemgrep
        return encryption_helper.encrypt(encrypt_var, self.asset_id)

    def decrypt_state(self, decrypt_var, token_name):
        """Handle decryption of token.
        :param decrypt_var: Variable needs to be decrypted
        :return: decrypted variable
        """
        self.debug_print(MSTEAMS_DECRYPT_TOKEN.format(token_name))  # nosemgrep
        return encryption_helper.decrypt(decrypt_var, self.asset_id)

    def _process_empty_response(self, response, action_result):
        """This function is used to process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # If response is OK or No-Content
        if response.status_code in [200, 204]:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status code: {response.status_code}. Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result) -> RetVal[bool, Optional[Any]]:
        """This function is used to process html response.

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
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result) -> RetVal[bool, Optional[Any]]:
        """This function is used to process json response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            error_text = _get_error_message_from_exception(e, self)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. {error_text}"), None)

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        error_message = response.text.replace("{", "{{").replace("}", "}}")
        message = f"Error from server. Status Code: {response.status_code} Data from server: {error_message}"

        # Show only error message if available
        if isinstance(resp_json.get("error", {}), dict) and resp_json.get("error", {}).get("message"):
            error_message = resp_json["error"]["message"]
            message = f"Error from server. Status Code: {response.status_code} Data from server: {error_message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result) -> RetVal[bool, Optional[Any]]:
        """This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Response bodies and headers can contain credentials and must not enter debug logs.
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        if "text/javascript" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the API talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        error_message = response.text.replace("{", "{{").replace("}", "}}")
        message = f"Can't process response from server. Status Code: {response.status_code} Data from server: {error_message}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _update_request(self, action_result, endpoint, headers=None, params=None, data=None, method="get") -> tuple[bool, Optional[Any]]:
        """This function is used to update the headers with access_token before making REST call.

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
            endpoint = f"{MSTEAMS_MSGRAPH_BETA_API_BASE_URL}{endpoint}"
        elif not endpoint.startswith(MSTEAMS_MSGRAPH_API_BASE_URL):
            endpoint = f"{MSTEAMS_MSGRAPH_API_BASE_URL}{endpoint}"

        if headers is None:
            headers = {}

        self._client_id = urllib.quote(self._client_id)
        self._tenant = urllib.quote(self._tenant)
        token_data = {
            "client_id": self._client_id,
            "scope": self._scope,
            "client_secret": self._client_secret,
            "grant_type": MSTEAMS_REFRESH_TOKEN_STRING,
            "refresh_token": self._refresh_token,
        }

        if not self._access_token:
            if not self._refresh_token:
                # If none of the access_token and refresh_token is available
                return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_TOKEN_NOT_AVAILABLE_MSG), None

            # If refresh_token is available and access_token is not available, generate new access_token
            status = self._generate_new_access_token(action_result=action_result, data=token_data)

            if phantom.is_fail(status):
                return action_result.get_status(), None

        headers.update({"Authorization": f"Bearer {self._access_token}", "Accept": "application/json", "Content-Type": "application/json"})

        status, resp_json = self._make_rest_call(
            action_result=action_result, endpoint=endpoint, headers=headers, params=params, data=data, method=method
        )

        action_result_message = action_result.get_message().lower()

        if phantom.is_fail(status):
            # If token is expired, generate new token
            if self._is_token_expired(action_result_message):
                self.debug_print(MSTEAMS_TOKEN_EXPIRED_MSG)
                status = self._generate_new_access_token(action_result=action_result, data=token_data)

                if phantom.is_fail(status):
                    return action_result.get_status(), None

                headers["Authorization"] = f"Bearer {self._access_token}"

                status, resp_json = self._make_rest_call(
                    action_result=action_result, endpoint=endpoint, headers=headers, params=params, data=data, method=method
                )

                if phantom.is_fail(status):
                    return action_result.get_status(), None
            else:
                return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _is_token_expired(self, action_result_message: str) -> bool:
        return MSTEAMS_TOKEN_EXPIRED_MARKER in action_result_message

    def _get_oauth_config_hash(self):
        config = self.get_config()
        oauth_config = {
            MSTEAMS_CONFIG_TENANT_ID: config.get(MSTEAMS_CONFIG_TENANT_ID),
            MSTEAMS_CONFIG_CLIENT_ID: config.get(MSTEAMS_CONFIG_CLIENT_ID),
            MSTEAMS_CONFIG_CLIENT_SECRET: config.get(MSTEAMS_CONFIG_CLIENT_SECRET),
            MSTEAMS_CONFIG_SCOPE: config.get(MSTEAMS_CONFIG_SCOPE),
        }
        return hashlib.sha256(json.dumps(oauth_config, sort_keys=True).encode("utf-8")).hexdigest()

    def _is_oauth_config_changed(self):
        stored_oauth_config_hash = self._state.get(MSTEAMS_OAUTH_CONFIG_HASH)
        return bool(stored_oauth_config_hash and stored_oauth_config_hash != self._get_oauth_config_hash())

    def _save_oauth_config_hash(self):
        self._state[MSTEAMS_OAUTH_CONFIG_HASH] = self._get_oauth_config_hash()
        self.save_state(self._state)
        _save_app_state(self._state, self.get_asset_id(), self)

    def _make_rest_call(
        self, endpoint, action_result, headers=None, params=None, data=None, method="get", verify=True
    ) -> RetVal[bool, Optional[Any]]:
        """Function that makes the REST call to the app.

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
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)
        try:
            r = request_func(endpoint, data=data, headers=headers, verify=verify, params=params, timeout=MSTEAMS_DEFAULT_TIMEOUT)
        except Exception as e:
            error_text = _get_error_message_from_exception(e, self)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error connecting to server. {error_text}"), resp_json)

        return self._process_response(r, action_result)

    def _get_asset_name(self, action_result):
        """Get name of the asset using Phantom URL.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message), asset name
        """

        asset_id = self.get_asset_id()
        rest_endpoint = MSTEAMS_PHANTOM_ASSET_INFO_URL.format(asset_id=asset_id)
        url = "{}{}".format(self.get_phantom_base_url() + "rest", rest_endpoint)
        status, resp_json = self._make_rest_call(action_result=action_result, endpoint=url, verify=False)

        if phantom.is_fail(status):
            return status, None

        asset_name = resp_json.get("name")
        if not asset_name:
            return action_result.set_status(phantom.APP_ERROR, f"Asset Name for id: {asset_id} not found.", None)
        return phantom.APP_SUCCESS, asset_name

    def _get_phantom_base_url_ms(self, action_result):
        """Get base url of phantom.

        :param action_result: object of ActionResult class
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        base url of phantom
        """
        url = "{}{}".format(self.get_phantom_base_url() + "rest", MSTEAMS_PHANTOM_SYS_INFO_URL)
        status, resp_json = self._make_rest_call(action_result=action_result, endpoint=url, verify=False)
        if phantom.is_fail(status):
            return status, None

        phantom_base_url = resp_json.get("base_url")
        if not phantom_base_url:
            return action_result.set_status(phantom.APP_ERROR, MSTEAMS_BASE_URL_NOT_FOUND_MSG), None

        phantom_base_url = phantom_base_url.strip("/")

        return phantom.APP_SUCCESS, phantom_base_url

    def _get_app_rest_url(self, action_result):
        """Get URL for making rest calls.

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

        self.save_progress(f"Using Phantom base URL as: {phantom_base_url}")
        app_json = self.get_app_json()
        app_name = app_json["name"]

        app_dir_name = _get_dir_name_from_app_name(app_name)
        url_to_app_rest = "{}/rest/handler/{}_{}/{}".format(phantom_base_url, app_dir_name, app_json["appid"], asset_name)
        return phantom.APP_SUCCESS, url_to_app_rest

    def _generate_new_access_token(self, action_result, data) -> bool:
        """This function is used to generate new access token using the code obtained on authorization.

        :param action_result: object of ActionResult class
        :param data: Data to send in REST call
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS
        """

        req_url = f"{MSTEAMS_LOGIN_BASE_URL}{MSTEAMS_SERVER_TOKEN_URL.format(tenant_id=self._tenant)}"

        status, resp_json = self._make_rest_call(action_result=action_result, endpoint=req_url, data=urllib.urlencode(data), method="post")
        if phantom.is_fail(status):
            return action_result.get_status()

        self._access_token = resp_json[MSTEAMS_ACCESS_TOKEN_STRING]
        self._refresh_token = resp_json[MSTEAMS_REFRESH_TOKEN_STRING]

        try:
            encrypted_access_token = self.encrypt_state(resp_json[MSTEAMS_ACCESS_TOKEN_STRING], "access")
        except Exception as e:
            self.debug_print(f"{MSTEAMS_ENCRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
            return action_result.set_status(phantom.APP_ERROR, MSTEAMS_ENCRYPTION_ERROR)

        try:
            encrypted_refresh_token = self.encrypt_state(resp_json[MSTEAMS_REFRESH_TOKEN_STRING], "refresh")
        except Exception as e:
            self.debug_print(f"{MSTEAMS_ENCRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
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
            if self._access_token != self.decrypt_state(
                self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_ACCESS_TOKEN_STRING), "access"
            ) or self._refresh_token != self.decrypt_state(
                self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_REFRESH_TOKEN_STRING), "refresh"
            ):
                message = "Error occurred while saving the newly generated access or "
                message += "refresh token (in place of the expired token) in the state file."
                message += " Please check the owner, owner group, and the permissions of the state file. The Phantom "
                message += "user should have the correct access rights and "
                message += "ownership for the corresponding state file (refer to readme file for more information)."
                return action_result.set_status(phantom.APP_ERROR, message)
        except Exception as e:
            self.debug_print(f"{MSTEAMS_DECRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
            return action_result.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)

        return action_result.set_status(phantom.APP_SUCCESS, status_message=MSTEAMS_TOKEN_GENERATED_MSG)

    def _handle_test_connectivity(self, param):
        """Testing of given credentials and obtaining authorization/admin consent for all other actions.

        :param param: (not used in this method)
        :return: status success/failure
        """
        app_state = {}
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(MSTEAMS_MAKING_CONNECTION_MSG)

        if self._access_token or self._refresh_token:
            if self._is_oauth_config_changed():
                self.save_progress("Asset OAuth configuration changed from last test connectivity run. Starting user authorization flow.")
            else:
                self.save_progress(MSTEAMS_CURRENT_USER_INFO_MSG)
                status, _ = self._update_request(action_result=action_result, endpoint=MSTEAMS_MSGRAPH_SELF_ENDPOINT)
                if not phantom.is_fail(status):
                    self._save_oauth_config_hash()
                    self.save_progress(MSTEAMS_GOT_CURRENT_USER_INFO_MSG)
                    self.save_progress(MSTEAMS_TEST_CONNECTIVITY_PASSED_MSG)
                    return action_result.set_status(phantom.APP_SUCCESS)

                self.save_progress("Stored credentials could not be validated. Starting user authorization flow.")

        # Get initial REST URL
        ret_val, app_rest_url = self._get_app_rest_url(action_result)
        if phantom.is_fail(ret_val):
            self.save_progress(MSTEAMS_REST_URL_NOT_AVAILABLE_MSG.format(error=action_result.get_message()))
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)

        # Append /result to create redirect_uri
        redirect_uri = f"{app_rest_url}/result"
        app_state["redirect_uri"] = redirect_uri

        self.save_progress(MSTEAMS_OAUTH_URL_MSG)
        self.save_progress(redirect_uri)

        # Authorization URL used to make request for getting code which is used to generate access token
        self._client_id = urllib.quote(self._client_id)
        self._tenant = urllib.quote(self._tenant)
        flow_nonce = secrets.token_hex(16)
        app_state["oauth_state_nonce"] = flow_nonce
        oauth_state = f"{self.get_asset_id()}:{flow_nonce}"
        authorization_url = MSTEAMS_AUTHORIZE_URL.format(
            tenant_id=self._tenant,
            client_id=self._client_id,
            redirect_uri=redirect_uri,
            state=urllib.quote(oauth_state),
            response_type="code",
            scope=self._scope,
        )
        authorization_url = f"{MSTEAMS_LOGIN_BASE_URL}{authorization_url}"

        app_state["authorization_url"] = authorization_url

        # URL which would be shown to the user
        start_query = urllib.urlencode({"asset_id": self.get_asset_id(), "state_nonce": flow_nonce})
        url_for_authorize_request = f"{app_rest_url}/start_oauth?{start_query}"
        _save_app_state(app_state, self.get_asset_id(), self)

        self.save_progress(MSTEAMS_AUTHORIZE_USER_MSG)
        self.save_progress(url_for_authorize_request)  # nosemgrep
        self.save_progress(MSTEAMS_AUTHORIZE_TROUBLESHOOT_MSG)
        self.save_progress(MSTEAMS_AUTHORIZE_WAIT_MSG)

        time.sleep(MSTEAMS_AUTHORIZE_WAIT_TIME)

        # Wait for some while user login to Microsoft
        status = self._wait(action_result=action_result)

        if phantom.is_fail(status):
            self.save_progress(MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.get_status()

        # Empty message to override last message of waiting
        self.send_progress("")
        self.save_progress(MSTEAMS_CODE_RECEIVED_MSG)
        self._state = _load_app_state(self.get_asset_id(), self)

        # if code is not available in the state file
        if not self._state or not self._state.get("code"):
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)

        if self._state.get(MSTEAMS_STATE_IS_ENCRYPTED):
            try:
                current_code = self.decrypt_state(self._state["code"], "code")
            except Exception as e:
                self.debug_print(f"{MSTEAMS_DECRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
                return action_result.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)
        else:
            current_code = self._state["code"]
        self.save_state(self._state)
        _save_app_state(self._state, self.get_asset_id(), self)
        self.save_progress(MSTEAMS_GENERATING_ACCESS_TOKEN_MSG)

        data = {
            "client_id": self._client_id,
            "scope": self._scope,
            "client_secret": self._client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": current_code,
        }
        # for first time access, new access token is generated
        ret_val = self._generate_new_access_token(action_result=action_result, data=data)

        if phantom.is_fail(ret_val):
            self.save_progress(MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.get_status()

        self.save_progress(MSTEAMS_CURRENT_USER_INFO_MSG)

        url = f"{MSTEAMS_MSGRAPH_API_BASE_URL}{MSTEAMS_MSGRAPH_SELF_ENDPOINT}"
        status, response = self._update_request(action_result=action_result, endpoint=url)

        if phantom.is_fail(status):
            self.save_progress(MSTEAMS_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.get_status()

        self._save_oauth_config_hash()
        self.save_progress(MSTEAMS_GOT_CURRENT_USER_INFO_MSG)
        self.save_progress(MSTEAMS_TEST_CONNECTIVITY_PASSED_MSG)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _wait(self, action_result):
        """This function is used to hold the action till user login.

        :param action_result: Object of ActionResult class
        :return: status (success/failed)
        """

        app_dir = os.path.dirname(os.path.abspath(__file__))
        # file to check whether the request has been granted or not
        auth_status_file_path = f"{app_dir}/{self.get_asset_id()}_{MSTEAMS_TC_FILE}"
        time_out = False

        # wait-time while request is being granted
        for i in range(0, 35):
            if os.path.isfile(auth_status_file_path):
                time_out = True
                os.unlink(auth_status_file_path)
                break
            time.sleep(MSTEAMS_TC_STATUS_SLEEP)

        if not time_out:
            return action_result.set_status(phantom.APP_ERROR, status_message="Timeout. Please try again later.")
        self.send_progress("Authenticated")
        return phantom.APP_SUCCESS

    def _handle_get_admin_consent(self, param):
        """This function is used to get the consent from admin.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, app_rest_url = self._get_app_rest_url(action_result)
        if phantom.is_fail(ret_val):
            return action_result.set_status(
                phantom.APP_ERROR,
                status_message=f"Unable to get the URL to the app's REST Endpoint. Error: {action_result.get_message()}",
            )
        redirect_uri = f"{app_rest_url}/result"

        # Store admin_consent_url to state file so that we can access it from _handle_rest_request
        self._client_id = urllib.quote(self._client_id)
        self._tenant = urllib.quote(self._tenant)
        flow_nonce = secrets.token_hex(16)
        self._state["admin_consent_state_nonce"] = flow_nonce
        oauth_state = f"{self.get_asset_id()}:{flow_nonce}"
        admin_consent_url = MSTEAMS_ADMIN_CONSENT_URL.format(
            tenant_id=self._tenant,
            client_id=self._client_id,
            redirect_uri=redirect_uri,
            state=urllib.quote(oauth_state),
        )
        admin_consent_url = f"{MSTEAMS_LOGIN_BASE_URL}{admin_consent_url}"
        self._state["admin_consent_url"] = admin_consent_url

        consent_query = urllib.urlencode({"asset_id": self.get_asset_id(), "state_nonce": flow_nonce})
        url_to_show = f"{app_rest_url}/admin_consent?{consent_query}"
        _save_app_state(self._state, self.get_asset_id(), self)

        self.save_progress("Waiting to receive the admin consent")
        self.debug_print("Waiting to receive the admin consent")

        self.save_progress(f"{MSTEAMS_ADMIN_CONSENT_MSG}{url_to_show}")
        self.debug_print(f"{MSTEAMS_ADMIN_CONSENT_MSG}{url_to_show}")

        time.sleep(MSTEAMS_AUTHORIZE_WAIT_TIME)

        # Wait till authorization is given or timeout occurred
        status = self._wait(action_result=action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        self._state = _load_app_state(self.get_asset_id(), self)

        if not self._state or not self._state.get("admin_consent"):
            return action_result.set_status(phantom.APP_ERROR, status_message=MSTEAMS_ADMIN_CONSENT_FAILED_MSG)

        return action_result.set_status(phantom.APP_SUCCESS, status_message=MSTEAMS_ADMIN_CONSENT_PASSED_MSG)

    def _handle_list_users(self, param):
        """This function is used to list all the users.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = MSTEAMS_MSGRAPH_LIST_USERS_ENDPOINT

        status, users = self._get_paginated_values(endpoint, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        for user in users:
            action_result.add_data(user)

        summary = action_result.update_summary({})
        summary["total_users"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_paginated_values(self, endpoint, action_result):
        values = []
        seen_endpoints = set()

        for _ in range(MSTEAMS_MAX_PAGINATION_PAGES):
            if endpoint in seen_endpoints:
                return action_result.set_status(phantom.APP_ERROR, "Microsoft Graph returned a non-progressing nextLink"), None
            seen_endpoints.add(endpoint)

            status, response = self._update_request(endpoint=endpoint, action_result=action_result)
            if phantom.is_fail(status):
                return status, None

            values.extend(response.get("value", []))
            endpoint = response.get(MSTEAMS_NEXT_LINK_STRING)
            if not endpoint:
                return phantom.APP_SUCCESS, values

        return action_result.set_status(phantom.APP_ERROR, "Microsoft Graph pagination exceeded the 1000-page limit"), None

    def _verify_parameters(self, group_id, channel_id, action_result) -> bool:
        """This function is used to verify that the provided group_id is valid and channel_id belongs
        to that group_id.

        :param group_id: ID of group
        :param channel_id: ID of channel
        :param action_result: Object of ActionResult class
        :return: status (success/failed)
        """

        endpoint = MSTEAMS_MSGRAPH_LIST_CHANNELS_ENDPOINT.format(group_id=_encode_graph_path_segment(group_id))
        status, channels = self._get_paginated_values(endpoint, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()
        channel_list = [channel["id"] for channel in channels]

        if channel_id not in channel_list:
            return action_result.set_status(
                phantom.APP_ERROR, status_message=MSTEAMS_INVALID_CHANNEL_MSG.format(channel_id=channel_id, group_id=group_id)
            )

        return phantom.APP_SUCCESS

    def _handle_send_channel_message(self, param: dict) -> str:
        """This function is used to Sends a message to a specified channel in a Microsoft Teams group.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = param[MSTEAMS_JSON_GROUP_ID]
        channel_id = param[MSTEAMS_JSON_CHANNEL_ID]
        message = param[MSTEAMS_JSON_MSG]

        status = self._verify_parameters(group_id=group_id, channel_id=channel_id, action_result=action_result)

        if phantom.is_fail(status):
            error_message = action_result.get_message()
            if "teamId" in error_message:
                error_message = error_message.replace("teamId", "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        endpoint = MSTEAMS_MSGRAPH_SEND_CHANNEL_MSG_ENDPOINT.format(
            group_id=_encode_graph_path_segment(group_id),
            channel_id=_encode_graph_path_segment(channel_id),
        )

        data = {"body": {"contentType": "html", "content": message}}

        # make rest call
        status, response = self._update_request(endpoint=endpoint, action_result=action_result, method="post", data=json.dumps(data))

        if phantom.is_fail(status):
            error_message = action_result.get_message()
            if "teamId" in error_message:
                error_message = error_message.replace("teamId", "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message="Message sent")

    def _handle_ask_question(self, param: dict) -> str:
        """This function is used to Sends a message to a specified channel in a Microsoft Teams group.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = param.get(MSTEAMS_JSON_GROUP_ID)
        channel_id = param.get(MSTEAMS_JSON_CHANNEL_ID)
        user_id = param.get(MSTEAMS_JSON_USER_ID)
        message = param[MSTEAMS_JSON_MSG]
        choices = param.get(MSTEAMS_JSON_CHOICES, "")

        choices_split = get_list_from_string(choices)

        card = create_question_card(message, choices_split)
        bot = TeamsChannelAccount(id=self._client_id, name="SOARBot")
        activity = Activity(type="message", attachments=[card])

        status = self._verify_parameters(group_id=group_id, channel_id=channel_id, action_result=action_result)

        if phantom.is_fail(status):
            error_message = action_result.get_message()
            if "teamId" in error_message:
                error_message = error_message.replace("teamId", "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        channel_data = TeamsChannelData(
            channel=ChannelInfo(id=channel_id),
            team=TeamInfo(id=group_id),
            tenant=TenantInfo(id=self._tenant),
        )
        parameters = ConversationParameters(
            channel_data=channel_data,
            tenant_id=self._tenant,
            bot=bot,
            activity=activity,
        )
        reference = ConversationReference(channel_id=channel_id)

        adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings(app_id=self._client_id, app_password=self._client_secret))

        async def handle_create_conversation(turn_context: TurnContext) -> Activity:
            return turn_context.activity

        activity: Activity = asyncio.run(
            adapter.create_conversation(
                reference=reference,
                conversation_parameters=parameters,
                service_url="https://smba.trafficmanager.net/teams",
                logic=handle_create_conversation,
            )
        )

        self.save_progress(f"Sent message to channel with activity ID: {activity.id}")
        conversation_id = getattr(getattr(activity, "conversation", None), "id", None)
        if not conversation_id:
            return action_result.set_status(phantom.APP_ERROR, "Microsoft Teams did not return a conversation identifier")
        action_result.update_summary({"expected_conversation_id": conversation_id})
        suspend_token = self.suspend_run(activity.id)
        self.save_progress(f"Delegated action to webhook with token: {suspend_token}")
        return True

    def _handle_list_channels(self, param):
        """This function is used to list all the channels of the particular group.

        :param param: Dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = param[MSTEAMS_JSON_GROUP_ID]

        endpoint = MSTEAMS_MSGRAPH_LIST_CHANNELS_ENDPOINT.format(group_id=_encode_graph_path_segment(group_id))

        status, channels = self._get_paginated_values(endpoint, action_result)
        if phantom.is_fail(status):
            error_message = action_result.get_message()
            if "teamId" in error_message:
                error_message = error_message.replace("teamId", "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        for channel in channels:
            action_result.add_data(channel)

        summary = action_result.update_summary({})
        summary["total_channels"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_groups(self, param):
        """This function is used to list all the groups for Microsoft Team.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = MSTEAMS_MSGRAPH_GROUPS_ENDPOINT

        status, groups = self._get_paginated_values(endpoint, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        for group in groups:
            action_result.add_data(group)

        summary = action_result.update_summary({})
        summary["total_groups"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_teams(self, param):
        """This function is used to list all the teams for Microsoft Team.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        endpoint = MSTEAMS_MSGRAPH_TEAMS_ENDPOINT

        status, teams = self._get_paginated_values(endpoint, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        for team in teams:
            action_result.add_data(team)

        summary = action_result.update_summary({})
        summary["total_teams"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_meeting(self, param):
        """This function is used to create meeting for Microsoft Teams.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        use_calendar = param.get(MSTEAMS_JSON_CALENDAR, False)
        subject = param.get(MSTEAMS_JSON_SUBJECT)
        data = {}
        if subject:
            data.update({"subject": subject})
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
                    attendee_dict = {"emailAddress": {"address": attendee}}
                    attendees_list.append(attendee_dict)
            data.update({"isOnlineMeeting": True})
            if description:
                data.update({"body": {"content": description}})
            if start_time:
                data.update({"start": {"dateTime": start_time, "timeZone": self._timezone}})
            if end_time:
                data.update({"end": {"dateTime": end_time, "timeZone": self._timezone}})
            if attendees_list:
                data.update({"attendees": attendees_list})
        # make rest call
        status, response = self._update_request(endpoint=endpoint, action_result=action_result, method="post", data=json.dumps(data))

        if phantom.is_fail(status):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message="Meeting Created Successfully")

    def _handle_get_channel_message(self, param: dict) -> str:
        """This function is used to get message from specified channel in a Microsoft Teams group.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        group_id = param[MSTEAMS_JSON_GROUP_ID]
        channel_id = param[MSTEAMS_JSON_CHANNEL_ID]
        message_id = param[MSTEAMS_JSON_MSG_ID]

        status = self._verify_parameters(group_id=group_id, channel_id=channel_id, action_result=action_result)

        if phantom.is_fail(status):
            error_message = action_result.get_message()
            if "teamId" in error_message:
                error_message = error_message.replace("teamId", "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        endpoint = MSTEAMS_MSGRAPH_GET_CHANNEL_MSG_ENDPOINT.format(
            group_id=_encode_graph_path_segment(group_id),
            channel_id=_encode_graph_path_segment(channel_id),
            message_id=_encode_graph_path_segment(message_id),
        )

        # make rest call
        ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result, method="get")

        if phantom.is_fail(ret_val):
            error_message = action_result.get_message()
            if "teamId" in error_message:
                error_message = error_message.replace("teamId", "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message="Message successfully retrieved")

    def _handle_get_chat_message(self, param: dict) -> str:
        """This function is used to get the message from the specified chat.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        chat_id = param[MSTEAMS_JSON_CHAT_ID]
        message_id = param[MSTEAMS_JSON_MSG_ID]

        endpoint = MSTEAMS_MSGRAPH_GET_CHAT_MSG_ENDPOINT.format(
            chat_id=_encode_graph_path_segment(chat_id),
            message_id=_encode_graph_path_segment(message_id),
        )

        # make rest call
        ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result, method="get")

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, action_result.get_message())

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message="Message successfully retrieved")

    def _handle_get_response(self, param: dict) -> str:
        """This function is used to get reply messages from chat.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        chat_id = param[MSTEAMS_JSON_CHAT_ID]
        message_id = param[MSTEAMS_JSON_MSG_ID]

        endpoint = MSTEAMS_MSGRAPH_SEND_DIRECT_MSG_ENDPOINT.format(chat_id=_encode_graph_path_segment(chat_id))

        endpoint += "?$orderby=createdDateTime+desc&$top=50"

        all_replies = []
        seen_endpoints = {endpoint}
        page_count = 0

        while True:
            page_count += 1
            # make rest call
            ret_val, response = self._update_request(endpoint=endpoint, action_result=action_result, method="get")

            if phantom.is_fail(ret_val):
                return action_result.set_status(phantom.APP_ERROR, action_result.get_message())

            replies = response.get("value", [])

            if not replies:
                return action_result.set_status(phantom.APP_ERROR, action_result.get_message())

            message_list = []

            try:
                for reply in replies:
                    message_list.append(reply.get("id"))
                    attachments = reply.get("attachments", [])
                    attachment_count = len(attachments)

                    if attachment_count > 0:
                        attachment_ids = [attachment.get("id") for attachment in attachments]

                        if message_id in attachment_ids:
                            reply["contain_attachment"] = "Yes" if attachment_count > 1 else "No"
                            all_replies.append(reply)

            except Exception as exc:
                return action_result.set_status(phantom.APP_ERROR, f"An error occurred: {exc}")

            if message_id in message_list:
                break

            if response.get(MSTEAMS_NEXT_LINK_STRING):
                next_endpoint = response.get(MSTEAMS_NEXT_LINK_STRING)
                if page_count >= MSTEAMS_MAX_PAGINATION_PAGES:
                    return action_result.set_status(phantom.APP_ERROR, "Microsoft Graph pagination exceeded the 1000-page limit")
                if next_endpoint in seen_endpoints:
                    return action_result.set_status(phantom.APP_ERROR, "Microsoft Graph returned a non-progressing nextLink")
                seen_endpoints.add(next_endpoint)
                endpoint = next_endpoint
            else:
                break

        if not all_replies:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"get response action did not find reply for {message_id} message",
            )

        for reply in all_replies:
            try:
                body = reply.get("body")

                if body is None or body.get("content") is None:
                    continue

                text = re.findall(r"</attachment>\n(.*?)\n<p>", body.get("content"))
                reply.get("body")["message_reply"] = "".join(text).strip()
                action_result.add_data(reply)

            except Exception as exc:
                return action_result.set_status(phantom.APP_ERROR, f"Cannot find message text in body.content object. {exc}")

        return action_result.set_status(phantom.APP_SUCCESS, status_message="Successfully found a reply to the message")

    def _handle_list_chats(self, param):
        """This function is used to list all chats for the current user with optional filters.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        user_filter = param.get(MSTEAMS_JSON_USER_FILTER)
        chat_type_filter = param.get(MSTEAMS_JSON_CHAT_TYPE_FILTER)

        if chat_type_filter and chat_type_filter not in MSTEAMS_VALID_CHAT_TYPES:
            return action_result.set_status(phantom.APP_ERROR, "Invalid chat type filter")

        endpoint = MSTEAMS_MSGRAPH_LIST_CHATS_ENDPOINT

        status, chats = self._get_paginated_values(endpoint, action_result)
        if phantom.is_fail(status):
            return action_result.get_status()

        for chat in chats:
            # Filters
            if chat_type_filter and chat_type_filter != chat.get("chatType", ""):
                continue

            if user_filter:
                user_match = False
                for member in chat.get("members", []):
                    user_id = member.get("userId", "")
                    email = member.get("email", "")
                    if user_filter in user_id or user_filter in email:
                        user_match = True
                        break
                if not user_match:
                    continue

            action_result.add_data(chat)

        summary = action_result.update_summary({})
        summary["total_chats"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _send_chat_message(self, action_result, chat_id, message):
        """This function is used to send a message to a chat.

        :param action_result: ActionResult object
        :param chat_id: ID of desired chat
        :param message: Message to be sent
        :return: status success/failure
        """
        endpoint = MSTEAMS_MSGRAPH_SEND_DIRECT_MSG_ENDPOINT.format(chat_id=_encode_graph_path_segment(chat_id))

        data = {"body": {"contentType": "html", "content": message}}

        # make rest call
        status, response = self._update_request(endpoint=endpoint, action_result=action_result, method="post", data=json.dumps(data))

        if phantom.is_fail(status):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response

    def _handle_send_chat_message(self, param):
        """This function is used to send a message to a chat.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        chat_id = param[MSTEAMS_JSON_CHAT_ID]

        message = param[MSTEAMS_JSON_MSG]

        status, response = self._send_chat_message(action_result, chat_id, message)

        if phantom.is_fail(status):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message="Message sent to chat successfully")

    def _handle_send_direct_message(self, param):
        """This function is used to send a direct message to a user.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        user_id = param[MSTEAMS_JSON_USER_ID]
        message = param[MSTEAMS_JSON_MSG]

        # Get our ID
        status, me_response = self._update_request(endpoint=MSTEAMS_MSGRAPH_LIST_ME_ENDPOINT, action_result=action_result)

        if phantom.is_fail(status):
            return action_result.set_status(phantom.APP_ERROR, "Failed to retrieve current user information")

        current_user_id = me_response.get("id")
        if not current_user_id:
            return action_result.set_status(phantom.APP_ERROR, "Failed to retrieve current user ID")

        # Get chats and find our 1:1 with user
        status, response = self._update_request(endpoint=MSTEAMS_MSGRAPH_LIST_CHATS_ENDPOINT, action_result=action_result)

        if phantom.is_fail(status):
            return action_result.get_status()

        chat_id = None
        for chat in response.get("value", []):
            if chat.get("chatType") == "oneOnOne":
                members = chat.get("members", [])
                if len(members) == 2 and any(member.get("userId") == user_id for member in members):
                    chat_id = chat.get("id")
                    break

        if not chat_id:
            # Create new chat if none exists
            create_chat_endpoint = "/chats"
            create_chat_data = {
                "chatType": "oneOnOne",
                "members": [
                    {
                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                        "roles": ["owner"],
                        "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{_encode_graph_path_segment(current_user_id)}",
                    },
                    {
                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                        "roles": ["owner"],
                        "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{_encode_graph_path_segment(user_id)}",
                    },
                ],
            }
            status, response = self._update_request(
                endpoint=create_chat_endpoint, action_result=action_result, method="post", data=json.dumps(create_chat_data)
            )

            if phantom.is_fail(status):
                return action_result.get_status()

            chat_id = response.get("id")

        # Send chat message now
        status, response = self._send_chat_message(action_result, chat_id, message)

        if phantom.is_fail(status):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, status_message="Message sent to user successfully")

    def _get_bounded_int(self, action_result, param, name, default, minimum, maximum):
        """Read a whole-number parameter within the configured bounds.

        Out-of-range is an error rather than a silent clamp: a playbook that asks
        for 100000 checks is expressing an intent the action cannot honour, and
        quietly doing something else would make the timeout it reports a lie.
        """

        value = param.get(name)
        if value in (None, ""):
            return phantom.APP_SUCCESS, default
        try:
            if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
                raise ValueError("not a whole number")
            value = int(value)
        except (TypeError, ValueError, OverflowError):
            return action_result.set_status(phantom.APP_ERROR, f"Parameter '{name}' must be a whole number."), None
        if not minimum <= value <= maximum:
            return (
                action_result.set_status(phantom.APP_ERROR, f"Parameter '{name}' must be between {minimum} and {maximum}."),
                None,
            )
        return phantom.APP_SUCCESS, value

    def _build_adaptive_card_message_payload(self, card_obj: dict) -> dict:
        """Build a Microsoft Graph chat/channel message body with an adaptive card attachment."""

        attachment_id = str(uuid.uuid4())
        card_json = json.dumps(card_obj, separators=(",", ":"))
        return {
            "body": {"contentType": "html", "content": f'<attachment id="{attachment_id}"></attachment>'},
            "attachments": [
                {
                    "id": attachment_id,
                    "contentType": MSTEAMS_ADAPTIVE_CARD_CONTENT_TYPE,
                    "contentUrl": None,
                    "content": card_json,
                }
            ],
        }

    def _find_users(self, action_result, value, select):
        """Every user in the tenant matching one identifier. Returns (status, matches).

        Try a UPN or object ID directly, then an exact directory search. Mail
        addresses can differ from UPNs, so they also need the search fallback.
        """

        value = str(value).strip()
        if not value:
            return phantom.APP_SUCCESS, []

        if "@" in value or re.match(MSTEAMS_GUID_PATTERN, value):
            status, response = self._update_request(
                action_result,
                f"{MSTEAMS_MSGRAPH_LIST_USERS_ENDPOINT}/{_encode_graph_path_segment(value)}",
                params={"$select": select},
            )
            if phantom.is_success(status) and isinstance(response, dict) and response.get("id"):
                return phantom.APP_SUCCESS, [response]

        # Doubling the quote is how OData escapes one inside a string literal.
        escaped = value.replace("'", "''")
        status, response = self._update_request(
            action_result,
            MSTEAMS_MSGRAPH_LIST_USERS_ENDPOINT,
            params={
                "$filter": f"mail eq '{escaped}' or userPrincipalName eq '{escaped}' or displayName eq '{escaped}'",
                "$select": select,
                # Three is enough to tell "one" from "more than one" and to name
                # a couple of the clashes back to whoever has to disambiguate.
                "$top": "3",
            },
        )
        if phantom.is_fail(status) or not isinstance(response, dict):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, response.get("value") or []

    def _lookup_approver(self, action_result, value):
        """Find one user in the tenant. Returns {'id', 'name'} or None."""

        status, matches = self._find_users(action_result, value, MSTEAMS_USER_SELECT_BASIC)
        if phantom.is_fail(status) or not matches or len(matches) != 1:
            # Zero is no such user; more than one means the name is ambiguous and
            # guessing which person was meant is not acceptable for an approval.
            return None
        return {"id": matches[0]["id"], "name": matches[0].get("displayName") or value}

    def _resolve_approvers(self, action_result, approvers):
        """Resolve approver entries to Azure AD object IDs and display names.

        Reaction identities are matched by object ID. Resolve names, UPNs and
        email addresses before posting so ambiguous entries fail closed.
        """
        resolved = []
        for entry in approvers:
            value = str(entry).strip()
            if not value:
                continue
            try:
                found = self._lookup_approver(action_result, value)
            except Exception as e:
                return None, MSTEAMS_APPROVER_LOOKUP_FAILED_MSG.format(approver=value, error=_get_error_message_from_exception(e, self))
            if not found:
                return None, MSTEAMS_APPROVER_UNRESOLVED_MSG.format(approver=value)
            resolved.append({"id": str(found["id"]).lower(), "name": found["name"]})
        return resolved, ""

    def _get_signed_in_identity(self, action_result):
        """The delegated account this asset posts as: object ID and display name.

        The ID separates our own seeded reactions from an approver's.
        """

        status, response = self._update_request(endpoint=MSTEAMS_MSGRAPH_LIST_ME_ENDPOINT, action_result=action_result)
        if phantom.is_fail(status):
            return action_result.get_status(), None
        user_id = (response or {}).get("id")
        if not user_id:
            return action_result.set_status(phantom.APP_ERROR, "Failed to retrieve current user ID"), None
        return phantom.APP_SUCCESS, {
            "id": str(user_id).strip().lower(),
            "name": (response or {}).get("displayName") or "",
        }

    def _resolve_one_on_one_chat_id(self, action_result, user_id):
        """Create or retrieve the delegated user's one-on-one chat."""
        status, identity = self._get_signed_in_identity(action_result)
        if phantom.is_fail(status):
            return status, None
        members = [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"{MSTEAMS_MSGRAPH_API_BASE_URL}/users/{_encode_graph_path_segment(member_id)}",
            }
            for member_id in (identity["id"], user_id)
        ]
        status, response = self._update_request(
            action_result, "/chats", method="post", data=json.dumps({"chatType": "oneOnOne", "members": members})
        )
        if phantom.is_fail(status):
            return status, None
        chat_id = (response or {}).get("id")
        if not chat_id:
            return action_result.set_status(phantom.APP_ERROR, "Microsoft Graph did not return a chat ID."), None
        return phantom.APP_SUCCESS, chat_id

    def _resolve_reaction_target(self, action_result, destination, param):
        """Work out which Graph message collection the card should be posted to.

        Returns (status, {'messages_endpoint', 'reaction_endpoint'}) where
        'reaction_endpoint' still needs its message_id substituted -- the ID only
        exists once the card has actually been posted.
        """

        if destination == "channel":
            group_id = param.get(MSTEAMS_JSON_GROUP_ID)
            channel_id = param.get(MSTEAMS_JSON_CHANNEL_ID)
            if not group_id or not channel_id:
                return (
                    action_result.set_status(phantom.APP_ERROR, "For destination 'channel', provide both 'group_id' and 'channel_id'."),
                    None,
                )

            status = self._verify_parameters(group_id=group_id, channel_id=channel_id, action_result=action_result)
            if phantom.is_fail(status):
                error_message = action_result.get_message()
                if "teamId" in error_message:
                    error_message = error_message.replace("teamId", "'group_id'")
                return action_result.set_status(phantom.APP_ERROR, error_message), None

            encoded_group = _encode_graph_path_segment(group_id)
            encoded_channel = _encode_graph_path_segment(channel_id)
            return phantom.APP_SUCCESS, {
                "messages_endpoint": MSTEAMS_MSGRAPH_SEND_CHANNEL_MSG_ENDPOINT.format(group_id=encoded_group, channel_id=encoded_channel),
                "reaction_endpoint": MSTEAMS_MSGRAPH_SET_CHANNEL_MSG_REACTION_ENDPOINT.format(
                    group_id=encoded_group, channel_id=encoded_channel, message_id="{message_id}"
                ),
                # A channel post has a reply thread to fall back to; a chat does
                # not, so there the fallback is a new message in the chat.
                "threaded": True,
            }

        if destination == "direct_message":
            user_id = param.get(MSTEAMS_JSON_USER_ID)
            if not user_id:
                return action_result.set_status(phantom.APP_ERROR, "For destination 'direct_message', provide 'user_id'."), None
            status, chat_id = self._resolve_one_on_one_chat_id(action_result, user_id)
            if phantom.is_fail(status):
                return action_result.get_status(), None
        else:
            chat_id = param.get(MSTEAMS_JSON_CHAT_ID)
            if not chat_id:
                return action_result.set_status(phantom.APP_ERROR, "For destination 'chat', provide 'chat_id'."), None

        encoded_chat = _encode_graph_path_segment(chat_id)
        return phantom.APP_SUCCESS, {
            "messages_endpoint": MSTEAMS_MSGRAPH_SEND_DIRECT_MSG_ENDPOINT.format(chat_id=encoded_chat),
            "reaction_endpoint": MSTEAMS_MSGRAPH_SET_CHAT_MSG_REACTION_ENDPOINT.format(chat_id=encoded_chat, message_id="{message_id}"),
            "threaded": False,
        }

    @staticmethod
    def _approving_reaction(reactions):
        """The reaction that approves -- the fallback when only one can be seeded."""

        return next((reaction for reaction in reactions if reaction["approves"]), reactions[0] if reactions else None)

    def _seed_reactions(self, action_result, target, message_id, reactions):
        """Seed only the approving choice; this account's reactions never decide."""
        approving = self._approving_reaction(reactions)
        endpoint = target["reaction_endpoint"].format(message_id=_encode_graph_path_segment(message_id))
        status, _ = self._update_request(
            action_result=action_result,
            endpoint=endpoint,
            method="post",
            data=json.dumps({"reactionType": approving["emoji"]}),
        )
        if phantom.is_fail(status):
            message = MSTEAMS_REACTION_SEED_FAILED_MSG.format(reaction=approving["emoji"], error=action_result.get_message())
            self.save_progress(message)
            return [message]
        return []

    @staticmethod
    def _seeded_reactions_present(raw_reactions, reactions, self_id):
        """Which accepted reactions this account actually holds on the message.

        Read from the message rather than inferred from the seed calls: a 204
        from setReaction says the call was accepted, not that the reaction stuck.
        """

        wanted = {reaction["key"]: reaction for reaction in reactions}
        present = []
        for entry in raw_reactions or []:
            if not isinstance(entry, dict):
                continue
            reactor_id = str((((entry.get("user") or {}).get("user")) or {}).get("id") or "").strip().lower()
            if not self_id or reactor_id != self_id:
                continue
            choice = wanted.get(normalize_reaction(entry.get("reactionType")))
            if choice and choice["emoji"] not in present:
                present.append(choice["emoji"])
        return present

    def _resolve_user_identity(self, action_result, user_id, fallback_name=""):
        """Turn a reacting user's object ID into something a person can read.

        A reaction carries only a display name and an object ID. An object ID is
        a database key: it identifies the approver to an auditor but tells a
        human reading the card nothing, so the directory is asked for the user
        principal name and mail as well. Best-effort -- a failed lookup degrades
        to what the reaction itself carried rather than failing the approval.
        """

        identity = {"name": fallback_name or "", "upn": "", "email": "", "aad_id": user_id or ""}
        if not user_id:
            return identity

        try:
            status, response = self._update_request(
                action_result,
                f"{MSTEAMS_MSGRAPH_LIST_USERS_ENDPOINT}/{_encode_graph_path_segment(user_id)}",
                params={"$select": "id,displayName,userPrincipalName,mail"},
            )
        except Exception as e:
            self.save_progress(f"Could not look up the approver's directory entry: {_get_error_message_from_exception(e, self)}")
            return identity

        if phantom.is_fail(status) or not isinstance(response, dict):
            self.save_progress(f"Could not look up the approver's directory entry: {action_result.get_message()}")
            return identity

        identity["name"] = response.get("displayName") or identity["name"]
        identity["upn"] = response.get("userPrincipalName") or ""
        identity["email"] = response.get("mail") or ""
        return identity

    @staticmethod
    def _find_answering_reaction(raw_reactions, reactions, self_id, approver_ids):
        """Split a message's reactions into the answer and the ones turned away.

        Returns (answer, ignored). 'answer' is the oldest eligible reaction, or
        None if nobody has answered yet: several can land between two checks, and
        the first person to respond is the one who decided.

        'ignored' holds reactions that were a real attempt to answer -- a
        configured emoji -- from somebody not on the approver list. They never
        decide anything, but silently dropping them would leave no record that
        someone tried. Reactions with an emoji that is not configured are not
        attempts to answer and are not reported.
        """

        wanted = {reaction["key"]: reaction for reaction in reactions}
        eligible = []
        ignored = []

        for entry in raw_reactions or []:
            if not isinstance(entry, dict):
                continue
            choice = wanted.get(normalize_reaction(entry.get("reactionType")))
            if not choice:
                continue

            identity = (entry.get("user") or {}).get("user") or {}
            reactor_id = str(identity.get("id") or "").strip().lower()
            # The seeded reactions are ours. Counting them would decide every
            # approval the instant it was posted.
            if not reactor_id or reactor_id == self_id:
                continue

            created = str(entry.get("createdDateTime") or "")
            if approver_ids and reactor_id not in approver_ids:
                ignored.append(
                    {
                        "reaction": entry.get("reactionType"),
                        "reaction_emoji": choice["emoji"],
                        "answer": choice["label"],
                        "reacted_by": identity.get("displayName") or "",
                        "reacted_by_aad_id": identity.get("id") or "",
                        "reacted_at": created,
                        "reason": "not a listed approver",
                    }
                )
                continue

            # Fractional seconds and offsets do not sort chronologically as strings.
            try:
                timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                timestamp = datetime.max.replace(tzinfo=timezone.utc)
            # A simultaneous approve/deny tie resolves to deny.
            eligible.append(((timestamp, choice["approves"]), entry, choice, identity))

        if not eligible:
            return None, ignored

        eligible.sort(key=lambda item: item[0])
        _, entry, choice, identity = eligible[0]
        return (entry, choice, identity), ignored

    def _close_reaction_message(self, action_result, target, message_id, card_obj, blocks):
        """Edit the posted approval message so it records how it ended.

        Returns (updated, error). Editing is presentation, never the decision
        itself, so every failure here is reported rather than raised: the
        playbook has its answer regardless of what Teams does with the card.

        A delegated PATCH can rewrite a message this account sent, which is what
        makes this possible without the Azure Bot. Where it is refused -- most
        often a missing 'ChannelMessage.ReadWrite' -- the same record is posted
        as a reply instead, so the outcome is still visible next to the request.
        """

        encoded_id = _encode_graph_path_segment(message_id)
        closed_card = finalize_reaction_card(card_obj, blocks)

        status, _ = self._update_request(
            action_result=action_result,
            endpoint=f"{target['messages_endpoint']}/{encoded_id}",
            method="patch",
            data=json.dumps(self._build_adaptive_card_message_payload(closed_card)),
        )
        if phantom.is_success(status):
            return True, ""

        error = MSTEAMS_REACTION_UPDATE_FAILED_MSG.format(error=action_result.get_message())
        self.save_progress(f"{error} {MSTEAMS_REACTION_UPDATE_SCOPE_HINT}")

        # A chat has no reply thread, so there the record goes into the chat as
        # its own message, immediately after the one it closes.
        reply_endpoint = f"{target['messages_endpoint']}/{encoded_id}/replies" if target.get("threaded") else target["messages_endpoint"]
        status, _ = self._update_request(
            action_result=action_result,
            endpoint=reply_endpoint,
            method="post",
            data=json.dumps(self._build_adaptive_card_message_payload(closed_card)),
        )
        if phantom.is_fail(status):
            return False, f"{error} Posting it as a reply also failed: {action_result.get_message()}"

        return False, f"{error} It was posted as a reply instead."

    def _handle_ask_for_approval_reactions(self, param: dict) -> str:
        """Post an approval card over Graph and watch for an emoji reaction on it.

        Post as the delegated user and poll a bounded number of times. No
        suspended action, webhook callback or Azure Bot is required.
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        destination = (param.get(MSTEAMS_JSON_DESTINATION) or "").strip().lower()
        if destination not in MSTEAMS_VALID_REACTION_DESTINATIONS:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid destination. Use one of: {', '.join(sorted(MSTEAMS_VALID_REACTION_DESTINATIONS))}.",
            )

        try:
            reactions = parse_reactions(param.get(MSTEAMS_JSON_REACTIONS) or MSTEAMS_REACTION_DEFAULT_REACTIONS)
        except ValueError as e:
            return action_result.set_status(phantom.APP_ERROR, f"Parameter 'reactions' is not valid: {e}")

        if len(reactions) < 2:
            return action_result.set_status(
                phantom.APP_ERROR,
                "Parameter 'reactions' needs at least two distinct emoji. The first approves unless one sets \"approves\": true.",
            )

        if not any(r["approves"] for r in reactions) or all(r["approves"] for r in reactions):
            return action_result.set_status(phantom.APP_ERROR, "Configure at least one approving and one rejecting reaction.")

        status, max_checks = self._get_bounded_int(
            action_result, param, MSTEAMS_JSON_MAX_CHECKS, MSTEAMS_REACTION_DEFAULT_MAX_CHECKS, 1, MSTEAMS_REACTION_MAX_CHECKS_LIMIT
        )
        if phantom.is_fail(status):
            return action_result.get_status()

        status, check_interval = self._get_bounded_int(
            action_result,
            param,
            MSTEAMS_JSON_CHECK_INTERVAL,
            MSTEAMS_REACTION_DEFAULT_CHECK_INTERVAL,
            MSTEAMS_REACTION_MIN_CHECK_INTERVAL,
            MSTEAMS_REACTION_MAX_CHECK_INTERVAL,
        )
        if phantom.is_fail(status):
            return action_result.get_status()

        resolved_approvers, approver_error = self._resolve_approvers(action_result, get_list_from_string(param.get(MSTEAMS_JSON_APPROVERS, "")))
        if resolved_approvers is None:
            return action_result.set_status(phantom.APP_ERROR, approver_error)
        approver_ids = {approver["id"] for approver in resolved_approvers}

        seed_mode = str(param.get(MSTEAMS_JSON_SEED_REACTIONS, "approving")).strip().lower()
        if seed_mode not in ("approving", "none"):
            return action_result.set_status(phantom.APP_ERROR, "Parameter 'seed_reactions' must be 'approving' or 'none'.")

        adaptive_raw = param.get(MSTEAMS_JSON_ADAPTIVE_CARD)
        if adaptive_raw is not None and str(adaptive_raw).strip():
            try:
                card_obj = json.loads(str(adaptive_raw))
            except json.JSONDecodeError as e:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid adaptive card JSON: {e}")
            if not isinstance(card_obj, dict):
                return action_result.set_status(phantom.APP_ERROR, "Adaptive card must be a JSON object at the root.")
        else:
            message = param.get(MSTEAMS_JSON_MSG)
            if not message or not str(message).strip():
                return action_result.set_status(
                    phantom.APP_ERROR, "Parameter 'message' is required unless 'adaptive_card' supplies a custom card."
                )
            try:
                # The card names people; matching is by Azure AD object ID.
                card_obj = create_reaction_approval_card(
                    str(param.get(MSTEAMS_JSON_TITLE) or "Approval required"),
                    str(message),
                    param.get(MSTEAMS_JSON_DETAILS) or "",
                    reactions,
                    [approver["name"] for approver in resolved_approvers],
                )
            except Exception as e:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Could not build the approval card: {_get_error_message_from_exception(e, self)}"
                )

        # Identify ourselves before posting: without this the seeded reactions
        # cannot be told apart from an approver's, and the action would answer
        # itself on the first check.
        status, self_identity = self._get_signed_in_identity(action_result)
        if phantom.is_fail(status):
            return action_result.get_status()
        self_id = self_identity["id"]
        if approver_ids and not (approver_ids - {self_id}):
            return action_result.set_status(phantom.APP_ERROR, "The sending account cannot approve its own request. Specify another approver.")

        status, target = self._resolve_reaction_target(action_result, destination, param)
        if phantom.is_fail(status):
            return action_result.get_status()

        status, response = self._update_request(
            action_result=action_result,
            endpoint=target["messages_endpoint"],
            method="post",
            data=json.dumps(self._build_adaptive_card_message_payload(card_obj)),
        )
        if phantom.is_fail(status):
            error_message = action_result.get_message()
            if "teamId" in error_message:
                error_message = error_message.replace("teamId", "'group_id'")
            return action_result.set_status(phantom.APP_ERROR, error_message)

        message_id = (response or {}).get("id")
        if not message_id:
            return action_result.set_status(phantom.APP_ERROR, "Posted the card but Microsoft Teams did not return a message ID to watch.")

        self.save_progress(f"Posted approval card as message {message_id}")
        action_result.update_summary(
            {
                "message_id": message_id,
                "destination": destination,
                "expected_approver_ids": sorted(approver_ids),
            }
        )

        message_endpoint = f"{target['messages_endpoint']}/{_encode_graph_path_segment(message_id)}"

        seed_errors = []
        if seed_mode != "none":
            seed_errors = self._seed_reactions(action_result, target, message_id, reactions)

        record = {
            "message_id": message_id,
            "web_url": (response or {}).get("webUrl"),
            "destination": destination,
            "seeded": False,
            "seeded_reactions": [],
            "seed_mode": seed_mode,
            "seed_note": "",
            "seed_errors": seed_errors,
        }

        record.update({"approved": False, "timed_out": False})
        action_result.add_data(record)
        answered = False
        # Keyed so the same standing reaction is not recorded once per check --
        # an ignored reaction stays on the message for every remaining poll.
        ignored_seen = {}
        seeds_checked = False
        for check in range(1, max_checks + 1):
            status, message_body = self._update_request(action_result=action_result, endpoint=message_endpoint, method="get")
            if phantom.is_fail(status):
                # Fail promptly when the first read cannot establish access.
                # Later errors consume checks but allow another bounded retry.
                if check == 1:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        f"Could not read reactions on message '{message_id}': {action_result.get_message()}. {MSTEAMS_REACTION_SCOPE_HINT}",
                    )
                self.save_progress(f"Check {check}/{max_checks} could not read the message: {action_result.get_message()}")
            else:
                raw_reactions = (message_body or {}).get("reactions")
                if not seeds_checked:
                    # setReaction returning 204 means the call was accepted, not
                    # that the reaction stuck, so what is really on the message
                    # is read back once -- from a poll we were making anyway.
                    seeds_checked = True
                    record["seeded_reactions"] = self._seeded_reactions_present(raw_reactions, reactions, self_id)
                    record["seeded"] = bool(record["seeded_reactions"])
                    if seed_mode != "none" and len(record["seeded_reactions"]) < len(reactions):
                        # Expected on most tenants, so it is reported as a note.
                        # Carrying it in seed_errors made a normal outcome read
                        # like a failure.
                        note = MSTEAMS_REACTION_SINGLE_SEED_NOTE.format(
                            requested=len(reactions),
                            landed=len(record["seeded_reactions"]),
                            emoji=" ".join(record["seeded_reactions"]) or "none",
                        )
                        self.save_progress(note)
                        record["seed_note"] = note

                found, ignored = self._find_answering_reaction(raw_reactions, reactions, self_id, approver_ids)
                for entry in ignored:
                    ignored_seen.setdefault((entry["reacted_by_aad_id"], entry["reaction_emoji"], entry["reacted_at"]), entry)
                if found:
                    entry, choice, identity = found
                    approver = self._resolve_user_identity(action_result, identity.get("id") or "", identity.get("displayName") or "")
                    record.update(
                        {
                            "approved": choice["approves"],
                            "answer": choice["label"],
                            "reaction": entry.get("reactionType"),
                            "reaction_emoji": choice["emoji"],
                            "answered_by": approver["name"],
                            "answered_by_upn": approver["upn"],
                            "answered_by_email": approver["email"],
                            "answered_by_aad_id": approver["aad_id"],
                            "answered_at": entry.get("createdDateTime") or "",
                            "checks_performed": check,
                            "timed_out": False,
                        }
                    )
                    answered = True
                    break

            if check < max_checks:
                self.save_progress(f"No response yet (check {check}/{max_checks}); waiting {check_interval}s")
                time.sleep(check_interval)

        if not answered:
            record.update(
                {
                    "approved": False,
                    "answer": "",
                    "reaction": "",
                    "reaction_emoji": "",
                    "answered_by": "",
                    "answered_by_upn": "",
                    "answered_by_email": "",
                    "answered_by_aad_id": "",
                    "answered_at": "",
                    "checks_performed": max_checks,
                    "timed_out": True,
                }
            )
            # Only max_checks - 1 gaps are actually waited through, and a single
            # check waits no time at all -- reporting a duration there would be
            # a plain untruth.
            waited = (max_checks - 1) * check_interval
            if waited <= 0:
                window = ""
            elif waited < 120:
                window = f" (about {waited} seconds)"
            else:
                window = f" (about {round(waited / 60)} minutes)"

            # Leave nothing in Teams that still looks like a live approval.
            updated, update_error = self._close_reaction_message(
                action_result, target, message_id, card_obj, reaction_expired_blocks(max_checks, window)
            )
            record["card_updated"] = updated
            record["card_update_error"] = update_error
            record["ignored_reactions"] = list(ignored_seen.values())

            action_result.update_summary({"approved": False, "timed_out": True, "ignored_reactions": len(record["ignored_reactions"])})
            # An approval that nobody answered is not an approval. Failing here
            # keeps a playbook that only branches on action status from reading
            # silence as consent.
            return action_result.set_status(
                phantom.APP_ERROR,
                MSTEAMS_REACTION_NO_RESPONSE_MSG.format(checks=max_checks, interval=check_interval, window=window),
            )

        updated, update_error = self._close_reaction_message(
            action_result,
            target,
            message_id,
            card_obj,
            reaction_decision_blocks(choice, approver, record["answered_at"]),
        )
        record["card_updated"] = updated
        record["card_update_error"] = update_error
        record["ignored_reactions"] = list(ignored_seen.values())

        action_result.update_summary(
            {
                "approved": record["approved"],
                "timed_out": False,
                "answer": record["answer"],
                "ignored_reactions": len(record["ignored_reactions"]),
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS, describe_reaction_decision(choice, approver, record["answered_at"]))

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        self.debug_print("action_id", self.get_action_identifier())

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "send_channel_message": self._handle_send_channel_message,
            "ask_question": self._handle_ask_question,
            "ask_for_approval_reactions": self._handle_ask_for_approval_reactions,
            "send_direct_message": self._handle_send_direct_message,
            "send_chat_message": self._handle_send_chat_message,
            "list_groups": self._handle_list_groups,
            "list_teams": self._handle_list_teams,
            "list_users": self._handle_list_users,
            "list_channels": self._handle_list_channels,
            "get_admin_consent": self._handle_get_admin_consent,
            "create_meeting": self._handle_create_meeting,
            "get_channel_message": self._handle_get_channel_message,
            "get_chat_message": self._handle_get_chat_message,
            "get_response": self._handle_get_response,
            "list_chats": self._handle_list_chats,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in action_mapping.keys():
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
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

        self._tenant = config[MSTEAMS_CONFIG_TENANT_ID]
        self._client_id = config[MSTEAMS_CONFIG_CLIENT_ID]
        self._client_secret = config[MSTEAMS_CONFIG_CLIENT_SECRET]
        self._access_token = self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_ACCESS_TOKEN_STRING)
        self._refresh_token = self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_REFRESH_TOKEN_STRING)
        self._scope = config[MSTEAMS_CONFIG_SCOPE]
        if self._state.get(MSTEAMS_STATE_IS_ENCRYPTED):
            try:
                if self._access_token:
                    self._access_token = self.decrypt_state(self._access_token, "access")
            except Exception as e:
                self.debug_print(f"{MSTEAMS_DECRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
                return self.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)

            try:
                if self._refresh_token:
                    self._refresh_token = self.decrypt_state(self._refresh_token, "refresh")
            except Exception as e:
                self.debug_print(f"{MSTEAMS_DECRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
                return self.set_status(phantom.APP_ERROR, MSTEAMS_DECRYPTION_ERROR)
        self._timezone = config.get(MSTEAMS_CONFIG_TIMEZONE)
        return phantom.APP_SUCCESS

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices, etc.

        :return: status (success/failure)
        """
        try:
            if self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_ACCESS_TOKEN_STRING):
                self._state[MSTEAMS_TOKEN_STRING][MSTEAMS_ACCESS_TOKEN_STRING] = self.encrypt_state(self._access_token, "access")
        except Exception as e:
            self.debug_print(f"{MSTEAMS_ENCRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
            return self.set_status(phantom.APP_ERROR, MSTEAMS_ENCRYPTION_ERROR)

        try:
            if self._state.get(MSTEAMS_TOKEN_STRING, {}).get(MSTEAMS_REFRESH_TOKEN_STRING):
                self._state[MSTEAMS_TOKEN_STRING][MSTEAMS_REFRESH_TOKEN_STRING] = self.encrypt_state(self._refresh_token, "refresh")
        except Exception as e:
            self.debug_print(f"{MSTEAMS_ENCRYPTION_ERROR}: {_get_error_message_from_exception(e, self)}")
            return self.set_status(phantom.APP_ERROR, MSTEAMS_ENCRYPTION_ERROR)
        self._state[MSTEAMS_STATE_IS_ENCRYPTED] = True
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        _save_app_state(self._state, self.get_asset_id(), self)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

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
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = BaseConnector._get_phantom_base_url() + "login"

            print("Logging into Platform to get the session id")
            r2 = requests.post(
                BaseConnector._get_phantom_base_url() + "login", verify=verify, data=data, headers=headers, timeout=MSTEAMS_DEFAULT_TIMEOUT
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platfrom. Error: {e!s}")
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
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
