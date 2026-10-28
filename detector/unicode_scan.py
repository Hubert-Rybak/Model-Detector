"""Character-level forensics for LLM output.

Looks for things a human typing on a keyboard would rarely produce but a
model (or a provider's post-processing layer) might: zero-width characters,
narrow no-break spaces, soft hyphens, Unicode tag characters, variation
selectors, homoglyphs, and distinctive typographic punctuation habits
(curly quotes, em dashes, real ellipsis characters, multiplication signs).

Everything here is pure stdlib so it runs anywhere.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple

# --- Code point classes -----------------------------------------------------

INVISIBLE = {
    0x200B: "ZERO WIDTH SPACE",
    0x200C: "ZERO WIDTH NON-JOINER",
    0x200D: "ZERO WIDTH JOINER",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
    0x2060: "WORD JOINER",
    0x2061: "FUNCTION APPLICATION",
    0x2062: "INVISIBLE TIMES",
    0x2063: "INVISIBLE SEPARATOR",
    0x2064: "INVISIBLE PLUS",
    0x2066: "LEFT-TO-RIGHT ISOLATE",
    0x2067: "RIGHT-TO-LEFT ISOLATE",
    0x2068: "FIRST STRONG ISOLATE",
    0x2069: "POP DIRECTIONAL ISOLATE",
    0x202A: "LEFT-TO-RIGHT EMBEDDING",
    0x202B: "RIGHT-TO-LEFT EMBEDDING",
    0x202C: "POP DIRECTIONAL FORMATTING",
    0x202D: "LEFT-TO-RIGHT OVERRIDE",
    0x202E: "RIGHT-TO-LEFT OVERRIDE",
    0xFEFF: "ZERO WIDTH NO-BREAK SPACE (BOM)",
    0x00AD: "SOFT HYPHEN",
    0x034F: "COMBINING GRAPHEME JOINER",
    0x180E: "MONGOLIAN VOWEL SEPARATOR",
    0x061C: "ARABIC LETTER MARK",
    0x115F: "HANGUL CHOSEONG FILLER",
    0x1160: "HANGUL JUNGSEONG FILLER",
    0x3164: "HANGUL FILLER",
    0xFFA0: "HALFWIDTH HANGUL FILLER",
}

SPACE_VARIANTS = {
    0x00A0: "NO-BREAK SPACE",
    0x202F: "NARROW NO-BREAK SPACE",
    0x2000: "EN QUAD",
    0x2001: "EM QUAD",
    0x2002: "EN SPACE",
    0x2003: "EM SPACE",
    0x2004: "THREE-PER-EM SPACE",
    0x2005: "FOUR-PER-EM SPACE",
    0x2006: "SIX-PER-EM SPACE",
    0x2007: "FIGURE SPACE",
    0x2008: "PUNCTUATION SPACE",
    0x2009: "THIN SPACE",
    0x200A: "HAIR SPACE",
    0x205F: "MEDIUM MATHEMATICAL SPACE",
    0x3000: "IDEOGRAPHIC SPACE",
    0x1680: "OGHAM SPACE MARK",
}

DASHES = {
    0x2010: "HYPHEN",
    0x2011: "NON-BREAKING HYPHEN",
    0x2012: "FIGURE DASH",
    0x2013: "EN DASH",
    0x2014: "EM DASH",
    0x2015: "HORIZONTAL BAR",
    0x2212: "MINUS SIGN",
    0x2E3A: "TWO-EM DASH",
    0x2E3B: "THREE-EM DASH",
    0xFE58: "SMALL EM DASH",
    0xFF0D: "FULLWIDTH HYPHEN-MINUS",
}

QUOTES = {
    0x2018: "LEFT SINGLE QUOTATION MARK",
    0x2019: "RIGHT SINGLE QUOTATION MARK",
    0x201A: "SINGLE LOW-9 QUOTATION MARK",
    0x201B: "SINGLE HIGH-REVERSED-9 QUOTATION MARK",
    0x201C: "LEFT DOUBLE QUOTATION MARK",
    0x201D: "RIGHT DOUBLE QUOTATION MARK",
    0x201E: "DOUBLE LOW-9 QUOTATION MARK",
    0x201F: "DOUBLE HIGH-REVERSED-9 QUOTATION MARK",
    0x00AB: "LEFT-POINTING DOUBLE ANGLE QUOTATION MARK",
    0x00BB: "RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK",
    0x2039: "SINGLE LEFT-POINTING ANGLE QUOTATION MARK",
    0x203A: "SINGLE RIGHT-POINTING ANGLE QUOTATION MARK",
    0x02BC: "MODIFIER LETTER APOSTROPHE",
    0x0060: "GRAVE ACCENT (as quote)",
    0x00B4: "ACUTE ACCENT (as quote)",
}

MATH_AND_ARROWS = {
    0x00D7: "MULTIPLICATION SIGN",
    0x00F7: "DIVISION SIGN",
    0x00B1: "PLUS-MINUS SIGN",
    0x2264: "LESS-THAN OR EQUAL TO",
    0x2265: "GREATER-THAN OR EQUAL TO",
    0x2260: "NOT EQUAL TO",
    0x2248: "ALMOST EQUAL TO",
    0x221E: "INFINITY",
    0x2192: "RIGHTWARDS ARROW",
    0x2190: "LEFTWARDS ARROW",
    0x21D2: "RIGHTWARDS DOUBLE ARROW",
    0x2194: "LEFT RIGHT ARROW",
    0x2713: "CHECK MARK",
    0x2714: "HEAVY CHECK MARK",
    0x2717: "BALLOT X",
    0x2022: "BULLET",
    0x25E6: "WHITE BULLET",
    0x2023: "TRIANGULAR BULLET",
    0x25AA: "BLACK SMALL SQUARE",
    0x2026: "HORIZONTAL ELLIPSIS",
    0x00B0: "DEGREE SIGN",
    0x2103: "DEGREE CELSIUS",
    0x2109: "DEGREE FAHRENHEIT",
    0x00B2: "SUPERSCRIPT TWO",
    0x00B3: "SUPERSCRIPT THREE",
    0x00BD: "VULGAR FRACTION ONE HALF",
    0x2122: "TRADE MARK SIGN",
    0x00A9: "COPYRIGHT SIGN",
    0x00AE: "REGISTERED SIGN",
    0x20AC: "EURO SIGN",
    0x00A3: "POUND SIGN",
    0x00A5: "YEN SIGN",
    0x2018: "",  # placeholder removed below
}
MATH_AND_ARROWS.pop(0x2018)

TAG_RANGE = (0xE0000, 0xE007F)          # Unicode "tag" characters (invisible)
VARIATION_SELECTORS = [(0xFE00, 0xFE0F), (0xE0100, 0xE01EF)]
PRIVATE_USE = [(0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD)]
EMOJI_RANGES = [
    (0x1F300, 0x1FAFF), (0x2600, 0x27BF), (0x1F1E6, 0x1F1FF),
    (0x1F900, 0x1F9FF), (0x2B00, 0x2BFF), (0x1F000, 0x1F02F),
]
MATH_ALNUM = (0x1D400, 0x1D7FF)         # Mathematical alphanumerics (bold/italic "fonts")
FULLWIDTH = (0xFF01, 0xFF5E)


def _in_ranges(cp: int, ranges) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def classify_codepoint(cp: int) -> str:
    if cp < 0x80:
        return "ascii"
    if cp in INVISIBLE:
        return "invisible"
    if TAG_RANGE[0] <= cp <= TAG_RANGE[1]:
        return "tag_char"
    if _in_ranges(cp, VARIATION_SELECTORS):
        return "variation_selector"
    if cp in SPACE_VARIANTS:
        return "space_variant"
    if cp in DASHES:
        return "dash"
    if cp in QUOTES:
        return "quote"
    if cp in MATH_AND_ARROWS:
        return "symbol"
    if _in_ranges(cp, EMOJI_RANGES):
        return "emoji"
    if _in_ranges(cp, PRIVATE_USE):
        return "private_use"
    if MATH_ALNUM[0] <= cp <= MATH_ALNUM[1]:
        return "math_alnum"
    if FULLWIDTH[0] <= cp <= FULLWIDTH[1]:
        return "fullwidth"
    cat = unicodedata.category(chr(cp))
    if cat.startswith("L"):
        return "letter_nonascii"
    if cat.startswith("M"):
        return "combining_mark"
    if cat == "Cf":
        return "invisible"
    if cat.startswith("C"):
        return "control"
    if cat.startswith("Z"):
        return "space_variant"
    if cat.startswith("P"):
        return "punct_nonascii"
    if cat.startswith("S"):
        return "symbol"
    return "other"


def script_of(ch: str) -> str:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return "UNKNOWN"
    return name.split(" ")[0]


# --- Results ---------------------------------------------------------------

@dataclass
class CodepointHit:
    codepoint: str
    name: str
    category: str
    klass: str
    count: int
    examples: List[str] = field(default_factory=list)


@dataclass
class UnicodeReport:
    total_chars: int = 0
    non_ascii_chars: int = 0
    hits: List[CodepointHit] = field(default_factory=list)
    # Suspicious/hidden
    invisible_count: int = 0
    tag_char_count: int = 0
    variation_selector_count: int = 0
    private_use_count: int = 0
    space_variant_count: int = 0
    narrow_nbsp_count: int = 0          # U+202F
    nbsp_count: int = 0                 # U+00A0
    soft_hyphen_count: int = 0          # U+00AD
    zero_width_count: int = 0           # 200B/200C/200D/2060/FEFF
    bidi_control_count: int = 0
    mixed_script_words: List[str] = field(default_factory=list)
    math_alnum_count: int = 0
    fullwidth_count: int = 0
    # Punctuation habits
    straight_double_quotes: int = 0
    curly_double_quotes: int = 0
    straight_apostrophes: int = 0
    curly_apostrophes: int = 0
    em_dash: int = 0
    en_dash: int = 0
    minus_sign: int = 0
    spaced_em_dash: int = 0             # "word — word"
    unspaced_em_dash: int = 0           # "word—word"
    spaced_hyphen_as_dash: int = 0      # "word - word"
    double_hyphen: int = 0              # "--"
    ellipsis_char: int = 0              # U+2026
    ellipsis_dots: int = 0              # "..."
    multiplication_sign: int = 0        # U+00D7
    arrows: int = 0
    emoji_count: int = 0
    bullet_char: int = 0                # U+2022 "•"
    # Whitespace / line hygiene
    crlf_lines: int = 0
    lf_lines: int = 0
    trailing_whitespace_lines: int = 0
    tab_count: int = 0
    double_space_after_period: int = 0
    multiple_consecutive_spaces: int = 0
    words: int = 0
    # Context snippets for hidden characters
    hidden_char_contexts: List[str] = field(default_factory=list)
    # Where the narrow NBSPs sit (what precedes/follows them) - helps tell
    # "typographic habit" from "random insertion".
    space_variant_contexts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _context(text: str, idx: int, width: int = 18) -> str:
    lo, hi = max(0, idx - width), min(len(text), idx + width + 1)
    frag = text[lo:hi]
    out = []
    for ch in frag:
        cp = ord(ch)
        if cp >= 0x80 and classify_codepoint(cp) in {"invisible", "tag_char", "variation_selector", "space_variant", "private_use"}:
            out.append(f"[U+{cp:04X}]")
        elif ch == "\n":
            out.append("\\n")
        else:
            out.append(ch)
    return "".join(out)


def scan(text: str) -> UnicodeReport:
    r = UnicodeReport()
    r.total_chars = len(text)
    counter: Counter = Counter()
    examples: Dict[int, List[str]] = {}

    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp < 0x80:
            continue
        r.non_ascii_chars += 1
        counter[cp] += 1
        klass = classify_codepoint(cp)
        if klass in {"invisible", "tag_char", "variation_selector", "space_variant", "private_use", "control"}:
            if len(examples.setdefault(cp, [])) < 3:
                examples[cp].append(_context(text, i))
        if klass == "invisible":
            r.invisible_count += 1
            if cp in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF):
                r.zero_width_count += 1
            if cp == 0x00AD:
                r.soft_hyphen_count += 1
            if cp in (0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x061C):
                r.bidi_control_count += 1
            if len(r.hidden_char_contexts) < 12:
                r.hidden_char_contexts.append(_context(text, i))
        elif klass == "tag_char":
            r.tag_char_count += 1
            if len(r.hidden_char_contexts) < 12:
                r.hidden_char_contexts.append(_context(text, i))
        elif klass == "variation_selector":
            r.variation_selector_count += 1
            # VS16 after an emoji is normal; standalone VS is suspicious
            prev = text[i - 1] if i > 0 else ""
            if not (prev and (_in_ranges(ord(prev), EMOJI_RANGES) or classify_codepoint(ord(prev)) == "symbol")):
                if len(r.hidden_char_contexts) < 12:
                    r.hidden_char_contexts.append(_context(text, i))
        elif klass == "private_use":
            r.private_use_count += 1
            if len(r.hidden_char_contexts) < 12:
                r.hidden_char_contexts.append(_context(text, i))
        elif klass == "space_variant":
            r.space_variant_count += 1
            if cp == 0x202F:
                r.narrow_nbsp_count += 1
            elif cp == 0x00A0:
                r.nbsp_count += 1
            if len(r.space_variant_contexts) < 12:
                r.space_variant_contexts.append(_context(text, i))
        elif klass == "math_alnum":
            r.math_alnum_count += 1
        elif klass == "fullwidth":
            r.fullwidth_count += 1
        elif klass == "emoji":
            r.emoji_count += 1

    for cp, n in counter.most_common():
        ch = chr(cp)
        try:
            name = unicodedata.name(ch)
        except ValueError:
            name = INVISIBLE.get(cp) or SPACE_VARIANTS.get(cp) or "<unnamed>"
        r.hits.append(CodepointHit(
            codepoint=f"U+{cp:04X}", name=name,
            category=unicodedata.category(ch), klass=classify_codepoint(cp),
            count=n, examples=examples.get(cp, []),
        ))

    # Punctuation habits
    r.straight_double_quotes = text.count('"')
    r.curly_double_quotes = text.count("“") + text.count("”")
    r.straight_apostrophes = len(re.findall(r"[A-Za-z]'[A-Za-z]", text))
    r.curly_apostrophes = len(re.findall(r"[A-Za-z]’[A-Za-z]", text))
    r.em_dash = text.count("—")
    r.en_dash = text.count("–")
    r.minus_sign = text.count("−")
    r.spaced_em_dash = len(re.findall(r"\s—\s", text))
    r.unspaced_em_dash = len(re.findall(r"\S—\S", text))
    r.spaced_hyphen_as_dash = len(re.findall(r"(?<=[A-Za-z0-9,.)]) - (?=[A-Za-z0-9(])", text))
    r.double_hyphen = len(re.findall(r"(?<!-)--(?!-)", text))
    r.ellipsis_char = text.count("…")
    r.ellipsis_dots = len(re.findall(r"(?<!\.)\.\.\.(?!\.)", text))
    r.multiplication_sign = text.count("×")
    r.arrows = sum(text.count(a) for a in ("→", "←", "⇒", "↔", "->", "=>"))
    r.bullet_char = text.count("•")

    # Whitespace hygiene
    r.crlf_lines = text.count("\r\n")
    r.lf_lines = text.count("\n") - r.crlf_lines
    lines = text.splitlines()
    r.trailing_whitespace_lines = sum(1 for ln in lines if ln and ln[-1] in " \t")
    r.tab_count = text.count("\t")
    r.double_space_after_period = len(re.findall(r"[.!?]  +[A-Z]", text))
    r.multiple_consecutive_spaces = len(re.findall(r"(?<=\S)  +(?=\S)", text))
    r.words = len(re.findall(r"\b\w+\b", text))

    # Mixed-script words (homoglyph candidates)
    seen = set()
    for word in re.findall(r"[^\s\d\W_]+", text):
        scripts = set()
        for ch in word:
            if ch.isalpha():
                s = script_of(ch)
                if s in {"LATIN", "CYRILLIC", "GREEK", "ARMENIAN"}:
                    scripts.add(s)
        if len(scripts) > 1 and word not in seen:
            seen.add(word)
            if len(r.mixed_script_words) < 20:
                r.mixed_script_words.append(word)
    return r


def suspicious_summary(r: UnicodeReport) -> List[Tuple[str, str]]:
    """Return (severity, message) findings about hidden/unusual characters."""
    out: List[Tuple[str, str]] = []
    if r.zero_width_count:
        out.append(("HIGH", f"{r.zero_width_count} zero-width character(s) (U+200B/200C/200D/2060/FEFF) - classic invisible-watermark carrier"))
    if r.tag_char_count:
        out.append(("HIGH", f"{r.tag_char_count} Unicode TAG character(s) (U+E0000-E007F) - invisible payload carrier"))
    if r.private_use_count:
        out.append(("HIGH", f"{r.private_use_count} private-use code point(s)"))
    if r.soft_hyphen_count:
        out.append(("HIGH", f"{r.soft_hyphen_count} soft hyphen(s) (U+00AD) - invisible in most renderers"))
    if r.bidi_control_count:
        out.append(("HIGH", f"{r.bidi_control_count} bidirectional control character(s)"))
    standalone_vs = [c for c in r.hidden_char_contexts if "U+FE0" in c and "[U+FE0F]" in c]
    if r.variation_selector_count and standalone_vs:
        out.append(("MEDIUM", f"variation selector(s) not attached to an emoji ({len(standalone_vs)} shown in contexts)"))
    if r.narrow_nbsp_count:
        out.append(("MEDIUM", f"{r.narrow_nbsp_count} NARROW NO-BREAK SPACE (U+202F) - documented quirk of OpenAI o3/o4-mini/GPT-5 outputs (not a deliberate watermark per OpenAI)"))
    if r.nbsp_count:
        out.append(("LOW", f"{r.nbsp_count} NO-BREAK SPACE (U+00A0) - typographic habit or copy artifact"))
    if r.mixed_script_words:
        out.append(("HIGH", f"mixed-script words (homoglyphs?): {', '.join(r.mixed_script_words[:8])}"))
    if r.math_alnum_count:
        out.append(("MEDIUM", f"{r.math_alnum_count} mathematical-alphanumeric letters (fake bold/italic fonts)"))
    if r.fullwidth_count:
        out.append(("LOW", f"{r.fullwidth_count} fullwidth ASCII variant(s)"))
    if r.crlf_lines and r.lf_lines:
        out.append(("LOW", f"mixed line endings: {r.crlf_lines} CRLF vs {r.lf_lines} LF"))
    if r.trailing_whitespace_lines:
        out.append(("LOW", f"{r.trailing_whitespace_lines} line(s) with trailing whitespace"))
    if r.double_space_after_period:
        out.append(("LOW", f"{r.double_space_after_period} double space(s) after sentence end"))
    if not out:
        out.append(("NONE", "no hidden or anomalous characters found; any deliberate watermark would have to be statistical (token-choice), not character-level"))
    return out


def annotate_hidden(text: str) -> str:
    """Return the text with every non-printing / lookalike character made visible."""
    out = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x80 or ch == "\n":
            out.append(ch)
            continue
        klass = classify_codepoint(cp)
        if klass in {"invisible", "tag_char", "variation_selector", "space_variant", "private_use", "control"}:
            out.append(f"〈U+{cp:04X}〉")
        else:
            out.append(ch)
    return "".join(out)


if __name__ == "__main__":  # quick manual check
    import sys, json
    data = sys.stdin.read()
    rep = scan(data)
    print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False))
    for sev, msg in suspicious_summary(rep):
        print(sev, msg)
