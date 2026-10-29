// Write one labelled sample into corpus/<provider>/<model-slug>/<prompt>.md.
//   node tools/add_sample.mjs --provider anthropic --model "Claude Haiku 5.5" --prompt p01 --source agent --file reply.txt
// If the reply ends with a line "-----MODEL: ...", that line is moved into the front matter as `reported_model`.
import fs from "node:fs";
import path from "node:path";
import { slug } from "./corpus.mjs";

const a = Object.fromEntries(process.argv.slice(2).map((x, i, arr) => x.startsWith("--") ? [x.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : []).filter(Boolean));
if (!a.provider || !a.model || !a.prompt || !a.file) { console.error("usage: --provider P --model M --prompt pNN --source S --file F [--note N]"); process.exit(2); }
let text = fs.readFileSync(a.file, "utf8").replace(/\r\n/g, "\n").trim();
let reported = "";
const m = text.match(/\n?-{3,}\s*MODEL:\s*(.*)\s*$/i);
if (m) { reported = m[1].trim(); text = text.slice(0, m.index).trim(); }
// strip a leading harness wrapper if the agent echoed one
text = text.replace(/^\s*(?:Here(?:'s| is) (?:the|my) (?:reply|response)[^\n]*\n+)/i, "");
const dir = path.join("corpus", a.provider, slug(a.model));
fs.mkdirSync(dir, { recursive: true });
const out = path.join(dir, `${a.prompt}.md`);
const fm = [`provider: ${a.provider}`, `model: ${a.model}`, `source: ${a.source || "unknown"}`, `date: ${new Date().toISOString().slice(0, 10)}`, `prompt: ${a.prompt}`, reported ? `reported_model: ${reported}` : null, a.note ? `note: ${a.note}` : null].filter(Boolean);
fs.writeFileSync(out, `---\n${fm.join("\n")}\n---\n${text}\n`);
console.log(`${out}: ${text.split(/\s+/).length} words${reported ? `; reported model: ${reported}` : ""}`);
