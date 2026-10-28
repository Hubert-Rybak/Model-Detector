"""Stylometric and formatting features for a free-form LLM response.

Returns a flat dict of numbers (rates are per 1,000 words unless the name
says otherwise) plus a few small lists used by the report. Pure stdlib.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from typing import Dict, List

from .unicode_scan import scan as unicode_scan

CODE_FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.M)
BOLD_RE = re.compile(r"\*\*([^*\n][^*\n]*?)\*\*|__([^_\n][^_\n]*?)__")
ITALIC_RE = re.compile(r"(?<![*\w])\*(?!\*)([^*\n]+?)\*(?!\*)|(?<![_\w])_(?!_)([^_\n]+?)_(?!_)")
BULLET_RE = re.compile(r"^(\s*)([-*+•–—◦▪‣])\s+(.*)$", re.M)
NUMBERED_RE = re.compile(r"^(\s*)(\d+)([.)])\s+(.*)$", re.M)
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$", re.M)
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)
HR_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", re.M)
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?", re.M)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“(\[])|\n{2,}")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")

OPENERS = [
    ("certainly", r"^\s*certainly[!,.]"),
    ("sure", r"^\s*sure[!,.]"),
    ("absolutely", r"^\s*absolutely[!,.]"),
    ("of_course", r"^\s*of course[!,.]"),
    ("great_question", r"^\s*(great|good|excellent|fantastic|interesting) question"),
    ("heres", r"^\s*(here'?s|here is|here are)\b"),
    ("happy_to", r"^\s*i('d| would) be (happy|glad) to|^\s*i'?m happy to"),
    ("okay_alright", r"^\s*(okay|ok|alright|all right)[!,.]"),
    ("lets", r"^\s*let'?s\b"),
    ("youre_right", r"^\s*you'?re (absolutely |completely |totally )?right"),
    ("greeting", r"^\s*(hi|hello|hey)\b"),
    ("title_or_header", r"^\s*(#{1,6}\s|\*\*[^*]+\*\*\s*$)"),
    ("direct", r"^\s*[A-Z][a-z]"),
]

CLOSERS = [
    ("offer_would_you_like", r"would you like( me)?\b"),
    ("offer_want_me_to", r"\b(want|like) me to\b|\bdo you want me\b|\bshall i\b|\bshould i\b"),
    ("offer_if_youd_like", r"\bif you('d| would) like\b|\bif you want\b|\bif you need\b|\bif you'?re interested\b"),
    ("let_me_know", r"\blet me know\b"),
    ("feel_free", r"\bfeel free\b"),
    ("hope_this_helps", r"\bhope (this|that|it) helps\b"),
    ("happy_to_help", r"\bhappy to (help|assist|elaborate|dive|go)\b"),
    ("any_other_questions", r"\bany (other|further|more) questions\b"),
    ("ends_with_question", r"\?\s*$"),
    ("emoji_signoff", r"[\U0001F300-\U0001FAFF☀-➿]\s*$"),
]

RHETORIC = {
    # "It's not X, it's Y" / "isn't just X — it's Y" / "not because X but because Y"
    "antithesis_not_but": r"\b(?:is|it'?s|that'?s|this is|was|are|were|isn'?t|aren'?t|wasn'?t|not)\s+(?:just|only|merely|simply|about|really)?\s*[^.!?;:\n]{2,70}?(?:—|–|,|;|\.)\s*(?:it'?s|but|rather|that'?s)\b",
    "not_x_period_its_y": r"\b(?:Not|Isn'?t|It isn'?t)\b[^.!?\n]{2,60}[.!]\s+(?:It'?s|That'?s)\b",
    "tricolon_fragments": r"\b(?:No|Not)\s[^.!?\n]{1,40}[.!]\s+(?:No|Not)\s[^.!?\n]{1,40}[.!]\s+(?:Just|Only|Simply)\b",
    "the_catch_question": r"\b(?:The|Your|My)\s+(?:catch|result|kicker|upshot|twist|problem|answer|takeaway|bottom line|short version|good news|bad news|key|trick|difference|reason|cost|risk|downside|upside)\?",
    "heres_the_thing": r"\bhere'?s (?:the thing|why|how|what|where|the catch|the deal|the kicker|a quick|the short version|the breakdown|the gist)\b",
    "think_of_it": r"\b(?:think of (?:it|this|them) (?:like|as)|imagine (?:you|a|that|this|if))\b",
    "break_it_down": r"\b(?:let'?s|i'?ll)?\s*break (?:it|this|that|things) down\b",
    "in_other_words": r"\bin other words\b",
    "bottom_line": r"\b(?:bottom line|the takeaway|key takeaways?|tl;?dr|in short|in summary|in a nutshell|to sum up|in essence|at its core|at the end of the day|put simply|simply put|long story short)\b",
    "worth_noting": r"\b(?:it'?s worth (?:noting|mentioning|remembering)|note that|keep in mind|it'?s important to (?:note|remember|understand)|importantly|notably|crucially|that said|that being said|with that said)\b",
    "dash_aside": r"\s—\s[^—\n]{3,60}\s—\s",
    "colon_lead_bullet": r"^\s*(?:[-*•]|\d+[.)])\s+\*\*[^*\n]{1,60}\*\*\s*[:—–-]",
    "bold_colon_lead": r"^\s*(?:[-*•]|\d+[.)])\s+\*\*[^*\n]{1,60}:\*\*",
    "rhetorical_q_then_answer": r"\?\s+(?:Because|Yes|No|Not|It|That|Simple|Exactly|Absolutely|Well)\b",
    "sentence_initial_and_but": r"(?:^|[.!?]\s+)(?:And|But|So|Because|Which|Or)\s+[a-z]",
    "one_word_sentence": r"(?:^|[.!?]\s+)[A-Z][a-z]{1,12}[.!]",
    "parenthetical": r"\([^()\n]{3,80}\)",
    "fragment_lines": r"^(?:[A-Z][^.!?\n]{2,40})$",
    "second_person_you": r"\byou(?:'re|'ll|'ve|'d|r)?\b",
    "first_person_i": r"\bI(?:'m|'d|'ll|'ve)?\b",
    "we_us": r"\b(?:we|us|our)\b",
    "exclamations": r"!",
    "questions": r"\?",
    "semicolons": r";",
    "colons_in_prose": r"[A-Za-z]:\s",
    "quoted_phrases": r"[\"“][^\"”\n]{2,60}[\"”]",
    "numbers_with_units": r"\b\d+(?:[.,]\d+)?\s?(?:%|km|mi|kg|lb|ms|s|m|cm|mm|°[CF]?|px|GB|MB|KB|TB|Hz|kHz|MHz|GHz|W|kW|V|A|mAh)\b",
    "percent_sign": r"\d\s?%",
    "contractions": r"\b\w+(?:n't|'re|'ve|'ll|'d|'m|'s)\b|\b\w+(?:n’t|’re|’ve|’ll|’d|’m|’s)\b",
}

SUMMARY_HEADERS = r"^(?:#{1,6}\s*)?(?:\*\*)?\s*(?:summary|key takeaways?|tl;?dr|bottom line|in summary|conclusion|final thoughts|wrap[- ]?up|quick recap|recap|the short version|overview|next steps|what this means)\b"


def strip_code(text: str) -> str:
    return INLINE_CODE_RE.sub(" ", CODE_FENCE_RE.sub("\n", text))


def _rate(n: int, words: int) -> float:
    return round(1000.0 * n / words, 2) if words else 0.0


def sentences_of(prose: str) -> List[str]:
    # Remove markdown list/heading markers so they don't fragment sentences
    cleaned = re.sub(r"^\s*(?:#{1,6}\s+|[-*+•]\s+|\d+[.)]\s+|>\s*)", "", prose, flags=re.M)
    cleaned = re.sub(r"\*\*|__", "", cleaned)
    parts = [s.strip() for s in SENTENCE_SPLIT_RE.split(cleaned) if s and s.strip()]
    return [p for p in parts if len(WORD_RE.findall(p)) >= 1]


def extract(text: str, phrases: Dict[str, List[str]] | None = None) -> dict:
    """Compute features. ``phrases`` is an optional {family: [phrase,...]} lexicon;
    each phrase occurrence count is returned under ``lex:<family>:<phrase>``."""
    f: Dict[str, object] = {}
    raw = text
    prose = strip_code(raw)
    lower = prose.lower()
    words = WORD_RE.findall(prose)
    n_words = len(words)
    f["n_chars"] = len(raw)
    f["n_words"] = n_words
    lines = raw.splitlines()
    f["n_lines"] = len(lines)
    paragraphs = [p for p in re.split(r"\n\s*\n", raw.strip()) if p.strip()]
    f["n_paragraphs"] = len(paragraphs)
    para_lens = [len(WORD_RE.findall(p)) for p in paragraphs] or [0]
    f["para_words_mean"] = round(statistics.mean(para_lens), 1)
    f["para_words_max"] = max(para_lens)
    f["share_one_line_paragraphs"] = round(sum(1 for p in paragraphs if "\n" not in p.strip() and len(WORD_RE.findall(p)) < 25) / max(1, len(paragraphs)), 2)

    # --- Markdown structure ---
    headers = HEADER_RE.findall(raw)
    f["headers_total"] = len(headers)
    for lvl in range(1, 5):
        f[f"headers_h{lvl}"] = sum(1 for h, _ in headers if len(h) == lvl)
    header_texts = [t for _, t in headers]
    f["headers_title_case_share"] = round(sum(1 for t in header_texts if _is_title_case(t)) / len(header_texts), 2) if header_texts else 0.0
    f["headers_with_colon"] = sum(1 for t in header_texts if t.rstrip().endswith(":"))
    f["headers_with_emoji"] = sum(1 for t in header_texts if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", t))
    f["headers_numbered"] = sum(1 for t in header_texts if re.match(r"^\d+[.)]?\s", t))
    f["bold_spans"] = len(BOLD_RE.findall(raw))
    f["bold_rate"] = _rate(f["bold_spans"], n_words)
    f["bold_whole_line"] = len(re.findall(r"^\s*\*\*[^*\n]+\*\*:?\s*$", raw, re.M))
    f["italic_spans"] = len(ITALIC_RE.findall(prose))
    bullets = BULLET_RE.findall(raw)
    f["bullet_lines"] = len(bullets)
    marker_counts = Counter(m for _, m, _ in bullets)
    f["bullet_dash"] = marker_counts.get("-", 0)
    f["bullet_star"] = marker_counts.get("*", 0)
    f["bullet_plus"] = marker_counts.get("+", 0)
    f["bullet_dot"] = marker_counts.get("•", 0)
    f["bullet_endash"] = marker_counts.get("–", 0) + marker_counts.get("—", 0)
    f["bullet_nested"] = sum(1 for ind, _, _ in bullets if len(ind.expandtabs(4)) >= 2)
    numbered = NUMBERED_RE.findall(raw)
    f["numbered_lines"] = len(numbered)
    f["numbered_paren_style"] = sum(1 for _, _, sep, _ in numbered if sep == ")")
    f["numbered_restart_1"] = sum(1 for _, num, _, _ in numbered if num == "1")
    f["list_items_total"] = f["bullet_lines"] + f["numbered_lines"]
    f["list_share_of_lines"] = round(f["list_items_total"] / max(1, len([l for l in lines if l.strip()])), 2)
    f["bold_lead_in_items"] = len(re.findall(RHETORIC["colon_lead_bullet"], raw, re.M)) + len(re.findall(RHETORIC["bold_colon_lead"], raw, re.M))
    f["bold_colon_inside"] = len(re.findall(RHETORIC["bold_colon_lead"], raw, re.M))     # "**Term:** text"
    f["bold_colon_outside"] = len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s+\*\*[^*\n:]{1,60}\*\*:", raw, re.M))  # "**Term**: text"
    f["table_rows"] = len(TABLE_ROW_RE.findall(raw))
    f["has_table"] = int(bool(TABLE_SEP_RE.search(raw)))
    f["code_fences"] = len(CODE_FENCE_RE.findall(raw))
    f["code_fence_langs"] = sorted(set(re.findall(r"```([A-Za-z0-9_+-]+)", raw)))
    f["inline_code"] = len(INLINE_CODE_RE.findall(raw))
    f["horizontal_rules"] = len(HR_RE.findall(raw))
    f["blockquotes"] = len(BLOCKQUOTE_RE.findall(raw))
    f["summary_section"] = int(bool(re.search(SUMMARY_HEADERS, raw, re.I | re.M)))
    f["emoji_line_starts"] = len(re.findall(r"^\s*[\U0001F300-\U0001FAFF☀-➿✅❌\U0001F539\U0001F538]", raw, re.M))

    # --- Sentences ---
    sents = sentences_of(prose)
    s_lens = [len(WORD_RE.findall(s)) for s in sents] or [0]
    f["n_sentences"] = len(sents)
    f["sent_len_mean"] = round(statistics.mean(s_lens), 1)
    f["sent_len_std"] = round(statistics.pstdev(s_lens), 1) if len(s_lens) > 1 else 0.0
    f["sent_len_max"] = max(s_lens)
    f["share_short_sentences"] = round(sum(1 for n in s_lens if n <= 6) / len(s_lens), 2)
    f["share_long_sentences"] = round(sum(1 for n in s_lens if n >= 30) / len(s_lens), 2)
    f["type_token_ratio"] = round(len(set(w.lower() for w in words)) / n_words, 3) if n_words else 0.0
    f["avg_word_len"] = round(sum(len(w) for w in words) / n_words, 2) if n_words else 0.0
    f["share_long_words"] = round(sum(1 for w in words if len(w) >= 9) / n_words, 3) if n_words else 0.0

    # --- Openers / closers ---
    first_line = next((l for l in lines if l.strip()), "")
    f["opener"] = next((name for name, pat in OPENERS if re.search(pat, first_line, re.I)), "other")
    f["first_words"] = " ".join(first_line.split()[:8])
    tail = prose[-400:]
    for name, pat in CLOSERS:
        f[f"closer_{name}"] = int(bool(re.search(pat, tail, re.I)))
    f["last_words"] = " ".join(prose.strip().split()[-12:])

    # --- Rhetoric / punctuation ---
    for name, pat in RHETORIC.items():
        flags = re.I | re.M if name not in {"sentence_initial_and_but", "one_word_sentence", "first_person_i", "not_x_period_its_y", "tricolon_fragments", "the_catch_question", "fragment_lines"} else re.M
        n = len(re.findall(pat, prose, flags))
        f[f"rh_{name}"] = n
        f[f"rh_{name}_rate"] = _rate(n, n_words)

    # --- Character-level habits (from unicode scan) ---
    u = unicode_scan(raw)
    f["em_dash_rate"] = _rate(u.em_dash, n_words)
    f["en_dash_rate"] = _rate(u.en_dash, n_words)
    f["spaced_em_dash"] = u.spaced_em_dash
    f["unspaced_em_dash"] = u.unspaced_em_dash
    f["spaced_hyphen_dash_rate"] = _rate(u.spaced_hyphen_as_dash, n_words)
    f["double_hyphen"] = u.double_hyphen
    f["curly_quote_share"] = round(u.curly_double_quotes / (u.curly_double_quotes + u.straight_double_quotes), 2) if (u.curly_double_quotes + u.straight_double_quotes) else -1
    f["curly_apostrophe_share"] = round(u.curly_apostrophes / (u.curly_apostrophes + u.straight_apostrophes), 2) if (u.curly_apostrophes + u.straight_apostrophes) else -1
    f["ellipsis_char"] = u.ellipsis_char
    f["ellipsis_dots"] = u.ellipsis_dots
    f["multiplication_sign"] = u.multiplication_sign
    f["arrows"] = u.arrows
    f["emoji_count"] = u.emoji_count
    f["emoji_rate"] = _rate(u.emoji_count, n_words)
    f["narrow_nbsp"] = u.narrow_nbsp_count
    f["nbsp"] = u.nbsp_count
    f["zero_width"] = u.zero_width_count
    f["hidden_total"] = u.invisible_count + u.tag_char_count + u.private_use_count
    f["bullet_char_unicode"] = u.bullet_char

    # --- Lexicon ---
    if phrases:
        for fam, plist in phrases.items():
            for ph in plist:
                core = re.escape(ph.lower()).replace(r"\ ", r"\s+")
                pat = (r"\b" if ph[0].isalnum() else "") + core + (r"\b" if ph[-1].isalnum() else "")
                n = len(re.findall(pat, lower))
                if n:
                    f[f"lex:{fam}:{ph}"] = n
    return f


def _is_title_case(t: str) -> bool:
    t = re.sub(r"[*_`#:]", "", t).strip()
    ws = [w for w in t.split() if w.isalpha()]
    if len(ws) < 2:
        return False
    caps = sum(1 for w in ws[1:] if w[0].isupper() and w.lower() not in {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "vs", "at", "by", "is", "as"})
    non_stop = sum(1 for w in ws[1:] if w.lower() not in {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "vs", "at", "by", "is", "as"})
    return non_stop > 0 and caps / non_stop >= 0.7


def lexicon_hits(f: dict) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for k, v in f.items():
        if k.startswith("lex:"):
            _, fam, ph = k.split(":", 2)
            out.setdefault(fam, {})[ph] = v
    return out
