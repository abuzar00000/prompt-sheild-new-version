const $ = (id) => document.getElementById(id);

function showToast(message) {
  const t = $("toast");
  t.textContent = message;
  t.hidden = false;
  t.classList.add("show");
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    t.classList.remove("show");
    setTimeout(() => {
      t.hidden = true;
    }, 400);
  }, 2200);
}

async function checkHealth() {
  const pill = $("health-pill");
  try {
    const r = await fetch("/health");
    if (!r.ok) throw new Error(String(r.status));
    const j = await r.json();
    pill.textContent = j.status === "ok" ? "Connected" : "Unknown";
    pill.classList.add("ok");
    pill.setAttribute("title", "API is responding");
  } catch {
    pill.textContent = "Offline";
    pill.classList.remove("ok");
    pill.setAttribute("title", "Start the server (uvicorn on port 8080)");
  }
}

function copyText(id, successMsg) {
  const el = $(id);
  if (!el?.textContent?.trim() || el.textContent.trim() === "—") return;
  navigator.clipboard.writeText(el.textContent).then(
    () => showToast(successMsg),
    () => showToast("Could not copy")
  );
}

function renderWarnings(list) {
  const box = $("warnings");
  if (!list?.length) {
    box.hidden = true;
    box.innerHTML = "";
    return;
  }
  box.hidden = false;
  box.innerHTML = `<strong>Heads up</strong><ul>${list.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul>`;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function renderEntities(rows) {
  const tbody = $("entities-table").querySelector("tbody");
  tbody.innerHTML = "";
  if (!rows?.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="3" class="empty-row">Nothing was masked — try a longer prompt or add terms in glossary.</td>`;
    tbody.appendChild(tr);
    return;
  }
  for (const e of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><code>${escapeHtml(e.placeholder)}</code></td><td>${escapeHtml(e.entity_type)}</td><td>${escapeHtml(e.source)}</td>`;
    tbody.appendChild(tr);
  }
}

function updateCharCount() {
  const ta = $("prompt");
  const n = ta.value.length;
  $("char-count").textContent = n.toLocaleString();
}

function parseTerms(text) {
  return text
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

function updateGlossaryCount() {
  const ta = $("glossary-terms");
  if (!ta) return;
  const n = parseTerms(ta.value).length;
  const el = $("glossary-count");
  if (el) el.textContent = n.toLocaleString();
}

async function loadGlossary() {
  const ta = $("glossary-terms");
  if (!ta) return;
  try {
    const r = await fetch("/config/glossary");
    if (!r.ok) return;
    const j = await r.json();
    const terms = Array.isArray(j.terms) ? j.terms : [];
    ta.value = terms.join("\n");
    updateGlossaryCount();
  } catch {
    // ignore
  }
}

async function saveGlossary() {
  const btn = $("save-glossary");
  const ta = $("glossary-terms");
  if (!btn || !ta) return;

  btn.disabled = true;
  btn.setAttribute("aria-busy", "true");
  try {
    const terms = parseTerms(ta.value);
    const r = await fetch("/config/glossary", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ terms }),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.detail ?? `HTTP ${r.status}`);
    ta.value = (j.terms || []).join("\n");
    updateGlossaryCount();
    showToast("Keywords saved");
  } catch (e) {
    showToast("Could not save keywords");
  } finally {
    btn.disabled = false;
    btn.removeAttribute("aria-busy");
  }
}

