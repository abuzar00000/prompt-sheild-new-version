from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from backend.config_loader import project_root


@dataclass
class GlossaryData:
    terms: list[str]
    patterns: list[dict[str, str]]


def load_glossary(relative_path: str | None = None) -> GlossaryData:
    root = project_root()
    path = root / (relative_path or "config/glossary.yml")
    if not path.is_file():
        return GlossaryData(terms=[], patterns=[])
    with path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    terms = [str(t).strip() for t in raw.get("terms") or [] if str(t).strip()]
    patterns = []
    for p in raw.get("patterns") or []:
        if isinstance(p, dict) and p.get("pattern") and p.get("name"):
            patterns.append({"name": str(p["name"]), "pattern": str(p["pattern"])})
    return GlossaryData(terms=terms, patterns=patterns)


def save_glossary(glossary: GlossaryData, relative_path: str | None = None) -> None:
    """Persist org glossary to YAML (local single-org use)."""
    root = project_root()
    path = root / (relative_path or "config/glossary.yml")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "terms": sorted(list(dict.fromkeys([t.strip() for t in glossary.terms if t.strip()]))),
        "patterns": glossary.patterns,
    }
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def embedding_phrases(glossary: GlossaryData, min_len: int = 3) -> list[str]:
    """Phrases used for semantic similarity (skip very short / placeholder noise)."""
    out: list[str] = []
    for t in glossary.terms:
        t = t.strip()
        if len(t) >= min_len and not t.startswith("REPLACE_"):
            out.append(t)
    return out
