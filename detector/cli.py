"""Command-line entry point.

    python -m detector new <case>            create samples/<case>/ with empty turn files
    python -m detector analyze <case_dir>    run the full analysis, write report.md + result.json
    python -m detector scan <file>           character-level scan of one file
    python -m detector annotate <file>       print the file with hidden characters made visible
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from dataclasses import asdict

from . import features, probes, scorer, unicode_scan
from .report import render
from .signatures import LEXICON

TURN_FILES = {
    "essay": ["t1_essay.md", "turn1.md", "essay.md"],
    "battery": ["t2_battery.md", "turn2.md", "battery.md"],
    "ok": ["t3_ok.md", "turn3.md", "ok.md"],
    "gibberish": ["t4_gibberish.md", "turn4.md", "gibberish.md"],
    "mixed": ["t5_mixed.md", "turn5.md", "mixed.md"],
}
TEMPLATE_FILES = {
    "t1_essay.md": "", "t2_battery.md": "", "t3_ok.md": "", "t4_gibberish.md": "", "t5_mixed.md": "",
    "regen_1.md": "", "regen_2.md": "",
    "meta.json": json.dumps({"source": "chat|api|unknown", "notes": "", "ground_truth": None}, indent=2) + "\n",
}


def _read(path: str) -> str:
    with open(path, encoding="utf-8", newline="") as fh:   # newline='' keeps CRLF visible
        return fh.read()


def _strip_fence(text: str) -> str:
    """If the whole sample was pasted inside one ``` fence, unwrap it."""
    t = text.strip("\n")
    m = re.match(r"^```[^\n]*\n(.*)\n```\s*$", t, re.S)
    return m.group(1) if m else text


def load_case(case_dir: str) -> dict:
    turns = {}
    for key, names in TURN_FILES.items():
        for n in names:
            p = os.path.join(case_dir, n)
            if os.path.exists(p):
                txt = _read(p)
                if txt.strip():
                    turns[key] = _strip_fence(txt)
                break
    regens = []
    for n in sorted(os.listdir(case_dir)):
        if re.match(r"regen_\d+\.md$", n):
            txt = _read(os.path.join(case_dir, n))
            if txt.strip():
                regens.append(_strip_fence(txt))
    meta = {}
    mp = os.path.join(case_dir, "meta.json")
    if os.path.exists(mp):
        try:
            meta = json.loads(_read(mp))
        except json.JSONDecodeError:
            meta = {}
    return {"turns": turns, "regens": regens, "meta": meta}


MARKER_MAP = {"T1": "t1_essay.md", "T2": "t2_battery.md", "T3": "t3_ok.md", "T4": "t4_gibberish.md", "T5": "t5_mixed.md", "R1": "regen_1.md", "R2": "regen_2.md", "R3": "regen_3.md"}


def ingest(case_dir: str, blob: str) -> list:
    """Split a paste with '=== T1 ===' markers into the case's turn files."""
    os.makedirs(case_dir, exist_ok=True)
    parts = re.split(r"^\s*={2,}\s*(T[1-6]|R[1-3])\s*={2,}\s*$", blob, flags=re.M | re.I)
    written = []
    meta_lines = parts[0]
    for i in range(1, len(parts) - 1, 2):
        tag, body = parts[i].upper(), parts[i + 1]
        name = MARKER_MAP.get(tag)
        if not name:
            continue
        body = _strip_fence(body.strip("\n"))
        with open(os.path.join(case_dir, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
        written.append(name)
    meta = {}
    mp = os.path.join(case_dir, "meta.json")
    if os.path.exists(mp):
        try:
            meta = json.loads(_read(mp))
        except json.JSONDecodeError:
            meta = {}
    m = re.search(r"source\s*:\s*(\w+)", meta_lines, re.I)
    if m:
        meta["source"] = m.group(1).lower()
    notes = "\n".join(l for l in meta_lines.splitlines() if l.strip() and not re.match(r"\s*source\s*:", l, re.I)).strip()
    if notes:
        meta["notes"] = notes
    meta.setdefault("ground_truth", None)
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return written


def regen_diversity(samples: list) -> dict:
    if len(samples) < 2:
        return {}
    import itertools
    sims, jacs = [], []
    prefix = None
    for a, b in itertools.combinations(samples, 2):
        wa, wb = a.split(), b.split()
        sims.append(difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio())
        ga = {tuple(wa[i:i + 5]) for i in range(max(0, len(wa) - 4))}
        gb = {tuple(wb[i:i + 5]) for i in range(max(0, len(wb) - 4))}
        jacs.append(len(ga & gb) / max(1, len(ga | gb)))
        k = 0
        while k < min(len(wa), len(wb)) and wa[k] == wb[k]:
            k += 1
        prefix = k if prefix is None else min(prefix, k)
    ms, mj = sum(sims) / len(sims), sum(jacs) / len(jacs)
    if ms >= 0.9:
        verdict = "near-identical regenerations: deterministic decoding (temperature 0) or a fixed-key sampling watermark; cannot be told apart from text alone"
    elif ms >= 0.5:
        verdict = "partly repeated phrasing: low sampling entropy or a strong template; weak hint of entropy-reduced (watermarked) decoding"
    else:
        verdict = "normal diversity: no sign of deterministic or fixed-key sampling (a context-keyed watermark would still be invisible here)"
    return {"n": len(samples), "mean_similarity": round(ms, 3), "mean_jaccard": round(mj, 3), "identical_prefix_words": prefix, "verdict": verdict}


def analyze(case_dir: str, write: bool = True) -> dict:
    case = load_case(case_dir)
    turns = case["turns"]
    all_text = "\n".join(turns.values()) + "\n" + "\n".join(case["regens"])
    u_rep = unicode_scan.scan(all_text)
    u = u_rep.to_dict()
    findings = unicode_scan.suspicious_summary(u_rep)

    ctx = scorer.Context()
    ctx.u = u
    if "essay" in turns:
        ctx.f = features.extract(turns["essay"], LEXICON)
        ctx.has_essay = True
    if "battery" in turns:
        ctx.b = probes.parse_battery(turns["battery"])
    if "ok" in turns:
        ctx.ok = probes.parse_ok(turns["ok"])
    if "gibberish" in turns:
        ctx.gib = probes.parse_gibberish(turns["gibberish"])
    if "mixed" in turns:
        ctx.mix = probes.parse_mixed_language(turns["mixed"])
    regen = regen_diversity(([turns["essay"]] if "essay" in turns else []) + case["regens"])
    ctx.regen = regen

    result = scorer.evaluate(ctx)
    vcands = scorer.version_candidates(result["top"], ctx)
    hints = scorer.model_random_match(ctx)
    md = render(os.path.basename(os.path.normpath(case_dir)), result, ctx, vcands, hints, findings, u, ctx.f, regen)
    out = {
        "case": case_dir, "meta": case["meta"], "top": result["top"], "confidence": result["confidence"],
        "probs": result["probs"], "scores": result["scores"], "tier": result["tier"],
        "evidence": [asdict(e) for e in result["evidence"]], "version_candidates": vcands, "model_hints": hints,
        "unicode_findings": findings, "unicode": {k: v for k, v in u.items() if k != "hits"},
        "unicode_hits": u["hits"], "features": ctx.f, "battery": ctx.b, "ok": ctx.ok, "gibberish": ctx.gib, "mixed": ctx.mix, "regen": regen,
    }
    if write:
        with open(os.path.join(case_dir, "report.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(case_dir, "result.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    out["markdown"] = md
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="detector", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("case_dir"); a.add_argument("--quiet", action="store_true")
    n = sub.add_parser("new"); n.add_argument("case"); n.add_argument("--root", default="samples")
    s = sub.add_parser("scan"); s.add_argument("file")
    t = sub.add_parser("annotate"); t.add_argument("file")
    g = sub.add_parser("ingest"); g.add_argument("case_dir"); g.add_argument("file", help="pasted text with === T1 === markers ('-' for stdin)")
    args = ap.parse_args(argv)

    if args.cmd == "ingest":
        blob = sys.stdin.read() if args.file == "-" else _read(args.file)
        written = ingest(args.case_dir, blob)
        print(f"wrote {', '.join(written) or 'nothing (no markers found)'} into {args.case_dir}/")
        return

    if args.cmd == "new":
        d = os.path.join(args.root, args.case)
        os.makedirs(d, exist_ok=True)
        for name, content in TEMPLATE_FILES.items():
            p = os.path.join(d, name)
            if not os.path.exists(p):
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(content)
        print(f"created {d}/ with: {', '.join(TEMPLATE_FILES)}")
    elif args.cmd == "analyze":
        out = analyze(args.case_dir)
        if not args.quiet:
            print(out["markdown"])
        print(f"\n[written: {os.path.join(args.case_dir, 'report.md')} and result.json]", file=sys.stderr)
    elif args.cmd == "scan":
        rep = unicode_scan.scan(_read(args.file))
        for sev, msg in unicode_scan.suspicious_summary(rep):
            print(f"[{sev}] {msg}")
        d = rep.to_dict()
        for h in d["hits"]:
            print(f"{h['codepoint']}  {h['name']:<45} {h['klass']:<18} x{h['count']}")
        for k in ["straight_double_quotes", "curly_double_quotes", "straight_apostrophes", "curly_apostrophes", "em_dash", "en_dash", "spaced_em_dash", "unspaced_em_dash", "ellipsis_char", "ellipsis_dots", "narrow_nbsp_count", "nbsp_count", "zero_width_count"]:
            print(f"{k}: {d[k]}")
    elif args.cmd == "annotate":
        print(unicode_scan.annotate_hidden(_read(args.file)))


if __name__ == "__main__":
    main()
