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
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, unquote

import httpx

GRAPH_V1_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_BETA_BASE_URL = "https://graph.microsoft.com/beta"


def graph_url(endpoint: str) -> str:
    teams_endpoint = "/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')"
    if endpoint.startswith(teams_endpoint):
        return f"{GRAPH_BETA_BASE_URL}{endpoint}"
    if endpoint.startswith((GRAPH_V1_BASE_URL, GRAPH_BETA_BASE_URL)):
        return endpoint
    return f"{GRAPH_V1_BASE_URL}{endpoint}"


def encode_graph_path_segment(value: Any) -> str:
    raw_value = str(value)
    canonical_value = raw_value
    for _ in range(5):
        decoded_value = unquote(canonical_value)
        if decoded_value == canonical_value:
            break
        canonical_value = decoded_value
    if canonical_value in {".", ".."}:
        raise ValueError("Microsoft Graph path identifiers must not be dot segments")
    return quote(raw_value, safe="")


class _ErrorTextParser(HTMLParser):
    _IGNORED_TAGS = frozenset({"footer", "nav", "script", "style"})

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self.lines: list[str] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.lines.append(data.strip())


def graph_error_message(response: httpx.Response) -> str:
    content_type = response.headers.get("Content-Type", "").lower()
    if "json" in content_type or "text/javascript" in content_type:
        try:
            data = response.json()
        except ValueError as exc:
            return f"Unable to parse JSON response. {exc}"
        error = data.get("error", {}) if isinstance(data, dict) else {}
        message = error.get("message") if isinstance(error, dict) else None
        detail = message or response.text
        detail = detail.replace("{", "{{").replace("}", "}}")
        return (
            f"Error from server. Status Code: {response.status_code} "
            f"Data from server: {detail}"
        )

    if "html" in content_type:
        parser = _ErrorTextParser()
        try:
            parser.feed(response.text)
            error_text = "\n".join(parser.lines) or "Cannot parse error details"
        except Exception:
            error_text = "Cannot parse error details"
        return (
            f"Status Code: {response.status_code}. Data from server:\n"
            f"{error_text}\n"
        )

    if not response.content:
        return (
            ""
            if response.status_code in (200, 204)
            else f"Status code: {response.status_code}. Empty response and no information in the header"
        )

    detail = response.text.replace("{", "{{").replace("}", "}}")
    return (
        f"Can't process response from server. Status Code: {response.status_code} "
        f"Data from server: {detail}"
    )


def graph_token_rejected(response: httpx.Response) -> bool:
    if response.status_code != 401:
        return False
    try:
        error = response.json().get("error", {})
    except (ValueError, AttributeError):
        return False
    return isinstance(error, dict) and error.get("code") in {
        "InvalidAuthenticationToken",
        "ExpiredAuthenticationToken",
        "TokenExpired",
    }


def graph_request_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        message = graph_error_message(exc.response)
        return message or str(exc)
    if isinstance(exc, httpx.RequestError):
        return f"Error connecting to server. {exc}"
    return str(exc)
