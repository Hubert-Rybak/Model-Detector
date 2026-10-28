// Leave-one-out evaluation of the fingerprint on corpus/: family accuracy and confusion matrix.
//   node tools/eval.mjs [--corpus corpus] [--min-df 2]
import { trainNB, tokenize, analyze } from "../docs/engine.js";
import { loadCorpus } from "./corpus.mjs";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : []).filter(Boolean));
const samples = loadCorpus(args.corpus || "corpus").filter((s) => s.family && s.text.split(/\s+/).length >= 20);
for (const s of samples) s.bag = tokenize(s.text);
const minDf = Number(args["min-df"] || 2);
const fams = [...new Set(samples.map((s) => s.family))].sort();
const conf = Object.fromEntries(fams.map((a) => [a, Object.fromEntries(fams.map((b) => [b, 0]))]));
let correct = 0, rulesOnly = 0;
for (let i = 0; i < samples.length; i++) {
  const train = samples.filter((_, j) => j !== i);
  const model = { family: trainNB(train, { minDf, level: "family" }), models: null };
  const r = analyze(samples[i].text, model);
  const r0 = analyze(samples[i].text, null);
  const truth = samples[i].family;
  if (conf[truth] && conf[truth][r.top] !== undefined) conf[truth][r.top]++;
  if (r.top === truth) correct++;
  if (r0.top === truth) rulesOnly++;
  console.log(`${r.top === truth ? "ok  " : "MISS"} ${samples[i].id.padEnd(48)} truth=${truth.padEnd(9)} pred=${r.top.padEnd(9)} p=${r.probs[r.top].toFixed(2)} rules-only=${r0.top}`);
}
console.log(`\nLOO accuracy: ${correct}/${samples.length} = ${(100 * correct / Math.max(1, samples.length)).toFixed(1)}%  (rules only: ${(100 * rulesOnly / Math.max(1, samples.length)).toFixed(1)}%)`);
console.log("confusion (rows = truth, cols = predicted):");
console.log("          " + fams.map((f) => f.padStart(9)).join(""));
for (const a of fams) console.log(a.padEnd(10) + fams.map((b) => String(conf[a][b]).padStart(9)).join(""));
