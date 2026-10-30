#!/usr/bin/env python3
"""What a text-watermark key looks like, and what "entropy" means for it.

A self-contained, dependency-free demonstration of a keyed red-green watermark
(Kirchenbauer et al. 2023 style) on a toy language model built from the corpus:

  1. the key is just bytes; a keyed hash (HMAC-SHA256) of (key, previous token,
     candidate token) decides whether a candidate is "green"
  2. generation biases green tokens; detection counts green tokens with the key
     and reports a z-score; a wrong key sees nothing
  3. brute force: with a tiny key space the key can be recovered from one text;
     the cost grows as 2^bits, so a 128-bit key is out of reach
  4. signal entropy: only positions where the model has real choice can carry the
     mark, so bits-per-token depends on the text's own entropy
  5. a multi-bit variant: how a model ID *would* be stored if a vendor chose to
     (select one of 2^b derived keys), and why it still needs the master key to read

Usage: python3 tools/watermark_demo.py [--corpus corpus] [--tokens 300]
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import math
import os
import random
import re
import secrets
import time
from collections import Counter, defaultdict

WORD = re.compile(r"[a-z][a-z']+|[.,;:!?]")


# ------------------------------------------------------------------ toy language model
def load_words(root):
    words = []
    for prov in os.listdir(root):
        pd = os.path.join(root, prov)
        if not os.path.isdir(pd) or prov == "inbox":
            continue
        for mdl in os.listdir(pd):
            md = os.path.join(pd, mdl)
            if not os.path.isdir(md):
                continue
            for fn in os.listdir(md):
                if fn.endswith(".md"):
                    raw = open(os.path.join(md, fn), encoding="utf-8").read()
                    body = raw.split("---", 2)[2] if raw.startswith("---") else raw
                    body = re.sub(r"```.*?```", " ", body, flags=re.S)
                    body = re.sub(r"[*#|>`_]", " ", body)
                    words += WORD.findall(body.lower())
    return words


class Bigram:
    """P(next | prev) with add-k smoothing restricted to seen successors (keeps it cheap)."""

    def __init__(self, words):
        self.succ = defaultdict(Counter)
        for a, b in zip(words, words[1:]):
            self.succ[a][b] += 1
        self.vocab = sorted(set(words))
        self.uni = Counter(words)

    def dist(self, prev):
        c = self.succ.get(prev)
        if not c:
            c = self.uni
        tot = sum(c.values())
        return {w: n / tot for w, n in c.items()}


def entropy_bits(p):
    return -sum(v * math.log2(v) for v in p.values() if v > 0)


# ------------------------------------------------------------------ the watermark
def is_green(key: bytes, prev: str, tok: str, gamma: float) -> bool:
    """Keyed PRF: HMAC-SHA256(key, prev || tok) -> uniform in [0,1) -> green if < gamma."""
    h = hmac.new(key, (prev + "\x00" + tok).encode(), hashlib.sha256).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64 < gamma


def generate(lm, key, n, gamma=0.5, delta=2.0, seed=0, start="the"):
    rng = random.Random(seed)
    out, prev = [], start
    for _ in range(n):
        p = lm.dist(prev)
        toks = list(p)
        logits = [math.log(p[t]) + (delta if is_green(key, prev, t, gamma) else 0.0) for t in toks]
        m = max(logits)
        w = [math.exp(l - m) for l in logits]
        tok = rng.choices(toks, weights=w, k=1)[0]
        out.append(tok)
        prev = tok
    return out


def zscore(tokens, key, gamma=0.5, start="the"):
    prev, green, T = start, 0, 0
    seen = set()
    for t in tokens:
        if (prev, t) not in seen:           # score each context once (repeated-context masking)
            seen.add((prev, t))
            T += 1
            green += is_green(key, prev, t, gamma)
        prev = t
    return (green - gamma * T) / math.sqrt(T * gamma * (1 - gamma)) if T else 0.0, green, T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus")
    ap.add_argument("--tokens", type=int, default=300)
    a = ap.parse_args()
    words = load_words(a.corpus)
    lm = Bigram(words)
    print(f"toy language model: {len(words)} words, vocabulary {len(lm.vocab)}")
    ents = [entropy_bits(lm.dist(w)) for w in lm.vocab[:2000]]
    print(f"mean next-token entropy of the toy model: {sum(ents)/len(ents):.2f} bits (real LLMs: ~2-4 bits/token on prose, near 0 on code and facts)\n")

    # 1. what a key looks like
    key = secrets.token_bytes(16)
    print("1. A key is just random bytes. A 128-bit key:")
    print(f"   hex  : {key.hex()}")
    print(f"   int  : {int.from_bytes(key, 'big')}")
    print("   It never appears in the text. It only seeds a pseudorandom function of (key, context, candidate token).\n")

    # 2. detection with the right key vs wrong keys
    gamma, delta = 0.5, 2.0
    text = generate(lm, key, a.tokens, gamma, delta, seed=1)
    plain = generate(lm, key, a.tokens, gamma, 0.0, seed=1)   # delta 0 = no watermark
    z, g, T = zscore(text, key, gamma)
    z0, g0, T0 = zscore(plain, key, gamma)
    wrong = [zscore(text, secrets.token_bytes(16), gamma)[0] for _ in range(20)]
    print(f"2. Detection on {a.tokens} generated tokens (gamma={gamma}, delta={delta}):")
    print(f"   watermarked text, correct key : z = {z:+.2f}  ({g}/{T} scored tokens green)")
    print(f"   unwatermarked text, same key  : z = {z0:+.2f}  ({g0}/{T0} green)")
    print(f"   watermarked text, 20 wrong keys: z in [{min(wrong):+.2f}, {max(wrong):+.2f}], mean {sum(wrong)/len(wrong):+.2f}")
    print("   Without the key the green tokens look like a fair coin. That is the whole security argument.\n")
    print("   sample:", " ".join(text[:40]), "...\n")

    # 3. brute force
    print("3. Brute force over a small key space (keys = integers 0..2^16):")
    small_key = (12345).to_bytes(4, "big")
    text_small = generate(lm, small_key, a.tokens, gamma, delta, seed=2)
    t0 = time.time()
    best = max(range(2 ** 16), key=lambda k: zscore(text_small, k.to_bytes(4, "big"), gamma)[0])
    dt = time.time() - t0
    zb = zscore(text_small, best.to_bytes(4, "big"), gamma)[0]
    per_key = dt / 2 ** 16
    print(f"   true key 12345 -> recovered {best} with z={zb:+.2f} in {dt:.1f} s ({per_key*1e6:.0f} us per key on one text)")
    for bits in (24, 32, 64, 128):
        secs = per_key * 2 ** bits
        print(f"   {bits:3d}-bit key: {2**bits:.2e} candidates -> {secs/3600/24/365:.3g} years at this rate")
    print("   (a GPU detector is maybe 10^4x faster; it does not change the conclusion for 128+ bits)\n")

    # 4. signal entropy: how many bits of evidence per token
    print("4. Signal entropy: evidence per token depends on the text's own entropy.")
    for n in (50, 100, 200, 400, 800):
        zs = [zscore(generate(lm, key, n, gamma, delta, seed=s), key, gamma)[0] for s in range(5)]
        print(f"   {n:4d} tokens: mean z = {sum(zs)/5:+.2f}")
    # per-token log-likelihood ratio of green under watermark vs null
    pg = sum(1 for s in range(5) for t in [generate(lm, key, 200, gamma, delta, seed=10 + s)] for _ in [0] if True)
    greens = []
    for s in range(5):
        zz, gg, tt = zscore(generate(lm, key, 200, gamma, delta, seed=20 + s), key, gamma)
        greens.append(gg / tt)
    pgreen = sum(greens) / len(greens)
    kl = pgreen * math.log2(pgreen / gamma) + (1 - pgreen) * math.log2((1 - pgreen) / (1 - gamma))
    print(f"   observed green rate {pgreen:.2f} vs {gamma} under null -> about {kl:.3f} bits of evidence per scored token")
    print(f"   -> roughly {math.ceil(20 / kl) if kl > 0 else 'inf'} scored tokens for ~20 bits of evidence (p ~ 1e-6)")
    print("   Low-entropy positions (fixed phrases, code, numbers) cannot carry the mark: biasing them would change meaning.\n")

    # 5. multi-bit payload: how a model id *would* be stored
    print("5. A multi-bit payload (how a model ID would be stored if a vendor did it):")
    master = secrets.token_bytes(16)
    derive = lambda i: hmac.new(master, f"model-{i}".encode(), hashlib.sha256).digest()[:16]
    model_id = 5          # pretend: 8-bit id, 256 possible models
    text_id = generate(lm, derive(model_id), a.tokens, gamma, delta, seed=3)
    scores = [(zscore(text_id, derive(i), gamma)[0], i) for i in range(256)]
    scores.sort(reverse=True)
    print(f"   embed: generate with key_i = PRF(master, model_id={model_id}); the text carries log2(256) = 8 bits")
    print(f"   read : try all 256 derived keys -> best id {scores[0][1]} (z={scores[0][0]:+.2f}), runner-up id {scores[1][1]} (z={scores[1][0]:+.2f})")
    print("   Reading still needs the master key. Without it the 256 keys are 256 unknown 128-bit secrets.")
    print("   Anthropic states its deployed mark carries no identifying information (zero-bit), and the")
    print("   forensic sweep found no second channel, so this is a 'could', not an 'is'.")


if __name__ == "__main__":
    main()
