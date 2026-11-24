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
import hmac
from typing import TYPE_CHECKING

from soar_sdk.auth import create_oauth_callback_handler
from soar_sdk.webhooks.models import WebhookRequest, WebhookResponse

from .auth import AUTHORIZATION_URL_STATE_KEY, authorization_flow, oauth_token_client

if TYPE_CHECKING:
    from soar_sdk.app import App

OAUTH_CALLBACK_ROUTE = "oauth/callback"
OAUTH_START_ROUTE = "oauth/start"


def register_webhooks(app: "App") -> None:
    app.enable_webhooks(default_requires_auth=False)

    @app.webhook(OAUTH_START_ROUTE, allowed_methods=["GET"])
    def oauth_start(request: WebhookRequest) -> WebhookResponse:
        authorization_url = request.asset.auth_state.get_all().get(
            AUTHORIZATION_URL_STATE_KEY
        )
        if not authorization_url:
            return WebhookResponse.text_response(
                "OAuth authorization URL is unavailable. Run test connectivity again.",
                status_code=400,
            )
        return WebhookResponse(
            status_code=302,
            headers=[("Location", authorization_url)],
            content="",
        )

    oauth_callback = create_oauth_callback_handler(
        oauth_token_client,
        success_message=(
            "Code received. Please close this window, the action will continue to get new token."
        ),
    )

    @app.webhook(OAUTH_CALLBACK_ROUTE, allowed_methods=["GET"])
    def oauth_webhook(request: WebhookRequest) -> WebhookResponse:
        query = {
            key: values[-1] if values else "" for key, values in request.query.items()
        }

        if "admin_consent" in query:
            cache_state = request.asset.cache_state
            state = cache_state.get_all(force_reload=True)
            expected_state = state.get("microsoftteams_admin_consent_state", "")
            presented_state = query.get("state", "")
            if not expected_state or not hmac.compare_digest(
                expected_state, presented_state
            ):
                return WebhookResponse.text_response(
                    "ERROR: Invalid admin consent state", status_code=400
                )
            granted = query.get("admin_consent") == "True"
            state.pop("microsoftteams_admin_consent_state", None)
            state["microsoftteams_admin_consent_received"] = granted
            cache_state.put_all(state)
            if granted:
                return WebhookResponse.text_response(
                    "Admin Consent received. Please close this window."
                )
            return WebhookResponse.text_response(
                "Admin Consent declined. Please close this window and try again later.",
                status_code=400,
            )

        if query.get("error"):
            flow = authorization_flow(
                request.asset,
                str(request.asset_id),
                app.get_webhook_url(OAUTH_CALLBACK_ROUTE),
            )
            pending = flow.client.get_pending_session()
            if pending is not None:
                flow.client.complete_session(
                    pending.session_id,
                    error=query.get("error"),
                    error_description=query.get("error_description"),
                )
            error_text = query["error"]
            if query.get("error_description"):
                error_text += f" Details: {query['error_description']}"
            return WebhookResponse.text_response(
                f"Server returned Error: {error_text}", status_code=400
            )

        return oauth_callback(request)
