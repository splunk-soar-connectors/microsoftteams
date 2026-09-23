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
"""Exercise the real reaction methods with a fake Graph transport and SOAR result.

As in test_validation_followup, AST loading avoids the proprietary SOAR runtime.
These tests do not replace validation on a SOAR instance with a live Teams tenant.
"""

import ast
import json
import re
import unittest
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import microsoftteams_consts as consts
import microsoftteams_reactions as reactions


ROOT = Path(__file__).resolve().parents[1]


class ActionResult:
    def __init__(self, param):
        self.param = param
        self.data = []
        self.summary = {}
        self.status = 0
        self.message = ""

    def set_status(self, status, status_message=""):
        self.status, self.message = status, status_message
        return status

    def get_status(self):
        return self.status

    def get_message(self):
        return self.message

    def add_data(self, data):
        self.data.append(data)

    def update_summary(self, summary):
        self.summary.update(summary)
        return self.summary


def load_connector():
    source = ast.parse((ROOT / "microsoftteams_connector.py").read_text())
    connector = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "MicrosoftTeamConnector")
    names = {
        "_get_bounded_int",
        "_build_adaptive_card_message_payload",
        "_find_users",
        "_lookup_approver",
        "_resolve_approvers",
        "_get_signed_in_identity",
        "_resolve_one_on_one_chat_id",
        "_resolve_reaction_target",
        "_approving_reaction",
        "_seed_reactions",
        "_seeded_reactions_present",
        "_resolve_user_identity",
        "_find_answering_reaction",
        "_close_reaction_message",
        "_handle_ask_for_approval_reactions",
    }
    connector.body = [node for node in connector.body if isinstance(node, ast.FunctionDef) and node.name in names]
    connector.bases = []
    path_helper = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == "_encode_graph_path_segment")
    namespace = dict(vars(consts))
    namespace.update(vars(reactions))
    namespace.update(
        ActionResult=ActionResult,
        json=json,
        re=re,
        uuid=uuid,
        urllib=urllib.parse,
        datetime=datetime,
        timezone=timezone,
        time=SimpleNamespace(sleep=Mock()),
        phantom=SimpleNamespace(APP_SUCCESS=0, APP_ERROR=-1, is_fail=lambda status: status < 0, is_success=lambda status: status >= 0),
        get_list_from_string=lambda value: [item.strip() for item in value.split(",") if item.strip()],
        _get_error_message_from_exception=lambda exc, _: str(exc),
    )
    exec(
        compile(ast.fix_missing_locations(ast.Module(body=[path_helper, connector], type_ignores=[])), "connector-under-test", "exec"), namespace
    )
    return namespace["MicrosoftTeamConnector"], namespace["time"].sleep


Connector, sleep = load_connector()


def reaction(emoji="like", user="reviewer", at="2026-09-22T10:00:00Z"):
    return {"reactionType": emoji, "createdDateTime": at, "user": {"user": {"id": user, "displayName": user}}}


