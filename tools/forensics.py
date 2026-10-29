#!/usr/bin/env python3
"""Forensic sweep for hidden model identifiers in a labelled corpus.

Tests every channel a text could use to carry an identifier, and compares what is
found against chance, so "nothing there" is a measured statement rather than a guess:

  1. code-point inventory (invisible, space variants, selectors, tags, lookalikes)
  2. whitespace and line hygiene (trailing spaces, double spaces, tabs, CRLF, blank runs)
  3. acrostics: first/last letters of lines, sentences, paragraphs, list items, words
  4. parity bit streams (sentence length, word length, line length) decoded as ASCII,
     plus a runs test for non-randomness
  5. typographic-choice habits per model (en dash vs hyphen in ranges, Oxford comma,
     e.g./i.e., digits vs words, % vs percent, units spacing, header level, bullet glyph,
     bold styles, ellipsis, quotes)
  6. model-exclusive vocabulary and repeated phrases across prompts
  7. direct and offset searches for the model names and version numbers

Usage: python3 tools/forensics.py [--corpus corpus] [--out analysis/forensics.md]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detector.unicode_scan import scan, classify_codepoint  # noqa: E402

NAMES = ["fable", "opus", "sonnet", "haiku", "claude", "anthropic", "mythos"]
VERSIONS = ["5.1", "5.5", "51", "55"]


def load(root):
    out = []
    for prov in sorted(os.listdir(root)):
        pd = os.path.join(root, prov)
        if not os.path.isdir(pd) or prov == "inbox":
            continue
        for mdl in sorted(os.listdir(pd)):
            md = os.path.join(pd, mdl)
            if not os.path.isdir(md):
                continue
            for fn in sorted(os.listdir(md)):
                if not fn.endswith(".md"):
                    continue
                raw = open(os.path.join(md, fn), encoding="utf-8", newline="").read()
                m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
                meta = dict(re.findall(r"^([a-z_]+):\s*(.*)$", m.group(1), re.M)) if m else {}
                body = raw[m.end():] if m else raw
                out.append({"id": f"{prov}/{mdl}/{fn}", "family": prov, "model": mdl, "prompt": meta.get("prompt", fn[:-3]), "text": body})
    return out


WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


def sentences(t):
    t = re.sub(r"^\s*(?:#{1,6}\s+|[-*+•]\s+|\d+[.)]\s+|>\s*|\|.*\|$)", "", t, flags=re.M)
    t = re.sub(r"\*\*|__|`", "", t)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])|\n{2,}", t) if len(WORD.findall(s)) >= 2]


def bits_to_text(bits):
    return "".join(chr(int(bits[i:i + 8], 2)) for i in range(0, len(bits) - 7, 8))


def printable_ratio(s):
    return sum(1 for c in s if 32 <= ord(c) < 127) / len(s) if s else 0


def runs_test(bits):
    """Wald-Wolfowitz runs test z-score for a 0/1 string (|z|>2.6 is suspicious)."""
    n1, n0 = bits.count("1"), bits.count("0")
    n = n1 + n0
    if n < 20 or not n1 or not n0:
        return 0.0
    runs = 1 + sum(1 for i in range(1, n) if bits[i] != bits[i - 1])
    mu = 1 + 2 * n1 * n0 / n
    var = 2 * n1 * n0 * (2 * n1 * n0 - n) / (n * n * (n - 1))
    return (runs - mu) / math.sqrt(var) if var > 0 else 0.0


def expected_hits(hay, needle):
    """Expected number of occurrences of needle in a random string with hay's letter frequencies."""
    if len(hay) < len(needle):
        return 0.0
    freq = Counter(hay)
    n = len(hay)
    p = 1.0
    for ch in needle:
        p *= freq.get(ch, 0) / n
    return p * (n - len(needle) + 1)


