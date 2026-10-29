// Leave-one-out evaluation of the fingerprint on corpus/.
//   node tools/eval.mjs [--corpus corpus] [--min-df 2] [--level family|model] [--family anthropic]
//                       [--holdout prompt|doc] [--features all|style|markers]
// holdout=prompt (default when prompt ids exist): hold out every sample of one kit prompt at a
// time, so no class gets a topic-vocabulary advantage from paired prompts.
// level=family: predict the provider family with the full pipeline (rules + NB).
// level=model : predict the model within a family using the model-level NB alone.
import { trainNB, tokenize, analyze, nbScore, softmax } from "../docs/engine.js";
import { loadCorpus } from "./corpus.mjs";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : []).filter(Boolean));
let samples = loadCorpus(args.corpus || "corpus").filter((s) => s.family && s.text.split(/\s+/).length >= 20);
const level = args.level || "family";
if (args.family) samples = samples.filter((s) => s.family === args.family);
const features = args.features || "all";
for (const s of samples) s.bag = tokenize(s.text, null, { mode: features });
const minDf = Number(args["min-df"] || 2);
const holdout = args.holdout || (samples.every((s) => s.prompt) ? "prompt" : "doc");
const labelOf = (s) => (level === "model" ? s.model : s.family);
const labels = [...new Set(samples.map(labelOf))].sort();
const conf = Object.fromEntries(labels.map((a) => [a, Object.fromEntries(labels.map((b) => [b, 0]))]));
let correct = 0, rulesOnly = 0, sumP = 0;
for (let i = 0; i < samples.length; i++) {
  const train = holdout === "prompt" ? samples.filter((x) => x.prompt !== samples[i].prompt) : samples.filter((_, j) => j !== i);
  const truth = labelOf(samples[i]);
  let pred, p, r0top = "-";
  if (level === "model") {
    const nb = trainNB(train, { minDf, level: "model" });
    const sc = nbScore(samples[i].bag, nb);
    const probs = softmax(sc.logodds);
    pred = Object.keys(probs).sort((a, b) => probs[b] - probs[a])[0]; p = probs[pred];
  } else {
    const model = { features, family: trainNB(train, { minDf, level: "family" }), models: null };
    const r = analyze(samples[i].text, model);
    const r0 = analyze(samples[i].text, null);
    pred = r.top; p = r.probs[r.top]; r0top = r0.top;
    if (r0top === truth) rulesOnly++;
  }
  if (conf[truth] && conf[truth][pred] !== undefined) conf[truth][pred]++;
  if (pred === truth) correct++;
  sumP += p;
  console.log(`${pred === truth ? "ok  " : "MISS"} ${samples[i].id.padEnd(44)} truth=${truth.padEnd(18)} pred=${pred.padEnd(18)} p=${p.toFixed(2)}${level === "family" ? ` rules-only=${r0top}` : ""}`);
}
console.log(`\nhold-out=${holdout} features=${features}`);
console.log(`LOO accuracy (${level}): ${correct}/${samples.length} = ${(100 * correct / Math.max(1, samples.length)).toFixed(1)}%  mean p(top)=${(sumP / Math.max(1, samples.length)).toFixed(2)}${level === "family" ? `  (rules only: ${(100 * rulesOnly / Math.max(1, samples.length)).toFixed(1)}%)` : ""}  chance=${(100 / labels.length).toFixed(1)}%`);
console.log("confusion (rows = truth, cols = predicted):");
const w = Math.max(10, ...labels.map((l) => l.length + 1));
console.log(" ".repeat(w) + labels.map((f) => f.slice(0, w - 1).padStart(w)).join(""));
for (const a of labels) console.log(a.padEnd(w) + labels.map((b) => String(conf[a][b]).padStart(w)).join(""));