class FakeConnector(Connector):
    def __init__(self, polls=None):
        self.polls = iter(polls if polls is not None else [[]])
        self.calls = []
        self.seed = None
        self.seed_failure = False
        self.patch_failure = False
        self.reply_failure = False
        self.lookup_failure = False
        self.ambiguous = False
        self.missing_sender = False
        self.save_progress = Mock()
        self._verify_parameters = Mock(return_value=0)

    def get_action_identifier(self):
        return "ask_for_approval_reactions"

    def add_action_result(self, result):
        self.result = result
        return result

    def _update_request(self, action_result, endpoint, method="get", data=None, params=None):
        payload = json.loads(data) if data else None
        self.calls.append((method, endpoint, payload, params))
        if endpoint == "/me":
            return 0, {} if self.missing_sender else {"id": "sender", "displayName": "Automation"}
        if endpoint.startswith("/users"):
            if self.lookup_failure:
                return action_result.set_status(-1, "Directory unavailable"), None
            user = {"id": "reviewer", "displayName": "Reviewer", "userPrincipalName": "reviewer@example.com"}
            if endpoint == "/users":
                return 0, {"value": [user, dict(user, id="other")] if self.ambiguous else [user]}
            if endpoint.endswith("/sender%40example.com"):
                user["id"] = "sender"
            return 0, user
        if endpoint == "/chats":
            return 0, {"id": "direct-chat"}
        if endpoint.endswith("/setReaction"):
            if self.seed_failure:
                return action_result.set_status(-1, "Seed refused"), None
            self.seed = reaction(payload["reactionType"], "sender")
            return 0, {}
        if method == "patch":
            if self.patch_failure:
                return action_result.set_status(-1, "Edit refused"), None
            return 0, {}
        if method == "post":
            if self.reply_failure and self.patch_failure and any(call[0] == "patch" for call in self.calls):
                return action_result.set_status(-1, "Reply refused"), None
            return 0, {"id": "message/1", "webUrl": "https://teams.microsoft.com/example"}
        if method == "get" and "/messages/" in endpoint:
            poll = next(self.polls)
            if poll is None:
                return action_result.set_status(-1, "Read refused"), None
            return 0, {"reactions": ([self.seed] if self.seed else []) + poll}
        raise AssertionError(f"Unexpected request: {method} {endpoint}")

    def run(self, **overrides):
        param = {"destination": "chat", "chat_id": "chat:1", "message": "Approve isolation?", "max_checks": 1}
        param.update(overrides)
        self._handle_ask_for_approval_reactions(param)
        return self.result


