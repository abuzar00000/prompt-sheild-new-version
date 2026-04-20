from __future__ import annotations

import re
import unicodedata
from typing import Any

from backend.anonymizer.placeholders import anonymize, list_placeholders_in_text
from backend.config_loader import merged_settings
from backend.detection.builtin_patterns import builtin_pattern_spans
from backend.detection.embedding_matcher import embedding_hits
from backend.detection.glossary_rules import glossary_pattern_spans, glossary_term_spans
from backend.detection.presidio_layer import presidio_spans
from backend.glossary import embedding_phrases, load_glossary
from backend.rewriter.gemini_client import answer_with_gemini, rewrite_with_gemini
from backend.rewriter.grok_client import answer_with_grok, rewrite_with_grok
from backend.rewriter.ollama_client import rewrite_with_ollama


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _collect_spans(text: str, settings: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    det = settings.get("detection") or {}
    paths = settings.get("paths") or {}
    glossary_path = paths.get("glossary", "config/glossary.yml")
    glossary = load_glossary(glossary_path)

    spans: list[dict[str, Any]] = []
    longest_first = bool(det.get("glossary_longest_first", True))

    spans.extend(glossary_term_spans(text, glossary.terms, longest_first=longest_first))
    spans.extend(glossary_pattern_spans(text, glossary.patterns))

    if bool(det.get("builtin_patterns_enabled", True)):
        spans.extend(builtin_pattern_spans(text))

    presidio_on = bool(det.get("presidio_enabled", True))
    spans.extend(presidio_spans(text, presidio_on))

    embed_on = bool(det.get("embedding_enabled", True))
    if embed_on:
        emb = settings.get("embedding") or {}
        phrases = embedding_phrases(glossary)
        if phrases:
            model_name = str(emb.get("model", "sentence-transformers/all-MiniLM-L6-v2"))
            threshold = float(emb.get("similarity_threshold", 0.72))
            batch = int(emb.get("batch_size", 32))
            full_sent = bool(det.get("embedding_replace_full_sentence", True))
            try:
                spans.extend(
                    embedding_hits(
                        text,
                        phrases,
                        model_name=model_name,
                        threshold=threshold,
                        batch_size=batch,
                        replace_full_sentence_if_no_literal=full_sent,
                    )
                )
            except Exception as e:
                warnings.append(
                    f"Embedding matcher failed ({type(e).__name__}); upgrade PyTorch if needed or add terms to glossary."
                )

    return spans, warnings


def _placeholder_guard(redacted: str, final: str) -> list[str]:
    need = set(list_placeholders_in_text(redacted))
    have = set(list_placeholders_in_text(final))
    missing = sorted(need - have)
    if missing:
        return [f"Rewriter dropped placeholders: {', '.join(missing)}; review output."]
    return []


def _reinsert_placeholders(text: str, placeholder_map: dict[str, str]) -> str:
    """Replace placeholders like [PERSON_1] with original text (local-only)."""
    if not text or not placeholder_map:
        return text

    def repl(m):
        tok = m.group(0)
        return placeholder_map.get(tok, tok)

    return re.sub(r"\[[A-Z0-9_]+_\d+\]", repl, text)


async def run_pipeline(
    prompt: str,
    *,
    skip_rewrite: bool = False,
    skip_grok_answer: bool = False,
) -> dict[str, Any]:
    settings = merged_settings()
    text = _normalize_text(prompt)
    warnings: list[str] = []

    if not text:
        return {
            "final_prompt": "",
            "redacted_prompt": "",
            "assistant_answer": "",
            "grok_answer": "",
            "entities": [],
            "warnings": ["Empty prompt."],
        }

    spans, det_warnings = _collect_spans(text, settings)
    warnings.extend(det_warnings)

    redacted, entities = anonymize(text, spans)
    placeholder_map = {e["placeholder"]: (e.get("original_text") or "") for e in entities if e.get("original_text")}

    # Stage 1: local rewrite (default: Ollama) on redacted text
    final = redacted
    rw = settings.get("rewrite") or {}
    provider = str(rw.get("provider", "ollama")).lower().strip()

    if not skip_rewrite:
        if provider == "ollama":
            try:
                final = await rewrite_with_ollama(redacted, settings)
                warnings.extend(_placeholder_guard(redacted, final))
            except Exception as e:
                warnings.append(
                    f"Ollama rewrite failed ({type(e).__name__}: {str(e)[:240]}). Returning redacted prompt."
                )
                final = redacted
        elif provider == "grok":
            api_key = settings.get("_grok_api_key")
            if not api_key:
                warnings.append("GROK_API_KEY not set; returning redacted prompt without Grok rewrite.")
                final = redacted
            else:
                try:
                    final = await rewrite_with_grok(redacted, settings, api_key)
                    warnings.extend(_placeholder_guard(redacted, final))
                except Exception as e:
                    warnings.append(
                        f"Grok rewrite failed ({type(e).__name__}: {str(e)[:220]}); returning redacted prompt."
                    )
                    final = redacted
        else:
            warnings.append(f"Unknown rewrite.provider {provider!r} (use ollama or grok); returning redacted prompt.")
            final = redacted
    else:
        warnings.append("Rewrite skipped by request.")

    prompt_after_ollama = final
    prompt_after_gemini_rewrite = ""

    # Stage 2: optional Gemini rewrite (then Gemini answer will use this rewritten prompt)
    gr = settings.get("gemini_rewrite") or {}
    if bool(gr.get("enabled", False)):
        gkey = (settings.get("_google_api_key") or "").strip()
        if not gkey:
            warnings.append("Gemini rewrite is enabled but GOOGLE_API_KEY (or GEMINI_API_KEY) is not set.")
        elif not prompt_after_ollama.strip():
            warnings.append("Nothing to send to Gemini rewrite (empty prompt).")
        else:
            try:
                prompt_after_gemini_rewrite = await rewrite_with_gemini(prompt_after_ollama, settings, gkey)
                warnings.extend(_placeholder_guard(prompt_after_ollama, prompt_after_gemini_rewrite))
                final = prompt_after_gemini_rewrite
            except Exception as e:
                warnings.append(f"Gemini rewrite failed ({type(e).__name__}: {str(e)[:220]}). Using Ollama prompt.")
                final = prompt_after_ollama

    assistant_answer = ""
    gm = settings.get("gemini_answer") or {}
    ga = settings.get("grok_answer") or {}

    if bool(gm.get("enabled", False)):
        if skip_grok_answer:
            warnings.append("Cloud assistant answer skipped by request.")
        else:
            gkey = (settings.get("_google_api_key") or "").strip()
            if not gkey:
                warnings.append("Gemini answer is enabled but GOOGLE_API_KEY (or GEMINI_API_KEY) is not set.")
            elif not final.strip():
                warnings.append("Nothing to send to Gemini (empty final prompt).")
            else:
                try:
                    assistant_answer = await answer_with_gemini(final, settings, gkey)
                except Exception as e:
                    warnings.append(f"Gemini answer failed ({type(e).__name__}: {str(e)[:220]}).")
    elif bool(ga.get("enabled", False)):
        if skip_grok_answer:
            warnings.append("Cloud assistant answer skipped by request.")
        else:
            api_key = settings.get("_grok_api_key")
            if not api_key:
                warnings.append("Grok answer is enabled but GROK_API_KEY is not set.")
            elif not final.strip():
                warnings.append("Nothing to send to Grok (empty final prompt).")
            else:
                try:
                    assistant_answer = await answer_with_grok(final, settings, api_key)
                except Exception as e:
                    warnings.append(f"Grok answer failed ({type(e).__name__}: {str(e)[:220]}).")

    out_entities = [
        {
            "placeholder": e["placeholder"],
            "entity_type": e["entity_type"],
            "source": e["source"],
            "label": e.get("label"),
        }
        for e in entities
    ]

    return {
        "final_prompt": final,
        "redacted_prompt": redacted,
        "prompt_after_ollama": prompt_after_ollama,
        "prompt_after_gemini_rewrite": prompt_after_gemini_rewrite,
        "assistant_answer": assistant_answer,
        # If enabled, always return a rendered view (it may be identical if no placeholders were used in the answer).
        "assistant_answer_rendered": (
            _reinsert_placeholders(assistant_answer, placeholder_map)
            if bool((settings.get("reinsert") or {}).get("enabled", False))
            else ""
        ),
        "grok_answer": assistant_answer,
        "entities": out_entities,
        "warnings": warnings,
    }
