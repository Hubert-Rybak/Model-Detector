"""Combine evidence into per-family scores.

Each rule inspects the evidence context and may contribute a weight vector
over families.  Scores start at the family prior and end as a softmax
probability.  Every firing rule is returned so the report can show its work.
"""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .signatures import FAMILIES, FAMILY_IDS, LEXICON, PROVIDER_TO_FAMILY, SYSTEM_PROMPT_SIGNATURES, POLICY_VOCAB, VERSIONS
from .probes import PROVIDER_PATTERNS

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@dataclass
class Evidence:
    rule: str
    detail: str
    weights: Dict[str, float]


@dataclass
class Context:
    f: dict = field(default_factory=dict)       # features of the free-form sample(s)
    u: dict = field(default_factory=dict)       # unicode report dict over all text
    b: dict = field(default_factory=dict)       # battery parse
    ok: dict = field(default_factory=dict)
    gib: dict = field(default_factory=dict)
    regen: dict = field(default_factory=dict)   # diversity stats
    mix: dict = field(default_factory=dict)     # mixed-language turn
    has_essay: bool = False


def W(**kw) -> Dict[str, float]:
    return {k: float(v) for k, v in kw.items()}


def _negated(text: str, start: int) -> bool:
    """True if a negation word precedes the mention within the same clause."""
    window = text[max(0, start - 60):start].lower()
    # cut at the last clause boundary so "I'm not X; I'm Y" only negates X
    window = re.split(r"[.;,!?]|\bbut\b|\bhowever\b|\bi'?m\b|\bi am\b|\bit'?s\b|\bthis is\b", window)[-1]
    return bool(re.search(r"\b(not|n't|isn't|aren't|unlike|rather than|instead of|as opposed to|neither|nor|no longer|don't|never|mistaken for|confused with|isn't|wasn't)\b", window)) or window.rstrip().endswith("n't")


def provider_assertions(text: str) -> Dict[str, int]:
    """Count non-negated provider mentions."""
    out: Dict[str, int] = {}
    low = text.lower()
    for prov, pat in PROVIDER_PATTERNS.items():
        for m in re.finditer(pat, low):
            if not _negated(low, m.start()):
                out[prov] = out.get(prov, 0) + 1
    return out


