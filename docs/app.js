import { analyze, annotate } from "./engine.js";
import { FAMILIES, FAMILY_IDS, WATERMARK_STATUS } from "./reference.js";
import MODEL from "./model.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const EXAMPLE = `Here’s the thing — most beginners point the telescope at the brightest thing in the sky and get disappointed. Don’t.\n\n## Why planets don’t twinkle\n\n- **Stars are points.** A single beam of light crossing turbulent air flickers.\n- **Planets are discs.** Thousands of beams, each wobbling independently, average out.\n\nNot magic. Not a better scope. Just averaging.\n\n## First night, step by step\n\n1. **Set up before dark** and align the finder.\n2. **Let it cool** for 30–45 minutes.\n3. **Start low-power** (the 25 mm eyepiece).\n\n| Target | Why |\n|---|---|\n| Moon | Craters pop along the terminator |\n| Jupiter | Four moons shift nightly |\n\nAs Carl Sagan said, “Somewhere, something incredible is waiting to be known.”\n\nWould you like me to turn this into a printable checklist?`;

function fmtW(w) { return Object.entries(w).filter(([, v]) => Math.abs(v) >= 0.05).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).map(([k, v]) => `${k} ${v > 0 ? "+" : ""}${v.toFixed(1)}`).join(", "); }

function render(r) {
  $("results").hidden = false;
  const top = r.top;
  $("verdict").innerHTML = `<div class="verdict">${esc(FAMILIES[top].name)}</div><span class="tag ${r.confidence}">confidence: ${r.confidence}</span> <span class="tag">p = ${r.probs[top].toFixed(2)}</span> <span class="tag">margin ${r.margin} log-odds</span>
    <div class="muted" style="margin-top:8px">Fingerprint strength</div><div class="meter"><i style="width:${Math.round(100 * r.fingerprint_strength)}%"></i></div>`;
  $("bars").innerHTML = r.ranked.slice(0, 6).map((k) => `<div>${esc(FAMILIES[k].name.split(" (")[0])}</div><div class="bar"><i style="width:${Math.max(1, Math.round(100 * r.probs[k]))}%"></i></div><div class="mono">${r.probs[k].toFixed(3)}</div>`).join("");
  const nbNote = r.nb ? `Learned fingerprint used at weight ${r.nb_weight.toFixed(2)} (${Object.entries(r.nb.docs).map(([k, v]) => `${k}: ${v} docs`).join(", ")}).` : "No trained fingerprint loaded: hand rules only.";
  $("verdict-notes").textContent = `${r.text_stats.words} words, ${r.text_stats.sentences} sentences. ${nbNote} ${r.text_stats.words < 120 ? "Short texts carry little signal; treat the verdict as a hint." : ""}`;
  const mEval = MODEL && MODEL.eval && MODEL.eval.models && MODEL.eval.models[top];
  const evalNote = mEval ? ` Hold-one-prompt-out accuracy of this model-level classifier on the corpus: ${Math.round(100 * mEval.accuracy)}% over ${mEval.classes} models (chance ${Math.round(100 * mEval.chance)}%)${mEval.accuracy < 0.5 ? ", so treat it as a weak hint" : ""}.` : "";
  $("model-level").innerHTML = r.model_level ? `<div class="muted" style="margin-top:8px">Within ${esc(FAMILIES[top].name.split(" (")[0])}, by learned model-level fingerprint:${esc(evalNote)}</div><ul>${r.model_level.map((m) => `<li><b>${esc(m.model)}</b>${m.p !== null ? ` p = ${m.p.toFixed(2)}` : ""} <span class="muted">(${m.docs} training docs${m.note ? ", " + esc(m.note) : ""})</span></li>`).join("")}</ul>` : "";
  $("findings").innerHTML = r.findings.map(([sev, msg]) => `<li><span class="sev-${sev}">${sev}</span> ${esc(msg)}</li>`).join("");
  $("decoded").innerHTML = r.hidden.length ? `<h3 style="font-size:14px;margin:10px 0 6px">Decoded payload attempts</h3>` + r.hidden.map((h) => `<div class="note" style="margin-bottom:8px"><b>${esc(h.scheme)}</b> <span class="muted">(${h.count} carrier chars${h.printable !== undefined ? `, ${Math.round(100 * h.printable)}% printable` : ""})</span>${h.bits ? `<div class="mono">bits: ${esc(h.bits)}${h.bits.length >= 256 ? "…" : ""}</div>` : ""}${h.hex ? `<div class="mono">hex: ${esc(h.hex)}</div>` : ""}${h.decoded !== undefined ? `<div class="mono">decoded: ${esc(h.decoded.slice(0, 400))}</div>` : ""}${h.note ? `<div class="muted">${esc(h.note)}</div>` : ""}</div>`).join("") : "";
  $("annot").innerHTML = annotate($("input").value).map((s) => s.hidden ? `<span class="hid" title="${esc(s.klass)}">〈${esc(s.label)}〉</span>` : s.mark ? `<span class="mk" title="${esc(s.label)}">${esc(s.text)}</span>` : esc(s.text)).join("");
  const hits = r.unicode.hits.filter((h) => h.klass !== "letter_nonascii");
  $("codepoints").innerHTML = hits.length ? `<table><tr><th>code point</th><th>char</th><th>name</th><th>class</th><th>count</th></tr>${hits.slice(0, 60).map((h) => `<tr><td class="mono">${h.codepoint}</td><td>${esc(h.char)}</td><td>${esc(h.name)}</td><td>${h.klass}</td><td>${h.count}</td></tr>`).join("")}</table>` : `<p class="muted">Only ASCII${r.unicode.hits.length ? " and accented letters" : ""}.</p>`;
  $("evidence").innerHTML = `<tr><th>rule</th><th>observation</th><th>weights</th></tr>` + r.rules.evidence.map((e) => `<tr><td class="mono">${esc(e.rule)}</td><td>${esc(e.detail)}</td><td class="mono">${esc(fmtW(e.weights))}</td></tr>`).join("");
  $("tokens").innerHTML = r.top_tokens.length ? `<p class="muted" style="margin-top:10px">Learned tokens favouring <b>${esc(top)}</b> over <b>${esc(r.second)}</b> (words, bigrams, § = style tokens):</p><p>${r.top_tokens.map((t) => `<span class="tag" title="log-odds ${t.delta}, count ${t.n}">${esc(t.token)} ${t.delta > 0 ? "+" : ""}${t.delta}</span>`).join(" ")}</p>` : "";
  $("watermark").innerHTML = `<p><b>${esc(FAMILIES[top].name.split(" (")[0])}</b>: ${esc(WATERMARK_STATUS[top] || "")}</p><p class="muted">Character-level scan above is the only part of a watermark a third party can read. Token-choice watermarks change which of several equally good words is picked, leave no visible trace, and are provably unreadable without the key. Public presence tests (Gloaguen et al., ICLR 2025) need hundreds to thousands of fresh generations from the model, not a single text.</p>`;
  $("model-info").textContent = modelInfoText();
}

