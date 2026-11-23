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
import secrets
import time
from collections.abc import Callable
from urllib.parse import quote, urlencode

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, ActionResult
from soar_sdk.params import Params

from ..asset import Asset

LOGIN_BASE_URL = "https://login.microsoftonline.com"


class AdminConsentOutput(ActionOutput):
    """The legacy action returns status and parameters without Graph data."""


def get_admin_consent(
    params: Params, soar: SOARClient, asset: Asset, redirect_uri: str
) -> AdminConsentOutput:
    asset_id = str(soar.get_asset_id())
    nonce = secrets.token_hex(16)
    expected_state = f"{asset_id}:{nonce}"
    cache_state = asset.cache_state
    state_data = cache_state.get_all()
    state_data.pop("microsoftteams_admin_consent_received", None)
    state_data["microsoftteams_admin_consent_state"] = expected_state
    cache_state.put_all(state_data)
    query = urlencode(
        {
            "client_id": asset.client_id,
            "redirect_uri": redirect_uri,
            "state": expected_state,
        }
    )
    consent_url = (
        f"{LOGIN_BASE_URL}/{quote(asset.tenant_id, safe='')}/adminconsent?{query}"
    )
    soar.set_message(
        "Open this URL in a browser as an administrator to provide consent: "
        f"{consent_url}"
    )

    for _ in range(35):
        time.sleep(3)
        state_data = cache_state.get_all(force_reload=True)
        if "microsoftteams_admin_consent_received" not in state_data:
            continue
        granted = state_data.pop("microsoftteams_admin_consent_received")
        cache_state.put_all(state_data)
        if granted:
            soar.set_message("Admin consent Received")
            return ActionResult(
                True, "Admin consent Received", params.model_dump(by_alias=True)
            )
        return ActionResult(
            False,
            "Admin consent not received",
            params.model_dump(by_alias=True),
        )

    state_data = cache_state.get_all()
    state_data.pop("microsoftteams_admin_consent_state", None)
    cache_state.put_all(state_data)
    return ActionResult(
        False,
        "Timeout waiting for admin consent. Please try again later.",
        params.model_dump(by_alias=True),
    )


def make_admin_consent_action(
    get_redirect_uri: Callable[[], str],
) -> Callable[[Params, SOARClient, Asset], AdminConsentOutput]:
    """Bind deferred SDK webhook URL lookup to the consent action handler."""

    def action(params: Params, soar: SOARClient, asset: Asset) -> AdminConsentOutput:
        return get_admin_consent(params, soar, asset, get_redirect_uri())

    return action
