from __future__ import annotations

import re


def sentence_spans(text: str) -> list[tuple[int, int, str]]:
    """
    English-oriented sentence boundaries (lightweight, no external NLP).
    Returns (char_start, char_end, sentence_text) with ends exclusive.
    """
    if not text:
        return []
    spans: list[tuple[int, int, str]] = []
    start = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ".!?" and (i + 1 == n or text[i + 1].isspace()):
            end = i + 1
            while end < n and text[end].isspace():
                end += 1
            raw = text[start:end]
            s = raw.strip()
            if s:
                lead = len(raw) - len(raw.lstrip())
                abs_start = start + lead
                abs_end = abs_start + len(s)
                spans.append((abs_start, abs_end, s))
            start = end
            i = end
            continue
        i += 1
    if start < n:
        raw = text[start:]
        s = raw.strip()
        if s:
            lead = len(raw) - len(raw.lstrip())
            abs_start = start + lead
            spans.append((abs_start, abs_start + len(s), s))
    if not spans:
        s = text.strip()
        if s:
            lead = text.find(s)
            spans.append((lead, lead + len(s), s))
    return spans


def word_tokens(sentence: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+|[^\s]", sentence)
