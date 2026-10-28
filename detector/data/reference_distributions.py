"""Per-model answer distributions for one-word random-choice probes.

Source: the public LLM fingerprint database at tosea.ai/free-tools/fingerprints
(data credited to T. Bruckner, "One Token Is Enough", arXiv:2607.10252,
CC-BY-4.0).  Each cell was sampled 30 times at temperature 1.0 with a
minimal one-word system prompt, data generated 2026-07-08.  Only the top
answers are published; the remaining mass is stored under "other".

Cells: "1-10", "1-100", "favorite_number", "coin", "color", "letter",
"animal", "city".  Values are probabilities (fractions of samples).

Run ``python -m detector.data.reference_distributions`` to rebuild
``random_priors.json`` (family-level aggregates + per-model tables).
"""
from __future__ import annotations

import json
import os

MODELS = {
    # ---------------- OpenAI ----------------
    "openai/gpt-5.5": {"family": "openai", "weight": 3, "randomness": 27, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"47": .633, "42": .2, "57": .1, "37": .067},
        "favorite_number": {"7": 1.0},
        "coin": {"heads": .067, "tails": .933},
        "color": {"purple": .5, "blue": .5},
        "letter": {"q": .9, "k": .1},
        "animal": {"giraffe": .4, "pangolin": .167, "capybara": .133, "other": .3},
        "city": {"valencia": .3, "lisbon": .267, "kyoto": .2, "other": .233},
    }},
    "openai/gpt-5.4": {"family": "openai", "weight": 2, "randomness": 22, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"47": .533, "57": .233, "73": .2, "67": .033},
        "favorite_number": {"7": 1.0},
        "coin": {"heads": .5, "tails": .5},
        "color": {"blue": .9, "teal": .067, "azure": .033},
        "letter": {"q": 1.0},
        "animal": {"otter": .967, "octopus": .033},
        "city": {"oslo": .4, "valencia": .3, "kyoto": .2, "other": .1},
    }},
    "openai/gpt-5.4-mini": {"family": "openai", "weight": 1, "randomness": 14, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .533, "73": .4, "47": .067},
        "favorite_number": {"7": 1.0},
        "coin": {"heads": .967, "tails": .033},
        "color": {"blue": .767, "cerulean": .133, "teal": .067, "azure": .033},
        "letter": {"q": .933, "g": .033, "r": .033},
        "animal": {"elephant": .533, "otter": .1, "dolphin": .067, "other": .3},
        "city": {"tokyo": .5, "kyoto": .267, "paris": .2, "other": .033},
    }},
    "openai/gpt-5.2": {"family": "openai", "weight": 2, "randomness": 16, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"57": .833, "42": .067, "37": .033, "47": .033, "73": .033},
        "favorite_number": {"7": 1.0},
        "coin": {"heads": .867, "tails": .133},
        "color": {"blue": .967, "cerulean": .033},
        "letter": {"k": .667, "q": .3, "g": .033},
        "animal": {"octopus": .567, "otter": .133, "elephant": .133, "other": .167},
        "city": {"lisbon": .733, "oslo": .167, "lima": .067, "other": .033},
    }},
    "openai/gpt-4.1": {"family": "openai", "weight": 1, "randomness": 25, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"47": .733, "57": .267},
        "coin": {"heads": 1.0},
        "color": {"cerulean": .367, "teal": .267, "turquoise": .133, "other": .233},
        "letter": {"j": .4, "q": .2, "k": .167, "other": .233},
        "animal": {"giraffe": .533, "elephant": .233, "okapi": .1, "other": .133},
        "city": {"oslo": .333, "kyoto": .267, "lisbon": .2, "other": .2},
    }},
    "openai/gpt-4o": {"family": "openai", "weight": 1, "randomness": 34, "cells": {
        "1-10": {"7": .867, "4": .067, "5": .067},
        "1-100": {"42": .433, "37": .233, "57": .167, "27": .067, "47": .067, "56": .033},
        "favorite_number": {"7": .6, "42": .35, "3": .05},
        "coin": {"heads": .667, "tails": .333},
        "color": {"blue": .633, "azure": .1, "turquoise": .067, "cyan": .067, "cerulean": .067, "teal": .033, "azurite": .033},
        "letter": {"g": .267, "m": .2, "k": .2, "other": .333},
        "animal": {"elephant": .733, "tiger": .167, "giraffe": .067, "other": .033},
        "city": {"tokyo": .467, "paris": .333, "berlin": .1, "other": .1},
    }},
    # ---------------- xAI ----------------
    "x-ai/grok-4.3": {"family": "xai", "weight": 2, "randomness": 28, "cells": {
        "1-10": {"7": .867, "5": .133},
        "1-100": {"42": .933, "17": .033, "47": .033},
        "favorite_number": {"42": .9, "7": .1},
        "coin": {"heads": .7, "tails": .3},
        "color": {"blue": .933, "red": .033, "purple": .033},
        "letter": {"a": .433, "q": .2, "z": .2, "other": .167},
        "animal": {"elephant": .633, "cat": .167, "dog": .067, "other": .133},
        "city": {"tokyo": .533, "paris": .3, "berlin": .1, "other": .067},
    }},
    "x-ai/grok-4.20": {"family": "xai", "weight": 1, "randomness": 24, "cells": {
        "1-10": {"7": .867, "5": .133},
        "1-100": {"42": .533, "47": .467},
        "favorite_number": {"7": 1.0},
        "coin": {"heads": .933, "tails": .067},
        "color": {"blue": 1.0},
        "letter": {"q": .533, "z": .267, "x": .1, "other": .1},
        "animal": {"elephant": .533, "lion": .133, "cat": .1, "other": .233},
        "city": {"tokyo": .5, "paris": .167, "toronto": .067, "other": .267},
    }},
    # ---------------- Google ----------------
    "google/gemini-3.1-flash-lite": {"family": "google", "weight": 2, "randomness": 20, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .867, "47": .1, "74": .033},
        "favorite_number": {"7": .533, "42": .467},
        "coin": {"heads": .8, "tails": .2},
        "color": {"blue": .867, "azure": .067, "indigo": .067},
        "letter": {"k": .7, "q": .167, "g": .067, "other": .033},
        "animal": {"elephant": .5, "tiger": .267, "penguin": .067, "other": .167},
        "city": {"tokyo": .7, "kyoto": .3},
    }},
    "google/gemini-2.5-flash": {"family": "google", "weight": 1, "randomness": 38, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .467, "73": .4, "57": .067, "other": .067},
        "favorite_number": {"42": .933, "6": .033, "1729": .033},
        "coin": {"heads": .7, "tails": .3},
        "color": {"red": .433, "blue": .4, "green": .067, "other": .1},
        "letter": {"r": .2, "x": .133, "q": .1, "g": .1, "z": .1, "other": .367},
        "animal": {"tiger": .233, "dog": .2, "lion": .167, "cat": .167, "other": .233},
        "city": {"london": .5, "paris": .267, "tokyo": .133, "other": .1},
    }},
    # ---------------- Anthropic ----------------
    "anthropic/claude-sonnet-4": {"family": "anthropic", "weight": 1, "randomness": 17, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"47": .667, "42": .333},
        "favorite_number": {"7": .833, "42": .133, "17": .033},
        "coin": {"heads": .967, "tails": .033},
        "color": {"blue": .967, "purple": .033},
        "letter": {"k": .633, "m": .367},
        "animal": {"elephant": .433, "penguin": .333, "other": .233},
        "city": {"tokyo": .333, "denver": .233, "barcelona": .133, "other": .3},
    }},
    # ---------------- Meta ----------------
    "meta-llama/llama-4-maverick": {"family": "meta", "weight": 2, "randomness": 21, "cells": {
        "1-10": {"7": .967, "5": .033},
        "1-100": {"53": .967, "43": .033},
        "favorite_number": {"42": .967, "1": .033},
        "coin": {"heads": .833, "tails": .167},
        "color": {"blue": 1.0},
        "letter": {"k": .8, "j": .2},
        "animal": {"tiger": .6, "giraffe": .333, "other": .067},
        "city": {"paris": .833, "tallinn": .1, "other": .067},
    }},
    # ---------------- Anthropic (batch 2) ----------------
    "anthropic/claude-sonnet-5": {"family": "anthropic", "weight": 3, "randomness": 5, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"47": .933, "37": .067},
        "favorite_number": {"7": 1.0},
        "coin": {"heads": 1.0},
        "color": {"blue": 1.0},
        "letter": {"k": .933, "m": .067},
        "animal": {"elephant": 1.0},
        "city": {"tokyo": .5, "paris": .333, "chicago": .167},
    }},
    "anthropic/claude-opus-4.8": {"family": "anthropic", "weight": 2, "randomness": 5, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"47": .933, "42": .067},
        "favorite_number": {"7": .533, "42": .467},
        "coin": {"heads": 1.0},
        "color": {"blue": 1.0},
        "letter": {"q": .567, "m": .433},
        "animal": {"dog": 1.0},
        "city": {"tokyo": .967, "paris": .033},
    }},
    "anthropic/claude-opus-4.6": {"family": "anthropic", "weight": 1, "randomness": 3, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .933, "47": .067},
        "favorite_number": {"42": 1.0},
        "coin": {"heads": 1.0},
        "color": {"blue": 1.0},
        "letter": {"g": 1.0},
        "animal": {"dog": .767, "tiger": .1, "other": .133},
        "city": {"prague": .933, "toronto": .033, "tokyo": .033},
    }},
    "anthropic/claude-haiku-4.5": {"family": "anthropic", "weight": 1, "randomness": 18, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .833, "47": .167},
        "coin": {"heads": 1.0},
        "color": {"blue": .667, "azure": .1, "purple": .1, "turquoise": .1, "teal": .033},
        "letter": {"q": .767, "k": .133, "g": .1},
        "animal": {"giraffe": .367, "platypus": .333, "otter": .133, "penguin": .067, "other": .1},
        "city": {"denver": .467, "tokyo": .133, "portland": .133, "paris": .1, "barcelona": .067, "other": .1},
    }},
    # ---------------- DeepSeek ----------------
    "deepseek/deepseek-v4-pro": {"family": "deepseek", "weight": 2, "randomness": 34, "cells": {
        "1-10": {"7": .862, "6": .069, "5": .034, "8": .034},
        "1-100": {"42": .233, "47": .2, "57": .133, "67": .1, "other": .333},
        "favorite_number": {"7": .833, "42": .167},
        "coin": {"heads": 1.0},
        "color": {"cerulean": .567, "turquoise": .1, "azure": .1, "indigo": .1, "lavender": .067, "magenta": .033, "teal": .033},
        "letter": {"m": .233, "k": .233, "j": .133, "q": .1, "other": .3},
        "animal": {"elephant": .433, "platypus": .1, "okapi": .067, "giraffe": .067, "dog": .067, "other": .267},
        "city": {"london": .267, "tokyo": .133, "paris": .133, "seoul": .1, "other": .367},
    }},
    "deepseek/deepseek-v3.2": {"family": "deepseek", "weight": 1, "randomness": 44, "cells": {
        "1-10": {"7": .9, "5": .067, "6": .033},
        "1-100": {"37": .233, "73": .167, "47": .133, "other": .467},
        "favorite_number": {"7": .704, "42": .185, "other": .111},
        "coin": {"heads": .367, "tails": .633},
        "color": {"blue": .833, "red": .167},
        "letter": {"k": .167, "g": .133, "d": .133, "c": .133, "other": .433},
        "animal": {"elephant": .333, "dog": .3, "cat": .1, "lion": .1, "other": .167},
        "city": {"chicago": .4, "tokyo": .3, "paris": .067, "amsterdam": .067, "other": .167},
    }},
    # ---------------- Alibaba Qwen ----------------
    "qwen/qwen3.7-max": {"family": "alibaba", "weight": 2, "randomness": 19, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .967, "27": .033},
        "favorite_number": {"7": .667, "42": .333},
        "coin": {"heads": .933, "tails": .067},
        "color": {"teal": .5, "crimson": .367, "cerulean": .067, "azure": .067},
        "letter": {"k": .967, "q": .033},
        "animal": {"axolotl": .6, "platypus": .133, "elephant": .067, "otter": .067, "other": .133},
        "city": {"kyoto": .867, "oslo": .067, "osaka": .033, "lima": .033},
    }},
    # ---------------- Mistral ----------------
    "mistralai/mistral-large-3": {"family": "mistral", "weight": 2, "randomness": 15, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .533, "47": .467},
        "favorite_number": {"7": 1.0},
        "coin": {"heads": 1.0},
        "color": {"teal": .8, "blue": .133, "lavender": .033, "turquoise": .033},
        "letter": {"q": .933, "k": .067},
        "animal": {"giraffe": .9, "kangaroo": .067, "lemur": .033},
        "city": {"tokyo": 1.0},
    }},
    # ---------------- Other families ----------------
    "moonshotai/kimi-k2.6": {"family": "other", "weight": 1, "randomness": 32, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"37": .4, "47": .333, "73": .2, "42": .067},
        "favorite_number": {"7": .724, "42": .207, "other": .07},
        "coin": {"heads": .967, "tails": .033},
        "color": {"magenta": .333, "teal": .185, "azure": .111, "cyan": .111, "crimson": .074, "other": .185},
        "letter": {"q": .5, "k": .214, "m": .107, "x": .107, "other": .07},
        "animal": {"platypus": .31, "axolotl": .276, "octopus": .138, "aardvark": .103, "other": .17},
        "city": {"bishkek": .36, "lviv": .08, "tashkent": .08, "vilnius": .08, "other": .4},
    }},
    "z-ai/glm-5.2": {"family": "other", "weight": 1, "randomness": 24, "cells": {
        "1-10": {"7": 1.0},
        "1-100": {"42": .862, "73": .138},
        "favorite_number": {"7": .633, "42": .367},
        "coin": {"heads": .862, "tails": .138},
        "color": {"cerulean": .321, "blue": .25, "teal": .143, "cyan": .107, "azure": .107, "other": .07},
        "letter": {"q": .786, "k": .107, "r": .071, "j": .036},
        "animal": {"platypus": .643, "elephant": .071, "panther": .071, "other": .214},
        "city": {"kyoto": .593, "springfield": .185, "tokyo": .148, "dubai": .074},
    }},
}

