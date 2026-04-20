from __future__ import annotations

import json
from typing import Any

import httpx

from backend.rewriter.prompts import ANSWER_SYSTEM, REWRITE_SYSTEM


def _extract_responses_api_text(data: dict[str, Any]) -> str:
    """Parse xAI /v1/responses body: output[].content[] output_text blocks."""
    parts: list[str] = []
    for item in data.get("output") or []:
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for block in item.get("content") or []:
            if block.get("type") == "output_text":
                t = block.get("text")
                if isinstance(t, str) and t:
                    parts.append(t)
    return "\n".join(parts).strip()


def _extract_chat_completions_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Grok returned no choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError("Unexpected Grok chat completions response shape")
    return content.strip()


async def _grok_complete(
    messages: list[dict[str, str]],
    settings: dict[str, Any],
    api_key: str,
    *,
    model: str,
    temperature: float,
    max_out: int,
) -> str:
    grok = settings.get("grok") or {}
    base_url = str(grok.get("base_url", "https://api.x.ai/v1")).rstrip("/")
    api = str(grok.get("api", "responses")).lower().strip()
    store = grok.get("store")
    if store is None:
        store = False
    timeout = float(grok.get("timeout_seconds", 120))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if api in ("responses", "response", "v1/responses"):
        url = f"{base_url}/responses"
        body: dict[str, Any] = {
            "model": model,
            "input": messages,
            "temperature": temperature,
            "max_output_tokens": max_out,
        }
        if store is not None:
            body["store"] = bool(store)
    elif api in ("chat", "chat_completions", "completions"):
        url = f"{base_url}/chat/completions"
        body = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_out,
            "messages": messages,
        }
    else:
        raise ValueError(f"Unknown grok.api: {api!r} (use 'responses' or 'chat_completions')")

    async with httpx.AsyncClient(
        timeout=timeout,
        http2=False,
        trust_env=False,
    ) as client:
        r = await client.post(url, headers=headers, content=json.dumps(body))
        if r.status_code >= 400:
            snippet = r.text.strip()
            if len(snippet) > 600:
                snippet = snippet[:600] + "…"
            raise RuntimeError(f"Grok HTTP {r.status_code}: {snippet or '(no body)'}")
        data = r.json()

    if api in ("responses", "response", "v1/responses"):
        text = _extract_responses_api_text(data)
        if not text:
            raise RuntimeError("Grok responses API returned no assistant output_text")
        return text
    return _extract_chat_completions_text(data)


async def rewrite_with_grok(
    redacted_prompt: str,
    settings: dict[str, Any],
    api_key: str,
) -> str:
    grok = settings.get("grok") or {}
    model = str(grok.get("model", "grok-4.20-reasoning"))
    rw = settings.get("rewrite") or {}
    temperature = float(rw.get("temperature", 0.2))
    max_out = int(rw.get("max_output_tokens", rw.get("max_tokens", 8192)))
    return await _grok_complete(
        [
            {"role": "system", "content": REWRITE_SYSTEM},
            {"role": "user", "content": redacted_prompt},
        ],
        settings,
        api_key,
        model=model,
        temperature=temperature,
        max_out=max_out,
    )


async def answer_with_grok(
    sanitized_prompt: str,
    settings: dict[str, Any],
    api_key: str,
) -> str:
    """Full LLM answer: send the polished (placeholder) prompt to Grok and return the assistant reply."""
    ga = settings.get("grok_answer") or {}
    grok = settings.get("grok") or {}
    system = str(ga.get("system_prompt") or ANSWER_SYSTEM)
    model_override = ga.get("model")
    model = str(model_override) if model_override else str(grok.get("model", "grok-4.20-reasoning"))
    temperature = float(ga.get("temperature", 0.4))
    max_out = int(ga.get("max_output_tokens", 8192))
    return await _grok_complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": sanitized_prompt},
        ],
        settings,
        api_key,
        model=model,
        temperature=temperature,
        max_out=max_out,
    )
