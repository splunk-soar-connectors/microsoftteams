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
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.params import Param, Params
from soar_sdk.exceptions import ActionFailure
from ..asset import Asset


class AskQuestionParams(Params):
    group_id: str = Param(
        description="ID of group", primary=True, cef_types=["ms teams group id"]
    )
    channel_id: str = Param(
        description="ID of channel", primary=True, cef_types=["ms teams channel id"]
    )
    message: str = Param(description="Question text (Markdown is supported)")
    choices: str | None = Param(
        description="Comma-separated list of possible answers (leave blank for a short-answer question)"
    )


class AskQuestionOutput(ActionOutput):
    answer: str = OutputField(example_values=["Green"])
    answered_by: str = OutputField(example_values=["John Smith"])


def ask_question(
    params: AskQuestionParams, soar: SOARClient, asset: Asset
) -> AskQuestionOutput:
    raise ActionFailure(
        "The deprecated ask_question action is deferred until the SOAR SDK supports suspended runs."
    )
