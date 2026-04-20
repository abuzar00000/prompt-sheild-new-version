from backend.detection.builtin_patterns import builtin_pattern_spans
from backend.detection.embedding_matcher import embedding_hits
from backend.detection.glossary_rules import glossary_pattern_spans, glossary_term_spans
from backend.detection.presidio_layer import presidio_spans
from backend.detection.tokenizer import sentence_spans

__all__ = [
    "builtin_pattern_spans",
    "embedding_hits",
    "glossary_pattern_spans",
    "glossary_term_spans",
    "presidio_spans",
    "sentence_spans",
]
