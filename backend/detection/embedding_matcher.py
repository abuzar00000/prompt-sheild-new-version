from __future__ import annotations

from typing import Any

import numpy as np

from backend.detection.tokenizer import sentence_spans

_model = None


def _get_model(name: str):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(name)
    return _model


def _cosine_sim_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = np.linalg.norm(a, axis=1, keepdims=True) + 1e-9
    b_norm = np.linalg.norm(b, axis=1, keepdims=True) + 1e-9
    return (a @ b.T) / (a_norm @ b_norm.T)


def embedding_hits(
    text: str,
    glossary_phrases: list[str],
    model_name: str,
    threshold: float,
    batch_size: int = 32,
    replace_full_sentence_if_no_literal: bool = True,
) -> list[dict[str, Any]]:
    """
    Local embedding similarity: map sentences to glossary phrases.
    If the matched phrase appears literally (case-insensitive), redact that span;
    otherwise optionally redact the whole sentence as SENSITIVE_CONTEXT.
    """
    if not glossary_phrases or not text.strip():
        return []

    sents = sentence_spans(text)
    if not sents:
        return []

    model = _get_model(model_name)
    phrases = list(dict.fromkeys(glossary_phrases))
    enc_p = model.encode(phrases, batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False)
    sent_texts = [s[2] for s in sents]
    enc_s = model.encode(sent_texts, batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False)
    sims = _cosine_sim_matrix(enc_s, enc_p)

    spans: list[dict[str, Any]] = []
    for i, (s0, s1, sent) in enumerate(sents):
        row = sims[i]
        j = int(np.argmax(row))
        score = float(row[j])
        if score < threshold:
            continue
        term = phrases[j]
        idx = sent.lower().find(term.lower())
        if idx >= 0:
            abs_start = s0 + idx
            abs_end = abs_start + len(term)
            spans.append(
                {
                    "start": abs_start,
                    "end": abs_end,
                    "entity_type": "GLOSSARY_SEM",
                    "source": "embedding",
                    "label": term[:120],
                    "score": score,
                }
            )
        elif replace_full_sentence_if_no_literal:
            spans.append(
                {
                    "start": s0,
                    "end": s1,
                    "entity_type": "SENSITIVE_CONTEXT",
                    "source": "embedding",
                    "label": term[:120],
                    "score": score,
                }
            )
    return spans
