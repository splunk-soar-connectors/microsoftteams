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
import hashlib
import hmac
import json
from urllib.parse import quote

from soar_sdk.auth import AuthorizationCodeFlow, OAuthConfig
from soar_sdk.auth.client import AuthorizationRequiredError, SOARAssetOAuthClient
from soar_sdk.auth.models import OAuthGrantType

from src.asset import Asset

LOGIN_BASE_URL = "https://login.microsoftonline.com"
AUTHORIZATION_URL_STATE_KEY = "microsoftteams_authorization_url"
OAUTH_CONFIG_HASH_KEY = "microsoftteams_oauth_config_hash"


def token_endpoint(tenant_id: str) -> str:
    return f"{LOGIN_BASE_URL}/{quote(tenant_id, safe='')}/oauth2/v2.0/token"


def authorization_flow(
    asset: Asset, asset_id: str, redirect_uri: str
) -> AuthorizationCodeFlow:
    return AuthorizationCodeFlow(
        auth_state=asset.auth_state,
        asset_id=asset_id,
        client_id=asset.client_id,
        client_secret=asset.client_secret,
        authorization_endpoint=(
            f"{LOGIN_BASE_URL}/{quote(asset.tenant_id, safe='')}/oauth2/v2.0/authorize"
        ),
        token_endpoint=token_endpoint(asset.tenant_id),
        redirect_uri=redirect_uri,
        scope=asset.scope,
        use_pkce=False,
        poll_timeout=105,
        poll_interval=3,
    )


def oauth_token_client(asset: Asset) -> SOARAssetOAuthClient:
    """Build the SDK OAuth state client used by Graph action requests."""
    configuration = OAuthConfig(
        client_id=asset.client_id,
        client_secret=asset.client_secret,
        token_endpoint=token_endpoint(asset.tenant_id),
        scope=asset.scope,
        grant_type=OAuthGrantType.AUTHORIZATION_CODE,
    )
    return SOARAssetOAuthClient(configuration, asset.auth_state)


def oauth_configuration_hash(asset: Asset) -> str:
    configuration = {
        "tenant_id": asset.tenant_id,
        "client_id": asset.client_id,
        "client_secret": asset.client_secret,
        "scope": asset.scope,
    }
    encoded = json.dumps(configuration, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_oauth_configuration(asset: Asset) -> None:
    auth_state = asset.auth_state
    state = auth_state.get_all()
    stored_hash = state.get(OAUTH_CONFIG_HASH_KEY)
    current_hash = oauth_configuration_hash(asset)
    if stored_hash and not hmac.compare_digest(stored_hash, current_hash):
        state.pop("oauth", None)
        state[OAUTH_CONFIG_HASH_KEY] = current_hash
        auth_state.put_all(state)
        raise AuthorizationRequiredError(
            "Microsoft Teams OAuth configuration changed. Test connectivity to authorize again."
        )


def save_oauth_configuration_hash(asset: Asset) -> None:
    state = asset.auth_state.get_all()
    state[OAUTH_CONFIG_HASH_KEY] = oauth_configuration_hash(asset)
    asset.auth_state.put_all(state)


def clear_oauth_token(asset: Asset) -> None:
    state = asset.auth_state.get_all()
    oauth_state = state.get("oauth")
    if isinstance(oauth_state, dict):
        oauth_state.pop("token", None)
        oauth_state.pop("session", None)
        state["oauth"] = oauth_state
        asset.auth_state.put_all(state)
