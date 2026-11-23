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
from soar_sdk.abstract import SOARClient
from soar_sdk.app import App

from .actions import register_actions
from .asset import Asset
from .test_connectivity import run_test_connectivity
from .webhooks import OAUTH_CALLBACK_ROUTE, OAUTH_START_ROUTE, register_webhooks


def create_microsoftteams_app() -> App:
    app = App(
        name="microsoftteams",
        app_type="information",
        logo="logo_microsoftteams.svg",
        logo_dark="logo_microsoftteams_dark.svg",
        product_vendor="Microsoft",
        product_name="Teams",
        publisher="Splunk",
        appid="6ba1906f-5899-44df-bb65-1bee4df8ca3c",
        fips_compliant=True,
        encrypt_cache_state=True,
        encrypt_ingest_state=True,
        asset_cls=Asset,
    )

    register_webhooks(app)

    @app.test_connectivity()
    def test_connectivity(soar: SOARClient, asset: Asset) -> None:
        run_test_connectivity(
            soar,
            asset,
            app.get_webhook_url(OAUTH_CALLBACK_ROUTE),
            app.get_webhook_url(OAUTH_START_ROUTE),
        )

    return register_actions(app)


app: App = create_microsoftteams_app()


if __name__ == "__main__":
    app.cli()
