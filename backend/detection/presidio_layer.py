from __future__ import annotations

from typing import Any

_engine = None


def _analyzer():
    global _engine
    if _engine is False:
        return None
    if _engine is not None:
        return _engine
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        _engine = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    except Exception:
        _engine = False
        return None
    return _engine


def presidio_spans(text: str, enabled: bool) -> list[dict[str, Any]]:
    if not enabled or not text:
        return []
    engine = _analyzer()
    if engine is None:
        return []
    try:
        results = engine.analyze(text=text, language="en")
    except Exception:
        return []
    spans: list[dict[str, Any]] = []
    for r in results:
        spans.append(
            {
                "start": r.start,
                "end": r.end,
                "entity_type": str(r.entity_type),
                "source": "presidio",
                "label": str(r.entity_type),
                "score": float(r.score),
            }
        )
    return spans
