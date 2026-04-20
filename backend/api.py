from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config_loader import load_yaml_settings, merged_settings, project_root
from backend.pipeline import run_pipeline
from backend.glossary import GlossaryData, load_glossary, save_glossary

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    merged_settings()
    yield


def _app_meta() -> dict[str, Any]:
    data = load_yaml_settings()
    api = data.get("api") or {}
    return {"title": api.get("title", "Prompt Shield"), "version": api.get("version", "0.1.0")}


meta = _app_meta()
app = FastAPI(title=meta["title"], version=str(meta["version"]), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SanitizeRequest(BaseModel):
    prompt: str = Field(..., min_length=0, description="Raw English prompt from the user.")
    skip_rewrite: bool = Field(
        False,
        description="If true, skip the local/cloud rewrite step (Ollama or Grok) and keep redacted text only.",
    )
    skip_grok_answer: bool = Field(
        False,
        description="If true, skip the cloud assistant answer (Gemini or Grok, whichever is enabled).",
    )


class EntityOut(BaseModel):
    placeholder: str
    entity_type: str
    source: str
    label: str | None = None


class SanitizeResponse(BaseModel):
    final_prompt: str
    redacted_prompt: str
    prompt_after_ollama: str = Field("", description="Prompt after local rewrite (Ollama).")
    prompt_after_gemini_rewrite: str = Field("", description="Prompt after optional Gemini rewrite.")
    assistant_answer: str = Field(
        "",
        description="Assistant reply from Gemini (or Grok if configured) using the final prompt.",
    )
    assistant_answer_rendered: str = Field(
        "",
        description="Local-only view: placeholders replaced with original sensitive terms (if enabled).",
    )
    grok_answer: str = Field(
        "",
        description="Same as assistant_answer (kept for older clients).",
    )
    entities: list[EntityOut]
    warnings: list[str]


class GlossaryResponse(BaseModel):
    terms: list[str]


class GlossaryUpdateRequest(BaseModel):
    terms: list[str] = Field(default_factory=list, description="One sensitive term per item.")


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/sanitize", response_model=SanitizeResponse)
async def sanitize(body: SanitizeRequest):
    result = await run_pipeline(
        body.prompt,
        skip_rewrite=body.skip_rewrite,
        skip_grok_answer=body.skip_grok_answer,
    )
    aa = result.get("assistant_answer", "") or result.get("grok_answer", "")
    return SanitizeResponse(
        final_prompt=result["final_prompt"],
        redacted_prompt=result["redacted_prompt"],
        prompt_after_ollama=result.get("prompt_after_ollama", ""),
        prompt_after_gemini_rewrite=result.get("prompt_after_gemini_rewrite", ""),
        assistant_answer=aa,
        assistant_answer_rendered=result.get("assistant_answer_rendered", ""),
        grok_answer=aa,
        entities=[EntityOut(**e) for e in result["entities"]],
        warnings=result["warnings"],
    )


@app.get("/config/glossary", response_model=GlossaryResponse)
async def get_glossary():
    s = merged_settings()
    paths = s.get("paths") or {}
    g = load_glossary(paths.get("glossary", "config/glossary.yml"))
    return GlossaryResponse(terms=g.terms)


@app.put("/config/glossary", response_model=GlossaryResponse)
async def put_glossary(body: GlossaryUpdateRequest):
    s = merged_settings()
    paths = s.get("paths") or {}
    gpath = paths.get("glossary", "config/glossary.yml")
    existing = load_glossary(gpath)
    updated = GlossaryData(terms=body.terms, patterns=existing.patterns)
    save_glossary(updated, gpath)
    return GlossaryResponse(terms=updated.terms)


_frontend_dir = project_root() / "frontend"
if _frontend_dir.is_dir():
    app.mount(
        "/ui",
        StaticFiles(directory=str(_frontend_dir), html=True),
        name="ui",
    )
