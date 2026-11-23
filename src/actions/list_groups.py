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


class ListGroupsOutput(ActionOutput):
    classification: str | None = OutputField(example_values=["classification"])
    createdDateTime: str | None = OutputField(example_values=["2018-01-30T09:43:13Z"])
    deletedDateTime: str | None = OutputField(example_values=["2018-01-30T09:43:13Z"])
    description: str | None = OutputField(example_values=["team2"])
    displayName: str | None = OutputField(example_values=["team2"])
    uniqueName: str | None
    expirationDateTime: str | None
    groupTypes: str | None = OutputField(example_values=["DynamicMembership"])
    id: str | None = OutputField(
        cef_types=["ms teams group id"],
        example_values=["594101ba-1fde-482d-8e24-3bbab23a3ca8"],
    )
    isAssignableToRole: bool | None
    mail: str | None = OutputField(
        cef_types=["email"], example_values=["team2@test.com"]
    )
    mailEnabled: bool | None
    mailNickname: str | None = OutputField(example_values=["team2"])
    membershipRule: str | None = OutputField(
        example_values=['user.department -eq "Marketing"']
    )
    membershipRuleProcessingState: str | None = OutputField(example_values=["on"])
    onPremisesDomainName: str | None
    onPremisesLastSyncDateTime: str | None = OutputField(
        example_values=["2018-01-30T09:43:13Z"]
    )
    onPremisesNetBiosName: str | None
    onPremisesProvisioningErrors: str | None
    onPremisesSamAccountName: str | None
    onPremisesSecurityIdentifier: str | None
    onPremisesSyncEnabled: bool | None
    preferredDataLocation: str | None
    preferredLanguage: str | None
    proxyAddresses: str | None = OutputField(example_values=["SMTP : team2@test.com"])
    renewedDateTime: str | None = OutputField(example_values=["2018-01-30T09:43:13Z"])
    resourceBehaviorOptions: str | None
    resourceProvisioningOptions: str | None
    securityEnabled: bool | None
    securityIdentifier: str | None = OutputField(
        example_values=["S-2-22-2-123456789-1234567890-123456789-1234567890"]
    )
    theme: str | None
    visibility: str | None = OutputField(example_values=["Private"])


class ListGroupsSummary(ActionOutput):
    total_groups: int


def list_groups(
    params: Params, soar: SOARClient, asset: Asset
) -> list[ListGroupsOutput]:
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        token = oauth_client.get_valid_token(auto_refresh=True)
        auth = StaticTokenAuth(token)
        groups: list[dict] = []
        endpoint = "/groups"
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
                groups.extend(page.get("value", []))
                endpoint = page.get("@odata.nextLink")
                if not endpoint:
                    break
            else:
                return ActionResult(
                    False,
                    "Microsoft Graph pagination exceeded the 1000-page limit",
                    params.model_dump(by_alias=True),
                )
        soar.set_summary(ListGroupsSummary(total_groups=len(groups)))
        return [ListGroupsOutput(**group) for group in groups]
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