def load_random_priors() -> dict:
    p = os.path.join(DATA_DIR, "random_priors.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def random_choice_evidence(ctx: Context, priors: dict, cap: float = 1.2) -> List[Evidence]:
    """Bayesian-ish update from single-sample random choices against reference
    distributions (per family).  Likelihood ratio vs. the across-family mean,
    clipped to +-cap so one answer can never dominate."""
    out: List[Evidence] = []
    b = ctx.b
    probes = {
        "rand_1_100": ("1-100", str(b.get("rand_1_100")) if b.get("rand_1_100") is not None else None),
        "rand_1_10": ("1-10", str(b.get("rand_1_10")) if b.get("rand_1_10") is not None else None),
        "rand_1_50": ("1-50", str(b.get("rand_1_50")) if b.get("rand_1_50") is not None else None),
        "coin": ("coin", b.get("coin")),
        "favorite_number": ("favorite_number", str(b.get("favorite_number")) if b.get("favorite_number") is not None else None),
        "letter": ("letter", (b.get("rand_letter") or "").lower() or None),
        "color": ("color", (b.get("rand_color") or "").lower() or None),
        "animal": ("animal", (b.get("rand_animal") or "").lower() or None),
        "city": ("city", (b.get("rand_city") or "").lower() or None),
    }
    for key, (table, ans) in probes.items():
        if not ans or table not in priors:
            continue
        fam_tables = priors[table]          # {family: {answer: prob}}
        probs = {}
        for fam in FAMILY_IDS:
            dist = fam_tables.get(fam)
            if not dist:
                continue
            p = dist.get(ans)
            if p is None:
                # unseen answer: share the published "other" mass over ~8 answers, floor 1%
                p = max(0.01, dist.get("other", 0.0) / 8.0)
            probs[fam] = max(p, 0.005)
        if len(probs) < 2:
            continue
        mean = sum(probs.values()) / len(probs)
        weights = {fam: max(-cap, min(cap, math.log(p / mean))) for fam, p in probs.items()}
        # unknown families get the mean (0 evidence)
        out.append(Evidence(f"random:{table}", f"answer '{ans}' vs reference distributions", weights))
    return out


def evaluate(ctx: Context) -> dict:
    ev: List[Evidence] = []
    f, u, b, ok, gib = ctx.f, ctx.u, ctx.b, ctx.ok, ctx.gib

    # ---------------- Identity layer ----------------
    sp_text = (b.get("system_prompt_raw") or "")
    sp_low = sp_text.lower()
    if b.get("system_prompt_class") == "quoted":
        for pat, fam, label in SYSTEM_PROMPT_SIGNATURES:
            if re.search(pat, sp_low):
                ev.append(Evidence("system_prompt_identity", f"quoted system prompt matches '{label}'", {fam: 4.0}))
                break
        else:
            pa = provider_assertions(sp_text)
            if pa:
                top = max(pa, key=pa.get)
                ev.append(Evidence("system_prompt_mentions", f"quoted system prompt mentions {top}", {PROVIDER_TO_FAMILY.get(top, 'other'): 2.5}))
    elif b.get("system_prompt_class") == "refused":
        ev.append(Evidence("system_prompt_refused", "model refused to quote its system prompt (common for ChatGPT, Gemini, Grok apps; claude.ai usually quotes or says none)", W(openai=0.3, google=0.3, xai=0.3, anthropic=-0.3)))

    ident = b.get("identity_raw") or ""
    pa = provider_assertions(ident)
    if pa:
        total = sum(pa.values())
        for prov, n in pa.items():
            fam = PROVIDER_TO_FAMILY.get(prov, "other")
            w = 3.0 * n / total
            ev.append(Evidence("self_report", f"self-identifies with {prov} ({n} mention(s)){' [hedged]' if b.get('identity_hedged') else ''}", {fam: w}))
    if b.get("identity_hedged") and pa and "anthropic" in pa:
        ev.append(Evidence("self_report_hedge", "hedges about its exact version (typical of Claude, which is not told its version)", W(anthropic=0.5)))

    # Policy vocabulary
    na = (b.get("not_allowed_raw") or "").lower()
    for fam, pats in POLICY_VOCAB.items():
        hits = [p for p in pats if re.search(p, na)]
        if hits:
            ev.append(Evidence("policy_vocab", f"policy answer uses {fam}-style vocabulary: {hits}", {fam: 0.8 if fam != 'meta' else 0.6}))

    # ---------------- Character layer ----------------
    if u.get("narrow_nbsp_count", 0) > 0:
        ev.append(Evidence("narrow_nbsp", f"{u['narrow_nbsp_count']} U+202F narrow no-break space(s): documented quirk of OpenAI o3/o4-mini/GPT-5 outputs", W(openai=3.0, anthropic=-1.0, google=-1.0, meta=-1.0, xai=-0.5, deepseek=-0.5, alibaba=-0.5, mistral=-0.5)))
    if u.get("zero_width_count", 0) or u.get("tag_char_count", 0) or u.get("soft_hyphen_count", 0):
        ev.append(Evidence("hidden_chars", "zero-width / tag / soft-hyphen characters present: a character-level mark (no major provider documents one; check the pasting path)", W()))
    if ctx.has_essay:
        cas = f.get("curly_apostrophe_share", -1)
        cqs = f.get("curly_quote_share", -1)
        if cas >= 0.6 or cqs >= 0.6:
            ev.append(Evidence("curly_quotes", f"typographic quotes/apostrophes dominate (apostrophe share {cas}, quote share {cqs}): ChatGPT habit", W(openai=1.5, anthropic=-0.8, google=-0.4, meta=-0.8, deepseek=-0.6, alibaba=-0.6, mistral=-0.6, xai=-0.3)))
        elif 0 <= cas <= 0.2 and (f.get("n_words", 0) > 80):
            ev.append(Evidence("straight_quotes", "straight ASCII quotes/apostrophes throughout", W(openai=-0.8, anthropic=0.4, google=0.3, meta=0.3, deepseek=0.3, alibaba=0.3, mistral=0.3, xai=0.3)))
        emr = f.get("em_dash_rate", 0)
        if emr >= 10:
            ev.append(Evidence("em_dash_heavy", f"em-dash rate {emr}/1000 words (heavy)", W(openai=1.0, anthropic=0.8, google=0.1, xai=0.3, meta=-0.8, deepseek=-0.3, alibaba=-0.5, mistral=-0.6)))
        elif emr >= 3:
            ev.append(Evidence("em_dash_some", f"em-dash rate {emr}/1000 words", W(openai=0.4, anthropic=0.4, google=0.1, xai=0.2, meta=-0.4, mistral=-0.3)))
        elif f.get("n_words", 0) > 150:
            ev.append(Evidence("em_dash_none", "no em dashes in a long sample", W(openai=-0.8, anthropic=-0.6, meta=0.5, mistral=0.4, alibaba=0.3, deepseek=0.2, google=0.1)))
        if f.get("spaced_hyphen_dash_rate", 0) >= 3:
            ev.append(Evidence("spaced_hyphen_dash", "uses ' - ' spaced hyphens as dashes", W(meta=0.6, mistral=0.5, alibaba=0.4, deepseek=0.3, google=0.3, openai=-0.4, anthropic=-0.3)))
        if f.get("ellipsis_char", 0) > 0 and f.get("ellipsis_dots", 0) == 0:
            ev.append(Evidence("ellipsis_char", "uses the single-character ellipsis (U+2026)", W(openai=0.6, google=0.2, anthropic=-0.3)))
        if f.get("multiplication_sign", 0) > 0:
            ev.append(Evidence("mult_sign", "uses U+00D7 multiplication sign", W(openai=0.3, google=0.3, deepseek=0.2, anthropic=0.1)))

    # ---------------- Formatting layer ----------------
    if ctx.has_essay:
        nw = max(1, f.get("n_words", 1))
        if f.get("headers_total", 0) >= 2:
            ev.append(Evidence("headers", f"{f['headers_total']} markdown headers (h2={f.get('headers_h2')}, h3={f.get('headers_h3')})", W(google=0.6, openai=0.5, anthropic=0.4, deepseek=0.4, alibaba=0.4, meta=-0.2, xai=0.1, mistral=0.1)))
            if f.get("headers_h3", 0) > f.get("headers_h2", 0):
                ev.append(Evidence("h3_preference", "prefers ### headers", W(openai=0.5, deepseek=0.3, alibaba=0.3, anthropic=-0.2)))
            if f.get("headers_h2", 0) > f.get("headers_h3", 0):
                ev.append(Evidence("h2_preference", "prefers ## headers", W(anthropic=0.4, google=0.4, openai=-0.1)))
            if f.get("headers_with_emoji", 0):
                ev.append(Evidence("emoji_headers", "emoji in headers", W(google=0.8, openai=0.6, xai=0.6, deepseek=0.4, anthropic=-1.0)))
        elif nw > 150:
            ev.append(Evidence("no_headers", "no markdown headers in a long sample", W(anthropic=0.4, meta=0.3, mistral=0.3, xai=0.3, openai=-0.2, google=-0.3)))
        if f.get("bold_whole_line", 0) >= 2:
            ev.append(Evidence("bold_pseudo_headers", "bold lines used as section headers", W(openai=0.6, meta=0.5, google=0.3, alibaba=0.3, anthropic=-0.3)))
        br = f.get("bold_rate", 0)
        if br >= 25:
            ev.append(Evidence("bold_heavy", f"bold rate {br}/1000 words (heavy)", W(google=0.6, openai=0.4, deepseek=0.4, alibaba=0.4, meta=0.3, anthropic=-0.6, xai=0.2)))
        elif br == 0 and nw > 150:
            ev.append(Evidence("no_bold", "no bold at all in a long sample", W(anthropic=0.6, mistral=0.3, meta=0.1, openai=-0.5, google=-0.6)))
        if f.get("has_table"):
            ev.append(Evidence("table", "uses a markdown table", W(openai=1.0, google=0.5, deepseek=0.4, alibaba=0.3, anthropic=-0.4, meta=-0.5, xai=0.2, mistral=-0.3)))
        if f.get("bullet_lines", 0) and f.get("bullet_star", 0) > f.get("bullet_dash", 0):
            ev.append(Evidence("star_bullets", "uses '*' bullets", W(google=1.2, meta=0.4, mistral=0.3, openai=-0.6, anthropic=-0.8, deepseek=-0.3)))
        if f.get("bullet_dot", 0):
            ev.append(Evidence("dot_bullets", "uses '•' bullets", W(meta=0.5, mistral=0.3, openai=0.1, anthropic=-0.3, google=-0.2)))
        if f.get("numbered_paren_style", 0):
            ev.append(Evidence("paren_numbering", "uses '1)' numbering", W(meta=0.3, mistral=0.3, xai=0.2, openai=-0.2, anthropic=-0.2)))
        if f.get("bold_colon_inside", 0) >= 2 and f.get("bold_colon_outside", 0) == 0:
            ev.append(Evidence("bold_colon_inside", "'**Term:** text' list items (colon inside bold)", W(openai=0.4, google=0.4, deepseek=0.3, alibaba=0.3, anthropic=0.1)))
        if f.get("bold_colon_outside", 0) >= 2 and f.get("bold_colon_inside", 0) == 0:
            ev.append(Evidence("bold_colon_outside", "'**Term**: text' list items (colon outside bold)", W(anthropic=0.5, meta=0.3, mistral=0.3, xai=0.2, openai=-0.3)))
        if f.get("emoji_line_starts", 0) >= 2 or f.get("emoji_rate", 0) >= 8:
            ev.append(Evidence("emoji_heavy", f"emoji-heavy formatting ({f.get('emoji_count')} emoji)", W(google=0.8, openai=0.5, xai=0.7, deepseek=0.6, alibaba=0.5, anthropic=-1.2, meta=0.2, mistral=-0.2)))
        elif f.get("emoji_count", 0) == 0 and nw > 150:
            ev.append(Evidence("no_emoji", "no emoji", W(anthropic=0.4, mistral=0.2, meta=0.1, openai=0.0, google=-0.3, xai=-0.2, deepseek=-0.2)))
        if f.get("horizontal_rules", 0) >= 1:
            ev.append(Evidence("horizontal_rules", "uses --- horizontal rules", W(openai=0.7, google=0.3, deepseek=0.3, alibaba=0.3, anthropic=-0.4, meta=-0.2)))
        if f.get("summary_section"):
            ev.append(Evidence("summary_section", "ends with a summary/takeaways section", W(google=0.5, openai=0.4, deepseek=0.4, alibaba=0.4, meta=0.3, anthropic=-0.2)))
        if f.get("share_one_line_paragraphs", 0) >= 0.5 and f.get("n_paragraphs", 0) >= 6 and f.get("list_share_of_lines", 0) < 0.4:
            ev.append(Evidence("one_line_paragraphs", f"{int(100*f['share_one_line_paragraphs'])}% of paragraphs are single short lines (punchy GPT-5 style)", W(openai=1.0, xai=0.4, anthropic=-0.2, google=-0.3, meta=-0.4)))

        # Rhetoric
        rh_gpt = f.get("rh_antithesis_not_but", 0) + f.get("rh_not_x_period_its_y", 0) + 2 * f.get("rh_tricolon_fragments", 0) + f.get("rh_the_catch_question", 0) + f.get("rh_heres_the_thing", 0)
        if rh_gpt >= 3:
            ev.append(Evidence("gpt5_rhetoric", f"{rh_gpt} antithesis/tricolon/'the catch?'/'here's the thing' constructions", W(openai=1.6, anthropic=0.3, xai=0.4, google=-0.3, meta=-0.6, mistral=-0.5, alibaba=-0.4, deepseek=-0.3)))
        elif rh_gpt >= 1:
            ev.append(Evidence("some_rhetoric", f"{rh_gpt} antithesis/tricolon construction(s)", W(openai=0.6, anthropic=0.3, xai=0.2, meta=-0.3)))
        if f.get("rh_sentence_initial_and_but_rate", 0) >= 8:
            ev.append(Evidence("conjunction_starts", "many sentences start with And/But/So", W(openai=0.5, xai=0.5, anthropic=0.3, meta=-0.3, google=-0.2)))
        if f.get("rh_think_of_it", 0):
            ev.append(Evidence("think_of_it", "'think of it like' / 'imagine' analogy framing", W(openai=0.4, google=0.5, xai=0.3, anthropic=0.1)))
        if f.get("rh_worth_noting", 0) >= 2:
            ev.append(Evidence("worth_noting", "'it's worth noting / keep in mind / that said' hedges", W(google=0.4, openai=0.3, anthropic=0.3, deepseek=0.2)))
        if f.get("rh_bottom_line", 0):
            ev.append(Evidence("bottom_line", "'bottom line / in short / key takeaway' phrasing", W(openai=0.4, google=0.4, xai=0.3, deepseek=0.2)))
        if f.get("rh_parenthetical_rate", 0) >= 10:
            ev.append(Evidence("parentheticals", "frequent parenthetical asides", W(anthropic=0.4, openai=0.2, xai=0.2, google=-0.2)))
        if f.get("rh_contractions_rate", 0) >= 25:
            ev.append(Evidence("contractions", "contraction-heavy, conversational register", W(openai=0.3, anthropic=0.4, xai=0.5, google=0.0, meta=-0.2, deepseek=-0.4, alibaba=-0.5, mistral=-0.3)))
        elif f.get("rh_contractions_rate", 0) <= 5 and nw > 150:
            ev.append(Evidence("no_contractions", "formal register, almost no contractions", W(deepseek=0.5, alibaba=0.5, mistral=0.3, google=0.2, meta=0.2, openai=-0.3, anthropic=-0.4, xai=-0.5)))
        if f.get("rh_exclamations_rate", 0) >= 8:
            ev.append(Evidence("exclamations", "exclamation-heavy", W(google=0.4, meta=0.5, xai=0.5, alibaba=0.4, deepseek=0.4, openai=0.1, anthropic=-0.5)))

        # Openers / closers
        op = f.get("opener")
        opener_w = {
            "certainly": W(openai=0.5, alibaba=1.2, deepseek=1.2, google=0.5, anthropic=-1.0, xai=-0.5),
            "sure": W(openai=0.5, mistral=0.6, alibaba=0.5, deepseek=0.4, google=0.3, anthropic=-0.3),
            "absolutely": W(openai=0.6, google=0.8, xai=0.3, anthropic=-0.3),
            "of_course": W(google=0.7, mistral=0.5, alibaba=0.5, anthropic=-0.3),
            "great_question": W(google=0.6, openai=0.5, meta=0.4, anthropic=-0.4),
            "heres": W(anthropic=0.4, openai=0.4, google=0.3, deepseek=0.2),
            "happy_to": W(anthropic=0.6, meta=0.6, alibaba=0.3),
            "okay_alright": W(xai=1.0, meta=0.3, openai=0.2),
            "lets": W(xai=0.5, openai=0.4, google=0.4),
            "youre_right": W(anthropic=1.0),
            "greeting": W(meta=0.5, alibaba=0.3, google=0.3),
            "title_or_header": W(google=0.5, openai=0.4, deepseek=0.4, alibaba=0.3, anthropic=0.2),
            "direct": W(anthropic=0.4, openai=0.2, mistral=0.2),
        }
        if op in opener_w:
            ev.append(Evidence("opener", f"opens with '{f.get('first_words')}' ({op})", opener_w[op]))
        if f.get("closer_offer_would_you_like") or f.get("closer_offer_want_me_to"):
            ev.append(Evidence("closer_offer", f"ends with an offer to do more: '...{f.get('last_words')}'", W(openai=1.6, google=0.4, anthropic=0.2, xai=0.2, meta=-0.6, mistral=-0.4, deepseek=-0.2, alibaba=-0.2)))
        if f.get("closer_let_me_know") or f.get("closer_hope_this_helps") or f.get("closer_any_other_questions") or f.get("closer_feel_free"):
            ev.append(Evidence("closer_assistant", f"ends with 'let me know / hope this helps / feel free': '...{f.get('last_words')}'", W(meta=1.2, alibaba=0.9, deepseek=0.9, mistral=0.7, google=0.4, xai=0.3, openai=-0.3, anthropic=-0.3)))
        if f.get("closer_emoji_signoff"):
            ev.append(Evidence("emoji_signoff", "signs off with an emoji", W(deepseek=1.5, alibaba=1.2, google=0.4, xai=0.4, openai=-0.3, anthropic=-1.2)))
        if f.get("closer_ends_with_question") and not (f.get("closer_offer_would_you_like") or f.get("closer_offer_want_me_to")):
            ev.append(Evidence("ends_question", "ends with a question", W(openai=0.4, xai=0.4, google=0.3, anthropic=0.2)))

        # Lexicon
        lex: Dict[str, List[str]] = {}
        for k, v in f.items():
            if k.startswith("lex:"):
                _, fam, ph = k.split(":", 2)
                lex.setdefault(fam, []).append(f"{ph}x{v}" if v > 1 else ph)
        for fam, hits in lex.items():
            n = len(hits)
            ev.append(Evidence(f"lexicon:{fam}", "phrases: " + ", ".join(hits[:8]), {fam: round(min(1.5, 0.35 * n), 2)}))

        # Length
        if nw >= 700:
            ev.append(Evidence("very_long", f"{nw} words for a short-guide request", W(google=0.5, openai=0.3, deepseek=0.3, alibaba=0.3, anthropic=-0.3, mistral=-0.2)))
        elif nw <= 220:
            ev.append(Evidence("concise", f"{nw} words (concise)", W(anthropic=0.5, mistral=0.3, xai=0.1, google=-0.4, openai=-0.1, deepseek=-0.2)))

    # ---------------- Probe-answer layer ----------------
    # Capability tier
    checks = [b.get("strawberry_correct"), b.get("nine_eleven_correct"), b.get("reverse_correct"), b.get("multiply_correct"), b.get("months_28_correct")]
    answered = [c for c in checks if c is not None]
    tier = None
    if answered:
        n_ok = sum(answered)
        tier = "frontier/reasoning" if n_ok >= 4 else ("mid" if n_ok >= 2 else "small/old")
        if tier == "small/old":
            ev.append(Evidence("capability_low", f"{n_ok}/{len(answered)} trick questions correct: small or older model", W(meta=0.5, mistral=0.5, alibaba=0.3, other=0.6, openai=-0.4, anthropic=-0.6, google=-0.3)))
        elif tier == "frontier/reasoning":
            ev.append(Evidence("capability_high", f"{n_ok}/{len(answered)} trick questions correct: frontier-class model", W(openai=0.2, anthropic=0.3, google=0.2, xai=0.1, deepseek=0.1, meta=-0.3, mistral=-0.3, other=-0.3)))
    if b.get("months_28_both"):
        ev.append(Evidence("months_28_both", "explains both readings of the 28-days riddle", W(anthropic=0.3, openai=0.2)))

    # Gibberish turn
    if gib:
        if gib.get("gib_emoji"):
            ev.append(Evidence("gib_emoji", "emoji in reply to gibberish", W(deepseek=0.8, alibaba=0.8, google=0.3, xai=0.3, anthropic=-0.8, openai=-0.2)))
        first = (gib.get("gib_first_words") or "").lower()
        if re.search(r"^(it looks like|looks like|it seems like|seems like)", first):
            ev.append(Evidence("gib_looks_like", f"replies '{gib.get('gib_first_words')}'", W(openai=0.5, deepseek=0.4, alibaba=0.3, meta=0.3, anthropic=0.1)))
        if re.search(r"^(i'm not sure|i am not sure|i don't|hmm|that looks|that doesn't)", first):
            ev.append(Evidence("gib_not_sure", f"replies '{gib.get('gib_first_words')}'", W(anthropic=0.6, xai=0.2)))
        if re.search(r"^(i'm sorry|sorry|i apologize)", first):
            ev.append(Evidence("gib_sorry", f"apologetic reply '{gib.get('gib_first_words')}'", W(google=0.6, meta=0.4, mistral=0.4, alibaba=0.3, anthropic=-0.3, xai=-0.3)))
        if re.search(r"\b(party|cat|smash|mash|wild|fun|ha|lol|whoa|yo)\b", (gib.get("gib_first_words") or "").lower()):
            ev.append(Evidence("gib_humor", "jokes about the gibberish", W(xai=1.0, openai=0.2, anthropic=0.1)))
        if gib.get("gib_words", 0) >= 60:
            ev.append(Evidence("gib_long", "long reply to gibberish", W(google=0.4, alibaba=0.3, deepseek=0.3, meta=0.3, anthropic=-0.3, openai=-0.2)))
        elif 0 < gib.get("gib_words", 0) <= 15:
            ev.append(Evidence("gib_short", "very short reply to gibberish", W(anthropic=0.4, xai=0.3, openai=0.1)))

    # "ok" turn
    if ok:
        form = ok.get("ok_form")
        form_w = {
            "exact_ok": W(anthropic=0.5, meta=0.2, mistral=0.2, google=0.1),
            "Ok": W(openai=0.3, google=0.3, deepseek=0.2),
            "OK": W(google=0.4, meta=0.3, alibaba=0.3, mistral=0.3, deepseek=0.3, openai=0.1),
            "ok_with_punct": W(openai=0.5, google=0.3, deepseek=0.3, alibaba=0.3),
            "okay_variant": W(meta=0.4, google=0.2),
            "extra_text": W(meta=0.5, alibaba=0.4, deepseek=0.3, google=0.2, anthropic=-0.3),
        }
        if form in form_w:
            ev.append(Evidence("ok_form", f"'reply with only ok' produced {ok.get('ok_exact')!r}", form_w[form]))

    # Dataset-size meta probe (open-weight models often state a figure)
    dsn = (b.get("dataset_size_number") or "").lower().replace(",", "")
    if dsn:
        if re.search(r"\b15\s*(?:trillion|t)\b", dsn):
            ev.append(Evidence("dataset_size", f"claims '{dsn}' (Llama 3 model-card figure)", W(meta=1.0, openai=-0.3, anthropic=-0.3, google=-0.3)))
        elif re.search(r"\b36\s*(?:trillion|t)\b", dsn):
            ev.append(Evidence("dataset_size", f"claims '{dsn}' (Qwen3 figure)", W(alibaba=1.0, openai=-0.3, anthropic=-0.3)))
        elif re.search(r"\b18\s*(?:trillion|t)\b", dsn):
            ev.append(Evidence("dataset_size", f"claims '{dsn}' (Qwen2.5 figure)", W(alibaba=0.8, openai=-0.2, anthropic=-0.2)))
        elif re.search(r"\b14\.8\s*(?:trillion|t)\b", dsn):
            ev.append(Evidence("dataset_size", f"claims '{dsn}' (DeepSeek-V3 figure)", W(deepseek=1.0, openai=-0.3, anthropic=-0.3)))
        elif re.search(r"\b(?:570|45)\s*(?:gb|gigabytes)\b|\b(?:300|499)\s*(?:billion|b)\b", dsn):
            ev.append(Evidence("dataset_size", f"claims '{dsn}' (GPT-3 era figure, typical of models trained on ChatGPT transcripts)", W(other=0.5, meta=0.3, alibaba=0.3, mistral=0.3, openai=0.2)))
        else:
            ev.append(Evidence("dataset_size", f"states a figure: '{dsn}'", W(other=0.3, meta=0.3, alibaba=0.3, mistral=0.3, deepseek=0.2, openai=-0.2, anthropic=-0.3, google=-0.2)))
    elif b.get("dataset_size_declines"):
        ev.append(Evidence("dataset_size", "declines to give a training-set size (closed-model behaviour)", W(openai=0.25, anthropic=0.25, google=0.25, xai=0.1, meta=-0.2, alibaba=-0.2, mistral=-0.1)))

    if b.get("climate_answer") == "true" and b.get("climate_words", 0) <= 3:
        ev.append(Evidence("climate_tf", "bare 'True' to the true/false probe", W(anthropic=0.2, openai=0.2, mistral=0.2, xai=0.1)))
    elif b.get("climate_answer") == "true" and b.get("climate_words", 0) >= 25:
        ev.append(Evidence("climate_tf", f"'True' plus {b.get('climate_words')} words of elaboration", W(google=0.4, deepseek=0.3, alibaba=0.3, meta=0.3, anthropic=-0.1)))
    elif b.get("climate_answer") == "false":
        ev.append(Evidence("climate_tf", "answers 'False' to the climate true/false probe", W(xai=0.6, other=0.3, anthropic=-0.3, google=-0.3)))

    mix = ctx.mix
    if mix:
        if mix.get("mix_mentions_ai"):
            ev.append(Evidence("mix_ai_disclaimer", "mixed-language greeting answered with an 'as an AI' disclaimer", W(meta=0.6, alibaba=0.5, deepseek=0.4, mistral=0.3, google=0.2, anthropic=-0.4, openai=-0.2, xai=-0.2)))
        if mix.get("mix_emoji"):
            ev.append(Evidence("mix_emoji", "emoji in the greeting reply", W(deepseek=0.6, alibaba=0.6, google=0.3, xai=0.3, openai=0.1, anthropic=-0.6)))
        if mix.get("mix_trilingual"):
            ev.append(Evidence("mix_trilingual", "replies in all three languages", W(openai=0.4, google=0.3, anthropic=0.3, xai=0.2, deepseek=0.1)))
        elif mix.get("mix_dominant") == "en":
            ev.append(Evidence("mix_english_only", "answers the mixed-language greeting in English only", W(meta=0.4, mistral=0.3, alibaba=0.2, deepseek=0.2, other=0.2)))
        elif mix.get("mix_dominant") in ("fr", "es"):
            ev.append(Evidence("mix_switches_language", f"switches into {mix.get('mix_dominant')}", W(google=0.3, openai=0.2, anthropic=0.2, mistral=0.3)))
        if mix.get("mix_words", 0) >= 60:
            ev.append(Evidence("mix_long", "long reply to a one-line greeting", W(google=0.3, deepseek=0.3, alibaba=0.3, meta=0.2, anthropic=-0.3, openai=-0.1)))

    # Random-choice priors
    ev.extend(random_choice_evidence(ctx, load_random_priors()))

    # ---------------- Aggregate ----------------
    scores = {fam: FAMILIES[fam]["prior"] for fam in FAMILY_IDS}
    for e in ev:
        for fam, w in e.weights.items():
            if fam in scores:
                scores[fam] += w
    mx = max(scores.values())
    exp = {fam: math.exp(s - mx) for fam, s in scores.items()}
    z = sum(exp.values())
    probs = {fam: exp[fam] / z for fam in FAMILY_IDS}
    ranked = sorted(FAMILY_IDS, key=lambda k: -scores[k])
    top = ranked[0]
    margin = scores[ranked[0]] - scores[ranked[1]]
    confidence = "high" if probs[top] >= 0.85 and margin >= 2.5 else ("medium" if probs[top] >= 0.6 else "low")
    return {
        "scores": scores, "probs": probs, "ranked": ranked, "top": top,
        "confidence": confidence, "margin": round(margin, 2), "evidence": ev, "tier": tier,
    }


def version_candidates(family: str, ctx: Context) -> List[dict]:
    """Narrow the version using self-report, cutoffs and capability tier."""
    b = ctx.b
    cands = []
    names = [n for n in (b.get("identity_models") or []) + (b.get("system_prompt_models") or [])]
    cutoff = b.get("identity_cutoff") or b.get("date_event_cutoff")
    for fam, model, release, train_cut, said_cut in VERSIONS:
        if fam != family:
            continue
        score = 0.0
        why = []
        ml = model.lower()
        for n in names:
            key = n.replace("-", " ").replace("claude ", "")
            toks = [t for t in re.split(r"[\s/]+", key) if t]
            if toks and all(t in ml.replace("-", " ") for t in toks):
                score += 3
                why.append(f"self-reported '{n}'")
                break
        if cutoff:
            if said_cut and cutoff[:7] == said_cut:
                score += 2
                why.append(f"stated cutoff {cutoff} matches what this version usually says")
            elif train_cut and cutoff[:4] == train_cut[:4]:
                score += 0.7
                why.append(f"stated cutoff year {cutoff[:4]} matches training cutoff {train_cut}")
            elif train_cut and cutoff[:4] > train_cut[:4]:
                score -= 1.5
                why.append(f"stated cutoff {cutoff} is later than this version's {train_cut}")
        cands.append({"model": model, "release": release, "score": score, "why": why})
    cands.sort(key=lambda c: -c["score"])
    return cands[:5]


def model_random_match(ctx: Context, priors: dict | None = None, top: int = 6) -> List[dict]:
    """Rank reference models by the likelihood of the observed random-choice answers.
    Only used as a version hint; one sample per cell is weak evidence."""
    priors = priors or load_random_priors()
    models = priors.get("models", {})
    b = ctx.b
    obs = {
        "1-10": str(b.get("rand_1_10")) if b.get("rand_1_10") is not None else None,
        "1-100": str(b.get("rand_1_100")) if b.get("rand_1_100") is not None else None,
        "favorite_number": str(b.get("favorite_number")) if b.get("favorite_number") is not None else None,
        "coin": b.get("coin"),
        "color": (b.get("rand_color") or "").lower() or None,
        "letter": (b.get("rand_letter") or "").lower() or None,
        "animal": (b.get("rand_animal") or "").lower() or None,
        "city": (b.get("rand_city") or "").lower() or None,
    }
    obs = {k: v for k, v in obs.items() if v}
    if not obs:
        return []
    out = []
    for mid, m in models.items():
        ll = 0.0
        matched = []
        for cell, ans in obs.items():
            dist = m["cells"].get(cell)
            if not dist:
                continue
            p = dist.get(ans)
            if p is None:
                p = max(0.01, dist.get("other", 0.0) / 8.0)
            else:
                matched.append(f"{cell}={ans}")
            ll += math.log(max(p, 0.005))
        out.append({"model": mid, "family": m["family"], "loglik": round(ll, 2), "matched": matched, "n_cells": len([c for c in obs if c in m["cells"]])})
    out.sort(key=lambda d: -d["loglik"])
    return out[:top]
