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
from src.actions._graph import graph_request_error, graph_token_rejected, graph_url
from src.auth import oauth_token_client, validate_oauth_configuration
from soar_sdk.action_results import ActionOutput, ActionResult, OutputField
from soar_sdk.params import Params
from src.asset import Asset


class AssignedlicensesOutput(ActionOutput):
    disabledPlans: str | None
    skuId: str | None = OutputField(example_values=["6fd2c87f-b296-42f0-b197-1e91e994b900"])


class AssignedplansOutput(ActionOutput):
    assignedDateTime: str | None = OutputField(example_values=["2018-01-24T11:17:21Z"])
    capabilityStatus: str | None = OutputField(example_values=["Enabled"])
    service: str | None = OutputField(example_values=["exchange"])
    servicePlanId: str | None = OutputField(
        example_values=["efb87545-963c-4e0d-99df-69c6916d9eb0"]
    )


class ProvisionedplansOutput(ActionOutput):
    capabilityStatus: str | None = OutputField(example_values=["Enabled"])
    provisioningStatus: str | None = OutputField(example_values=["Success"])
    service: str | None = OutputField(example_values=["exchange"])


class ListUsersOutput(ActionOutput):
    accountEnabled: bool | None
    assignedLicenses: list[AssignedlicensesOutput] | None
    assignedPlans: list[AssignedplansOutput] | None
    businessPhones: str | None = OutputField(example_values=["22211156"])
    city: str | None
    companyName: str | None
    country: str | None = OutputField(example_values=["US"])
    deletedDateTime: str | None = OutputField(example_values=["2018-01-24T11:16:50Z"])
    department: str | None
    deviceKeys: str | None
    displayName: str | None = OutputField(
        cef_types=["user name"], example_values=["Test User"]
    )
    employeeId: str | None
    givenName: str | None = OutputField(cef_types=["user name"], example_values=["User"])
    id: str | None = OutputField(example_values=["a1a6d0a2-b0f6-46c1-b49e-98a9ddabac09"])
    imAddresses: str | None = OutputField(cef_types=["email"], example_values=["test@abc.com"])
    jobTitle: str | None
    legalAgeGroupClassification: str | None
    mail: str | None = OutputField(cef_types=["email"], example_values=["test.user@abc.com"])
    mailNickname: str | None = OutputField(cef_types=["user name"], example_values=["User"])
    mobilePhone: str | None
    officeLocation: str | None
    onPremisesDomainName: str | None = OutputField(cef_types=["domain"])
    onPremisesExtensionAttributes: str | None
    onPremisesImmutableId: str | None
    onPremisesLastSyncDateTime: str | None = OutputField(
        example_values=["2018-01-24T11:16:50Z"]
    )
    onPremisesProvisioningErrors: str | None
    onPremisesSamAccountName: str | None
    onPremisesSecurityIdentifier: str | None
    onPremisesSyncEnabled: str | None
    onPremisesUserPrincipalName: str | None
    passwordPolicies: str | None
    passwordProfile: str | None
    postalCode: str | None
    preferredDataLocation: str | None
    preferredLanguage: str | None = OutputField(example_values=["en"])
    provisionedPlans: list[ProvisionedplansOutput] | None
    proxyAddresses: str | None = OutputField(example_values=["SMTP:test@abc.com"])
    refreshTokensValidFromDateTime: str | None = OutputField(
        example_values=["2018-01-24T11:16:50Z"]
    )
    showInAddressList: str | None
    state: str | None
    streetAddress: str | None
    surname: str | None = OutputField(example_values=["User"])
    usageLocation: str | None = OutputField(example_values=["US"])
    userPrincipalName: str | None = OutputField(
        cef_types=["email"], example_values=["test.user@abc.com"]
    )
    userType: str | None = OutputField(example_values=["Member"])


class ListUsersSummary(ActionOutput):
    total_users: int


def list_users(
    params: Params, soar: SOARClient, asset: Asset
) -> list[ListUsersOutput]:
    try:
        validate_oauth_configuration(asset)
        oauth_client = oauth_token_client(asset)
        token = oauth_client.get_valid_token(auto_refresh=True)
        auth = StaticTokenAuth(token)
        users: list[dict] = []
        endpoint = "/users"
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
                users.extend(page.get("value", []))
                endpoint = page.get("@odata.nextLink")
                if not endpoint:
                    break
            else:
                return ActionResult(
                    False,
                    "Microsoft Graph pagination exceeded the 1000-page limit",
                    params.model_dump(by_alias=True),
                )
        soar.set_summary(ListUsersSummary(total_users=len(users)))
        return [ListUsersOutput(**user) for user in users]
    except Exception as exc:
        return ActionResult(
            False, graph_request_error(exc), params.model_dump(by_alias=True)
        )