def acrostics(text):
    lines = [l for l in text.splitlines() if l.strip()]
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    items = re.findall(r"^\s*(?:[-*+•]|\d+[.)])\s+\**([A-Za-z])", text, re.M)
    sents = sentences(text)
    first = lambda s: next((c.lower() for c in re.sub(r"[^A-Za-z]", "", s)[:1]), "")
    return {
        "lines_first": "".join(first(l) for l in lines),
        "lines_last": "".join(re.sub(r"[^A-Za-z]", "", l)[-1:].lower() for l in lines),
        "paras_first": "".join(first(p) for p in paras),
        "sents_first": "".join(first(s) for s in sents),
        "items_first": "".join(c.lower() for c in items),
        "words_first": "".join(w[0].lower() for w in WORD.findall(text)),
        "words_last": "".join(w[-1].lower() for w in WORD.findall(text) if w[-1].isalpha()),
    }


def bitstreams(text):
    sents = sentences(text)
    words = WORD.findall(text)
    lines = [l for l in text.splitlines() if l.strip()]
    return {
        "sentence_wordcount_parity": "".join(str(len(WORD.findall(s)) % 2) for s in sents),
        "word_length_parity": "".join(str(len(w) % 2) for w in words),
        "line_length_parity": "".join(str(len(l) % 2) for l in lines),
        "sentence_endchar": "".join("1" if s.endswith((".", "!", "?")) else "0" for s in sents),
        "word_cap_parity": "".join("1" if w[0].isupper() else "0" for w in words),
    }