function modelInfoText() {
  if (!(MODEL && MODEL.n_samples)) return "No trained fingerprint bundled yet: verdicts come from hand rules only.";
  const fams = Object.entries(MODEL.per_family || {}).map(([k, v]) => `${k} ${v}`).join(", ");
  const fe = MODEL.eval && MODEL.eval.family;
  const famNote = fe ? ` Hold-one-prompt-out family accuracy: ${Math.round(100 * fe.accuracy)}% (chance ${Math.round(100 * fe.chance)}%).` : " Only one provider family in the corpus so far, so the learned part cannot separate providers yet.";
  return `Loaded fingerprint: ${MODEL.n_samples} labelled samples (${fams}), trained ${MODEL.trained_at.slice(0, 10)}.${famNote}`;
}

function run() {
  const text = $("input").value;
  if (!text.trim()) { $("status").textContent = "Paste some text first."; return; }
  $("status").textContent = "Analyzing…";
  setTimeout(() => {
    const model = (MODEL && MODEL.family && Object.keys(MODEL.family.classes || {}).length >= 2) ? MODEL : null;
    const r = analyze(text, model);
    render(r);
    $("status").textContent = "";
    window.__lastResult = r;
  }, 10);
}
$("analyze").addEventListener("click", run);
$("example").addEventListener("click", () => { $("input").value = EXAMPLE; run(); });
$("clear").addEventListener("click", () => { $("input").value = ""; $("results").hidden = true; $("status").textContent = ""; });
$("input").addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") run(); });

// --- Teach panel (localStorage only) ---
$("teach-family").innerHTML = FAMILY_IDS.map((k) => `<option value="${k}">${esc(FAMILIES[k].name)}</option>`).join("");
const KEY = "model-detector-samples";
const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } };
const save = (arr) => { try { localStorage.setItem(KEY, JSON.stringify(arr)); } catch { /* storage unavailable */ } };
const refresh = () => { $("teach-status").textContent = `${load().length} stored sample(s).`; };
refresh();
$("teach-add").addEventListener("click", () => {
  const text = $("input").value.trim();
  if (!text) { $("teach-status").textContent = "Nothing to add."; return; }
  const arr = load();
  arr.push({ family: $("teach-family").value, model: $("teach-model").value.trim() || "unknown", text, date: new Date().toISOString().slice(0, 10) });
  save(arr); refresh();
});
$("teach-export").addEventListener("click", () => {
  const arr = load();
  if (!arr.length) { $("teach-status").textContent = "No stored samples."; return; }
  const blob = arr.map((s) => `=== ${s.family}/${s.model} | ${s.date} ===\n${s.text}\n`).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([blob], { type: "text/plain;charset=utf-8" }));
  a.download = `samples-${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
});
$("teach-clear").addEventListener("click", () => { save([]); refresh(); });
$("model-info").textContent = modelInfoText();
