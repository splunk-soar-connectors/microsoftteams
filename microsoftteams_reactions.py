# Copyright (c) 2025-2026 Splunk Inc.
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
"""Reaction approval parsing and cards; no Bot Framework callbacks are needed."""

import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Union

from microsoftteams_consts import (
    MSTEAMS_REACTION_ALIASES,
    MSTEAMS_REACTION_IGNORED_CODEPOINTS,
    MSTEAMS_REACTION_LEGEND_BLOCK_ID,
    MSTEAMS_REACTION_PROMPT_BLOCK_ID,
    MSTEAMS_REACTION_TRANSIENT_BLOCK_IDS,
)


def resolve_reaction(value) -> str:
    """Resolve a typed alias, Unicode code-point sequence, or literal emoji.

    Unknown names fail before posting instead of becoming custom Graph reactions.
    Unicode notation supports sequences, for example U+2764 U+FE0F.
    """
    text = str(value or "").strip()
    alias = MSTEAMS_REACTION_ALIASES.get(text.strip(":").strip().lower())
    if alias:
        return alias
    if text.upper().startswith("U+"):
        if not re.fullmatch(r"U\+[0-9A-Fa-f]{4,6}(?:\s+U\+[0-9A-Fa-f]{4,6})*", text, re.IGNORECASE):
            raise ValueError("Use Unicode code points such as U+1F44D or U+2764 U+FE0F")
        points = [int(part[2:], 16) for part in text.split()]
        if any(point > 0x10FFFF or 0xD800 <= point <= 0xDFFF for point in points):
            raise ValueError("Reaction contains an invalid Unicode code point")
        text = "".join(chr(point) for point in points)
    # This permits emoji sequences without adding a Unicode database dependency.
    # Graph and the Teams client ultimately determine which emoji are supported.
    if not any((ord(ch) > 127 and unicodedata.category(ch).startswith("S")) or ch == "\u20e3" for ch in text):
        raise ValueError(f"Unknown reaction '{value}'. Use a documented name, an emoji, or Unicode notation such as U+1F44D")
    return text


def normalize_reaction(value) -> str:
    """Reduce a reaction to a form that can be compared across its spellings.

    Microsoft Graph hands back `reactionType` as the emoji itself on newer
    messages but as a legacy name ("like", "heart") on the six original Teams
    reactions, and Teams clients send skin-tone and presentation variants of the
    same emoji. Comparing raw strings therefore misses answers that a person
    plainly gave, so everything is folded to one key first.
    """
    text = str(value or "").strip()
    if not text:
        return ""

    # ":thumbsup:" is how the emoji is written in most chat tools, and a
    # playbook author will reach for it before pasting an emoji into a form.
    lookup = text.strip(":").strip().lower()
    text = MSTEAMS_REACTION_ALIASES.get(lookup, text)

    return "".join(ch for ch in text if ord(ch) not in MSTEAMS_REACTION_IGNORED_CODEPOINTS)


def _coerce_reaction(raw) -> tuple[str, str, object]:
    """Read one reaction from either an object or an 'emoji|label|approves' string."""
    if isinstance(raw, dict):
        emoji = str(raw.get("emoji") or raw.get("reaction") or raw.get("reactionType") or "").strip()
        label = str(raw.get("label") or raw.get("title") or "").strip()
        return emoji, label, raw.get("approves")

    parts = [part.strip() for part in str(raw).split("|")]
    emoji = parts[0]
    label = parts[1] if len(parts) > 1 else ""
    approves = parts[2] if len(parts) > 2 else None
    return emoji, label, approves


