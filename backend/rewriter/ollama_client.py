from __future__ import annotations

import json
from typing import Any

import httpx

from backend.rewriter.prompts import REWRITE_SYSTEM


async def rewrite_with_ollama(redacted_prompt: str, settings: dict[str, Any]) -> str:
    """Call local Ollama /api/chat (non-streaming)."""
    ol = settings.get("ollama") or {}
    base = str(ol.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
    model = str(ol.get("model", "mistral-nemo:latest"))
    timeout = float(ol.get("timeout_seconds", 300))
    rw = settings.get("rewrite") or {}
    temperature = float(rw.get("temperature", 0.2))
    num_predict = int(rw.get("max_output_tokens", rw.get("max_tokens", 4096)))

    url = f"{base}/api/chat"
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": REWRITE_SYSTEM},
            {"role": "user", "content": redacted_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    async with httpx.AsyncClient(
        timeout=timeout,
        http2=False,
        trust_env=False,
    ) as client:
        r = await client.post(url, headers={"Content-Type": "application/json"}, content=json.dumps(body))
        if r.status_code >= 400:
            snippet = r.text.strip()
            if len(snippet) > 600:
                snippet = snippet[:600] + "…"
            raise RuntimeError(f"Ollama HTTP {r.status_code}: {snippet or '(no body)'}")
        data = r.json()

    msg = data.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama returned empty assistant content")
    return content.strip()