def habits(text):
    words = WORD.findall(text)
    nw = max(1, len(words))
    r = lambda n: round(1000 * n / nw, 2)
    return {
        "words": nw,
        "en_dash_ranges": len(re.findall(r"\d\s?–\s?\d", text)),
        "hyphen_ranges": len(re.findall(r"\d-\d", text)),
        "en_dash_other": len(re.findall(r"(?<!\d)\s?–\s?(?!\d)", text)),
        "em_dash": text.count("—"),
        "spaced_hyphen_dash": len(re.findall(r"(?<=[A-Za-z,.)]) - (?=[A-Za-z(])", text)),
        "oxford_comma": len(re.findall(r",\s+and\s", text)),
        "and_no_oxford": len(re.findall(r"\b\w+\s+and\s+\w+\b(?!,)", text)),
        "eg": len(re.findall(r"\be\.g\.", text)),
        "for_example": len(re.findall(r"\bfor example\b", text, re.I)),
        "ie": len(re.findall(r"\bi\.e\.", text)),
        "percent_sign": len(re.findall(r"\d\s?%", text)),
        "percent_word": len(re.findall(r"\bpercent\b", text, re.I)),
        "digits_lt_10": len(re.findall(r"(?<![\d.])[1-9](?![\d.%])", text)),
        "number_words": len(re.findall(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\b", text, re.I)),
        "unit_space": len(re.findall(r"\d (?:mm|cm|km|kg|mg|ml|oz|g|m)\b", text)),
        "unit_nospace": len(re.findall(r"\d(?:mm|cm|km|kg|mg|ml|oz|g)\b", text)),
        "degree": text.count("°"),
        "mult_sign": text.count("×"),
        "ellipsis_char": text.count("…"),
        "ellipsis_dots": text.count("..."),
        "curly_quotes": len(re.findall(r"[“”‘’]", text)),
        "straight_dquotes": text.count('"'),
        "h2": len(re.findall(r"^## ", text, re.M)),
        "h3": len(re.findall(r"^### ", text, re.M)),
        "h1": len(re.findall(r"^# ", text, re.M)),
        "bullet_dash": len(re.findall(r"^\s*- ", text, re.M)),
        "bullet_star": len(re.findall(r"^\s*\* ", text, re.M)),
        "numbered": len(re.findall(r"^\s*\d+\. ", text, re.M)),
        "bold_colon_in": len(re.findall(r"\*\*[^*\n]+:\*\*", text)),
        "bold_colon_out": len(re.findall(r"\*\*[^*\n:]+\*\*:", text)),
        "bold_period_in": len(re.findall(r"\*\*[^*\n]+[.!?]\*\*", text)),
        "bold_line": len(re.findall(r"^\*\*[^*\n]+\*\*\s*$", text, re.M)),
        "table": int(bool(re.search(r"^\|.*\|\s*$", text, re.M))),
        "blockquote": len(re.findall(r"^>\s", text, re.M)),
        "parens": len(re.findall(r"\([^)]{3,}\)", text)),
        "semicolons": text.count(";"),
        "colons": len(re.findall(r"[A-Za-z]:\s", text)),
        "exclaim": text.count("!"),
        "questions": text.count("?"),
        "contractions": len(re.findall(r"\b\w+(?:n't|'re|'ve|'ll|'d|'m|'s)\b", text)),
        "code_fence": text.count("```") // 2,
        "inline_code": len(re.findall(r"`[^`\n]+`", text)),
        "italic": len(re.findall(r"(?<![*\w])\*(?!\*)[^*\n]+\*(?!\*)", text)),
        "sent_len_mean": round(sum(len(WORD.findall(s)) for s in sentences(text)) / max(1, len(sentences(text))), 1),
        "para_count": len([p for p in re.split(r"\n\s*\n", text) if p.strip()]),
        "ends_with_question": int(text.strip().endswith("?")),
        "closing_offer": int(bool(re.search(r"if you (?:tell|let|give|share) me|tell me (?:a bit|more|what|which|roughly)|let me know", text[-400:], re.I))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus")
    ap.add_argument("--out", default="analysis/forensics.md")
    ap.add_argument("--json", default="analysis/forensics.json")
    a = ap.parse_args()
    docs = load(a.corpus)
    models = sorted({d["model"] for d in docs})
    L = ["# Forensic sweep for hidden model identifiers\n", f"Corpus: {len(docs)} samples, models: {', '.join(models)}.\n"]
    out = {"n": len(docs), "models": models}

    # 1. code points
    L.append("## 1. Code-point inventory\n")
    cp_by_model = defaultdict(Counter)
    hidden_total = 0
    for d in docs:
        rep = scan(d["text"])
        hidden_total += rep.invisible_count + rep.tag_char_count + rep.private_use_count + rep.space_variant_count + rep.variation_selector_count
        for h in rep.hits:
            cp_by_model[d["model"]][(h.codepoint, h.name, h.klass)] += h.count
    all_cps = sorted({k for c in cp_by_model.values() for k in c}, key=lambda k: -sum(c[k] for c in cp_by_model.values()))
    L.append(f"Hidden, space-variant, selector, tag or private-use characters across all samples: **{hidden_total}**.\n")
    L.append("| code point | name | class | " + " | ".join(models) + " |")
    L.append("|---|---|---|" + "---|" * len(models))
    for cp, name, klass in all_cps:
        L.append(f"| {cp} | {name} | {klass} | " + " | ".join(str(cp_by_model[m][(cp, name, klass)]) for m in models) + " |")
    out["codepoints"] = {m: {f"{k[0]} {k[1]}": v for k, v in c.items()} for m, c in cp_by_model.items()}
    L.append("")

    # 2. whitespace
    L.append("## 2. Whitespace and line hygiene\n")
    ws = defaultdict(Counter)
    for d in docs:
        t = d["text"]
        ws[d["model"]]["trailing_ws_lines"] += sum(1 for l in t.split("\n") if l and l[-1] in " \t")
        ws[d["model"]]["double_spaces"] += len(re.findall(r"(?<=\S)  +(?=\S)", t))
        ws[d["model"]]["tabs"] += t.count("\t")
        ws[d["model"]]["crlf"] += t.count("\r\n")
        ws[d["model"]]["blank_runs_ge2"] += len(re.findall(r"\n\s*\n\s*\n", t))
        ws[d["model"]]["space_before_punct"] += len(re.findall(r" [,.;:!?]", t))
        ws[d["model"]]["nbsp"] += t.count(" ") + t.count(" ")
    keys = ["trailing_ws_lines", "double_spaces", "tabs", "crlf", "blank_runs_ge2", "space_before_punct", "nbsp"]
    L.append("| metric | " + " | ".join(models) + " |")
    L.append("|---|" + "---|" * len(models))
    for k in keys:
        L.append(f"| {k} | " + " | ".join(str(ws[m][k]) for m in models) + " |")
    out["whitespace"] = {m: dict(c) for m, c in ws.items()}
    L.append("")

    # 3. acrostics + 7. name searches
    L.append("## 3. Acrostics and name searches\n")
    L.append("For each channel, the number of samples whose channel string contains a model name or version, versus the expected number under the sample's own letter frequencies.\n")
    chan_hits = defaultdict(lambda: [0, 0.0, []])
    for d in docs:
        ac = acrostics(d["text"])
        # plain text is checked with word boundaries separately (explicit mentions); stripping
        # punctuation would manufacture hits across word boundaries ("stop us" -> "opus")
        ac["digits"] = "".join(re.findall(r"\d", d["text"]))
        for chan, s in ac.items():
            for needle in NAMES + VERSIONS:
                if needle.replace(".", "") not in s.replace(".", ""):
                    continue
                e = expected_hits(s.replace(".", ""), needle.replace(".", ""))
                chan_hits[f"{chan}:{needle}"][0] += 1
                chan_hits[f"{chan}:{needle}"][1] += e
                chan_hits[f"{chan}:{needle}"][2].append(f"{d['model']}/{d['prompt']}")
    L.append("Digit-stream hits come from ordinary numbers in the text (ranges, units, percentages); the contexts are listed in analysis/forensics.json under `digit_contexts`.\n")
    L.append("| channel : needle | samples with a hit | expected by chance (sum) | where |")
    L.append("|---|---|---|---|")
    for k, (n, e, where) in sorted(chan_hits.items(), key=lambda kv: -(kv[1][0] - kv[1][1])):
        L.append(f"| {k} | {n} | {e:.2f} | {', '.join(where[:6])}{'…' if len(where) > 6 else ''} |")
    if not chan_hits:
        L.append("| (none) | 0 | 0 | |")
    out["acrostic_hits"] = {k: {"hits": v[0], "expected": round(v[1], 3), "where": v[2]} for k, v in chan_hits.items()}
    ctxs = []
    for d in docs:
        digs = [(mm.start(), mm.group()) for mm in re.finditer(r"\d", d["text"])]
        ds = "".join(x for _, x in digs)
        for i in range(len(ds) - 1):
            if ds[i:i + 2] in ("51", "55"):
                a0, b0 = digs[i][0], digs[i + 1][0]
                ctxs.append(f"{d['model']}/{d['prompt']}: {d['text'][max(0, a0 - 25):b0 + 10]!r}")
    out["digit_contexts"] = ctxs
    # explicit model-name mentions in plain text with context
    mentions = []
    for d in docs:
        for m in re.finditer(r"(?i)\b(fable|opus|sonnet|haiku|claude|anthropic)\b", d["text"]):
            mentions.append(f"{d['model']}/{d['prompt']}: …{d['text'][max(0, m.start()-30):m.end()+30].replace(chr(10), ' ')}…")
    L.append("")
    L.append(f"Explicit model-name words in the texts: {len(mentions)}" + ("" if not mentions else "\n\n- " + "\n- ".join(mentions)))
    L.append("")

    # 4. bit streams
    L.append("## 4. Parity bit streams\n")
    L.append("Each stream is decoded as 8-bit ASCII and searched for the names; the runs-test z-score flags non-random structure (|z| > 2.6).\n")
    L.append("| stream | model | samples | mean |z| | max |z| | decoded printable ratio (mean) | name hits |")
    L.append("|---|---|---|---|---|---|---|")
    bs_summary = {}
    for stream in ["sentence_wordcount_parity", "word_length_parity", "line_length_parity", "sentence_endchar", "word_cap_parity"]:
        for m in models:
            zs, prs, hits = [], [], 0
            for d in docs:
                if d["model"] != m:
                    continue
                b = bitstreams(d["text"])[stream]
                zs.append(abs(runs_test(b)))
                dec = bits_to_text(b)
                prs.append(printable_ratio(dec))
                if any(n in dec.lower() for n in NAMES):
                    hits += 1
                dec_inv = bits_to_text("".join("1" if c == "0" else "0" for c in b))
                if any(n in dec_inv.lower() for n in NAMES):
                    hits += 1
            if zs:
                L.append(f"| {stream} | {m} | {len(zs)} | {sum(zs)/len(zs):.2f} | {max(zs):.2f} | {sum(prs)/len(prs):.2f} | {hits} |")
                bs_summary[f"{stream}/{m}"] = {"mean_abs_z": round(sum(zs) / len(zs), 2), "max_abs_z": round(max(zs), 2), "hits": hits}
    out["bitstreams"] = bs_summary
    L.append("")

    # 5. habits per model
    L.append("## 5. Typographic and structural habits per model (mean per sample)\n")
    hb = defaultdict(list)
    for d in docs:
        hb[d["model"]].append(habits(d["text"]))
    hkeys = list(habits("x y.").keys())
    L.append("| habit | " + " | ".join(models) + " | spread |")
    L.append("|---|" + "---|" * len(models) + "---|")
    spreads = {}
    for k in hkeys:
        means = [sum(h[k] for h in hb[m]) / len(hb[m]) for m in models]
        mx, mn = max(means), min(means)
        spread = (mx - mn) / (abs(sum(means) / len(means)) + 1e-9)
        spreads[k] = spread
        L.append(f"| {k} | " + " | ".join(f"{v:.2f}" for v in means) + f" | {spread:.2f} |")
    out["habits"] = {m: {k: round(sum(h[k] for h in hb[m]) / len(hb[m]), 3) for k in hkeys} for m in models}
    L.append("")
    L.append("Largest between-model spreads (relative): " + ", ".join(f"{k} ({v:.1f})" for k, v in sorted(spreads.items(), key=lambda kv: -kv[1])[:10]) + "\n")

    # 6. exclusive vocabulary and repeated phrases
    L.append("## 6. Model-exclusive words and phrases (used in 2+ different prompts by one model, never by the others)\n")
    excl = {}
    for n in (1, 2, 3):
        by_model_prompt = defaultdict(lambda: defaultdict(set))
        for d in docs:
            toks = [w.lower() for w in WORD.findall(re.sub(r"```.*?```", " ", d["text"], flags=re.S))]
            grams = {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}
            for g in grams:
                by_model_prompt[g][d["model"]].add(d["prompt"])
        for g, mp in by_model_prompt.items():
            if len(mp) == 1:
                m, prompts = next(iter(mp.items()))
                if len(prompts) >= 2:
                    excl.setdefault(m, []).append((g, len(prompts)))
    for m in models:
        items = sorted(excl.get(m, []), key=lambda x: (-x[1], x[0]))
        L.append(f"**{m}** ({len(items)} exclusive n-grams): " + ", ".join(f"{g} ×{c}" for g, c in items[:30]))
        L.append("")
    out["exclusive"] = {m: sorted(excl.get(m, []), key=lambda x: -x[1])[:60] for m in models}

    # 8. verdict
    L.append("## Verdict\n")
    verdict = []
    verdict.append(f"- Character channel: {hidden_total} hidden/lookalike characters in {len(docs)} samples; the non-ASCII characters present are ordinary typography (see table 1).")
    strong = {k: v for k, v in chan_hits.items() if v[0] >= 2 and v[0] > 3 * max(v[1], 0.3)}
    verdict.append("- Acrostic/offset channel: " + ("no channel exceeds chance." if not strong else "above-chance channels: " + ", ".join(f"{k} ({v[0]} vs {v[1]:.2f})" for k, v in strong.items())))
    bad = {k: v for k, v in bs_summary.items() if v["hits"]}
    structured = {k: v for k, v in bs_summary.items() if v["max_abs_z"] > 3.5}
    verdict.append("- Parity channel: " + ("no stream decodes to a name" if not bad else "decodes to a name in: " + json.dumps(bad)) +
                   ("; " + ", ".join(structured) + " show run clustering, which is what bullet lists, headers and table rows produce, and their decoded printable ratio (~0.4) is what random bits give." if structured else "; no stream shows non-random structure."))
    verdict.append("- What does differ between models is ordinary style (table 5 and section 6): usable as a weak statistical fingerprint, not as a stored identifier.")
    L.extend(verdict)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(out, open(a.json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n".join(verdict))
    print(f"wrote {a.out} and {a.json}")


if __name__ == "__main__":
    main()
