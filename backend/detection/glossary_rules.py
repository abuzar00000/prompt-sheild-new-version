from __future__ import annotations

import re
from typing import Any


def glossary_term_spans(text: str, terms: list[str], longest_first: bool = True) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    ordered = sorted((t for t in terms if t), key=len, reverse=longest_first)
    for term in ordered:
        try:
            pat = re.compile(re.escape(term), re.IGNORECASE)
        except re.error:
            continue
        for m in pat.finditer(text):
            spans.append(
                {
                    "start": m.start(),
                    "end": m.end(),
                    "entity_type": "GLOSSARY",
                    "source": "glossary_term",
                    "label": term[:80],
                }
            )
    return spans


def glossary_pattern_spans(text: str, patterns: list[dict[str, str]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for p in patterns:
        name = p.get("name", "PATTERN")
        raw_pat = p.get("pattern", "")
        if not raw_pat:
            continue
        try:
            pat = re.compile(raw_pat)
        except re.error:
            continue
        for m in pat.finditer(text):
            spans.append(
                {
                    "start": m.start(),
                    "end": m.end(),
                    "entity_type": str(name).upper().replace(" ", "_"),
                    "source": "glossary_regex",
                    "label": name,
                }
            )
    return spans
