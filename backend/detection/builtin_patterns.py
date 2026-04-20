from __future__ import annotations

import re
from typing import Any

# Dotted IPv4-like tokens (octets 0–999). Catches invalid-but-intended IPs (e.g. 192.168.402.56)
# that strict validators skip. May rarely match odd numerics; prefer over-leak for this use case.
_LENIENT_IPV4 = re.compile(
    r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    re.IGNORECASE,
)

# Military / org-style cyber unit wording (English).
_UNIT_CYBER = re.compile(
    r"\bunit\s+\d{1,4}\s+cyber\s+div(?:ision)?\b",
    re.IGNORECASE,
)
_NUM_CYBER = re.compile(
    r"\b\d{1,4}\s+cyber\s+div(?:ision)?\b",
    re.IGNORECASE,
)

# Common military ranks / titles (English). Extend as needed.
_RANK = re.compile(
    r"\b(?:pvt|private|cpl|corporal|sgt|sergeant|ssg|staff\s+sergeant|sfc|"
    r"msg|master\s+sergeant|1sg|first\s+sergeant|sgm|sergeant\s+major|"
    r"wo\d?|warrant\s+officer|"
    r"ens|ensign|lt|2lt|1lt|second\s+lieutenant|first\s+lieutenant|lieutenant|"
    r"capt|captain|maj|major|lt\s*col|lieutenant\s+colonel|col|colonel|"
    r"bg|brigadier\s+general|mg|major\s+general|lg|lieutenant\s+general|gen|general)\b",
    re.IGNORECASE,
)

# Name-introduction heuristics (captures a single token or short name sequence).
_MY_NAME_IS = re.compile(r"\bmy\s+name\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")
_I_AM = re.compile(r"\bi\s*(?:'m|am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")


def builtin_pattern_spans(text: str) -> list[dict[str, Any]]:
    """Always-on high-signal patterns (IPs Presidio misses, unit designators, ranks, intro names)."""
    spans: list[dict[str, Any]] = []

    for m in _LENIENT_IPV4.finditer(text):
        spans.append(
            {
                "start": m.start(),
                "end": m.end(),
                "entity_type": "IP_ADDRESS",
                "source": "builtin_ip_like",
                "label": "dotted_quad",
            }
        )

    for m in _UNIT_CYBER.finditer(text):
        spans.append(
            {
                "start": m.start(),
                "end": m.end(),
                "entity_type": "MILITARY_UNIT",
                "source": "builtin_unit",
                "label": "unit_cyber_div",
            }
        )

    for m in _NUM_CYBER.finditer(text):
        spans.append(
            {
                "start": m.start(),
                "end": m.end(),
                "entity_type": "MILITARY_UNIT",
                "source": "builtin_unit",
                "label": "n_cyber_div",
            }
        )

    for m in _RANK.finditer(text):
        spans.append(
            {
                "start": m.start(),
                "end": m.end(),
                "entity_type": "MILITARY_RANK",
                "source": "builtin_rank",
                "label": "rank",
            }
        )

    # These are conservative: redact name tokens introduced explicitly.
    for m in _MY_NAME_IS.finditer(text):
        name = m.group(1)
        spans.append(
            {
                "start": m.start(1),
                "end": m.start(1) + len(name),
                "entity_type": "PERSON",
                "source": "builtin_name_intro",
                "label": "my_name_is",
            }
        )
    for m in _I_AM.finditer(text):
        name = m.group(1)
        spans.append(
            {
                "start": m.start(1),
                "end": m.start(1) + len(name),
                "entity_type": "PERSON",
                "source": "builtin_name_intro",
                "label": "i_am",
            }
        )

    return spans
