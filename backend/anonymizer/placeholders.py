from __future__ import annotations

import re
from typing import Any


def merge_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Greedy: prefer longer spans; drop overlapping shorter ones."""

    def overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
        return a["start"] < b["end"] and b["start"] < a["end"]

    ordered = sorted(spans, key=lambda s: (s["end"] - s["start"]), reverse=True)
    picked: list[dict[str, Any]] = []
    for s in ordered:
        if any(overlaps(s, p) for p in picked):
            continue
        picked.append(s)
    return sorted(picked, key=lambda s: s["start"])


def anonymize(text: str, spans: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """
    Replace spans with [ENTITYTYPE_N] placeholders (stable order by start offset).
    Returns redacted text and entity records for the API.
    """
    merged = merge_spans(spans)
    merged.sort(key=lambda x: x["start"])
    counters: dict[str, int] = {}
    records: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    for s in merged:
        et = str(s.get("entity_type", "ENTITY"))
        safe_et = re.sub(r"[^A-Z0-9_]+", "_", et.upper()).strip("_") or "ENTITY"
        counters[safe_et] = counters.get(safe_et, 0) + 1
        ph = f"[{safe_et}_{counters[safe_et]}]"
        original_text = text[s["start"] : s["end"]]
        rec = {
            "placeholder": ph,
            "entity_type": safe_et,
            "source": str(s.get("source", "")),
            "label": s.get("label"),
            "start": s["start"],
            "end": s["end"],
            "original_text": original_text,
        }
        records.append(rec)
        segments.append({**s, "placeholder": ph})
    out = text
    for seg in sorted(segments, key=lambda x: x["start"], reverse=True):
        out = out[: seg["start"]] + seg["placeholder"] + out[seg["end"] :]
    return out, records


def list_placeholders_in_text(text: str) -> list[str]:
    return re.findall(r"\[[A-Z0-9_]+_\d+\]", text)
