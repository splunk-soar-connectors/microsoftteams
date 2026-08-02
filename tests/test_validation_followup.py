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
import unittest
import urllib.parse
from pathlib import Path


CONNECTOR = Path(__file__).resolve().parents[1] / "microsoftteams_connector.py"


def _function_source(name):
    source = CONNECTOR.read_text()
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    return ast.get_source_segment(source, function)


def _load_path_helper():
    source = CONNECTOR.read_text()
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_encode_graph_path_segment"
    )
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
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "must not be dot segments"
            ):
                helper(value)

    def test_path_helper_preserves_opaque_identifiers(self):
        self.assertEqual(
            _load_path_helper()("message/channel"), "message%2Fchannel"
        )


if __name__ == "__main__":
    unittest.main()