async function runSanitize() {
  const btn = $("run-btn");
  const label = btn.querySelector(".btn-label");
  const prompt = $("prompt").value;
  const skip = $("skip-rewrite").checked;
  const skipGrok = $("skip-grok-answer").checked;

  const defaultLabel = label ? label.textContent : "Clean & rewrite";
  btn.disabled = true;
  btn.setAttribute("aria-busy", "true");
  if (label) {
    label.textContent = skipGrok
      ? skip
        ? "Masking…"
        : "Masking & rewriting…"
      : skip
        ? "Masking… (then Gemini)"
        : "Masking, rewriting & Gemini…";
  }

  try {
    const r = await fetch("/sanitize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        skip_rewrite: skip,
        skip_grok_answer: skipGrok,
      }),
    });

    const data = await r.json().catch(() => ({}));

    if (!r.ok) {
      const detail = data.detail ?? JSON.stringify(data);
      throw new Error(typeof detail === "string" ? detail : `HTTP ${r.status}`);
    }

    const finalEl = $("final-out");
    const redEl = $("redacted-out");
    finalEl.textContent = data.final_prompt ?? "";
    redEl.textContent = data.redacted_prompt ?? "";
    const ol = $("ollama-out");
    const gr = $("gemini-rewrite-out");
    if (ol) ol.textContent = (data.prompt_after_ollama ?? "").trim() || "—";
    if (gr) gr.textContent = (data.prompt_after_gemini_rewrite ?? "").trim() || "—";
    const ga = $("assistant-answer-out");
    const ans = (data.assistant_answer ?? data.grok_answer ?? "").trim();
    ga.textContent = ans || "—";

    const rendered = (data.assistant_answer_rendered ?? "").trim();
    const card = $("assistant-answer-rendered-card");
    const out = $("assistant-answer-rendered-out");
    if (card && out) {
      if (rendered) {
        card.hidden = false;
        out.textContent = rendered;
      } else {
        card.hidden = true;
        out.textContent = "";
      }
    }

    renderWarnings(data.warnings ?? []);
    renderEntities(data.entities ?? []);
    $("output-section").hidden = false;

    $("output-section").scrollIntoView({ behavior: "smooth", block: "nearest" });
    showToast("Results are ready");
  } catch (e) {
    $("output-section").hidden = false;
    $("final-out").textContent = "";
    $("redacted-out").textContent = "";
    $("assistant-answer-out").textContent = "";
    const card = $("assistant-answer-rendered-card");
    const out = $("assistant-answer-rendered-out");
    if (card && out) {
      card.hidden = true;
      out.textContent = "";
    }
    const ol = $("ollama-out");
    const gr = $("gemini-rewrite-out");
    if (ol) ol.textContent = "";
    if (gr) gr.textContent = "";
    renderEntities([]);
    renderWarnings([`Something went wrong: ${e.message ?? e}`]);
    $("output-section").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } finally {
    btn.disabled = false;
    btn.removeAttribute("aria-busy");
    if (label) label.textContent = defaultLabel;
  }
}

$("run-btn").addEventListener("click", runSanitize);
$("copy-final").addEventListener("click", () => copyText("final-out", "Final prompt copied"));
$("copy-redacted").addEventListener("click", () => copyText("redacted-out", "Redacted text copied"));
$("copy-assistant-answer").addEventListener("click", () =>
  copyText("assistant-answer-out", "Answer copied")
);
const copyRendered = $("copy-assistant-answer-rendered");
if (copyRendered) {
  copyRendered.addEventListener("click", () =>
    copyText("assistant-answer-rendered-out", "Rendered answer copied")
  );
}
const copyOllama = $("copy-ollama");
if (copyOllama) copyOllama.addEventListener("click", () => copyText("ollama-out", "Ollama version copied"));
const copyGem = $("copy-gemini-rewrite");
if (copyGem) copyGem.addEventListener("click", () => copyText("gemini-rewrite-out", "Gemini rewrite copied"));
$("prompt").addEventListener("input", updateCharCount);
const glossaryTa = $("glossary-terms");
if (glossaryTa) glossaryTa.addEventListener("input", updateGlossaryCount);
const saveBtn = $("save-glossary");
if (saveBtn) saveBtn.addEventListener("click", saveGlossary);

updateCharCount();
loadGlossary();
checkHealth();
setInterval(checkHealth, 30000);