def parse_reactions(value) -> list[dict]:
    """Parse the 'reactions' parameter into ordered answer definitions.

    Input forms, in increasing order of control::

        thumbs_up,thumbs_down
        checkmark|Approve|true,cross|Deny|false
        U+1F44D|Approve|true,U+1F44E|Deny|false
        [{"emoji": "thumbs_up", "label": "Approve", "approves": true}]

    Names work anywhere an emoji does, so "thumbs up,thumbs down" is equivalent
    to the first form. Every returned entry carries emoji, label, approves and
    the normalized key the reaction poller matches on.
    """
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        raw_items = list(value)
    else:
        text = str(value).strip()
        if not text:
            return []
        if text[0] in "[{":
            # Comma-splitting a JSON object would silently produce reactions
            # named after fragments of it, so reject anything that is not an
            # array outright rather than half-parsing it.
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                raise ValueError(f"'reactions' looks like JSON but could not be parsed: {exc}") from exc
            if not isinstance(parsed, list):
                raise ValueError("'reactions' JSON must be an array of options")
            raw_items = parsed
        else:
            raw_items = text.split(",")

    reactions = []
    seen = set()
    for raw in raw_items:
        if not isinstance(raw, (str, dict)):
            raise ValueError("Each reaction must be a name, emoji, code-point sequence, or JSON object")
        emoji, label, approves = _coerce_reaction(raw)
        if not emoji:
            raise ValueError("Reaction options cannot be empty")

        resolved = resolve_reaction(emoji)
        key = normalize_reaction(resolved)
        if not key or key in seen:
            raise ValueError(f"Reaction '{emoji}' duplicates another option (skin tones count as the same reaction)")
        seen.add(key)

        if isinstance(approves, str):
            flag = approves.strip().lower()
            if flag not in ("true", "false", "yes", "no", "1", "0"):
                raise ValueError("The approval flag must be true or false")
            approves_flag = flag in ("true", "yes", "1")
        elif approves is None:
            approves_flag = None
        elif isinstance(approves, bool):
            approves_flag = approves
        else:
            raise ValueError("The approval flag must be true or false")

        reactions.append(
            {
                # Send the resolved emoji, not whatever the caller typed: Graph
                # will store "thumbs up" verbatim as a custom reaction nobody can
                # click, whereas 👍 lands on the reaction people already use.
                "emoji": resolved,
                "label": label or str(emoji).strip(),
                "approves": approves_flag,
                "key": key,
            }
        )

    if not reactions:
        return []

    # Without explicit flags the first option approves and the rest reject.
    if all(reaction["approves"] is None for reaction in reactions):
        for index, reaction in enumerate(reactions):
            reaction["approves"] = index == 0
    else:
        for reaction in reactions:
            reaction["approves"] = bool(reaction["approves"])

    return reactions


def parse_details(details: Union[str, dict, None]) -> list[tuple[str, str]]:
    """Turn the 'details' parameter into ordered label/value pairs for a FactSet.

    Accepts a JSON object, or plain "Label: value" lines, so a playbook can feed
    this straight from a format block without building JSON.
    """
    if not details:
        return []

    if isinstance(details, dict):
        return [(str(k), str(v)) for k, v in details.items()]

    text = str(details).strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return [(str(k), str(v)) for k, v in parsed.items()]
    except (ValueError, TypeError):
        pass

    pairs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        label, separator, value = line.partition(":")
        if separator:
            pairs.append((label.strip(), value.strip()))
        else:
            pairs.append((line, ""))
    return pairs


def _approval_header_blocks(title: str, message: str, details: Union[str, dict, None]) -> list:
    blocks = [
        {
            "type": "TextBlock",
            "text": title or "Approval required",
            "wrap": True,
            "style": "heading",
            "size": "medium",
            "weight": "bolder",
        }
    ]
    if message:
        blocks.append({"type": "TextBlock", "text": message, "wrap": True})

    facts = parse_details(details)
    if facts:
        blocks.append({"type": "FactSet", "facts": [{"title": label, "value": value} for label, value in facts]})
    return blocks


def create_reaction_approval_card(
    title: str, message: str, details: Union[str, dict, None], reactions: list[dict], approvers: list[str]
) -> dict:
    """Build the default card for the reaction-based approval flow.

    Returns raw card JSON rather than a Bot Framework Attachment, because this
    card is posted over Microsoft Graph, which embeds the card body inline in
    the message. It carries no Action.Submit buttons at all: the answer is the
    emoji reaction on the message, which is what lets this flow work without an
    Azure Bot.

    'reactions' must already be through parse_reactions().
    """

    body = _approval_header_blocks(title, message, details)
    body.append(
        {
            "type": "TextBlock",
            "id": MSTEAMS_REACTION_PROMPT_BLOCK_ID,
            "text": "Respond by reacting to this message:",
            "wrap": True,
            "weight": "bolder",
            "spacing": "medium",
        }
    )
    if reactions:
        body.append(
            {
                "type": "FactSet",
                "id": MSTEAMS_REACTION_LEGEND_BLOCK_ID,
                "facts": [
                    {
                        "title": reaction["emoji"],
                        "value": "{}{}".format(reaction["label"], " (approves)" if reaction["approves"] else ""),
                    }
                    for reaction in reactions
                ],
            }
        )
    if approvers:
        body.append(
            {
                "type": "TextBlock",
                "text": "Only these people can respond: {}".format(", ".join(approvers)),
                "wrap": True,
                "isSubtle": True,
                "size": "small",
                "spacing": "medium",
            }
        )

    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": body,
    }


