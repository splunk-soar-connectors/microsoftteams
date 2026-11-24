# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import httpx
from soar_sdk import logging
from soar_sdk.abstract import SOARClient
from soar_sdk.auth import StaticTokenAuth
from soar_sdk.auth.client import AuthorizationRequiredError, OAuthClientError
from soar_sdk.exceptions import ActionFailure

from .actions._graph import (
    GRAPH_V1_BASE_URL,
    graph_request_error,
    graph_token_rejected,
)
from .asset import Asset
from .auth import (
    AUTHORIZATION_URL_STATE_KEY,
    authorization_flow,
    oauth_token_client,
    save_oauth_configuration_hash,
    validate_oauth_configuration,
)


def run_test_connectivity(
    soar: SOARClient,
    asset: Asset,
    oauth_callback_url: str,
    oauth_start_url: str,
) -> None:
    oauth_client = oauth_token_client(asset)
    try:
        validate_oauth_configuration(asset)
        token = oauth_client.get_valid_token(auto_refresh=True)
        with httpx.Client(
            auth=StaticTokenAuth(token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            verify=True,
        ) as client:
            response = client.get(f"{GRAPH_V1_BASE_URL}/me")
            if graph_token_rejected(response):
                stored_token = oauth_client.get_stored_token()
                if stored_token is not None and stored_token.refresh_token:
                    refreshed_token = oauth_client.refresh_token(
                        stored_token.refresh_token
                    )
                    response = client.get(
                        f"{GRAPH_V1_BASE_URL}/me",
                        auth=StaticTokenAuth(refreshed_token),
                    )
            response.raise_for_status()
    except (AuthorizationRequiredError, OAuthClientError):
        flow = authorization_flow(asset, str(soar.get_asset_id()), oauth_callback_url)
        authorization_url = flow.get_authorization_url()
        auth_state = asset.auth_state.get_all()
        auth_state[AUTHORIZATION_URL_STATE_KEY] = authorization_url
        asset.auth_state.put_all(auth_state)
        start_url_with_asset = f"{oauth_start_url}?asset_id={soar.get_asset_id()}&"
        logging.info("Using OAuth URL:")
        logging.info(oauth_callback_url)
        logging.info("Please authorize user in a separate tab using URL")
        logging.info(start_url_with_asset)
        try:
            token = flow.wait_for_authorization()
            with httpx.Client(
                auth=StaticTokenAuth(token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
                verify=True,
            ) as client:
                response = client.get(f"{GRAPH_V1_BASE_URL}/me")
                if graph_token_rejected(response):
                    stored_token = oauth_client.get_stored_token()
                    if stored_token is not None and stored_token.refresh_token:
                        refreshed_token = oauth_client.refresh_token(
                            stored_token.refresh_token
                        )
                        response = client.get(
                            f"{GRAPH_V1_BASE_URL}/me",
                            auth=StaticTokenAuth(refreshed_token),
                        )
                response.raise_for_status()
        except Exception as authorization_error:
            raise ActionFailure(
                "Microsoft Teams connectivity check failed: "
                f"{graph_request_error(authorization_error)}"
            ) from authorization_error
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise ActionFailure(
            f"Microsoft Teams connectivity check failed: {graph_request_error(exc)}"
        ) from exc

    save_oauth_configuration_hash(asset)
    soar.set_message("Test connectivity passed")
