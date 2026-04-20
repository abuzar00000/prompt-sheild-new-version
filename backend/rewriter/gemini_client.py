from __future__ import annotations

from typing import Any

import httpx

from backend.rewriter.prompts import ANSWER_SYSTEM, REWRITE_SYSTEM


async def rewrite_with_gemini(redacted_or_local_prompt: str, settings: dict[str, Any], api_key: str) -> str:
    """Rewrite sanitized prompt using Gemini (v1beta generateContent)."""
    gr = settings.get("gemini_rewrite") or {}
    gm = settings.get("gemini_answer") or {}
    # allow override; otherwise follow gemini_answer model
    model = str(gr.get("model") or gm.get("model") or "gemini-2.5-flash")
    base = str(gr.get("api_base") or gm.get("api_base") or "https://generativelanguage.googleapis.com/v1beta").rstrip(
        "/"
    )
    timeout = float(gr.get("timeout_seconds", gm.get("timeout_seconds", 120)))
    temperature = float(gr.get("temperature", 0.2))
    max_out = int(gr.get("max_output_tokens", 4096))
    system = str(gr.get("system_prompt") or REWRITE_SYSTEM)

    url = f"{base}/models/{model}:generateContent"
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {
                "role": "user",
                "parts": [{"text": redacted_or_local_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_out,
        },
    }

    async with httpx.AsyncClient(timeout=timeout, http2=False, trust_env=False) as client:
        r = await client.post(url, params={"key": api_key}, json=body)
        if r.status_code >= 400:
            snippet = r.text.strip()
            if len(snippet) > 600:
                snippet = snippet[:600] + "…"
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {snippet or '(no body)'}")
        data = r.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    texts: list[str] = []
    for p in parts:
        t = p.get("text")
        if isinstance(t, str):
            texts.append(t)
    out = "\n".join(texts).strip()
    if not out:
        raise RuntimeError("Gemini returned empty text")
    return out


async def answer_with_gemini(sanitized_prompt: str, settings: dict[str, Any], api_key: str) -> str:
    """Call Google AI Studio (Gemini) generateContent (v1beta)."""
    gm = settings.get("gemini_answer") or {}
    model = str(gm.get("model", "gemini-2.5-flash"))
    base = str(gm.get("api_base", "https://generativelanguage.googleapis.com/v1beta")).rstrip("/")
    timeout = float(gm.get("timeout_seconds", 120))
    temperature = float(gm.get("temperature", 0.4))
    max_out = int(gm.get("max_output_tokens", 8192))
    system = str(gm.get("system_prompt") or ANSWER_SYSTEM)

    url = f"{base}/models/{model}:generateContent"
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {
                "role": "user",
                "parts": [{"text": sanitized_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_out,
        },
    }

    async with httpx.AsyncClient(timeout=timeout, http2=False, trust_env=False) as client:
        r = await client.post(url, params={"key": api_key}, json=body)
        if r.status_code >= 400:
            snippet = r.text.strip()
            if len(snippet) > 600:
                snippet = snippet[:600] + "…"
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {snippet or '(no body)'}")
        data = r.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    texts: list[str] = []
    for p in parts:
        t = p.get("text")
        if isinstance(t, str):
            texts.append(t)
    out = "\n".join(texts).strip()
    if not out:
        raise RuntimeError("Gemini returned empty text")
    return out