def reaction_decision_blocks(choice: dict, approver: dict, answered_at: str) -> list:
    """The banner that records who answered a reaction approval, and how.

    Include display name and UPN/email when the directory lookup permits it.
    """

    name, qualifier = decider_identity(approver)

    items = [
        {
            "type": "TextBlock",
            "text": "{} {} by {}".format(choice["emoji"], choice["label"], name),
            "wrap": True,
            "weight": "bolder",
            "size": "medium",
        }
    ]
    # Display names are neither unique nor stable, so the record carries a
    # verifying identifier next to the name whenever there is one to show.
    if qualifier:
        items.append({"type": "TextBlock", "text": qualifier, "wrap": True, "spacing": "none", "isSubtle": True, "size": "small"})
    items.append(
        {
            "type": "TextBlock",
            "text": f"Answered by reaction · {format_decision_time(answered_at)}",
            "wrap": True,
            "isSubtle": True,
            "size": "small",
            "spacing": "small",
        }
    )

    return [
        {
            "type": "Container",
            "style": "good" if choice["approves"] else "attention",
            "bleed": True,
            "spacing": "medium",
            "items": items,
        }
    ]


def reaction_expired_blocks(checks: int, window: str) -> list:
    """The banner that closes out an approval nobody answered."""

    detail = "Checked {} time{}{}. No eligible response was observed.".format(checks, "" if checks == 1 else "s", window)
    return [
        {
            "type": "Container",
            "style": "warning",
            "bleed": True,
            "spacing": "medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "⌛ No response — expired",
                    "wrap": True,
                    "weight": "bolder",
                    "size": "medium",
                },
                {"type": "TextBlock", "text": detail, "wrap": True, "isSubtle": True, "size": "small", "spacing": "small"},
            ],
        }
    ]


def finalize_reaction_card(card_obj: dict, blocks: list) -> dict:
    """Close a live approval card: drop the 'how to respond' prompt, add the outcome.

    Works on the built-in card and on a custom one from 'adaptive_card' alike.
    The prompt and legend are found by element id, which a custom card will not
    have, so a custom card is only ever appended to -- never edited underneath
    its author.
    """

    closed = deepcopy(card_obj) if isinstance(card_obj, dict) else {}
    body = closed.get("body")
    if not isinstance(body, list):
        body = []
    closed["body"] = [
        block for block in body if not (isinstance(block, dict) and block.get("id") in MSTEAMS_REACTION_TRANSIENT_BLOCK_IDS)
    ] + list(blocks)
    return closed


def describe_reaction_decision(choice: dict, approver: dict, answered_at: str) -> str:
    """Plain-text decision record, for the action message and the reply fallback."""

    name, qualifier = decider_identity(approver)
    who = f"{name} ({qualifier})" if qualifier else name
    return "{} {} by {} at {}.".format(choice["emoji"], choice["label"], who, format_decision_time(answered_at))


def decider_identity(submitter: dict) -> tuple[str, str]:
    """Display name and a verifying identifier for whoever reacted.

    Display names are neither unique nor stable, so the card carries the UPN
    (or email, or object ID) alongside the name: an approval record has to stay
    unambiguous when someone reads it back months later.
    """
    name = (submitter.get("name") or "").strip()
    # Only a UPN or an email says anything to a person reading the card. The
    # object ID is kept in the action results for audit either way, so it is
    # used here only when there is no better name to show at all.
    qualifier = (submitter.get("upn") or "").strip() or (submitter.get("email") or "").strip()

    if not name:
        # Teams normally sends a display name on the submit activity, but a
        # roster lookup failure in some scopes can leave us with only an ID.
        name = qualifier or (submitter.get("aad_id") or "").strip() or "an unidentified user"
    if qualifier.lower() == name.lower():
        qualifier = ""
    return name, qualifier


def format_decision_time(answered_at: str) -> str:
    """Render the decision timestamp for a human, not for a log parser."""
    try:
        parsed = datetime.fromisoformat(answered_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return answered_at or "an unknown time"

    suffix = " UTC" if parsed.utcoffset() in (None, timedelta(0)) else ""
    return f"{parsed.strftime('%d %b %Y, %H:%M')}{suffix}"