# Index-only knowledge (top 1-100 answer) for families without per-cell pages yet.
INDEX_TOP_1_100 = {
    # families whose per-cell pages were not fetched: index-level top answers only
    "other": {"42": .55, "47": .2, "37": .1, "73": .1, "other": .05},
}

FAMILY_FALLBACK_COLOR = {"deepseek": {"blue": .85, "other": .15}, "alibaba": {"blue": .65, "teal": .1, "turquoise": .07, "other": .18}, "mistral": {"blue": .8, "other": .2}}


def build() -> dict:
    cells = ["1-10", "1-100", "favorite_number", "coin", "color", "letter", "animal", "city"]
    fam_acc: dict = {c: {} for c in cells}
    fam_w: dict = {c: {} for c in cells}
    for mid, m in MODELS.items():
        fam = m["family"]
        for c in cells:
            dist = m["cells"].get(c)
            if not dist:
                continue
            acc = fam_acc[c].setdefault(fam, {})
            for ans, p in dist.items():
                acc[ans] = acc.get(ans, 0.0) + p * m["weight"]
            fam_w[c][fam] = fam_w[c].get(fam, 0.0) + m["weight"]
    out = {"models": MODELS, "families": {}}
    for c in cells:
        out[c] = {}
        for fam, acc in fam_acc[c].items():
            w = fam_w[c][fam]
            out[c][fam] = {ans: round(v / w, 4) for ans, v in acc.items()}
    for fam, dist in INDEX_TOP_1_100.items():
        out["1-100"].setdefault(fam, dist)
    for fam, dist in FAMILY_FALLBACK_COLOR.items():
        out["color"].setdefault(fam, dist)
    # generic priors everybody shares
    for fam in ["deepseek", "alibaba", "mistral"]:
        out["1-10"].setdefault(fam, {"7": .9, "other": .1})
        out["favorite_number"].setdefault(fam, {"7": .5, "42": .45, "other": .05})
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    data = build()
    with open(os.path.join(here, "random_priors.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("wrote random_priors.json with cells:", [k for k in data if k not in ("models", "families")])
