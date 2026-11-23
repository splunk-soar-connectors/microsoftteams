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
import httpx
from soar_sdk.auth import StaticTokenAuth
from ._graph import graph_request_error, graph_token_rejected, graph_url
from ..auth import oauth_token_client, validate_oauth_configuration
from soar_sdk.action_results import ActionOutput, ActionResult, OutputField
from soar_sdk.params import Params
from ..asset import Asset


class WritebackconfigurationOutput(ActionOutput):
    isEnabled: str | None
    onPremisesGroupType: str | None


class ListTeamsOutput(ActionOutput):
    classification: str | None
    createdByAppId: str | None
    createdDateTime: str | None = OutputField(example_values=["2018-02-05T21:42:33Z"])
    deletedDateTime: str | None
    description: str | None = OutputField(example_values=["TeamOne"])
    displayName: str | None = OutputField(example_values=["TeamOne"])
    expirationDateTime: str | None
    groupTypes: list[str] | None = OutputField(example_values=["Unified"])
    id: str | None = OutputField(
        cef_types=["ms teams group id"],
        example_values=["a84b973e-ad51-4248-9a3e-df054415f026"],
    )
    isAssignableToRole: str | None
    isManagementRestricted: str | None
    mail: str | None = OutputField(
        cef_types=["email"], example_values=["test@test.com"]
    )
    mailEnabled: bool | None
    mailNickname: str | None = OutputField(example_values=["TeamOne"])
    membershipRule: str | None
    membershipRuleProcessingState: str | None
    onPremisesDomainName: str | None = OutputField(cef_types=["domain"])
    onPremisesLastSyncDateTime: str | None
    onPremisesNetBiosName: str | None
    onPremisesSamAccountName: str | None
    onPremisesSecurityIdentifier: str | None
    onPremisesSyncEnabled: str | None
    preferredDataLocation: str | None
    preferredLanguage: str | None
    proxyAddresses: list[str] | None = OutputField(
        example_values=[
            "SPO:SPO_2e56f4be-737f-418d-8dee-7d01911b91df@SPO_a417c578-c7ee-480d-a225-d48057e74df5"
        ]
    )
    renewedDateTime: str | None = OutputField(example_values=["2018-02-05T21:42:33Z"])
    resourceProvisioningOptions: list[str] | None = OutputField(example_values=["Team"])
    securityEnabled: bool | None
    securityIdentifier: str | None = OutputField(
        example_values=["S-1-12-1-2823526206-1112059217-98516634-653268292"]
    )
    theme: str | None
    visibility: str | None = OutputField(example_values=["Public"])
    writebackConfiguration: WritebackconfigurationOutput | None


class ListTeamsSummary(ActionOutput):
    total_teams: int


def list_teams(params: Params, soar: SOARClient, asset: Asset) -> list[ListTeamsOutput]:
    endpoint = "/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')"
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        token = oauth_client.get_valid_token(auto_refresh=True)
        auth = StaticTokenAuth(token)
        teams: list[dict] = []
        seen_endpoints: set[str] = set()
        with httpx.Client(
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            verify=True,
        ) as client:
            for _ in range(1000):
                if endpoint in seen_endpoints:
                    return ActionResult(
                        False,
                        "Microsoft Graph returned a non-progressing nextLink",
                        params.model_dump(by_alias=True),
                    )
                seen_endpoints.add(endpoint)
                response = client.get(graph_url(endpoint), auth=auth)
                if graph_token_rejected(response):
                    stored_token = oauth_client.get_stored_token()
                    if stored_token is not None and stored_token.refresh_token:
                        auth = StaticTokenAuth(
                            oauth_client.refresh_token(stored_token.refresh_token)
                        )
                        response = client.get(graph_url(endpoint), auth=auth)
                response.raise_for_status()
                page = response.json()
                teams.extend(page.get("value", []))
                endpoint = page.get("@odata.nextLink")
                if not endpoint:
                    break
            else:
                return ActionResult(
                    False,
                    "Microsoft Graph pagination exceeded the 1000-page limit",
                    params.model_dump(by_alias=True),
                )
        soar.set_summary(ListTeamsSummary(total_teams=len(teams)))
        return [ListTeamsOutput(**team) for team in teams]
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
