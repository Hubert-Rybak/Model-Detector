// Shared corpus loader for the training tools.
// Accepts (a) corpus/<provider>/<model-slug>/*.md files with YAML-ish front matter and
// (b) corpus/inbox/*.txt paste files with "=== provider/model | note ===" separators.
import fs from "node:fs";
import path from "node:path";

export const FAMILY_ALIASES = {
  openai: "openai", chatgpt: "openai", gpt: "openai", anthropic: "anthropic", claude: "anthropic", google: "google", gemini: "google", gemma: "google",
  meta: "meta", llama: "meta", xai: "xai", grok: "xai", deepseek: "deepseek", alibaba: "alibaba", qwen: "alibaba", mistral: "mistral", mixtral: "mistral",
  human: "human", other: "other", microsoft: "other", phi: "other", copilot: "openai", amazon: "other", nova: "other", cohere: "other", kimi: "other", moonshot: "other", glm: "other", zhipu: "other", minimax: "other", perplexity: "other",
};
export const normFamily = (s) => FAMILY_ALIASES[String(s || "").toLowerCase().trim()] || (String(s || "").toLowerCase().trim() || null);
export const slug = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9.]+/g, "-").replace(/^-|-$/g, "");

function parseFrontMatter(txt) {
  const m = txt.match(/^---\s*\n([\s\S]*?)\n---\s*\n?/);
  if (!m) return [{}, txt];
  const meta = {};
  for (const line of m[1].split("\n")) { const mm = line.match(/^\s*([A-Za-z_]+)\s*:\s*(.*?)\s*$/); if (mm) meta[mm[1].toLowerCase()] = mm[2]; }
  return [meta, txt.slice(m[0].length)];
}

export function loadCorpus(root = "corpus") {
  const samples = [];
  if (!fs.existsSync(root)) return samples;
  for (const provider of fs.readdirSync(root)) {
    const pdir = path.join(root, provider);
    if (!fs.statSync(pdir).isDirectory()) continue;
    if (provider === "inbox") {
      for (const fn of fs.readdirSync(pdir).filter((f) => /\.(txt|md)$/i.test(f) && !/^EXAMPLE/i.test(f))) samples.push(...parseInbox(fs.readFileSync(path.join(pdir, fn), "utf8"), `${provider}/${fn}`));
      continue;
    }
    for (const modelDir of fs.readdirSync(pdir)) {
      const mdir = path.join(pdir, modelDir);
      if (!fs.statSync(mdir).isDirectory()) continue;
      for (const fn of fs.readdirSync(mdir).filter((f) => /\.(md|txt)$/i.test(f))) {
        const [meta, body] = parseFrontMatter(fs.readFileSync(path.join(mdir, fn), "utf8"));
        const text = body.trim();
        if (!text) continue;
        samples.push({ id: `${provider}/${modelDir}/${fn}`, family: normFamily(meta.provider || provider), model: slug(meta.model || modelDir), source: meta.source || "", prompt: meta.prompt || "", date: meta.date || "", text });
      }
    }
  }
  return samples;
}

export function parseInbox(blob, origin = "inbox") {
  const parts = blob.split(/^\s*={2,}\s*([^=\n]+?)\s*={2,}\s*$/m);
  const out = [];
  for (let i = 1; i + 1 < parts.length; i += 2) {
    const header = parts[i].trim();
    let body = parts[i + 1].trim();
    const fence = body.match(/^```[^\n]*\n([\s\S]*?)\n```\s*$/);
    if (fence) body = fence[1];
    if (!body.trim()) continue;
    const [labelPart, ...noteParts] = header.split("|").map((s) => s.trim());
    const [prov, ...rest] = labelPart.split("/");
    const family = normFamily(prov);
    const model = slug(rest.join("/") || prov);
    out.push({ id: `${origin}#${(i + 1) / 2}`, family, model, source: "", prompt: noteParts.join(" | "), date: "", text: body.trim() });
  }
  return out;
}
