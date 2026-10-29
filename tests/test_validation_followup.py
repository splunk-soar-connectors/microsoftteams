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
import ast
import json
import types
import unittest
import urllib.parse
import uuid
from pathlib import Path


CONNECTOR = Path(__file__).resolve().parents[1] / "microsoftteams_connector.py"


def _function_source(name):
    source = CONNECTOR.read_text()
    tree = ast.parse(source)
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(source, function)


class _FakeActionResult:
    def __init__(self):
        self.status = None
        self.message = None

    def set_status(self, status, status_message=None):
        self.status = status
        self.message = status_message
        return status


def _load_build_message_payload():
    source = CONNECTOR.read_text()
    tree = ast.parse(source)
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_build_message_payload")

    fake_phantom = types.SimpleNamespace(APP_SUCCESS="success", APP_ERROR="failed")
    namespace = {"phantom": fake_phantom, "json": json, "uuid": uuid}
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
            str(CONNECTOR),
            "exec",
        ),
        namespace,
    )
    return namespace["_build_message_payload"]


def _load_path_helper():
    source = CONNECTOR.read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_encode_graph_path_segment")
    namespace = {"urllib": urllib.parse}
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
            str(CONNECTOR),
            "exec",
        ),
        namespace,
    )
    return namespace["_encode_graph_path_segment"]


class ValidationFollowupTests(unittest.TestCase):
    def test_path_helper_rejects_encoded_dot_segments(self):
        helper = _load_path_helper()
        for value in (".", "..", "%2e", "%2E%2e", "%252e%252e"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "must not be dot segments"):
                helper(value)

    def test_path_helper_preserves_opaque_identifiers(self):
        self.assertEqual(_load_path_helper()("message/channel"), "message%2Fchannel")

    def test_oauth_start_requires_the_pending_flow_nonce(self):
        source = _function_source("_handle_login_redirect")
        self.assertIn('request.GET.get("state_nonce", "")', source)
        self.assertIn("hmac.compare_digest(stored_nonce, presented_nonce)", source)
        self.assertIn('key == "admin_consent_url"', source)

    def test_user_and_admin_start_links_carry_their_flow_nonce(self):
        source = CONNECTOR.read_text()
        self.assertIn('"state_nonce": flow_nonce', source)
        self.assertIn("start_oauth?{start_query}", source)
        self.assertIn("admin_consent?{consent_query}", source)

    def test_build_message_payload_requires_message_or_adaptive_card(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()

        status, data = build_message_payload(None, action_result, None, None)

        self.assertEqual(status, "failed")
        self.assertIsNone(data)
        self.assertIn("message", action_result.message)
        self.assertIn("adaptive_card", action_result.message)

    def test_build_message_payload_with_message_only(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()

        status, data = build_message_payload(None, action_result, "hello world", None)

        self.assertEqual(status, "success")
        self.assertEqual(data, {"body": {"contentType": "html", "content": "hello world"}})

    def test_build_message_payload_rejects_invalid_adaptive_card_json(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()

        status, data = build_message_payload(None, action_result, None, "{not valid json")

        self.assertEqual(status, "failed")
        self.assertIsNone(data)
        self.assertIn("adaptive_card", action_result.message)
        self.assertIn("valid JSON", action_result.message)

    def test_build_message_payload_rejects_non_object_adaptive_card(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()

        status, data = build_message_payload(None, action_result, None, json.dumps(["not", "an", "object"]))

        self.assertEqual(status, "failed")
        self.assertIsNone(data)
        self.assertIn("adaptive_card", action_result.message)
        self.assertIn("AdaptiveCard", action_result.message)

    def test_build_message_payload_rejects_adaptive_card_missing_type(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()
        card = {"version": "1.5", "body": []}

        status, data = build_message_payload(None, action_result, None, json.dumps(card))

        self.assertEqual(status, "failed")
        self.assertIsNone(data)
        self.assertIn("adaptive_card", action_result.message)
        self.assertIn("AdaptiveCard", action_result.message)

    def test_build_message_payload_rejects_adaptive_card_wrong_type(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()
        card = {"type": "ThumbnailCard", "version": "1.5", "body": []}

        status, data = build_message_payload(None, action_result, None, json.dumps(card))

        self.assertEqual(status, "failed")
        self.assertIsNone(data)

    def test_build_message_payload_with_adaptive_card_builds_attachment(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()
        card = {"type": "AdaptiveCard", "version": "1.5", "body": []}

        status, data = build_message_payload(None, action_result, None, json.dumps(card))

        self.assertEqual(status, "success")
        self.assertEqual(len(data["attachments"]), 1)
        attachment = data["attachments"][0]
        self.assertEqual(attachment["contentType"], "application/vnd.microsoft.card.adaptive")
        self.assertEqual(json.loads(attachment["content"]), card)
        self.assertIn(f'<attachment id="{attachment["id"]}"></attachment>', data["body"]["content"])

    def test_build_message_payload_with_message_and_adaptive_card_includes_both(self):
        build_message_payload = _load_build_message_payload()
        action_result = _FakeActionResult()
        card = {"type": "AdaptiveCard"}

        status, data = build_message_payload(None, action_result, "hi there", json.dumps(card))

        self.assertEqual(status, "success")
        self.assertIn("hi there", data["body"]["content"])
        self.assertEqual(len(data["attachments"]), 1)

    def test_send_handlers_read_adaptive_card_parameter(self):
        source = CONNECTOR.read_text()
        for function_name in ("_handle_send_channel_message", "_handle_send_chat_message", "_handle_send_direct_message"):
            with self.subTest(function_name=function_name):
                function_source = _function_source(function_name)
                self.assertIn("MSTEAMS_JSON_ADAPTIVE_CARD", function_source)


if __name__ == "__main__":
    unittest.main()