class ReactionParsingTests(unittest.TestCase):
    def test_typed_names_and_unicode_are_equivalent(self):
        for value in ("thumbs_up,thumbs_down", "👍,👎", "U+1F44D,U+1F44E", ":thumbsup:,:thumbsdown:"):
            with self.subTest(value=value):
                options = reactions.parse_reactions(value)
                self.assertEqual([r["key"] for r in options], ["👍", "👎"])
                self.assertEqual([r["approves"] for r in options], [True, False])

    def test_every_documented_alias_resolves(self):
        for name, emoji in consts.MSTEAMS_REACTION_ALIASES.items():
            self.assertEqual(reactions.resolve_reaction(name), emoji)

    def test_custom_labels_flags_and_json(self):
        options = reactions.parse_reactions("cross|Block|false,checkmark|Allow|true")
        self.assertEqual([(r["emoji"], r["label"], r["approves"]) for r in options], [("❌", "Block", False), ("✅", "Allow", True)])
        self.assertEqual(reactions.parse_reactions('[{"emoji":"rocket","label":"Go","approves":true}]')[0]["emoji"], "🚀")

    def test_unicode_sequences_and_skin_tones(self):
        self.assertEqual(reactions.resolve_reaction("u+2764 U+FE0F"), "❤️")
        self.assertEqual(reactions.normalize_reaction("👍🏽"), reactions.normalize_reaction("like"))
        self.assertEqual(reactions.normalize_reaction("❤"), reactions.normalize_reaction("heart"))
        self.assertEqual(reactions.resolve_reaction("U+1F469 U+200D U+1F4BB"), "👩‍💻")

    def test_rejects_typos_malformed_unicode_duplicates_and_invalid_flags(self):
        for value in (
            "thums_up,thumbs_down",
            "U+110000,cross",
            "U+D800,cross",
            "U+XYZ,cross",
            "U+0041,cross",
            "thumbs_up,like",
            "👍,👍🏽",
            "check|Go|maybe,cross",
            "check,",
            '{"emoji":"like"}',
            "[null]",
            "[broken",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                reactions.parse_reactions(value)

    def test_closed_card_removes_prompt_and_preserves_original(self):
        card = reactions.create_reaction_approval_card("Request", "Isolate?", "Host: test", reactions.parse_reactions("like,dislike"), [])
        closed = reactions.finalize_reaction_card(card, reactions.reaction_expired_blocks(1, ""))
        self.assertIn("Respond by reacting", json.dumps(card))
        self.assertNotIn("Respond by reacting", json.dumps(closed))
        self.assertIn("expired", json.dumps(closed))
        self.assertIn("test", json.dumps(closed))


class ReactionActionTests(unittest.TestCase):
    def setUp(self):
        sleep.reset_mock()

    def test_approve_and_deny_return_decisions(self):
        for emoji, approved in (("👍🏽", True), ("👎", False)):
            with self.subTest(emoji=emoji):
                result = FakeConnector([[reaction(emoji)]]).run()
                self.assertEqual(result.status, 0)
                self.assertEqual(result.data[0]["approved"], approved)
                self.assertFalse(result.data[0]["timed_out"])
                self.assertEqual(result.data[0]["answered_by_aad_id"], "reviewer")
                self.assertTrue(result.data[0]["card_updated"])

    def test_seed_cannot_approve_and_timeout_is_bounded(self):
        connector = FakeConnector([[], [], []])
        result = connector.run(max_checks=3, check_interval_seconds=5)
        self.assertEqual(result.status, -1)
        self.assertTrue(result.data[0]["timed_out"])
        self.assertFalse(result.data[0]["approved"])
        self.assertEqual(result.data[0]["checks_performed"], 3)
        self.assertEqual(result.data[0]["seeded_reactions"], ["👍"])
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(5)
        self.assertIn("expired", json.dumps([call[2] for call in connector.calls if call[0] == "patch"]))

    def test_one_check_never_sleeps(self):
        FakeConnector().run()
        sleep.assert_not_called()

    def test_unauthorized_reaction_is_ignored_and_deduplicated(self):
        bad = reaction(user="outsider")
        result = FakeConnector([[bad], [bad, reaction("👎")]]).run(approvers="reviewer@example.com", max_checks=2, check_interval_seconds=5)
        self.assertEqual(result.status, 0)
        self.assertFalse(result.data[0]["approved"])
        self.assertEqual(len(result.data[0]["ignored_reactions"]), 1)
        self.assertEqual(result.data[0]["ignored_reactions"][0]["reacted_by_aad_id"], "outsider")

    def test_missing_identity_never_counts_even_without_allowlist(self):
        result = FakeConnector([[reaction(user="")]]).run()
        self.assertTrue(result.data[0]["timed_out"])

    def test_earliest_timestamp_wins_with_fractional_seconds(self):
        result = FakeConnector([[reaction("like", at="2026-09-22T10:00:00.100Z"), reaction("dislike")]]).run()
        self.assertFalse(result.data[0]["approved"])

    def test_simultaneous_conflicting_choices_prefer_denial(self):
        result = FakeConnector([[reaction("like"), reaction("dislike")]]).run()
        self.assertFalse(result.data[0]["approved"])

    def test_no_seed_mode(self):
        connector = FakeConnector([[reaction()]])
        result = connector.run(seed_reactions="none")
        self.assertEqual(result.status, 0)
        self.assertFalse(result.data[0]["seeded"])
        self.assertFalse(any(call[1].endswith("/setReaction") for call in connector.calls))

    def test_seed_failure_does_not_prevent_answer(self):
        connector = FakeConnector([[reaction()]])
        connector.seed_failure = True
        result = connector.run()
        self.assertEqual(result.status, 0)
        self.assertIn("Seed refused", result.data[0]["seed_errors"][0])

    def test_failed_edit_posts_followup_without_losing_decision(self):
        connector = FakeConnector([[reaction()]])
        connector.patch_failure = True
        result = connector.run()
        self.assertEqual(result.status, 0)
        self.assertTrue(result.data[0]["approved"])
        self.assertFalse(result.data[0]["card_updated"])
        self.assertIn("reply instead", result.data[0]["card_update_error"])

    def test_failed_edit_and_followup_keep_decision(self):
        connector = FakeConnector([[reaction()]])
        connector.patch_failure = connector.reply_failure = True
        result = connector.run()
        self.assertEqual(result.status, 0)
        self.assertIn("Reply refused", result.data[0]["card_update_error"])

    def test_directory_enrichment_failure_keeps_answer(self):
        connector = FakeConnector([[reaction()]])
        connector.lookup_failure = True
        result = connector.run()
        self.assertEqual(result.status, 0)
        self.assertEqual(result.data[0]["answered_by_aad_id"], "reviewer")

    def test_first_read_failure_returns_error_with_message_id(self):
        result = FakeConnector([None]).run()
        self.assertEqual(result.status, -1)
        self.assertEqual(result.data[0]["message_id"], "message/1")
        self.assertFalse(result.data[0]["approved"])
        self.assertFalse(result.data[0]["timed_out"])
        sleep.assert_not_called()

    def test_later_read_failure_does_not_end_polling_early(self):
        result = FakeConnector([[], None, [reaction()]]).run(max_checks=3, check_interval_seconds=5)
        self.assertEqual(result.status, 0)
        self.assertEqual(result.data[0]["checks_performed"], 3)

    def test_invalid_configuration_fails_before_posting(self):
        cases = [
            dict(max_checks=0),
            dict(max_checks=1001),
            dict(max_checks=1.5),
            dict(max_checks=True),
            dict(check_interval_seconds=4),
            dict(check_interval_seconds=901),
            dict(seed_reactions="all"),
            dict(reactions="like"),
            dict(reactions="like|Yes|true,dislike|No|true"),
            dict(reactions="like|Yes|false,dislike|No|false"),
            dict(destination="invalid"),
            dict(adaptive_card="[]"),
            dict(adaptive_card="broken"),
            dict(message=""),
        ]
        for case in cases:
            with self.subTest(case=case):
                connector = FakeConnector()
                self.assertEqual(connector.run(**case).status, -1)
                self.assertFalse(any(call[0] == "post" for call in connector.calls))

    def test_unresolved_or_ambiguous_approvers_fail_before_posting(self):
        for flag in ("lookup_failure", "ambiguous"):
            connector = FakeConnector()
            setattr(connector, flag, True)
            self.assertEqual(connector.run(approvers="Reviewer").status, -1)
            self.assertFalse(any(call[0] == "post" for call in connector.calls))

    def test_sending_account_cannot_be_only_approver(self):
        connector = FakeConnector()
        self.assertEqual(connector.run(approvers="sender@example.com").status, -1)
        self.assertFalse(any(call[0] == "post" for call in connector.calls))

    def test_missing_sender_identity_fails_before_posting(self):
        connector = FakeConnector()
        connector.missing_sender = True
        self.assertEqual(connector.run().status, -1)
        self.assertFalse(any(call[0] == "post" for call in connector.calls))

    def test_channel_and_direct_message_destinations(self):
        for param, endpoint in (
            (dict(destination="channel", group_id="team/1", channel_id="channel:1"), "/teams/team%2F1/channels/channel%3A1/messages"),
            (dict(destination="direct_message", user_id="user/1"), "/chats/direct-chat/messages"),
        ):
            with self.subTest(param=param):
                connector = FakeConnector([[reaction()]])
                connector.patch_failure = True
                self.assertEqual(connector.run(**param).status, 0)
                self.assertIn(endpoint, [call[1] for call in connector.calls if call[0] == "post"])
                if param["destination"] == "channel":
                    self.assertIn(endpoint + "/message%2F1/replies", [call[1] for call in connector.calls])
                else:
                    chat_request = next(call[2] for call in connector.calls if call[1] == "/chats")
                    self.assertTrue(chat_request["members"][1]["user@odata.bind"].endswith("/users/user%2F1"))

    def test_custom_card_can_be_used_without_message(self):
        result = FakeConnector([[reaction()]]).run(message="", adaptive_card='{"type":"AdaptiveCard","version":"1.5","body":[]}')
        self.assertEqual(result.status, 0)


if __name__ == "__main__":
    unittest.main()
