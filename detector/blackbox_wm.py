"""Black-box watermark *presence* tests against an OpenAI-compatible chat endpoint.

Implements the designs of Gloaguen, Jovanović, Staab, Vechev, "Black-Box
Detection of Language Model Watermarks" (ICLR 2025, arXiv:2405.20777), which
need sampled text only (no logprobs, no temperature control), plus one cheap
heuristic of our own.  Pure stdlib.

    python -m detector.blackbox_wm --base-url https://api.example.com/v1 --model NAME \
        --api-key $KEY --test fixed --n 300

Tests
-----
fixed      Fixed-Sampling test (paper Sec. 3): query "This is the story of"
           n times at temperature 1 with ~50 generated tokens; count distinct
           outputs R(i) after i queries and compare the rarefaction curve to
           the no-watermark line R(i)=i with a Mann-Whitney U test.  Fixed-key
           sampling watermarks (Aaronson 2022 / Kuditipudi 2023, key size K)
           give R(n) = K(1-(1-1/K)^n).  Paper budget: n = 1,000.  A pilot with
           n = 200 already separates K = 256 (expected 139 distinct) from
           none (200).  Low-entropy decoding also lowers R, so inspect outputs.

redgreen   Red-Green test (paper Sec. 2 / Alg. 2-3): a grid of prefixes t1
           ("I ate", "I chose", ...) x digit contexts t2 (digit repeated H=15
           times) followed by a forced choice among four fruits.  For every
           cell estimate p(x*) of the most common fruit and its logit; flag
           cells deviating by more than 1.96 sigma from the median; the
           statistic is the spread of per-context flag counts, with a
           permutation p-value.  Context-keyed watermarks (red-green lists,
           and in principle any scheme whose keyed randomness depends only on
           the last few tokens, e.g. textGrain) make deviations cluster by
           digit.  Paper budget: 100 samples per cell (9,000 queries; the
           authors found 100+ per cell necessary).  --n-per-cell lower than
           100 is a pilot only.

context    Our cheap heuristic (unvalidated): compare the letter-choice
           distribution under two prompts that differ EARLY versus two that
           differ in the LAST tokens before generation.  Only a late change
           should move a context-keyed watermark's distribution.  JS
           divergence with a permutation p-value.

The authors' own runs on GPT-4, Claude 3 and Gemini 1.0/1.5 APIs (2024) did
not reject for any test, so a non-rejection is not evidence of absence; the
deployed SynthID-Text / Anthropic / textGrain schemes may be too weak or too
masked for these budgets.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
import urllib.request
from collections import Counter

FIXED_PROMPT = "This is the story of"
RG_PREFIXES = ["I ate", "I chose", "I picked", "I selected", "I took", "I went for", "I settled on", "I got", "I gathered", "I harvested"]
RG_FRUITS = ["mangoes", "pineapples", "papayas", "kiwis"]
RG_TEMPLATE = ('Complete the sentence "{prefix} {ctx}" using only and exactly a random word from the list: {fruits}. '
               'Answer in this specific format: {prefix} {ctx} apples. (here I chose another fruit for the sake of the example, '
               'you have to choose among {fruits})')
EARLY_FILLERS = ["Quick task.", "Small request."]
LATE_SUFFIXES = ["Letter:", "Your letter:"]
LETTER_BODY = "{filler} Reply with one uniformly random lowercase letter of the English alphabet and nothing else.\n{suffix}"


# ----------------------------------------------------------------------------- API
def chat(args, prompt: str, temperature: float = 1.0, max_tokens: int = 60) -> str:
    body = json.dumps({"model": args.model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(args.base_url.rstrip("/") + "/chat/completions", data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {args.api_key}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"] or ""


# ----------------------------------------------------------------------------- stats
def mann_whitney_p(a: list, b: list) -> float:
    """Two-sided Mann-Whitney U with normal approximation and tie correction."""
    n1, n2 = len(a), len(b)
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks = [0.0] * len(allv)
    i = 0
    tie_term = 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[k] = r
        t = j - i + 1
        tie_term += t ** 3 - t
        i = j + 1
    r1 = sum(r for r, (v, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    n = n1 + n2
    sigma = math.sqrt(n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1)))) if n > 1 else 0.0
    if sigma == 0:
        return 1.0
    z = (u1 - mu) / sigma
    return math.erfc(abs(z) / math.sqrt(2))


def jsd(p: Counter, q: Counter) -> float:
    keys = set(p) | set(q)
    np_, nq = sum(p.values()), sum(q.values())
    P = {k: p[k] / np_ for k in keys}
    Q = {k: q[k] / nq for k in keys}
    M = {k: 0.5 * (P[k] + Q[k]) for k in keys}
    kl = lambda A, B: sum(A[k] * math.log2(A[k] / B[k]) for k in keys if A[k] > 0)
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def perm_pvalue_jsd(a: list, b: list, observed: float, iters: int = 2000, seed: int = 0) -> float:
    rng = random.Random(seed)
    pool = list(a) + list(b)
    n = len(a)
    hits = 0
    for _ in range(iters):
        rng.shuffle(pool)
        if jsd(Counter(pool[:n]), Counter(pool[n:])) >= observed:
            hits += 1
    return (hits + 1) / (iters + 1)


# ----------------------------------------------------------------------------- tests
def run_fixed(args) -> dict:
    outs = []
    for i in range(args.n):
        outs.append(chat(args, FIXED_PROMPT, 1.0, args.tokens).strip())
        print(f"\r[fixed] {i + 1}/{args.n}", end="", file=sys.stderr)
    print(file=sys.stderr)
    R, seen = [], set()
    for o in outs:
        seen.add(o)
        R.append(len(seen))
    ideal = list(range(1, args.n + 1))
    p = mann_whitney_p(R, ideal)
    exp_k = {K: round(K * (1 - (1 - 1 / K) ** args.n), 1) for K in (256, 2048)}
    short = sum(1 for o in outs if len(o.split()) < 15)
    verdict = ("REJECT no-fixed-sampling (p < 0.05): outputs repeat far more than sampling predicts; fixed-key sampling or deterministic decoding"
               if p < 0.05 else "not rejected: no fixed-sampling watermark signal at this n")
    return {"n": args.n, "distinct": R[-1], "expected_distinct_no_wm": args.n, "expected_distinct_keysize": exp_k,
            "mann_whitney_p": p, "short_outputs": short, "verdict": verdict, "examples": outs[:3]}


def run_redgreen(args) -> dict:
    fruits = ", ".join(RG_FRUITS)
    H = args.context
    cells: dict = {}
    total = len(RG_PREFIXES) * 9 * args.n_per_cell
    done = 0
    for t1 in RG_PREFIXES:
        for d in range(1, 10):
            ctx = str(d) * H
            prompt = RG_TEMPLATE.format(prefix=t1, ctx=ctx, fruits=fruits)
            picks = []
            tries = 0
            while len(picks) < args.n_per_cell and tries < 3 * args.n_per_cell:
                tries += 1
                out = chat(args, prompt, 1.0, 40).lower()
                hit = [f for f in RG_FRUITS if f in out]
                if len(hit) == 1:
                    picks.append(hit[0])
                done += 1
                print(f"\r[redgreen] {done}/{total}", end="", file=sys.stderr)
            cells[(t1, d)] = Counter(picks)
    print(file=sys.stderr)
    allc = Counter()
    for c in cells.values():
        allc.update(c)
    xstar = allc.most_common(1)[0][0]
    eps = 0.5
    L = {k: math.log((c[xstar] + eps) / (sum(c.values()) - c[xstar] + eps)) for k, c in cells.items()}

    def statistic(Lmap: dict) -> float:
        # sigma^2 = median over prefixes of variance across digits
        var_by_t1 = [statistics.pvariance([Lmap[(t1, d)] for d in range(1, 10)]) for t1 in RG_PREFIXES]
        sigma = math.sqrt(max(statistics.median(var_by_t1), 1e-9))
        counts = []
        for d in range(1, 10):
            r = g = 0
            for t1 in RG_PREFIXES:
                med = statistics.median([Lmap[(t1, dd)] for dd in range(1, 10)])
                dev = Lmap[(t1, d)] - med
                if dev < -1.96 * sigma:
                    r += 1
                elif dev > 1.96 * sigma:
                    g += 1
            counts.append(max(r, g))
        return max(counts) - min(counts)

    S_obs = statistic(L)
    rng = random.Random(0)
    keys = list(L.keys())
    vals = list(L.values())
    hits = 0
    for _ in range(args.perms):
        rng.shuffle(vals)
        if statistic(dict(zip(keys, vals))) >= S_obs:
            hits += 1
    p = (hits + 1) / (args.perms + 1)
    return {"n_per_cell": args.n_per_cell, "cells": len(cells), "x_star": xstar, "overall": dict(allc), "S": S_obs, "perm_p": p,
            "verdict": ("REJECT no-red-green (p < 0.05): choice bias clusters by the digit context => context-keyed watermark signal" if p < 0.05
                        else "not rejected: no context-keyed signal at this budget" + (" (pilot budget; paper uses 100 per cell)" if args.n_per_cell < 100 else "")),
            "per_cell_pxstar": {f"{t1}|{d}": round(c[xstar] / max(1, sum(c.values())), 2) for (t1, d), c in cells.items()}}


def first_letter(s: str) -> str:
    for ch in s.strip().lower():
        if ch.isalpha():
            return ch
    return "?"


def run_context(args) -> dict:
    k = args.n
    early = {f: [first_letter(chat(args, LETTER_BODY.format(filler=f, suffix=LATE_SUFFIXES[0]), 1.0, 5)) for _ in range(k)] for f in EARLY_FILLERS}
    late = {sfx: [first_letter(chat(args, LETTER_BODY.format(filler=EARLY_FILLERS[0], suffix=sfx), 1.0, 5)) for _ in range(k)] for sfx in LATE_SUFFIXES}
    e1, e2 = list(early.values())
    l1, l2 = list(late.values())
    j_e, j_l = jsd(Counter(e1), Counter(e2)), jsd(Counter(l1), Counter(l2))
    p_e, p_l = perm_pvalue_jsd(e1, e2, j_e), perm_pvalue_jsd(l1, l2, j_l)
    signal = p_l < 0.05 and p_e >= 0.05 and j_l > 2 * j_e
    return {"n_per_variant": k, "early": {f: dict(Counter(v)) for f, v in early.items()}, "late": {s: dict(Counter(v)) for s, v in late.items()},
            "jsd_early": round(j_e, 4), "p_early": round(p_e, 4), "jsd_late": round(j_l, 4), "p_late": round(p_l, 4),
            "verdict": ("context-keyed signal: late change shifts the distribution, early change does not" if signal
                        else "no context-keyed signal at this n (or the letter choice is too peaked to test)")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    ap.add_argument("--test", choices=["fixed", "redgreen", "context", "all"], default="fixed")
    ap.add_argument("--n", type=int, default=200, help="queries for fixed/context tests (paper: 1000 for fixed)")
    ap.add_argument("--tokens", type=int, default=50, help="generated tokens per fixed-test query")
    ap.add_argument("--n-per-cell", type=int, default=20, help="red-green samples per grid cell (paper: 100)")
    ap.add_argument("--context", type=int, default=15, help="red-green digit repetitions H (upper bound on watermark context)")
    ap.add_argument("--perms", type=int, default=2000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    out = {}
    if args.test in ("fixed", "all"):
        out["fixed_sampling"] = run_fixed(args)
    if args.test in ("redgreen", "all"):
        out["red_green"] = run_redgreen(args)
    if args.test in ("context", "all"):
        out["context_shift"] = run_context(args)
    print(json.dumps(out, indent=1))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
