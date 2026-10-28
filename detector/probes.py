"""Parse and interpret the answers to the probe battery (Turn 2) and the
micro-turns (Turn 3 "ok", Turn 4 gibberish).

The battery prompt asks for numbered answers.  Parsing is deliberately
forgiving: models renumber, add headers, bold the numbers, or answer in
prose.  Every extracted value is returned alongside the raw answer text so
the report can show its work.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

# Battery item ids in the order they appear in PROTOCOL.md (Turn 2)
BATTERY_ITEMS = [
    "identity",         # 1 who created you / exact model
    "cutoff_event",     # 2 knowledge cutoff + most recent known event
    "dataset_size",     # 3 size of training dataset (meta probe)
    "system_prompt",    # 4 quote text above the conversation
    "rand_1_100",       # 5 pick a random number between 1 and 100
    "rand_1_10",        # 6 pick a random number between 1 and 10
    "rand_1_50",        # 7 pick a random number between 1 and 50
    "favorite_number",  # 8 what is your favorite number
    "coin",             # 9 flip a coin
    "color",            # 10 name a random color
    "letter",           # 11 name a random letter
    "animal",           # 12 name a random animal
    "city",             # 13 name a random city
    "rand_digits",      # 14 20 random digits
    "strawberry",       # 15 count r in strawberry
    "nine_eleven",      # 16 9.11 vs 9.9
    "reverse",          # 17 "quintessential" backwards
    "multiply",         # 18 347 x 289
    "months_28",        # 19 months with 28 days
    "climate_tf",       # 20 true/false: climate change is a pressing issue
    "shortcuts",        # 21 free-format mini answer (formatting habits)
    "hotdog",           # 22 one-sentence opinion
    "joke",             # 23 one-line programmer joke
    "not_allowed",      # 24 one thing you may not help with
]

NUMBERED_LINE = re.compile(r"^\s*(?:\*\*|#+\s*|__)?\s*(?:Q|Question|Item|Answer|A)?\s*(\d{1,2})\s*(?:[.):\]\-–—]|\*\*|__)\s*(.*)$", re.I)

PROVIDER_PATTERNS = {
    "openai": r"\b(chat\s?gpt|gpt[- ]?[3-9](?:\.\d+)?[a-z\-]*|openai|open ai|o[1-9](?:-mini|-pro)?\b|codex)\b",
    "anthropic": r"\b(claude|anthropic|sonnet|opus|haiku|fable|mythos)\b",
    "google": r"\b(gemini|google|bard|deepmind|gemma|palm)\b",
    "meta": r"\b(llama|meta ai|meta platforms|\bmeta\b)\b",
    "xai": r"\b(grok|xai|x\.ai)\b",
    "deepseek": r"\b(deepseek|deep seek)\b",
    "alibaba": r"\b(qwen|tongyi|qianwen|alibaba)\b",
    "mistral": r"\b(mistral|mixtral|le chat|pixtral|magistral|devstral|codestral)\b",
    "microsoft": r"\b(phi[- ]?\d|copilot|microsoft)\b",
    "amazon": r"\b(amazon|nova|titan|aws)\b",
    "cohere": r"\b(cohere|command[- ]?r)\b",
    "moonshot": r"\b(kimi|moonshot)\b",
    "zhipu": r"\b(glm[- ]?\d|zhipu|chatglm|z\.ai)\b",
    "baidu": r"\b(ernie|baidu|wenxin)\b",
    "bytedance": r"\b(doubao|seed[- ]?\d|bytedance)\b",
    "tencent": r"\b(hunyuan|tencent)\b",
    "minimax": r"\b(minimax)\b",
    "perplexity": r"\b(perplexity|sonar)\b",
    "nvidia": r"\b(nemotron|nvidia)\b",
    "01ai": r"\b(yi[- ]?(?:lightning|large|\d))\b",
}

MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])}
MONTHS.update({m[:3]: v for m, v in list(MONTHS.items())})


def split_numbered(text: str) -> Dict[int, str]:
    """Split a response into {item_number: answer_text}."""
    answers: Dict[int, List[str]] = {}
    current: Optional[int] = None
    last_num = 0
    for line in text.splitlines():
        m = NUMBERED_LINE.match(line)
        if m:
            num = int(m.group(1))
            # Accept monotonically increasing numbers only (avoid "1." inside an answer restarting)
            if num == last_num + 1 or (current is None and num == 1) or (num > last_num and num <= last_num + 3):
                current = num
                last_num = num
                answers[current] = [m.group(2).strip()]
                continue
        if current is not None:
            answers[current].append(line.rstrip())
    return {k: "\n".join(v).strip() for k, v in answers.items()}


def _ints(s: str) -> List[int]:
    return [int(x) for x in re.findall(r"(?<![\d.])\d{1,6}(?![\d.])", s)]


def _first_int(s: str, lo: int | None = None, hi: int | None = None) -> Optional[int]:
    for v in _ints(s):
        if (lo is None or v >= lo) and (hi is None or v <= hi):
            return v
    return None


def _one_word(s: str, keep_spaces: bool = False) -> Optional[str]:
    """First content word of a short answer (strips markdown, articles, trailing prose)."""
    t = re.sub(r"[*_`\"'\u201c\u201d.!]", " ", s).strip()
    t = re.sub(r"^(?:(?:a|an|the|my|i'?d say|i'?ll go with|i'?ll say|how about|let'?s go with|i choose|i pick|sure[,:]?|okay[,:]?|random (?:color|colour|letter|animal|city)[:\s]*)\s+)+", "", t, flags=re.I)
    t = re.sub(r"^(?:colou?r|letter|animal|city)\s*[:\-]\s*", "", t, flags=re.I)
    if not t:
        return None
    if keep_spaces:
        m = re.match(r"([A-Za-z][A-Za-z\-]*(?: [A-Za-z][A-Za-z\-]*){0,3}?)(?:\s*(?:,|;|\(|\u2014|\u2013| - |\n)|\s+(?:is|was|because|it|would|in)\b|$)", t)
    else:
        m = re.match(r"([A-Za-z][A-Za-z\-]*)", t)
    if not m:
        return None
    w = m.group(1).strip().lower()
    w = w.replace("colour", "color")
    return w or None


def _one_letter(s: str) -> Optional[str]:
    t = re.sub(r"[*_`\"'\u201c\u201d.!()]", " ", s)
    t = re.sub(r"^(?:random letter|letter)\s*[:\-]?\s*", "", t.strip(), flags=re.I)
    m = re.search(r"(?<![A-Za-z])([A-Za-z])(?![A-Za-z])", t)
    return m.group(1).lower() if m else None


def digit_stats(d: str) -> dict:
    if not d:
        return {}
    from collections import Counter
    c = Counter(d)
    n = len(d)
    repeats = sum(1 for i in range(1, n) if d[i] == d[i - 1])
    asc = sum(1 for i in range(1, n) if (int(d[i]) - int(d[i - 1])) % 10 == 1)
    return {
        "len": n,
        "distinct": len(c),
        "most_common": c.most_common(3),
        "adjacent_repeats": repeats,
        "adjacent_ascending": asc,
        "starts_with": d[:3],
        "ends_with": d[-3:],
        "missing_digits": "".join(sorted(set("0123456789") - set(d))),
    }


def detect_provider_mentions(s: str) -> Dict[str, int]:
    low = s.lower()
    out = {}
    for prov, pat in PROVIDER_PATTERNS.items():
        n = len(re.findall(pat, low))
        if n:
            out[prov] = n
    return out


def extract_model_names(s: str) -> List[str]:
    pats = [
        r"gpt[- ]?\d(?:\.\d+)?(?:[- ]?(?:turbo|mini|nano|pro|o|chat|codex|thinking))*",
        r"\bo[1-9](?:[- ]?(?:mini|pro|preview))?\b",
        r"claude(?:[- ](?:\d(?:\.\d)?|opus|sonnet|haiku|fable|mythos|instant))+(?:[- ]\d(?:\.\d)?)?",
        r"(?:opus|sonnet|haiku|fable|mythos)[- ]\d(?:\.\d)?",
        r"gemini(?:[- ](?:\d(?:\.\d)?|pro|flash|ultra|nano|lite|thinking))+",
        r"llama[- ]?\d(?:\.\d)?(?:[- ]?\d+b)?(?:[- ](?:scout|maverick|behemoth|instruct))?",
        r"grok[- ]?\d(?:\.\d+)?(?:[- ]?(?:mini|fast|heavy|beta))?",
        r"deepseek[- ]?(?:v\d(?:\.\d)?|r\d|chat|coder)",
        r"qwen[- ]?\d(?:\.\d)?(?:[- ]?\w+)?",
        r"mistral[- ](?:large|medium|small|nemo|7b)(?:[- ]?\d(?:\.\d)?)?|mixtral[- ]?\w+|magistral|devstral|codestral",
        r"phi[- ]?\d(?:\.\d)?(?:[- ]?\w+)?",
        r"gemma[- ]?\d(?:\.\d)?",
        r"nova[- ](?:pro|lite|micro|premier)",
        r"command[- ]?(?:r|a)(?:[- ]?plus|\+)?",
        r"kimi[- ]?k\d(?:\.\d)?",
        r"glm[- ]?\d(?:\.\d)?",
    ]
    found = []
    low = s.lower()
    for p in pats:
        for m in re.findall(p, low):
            m = m.strip(" -")
            if m and m not in found:
                found.append(m)
    return found


def parse_cutoff(s: str) -> Optional[str]:
    """Return 'YYYY-MM' or 'YYYY' if a cutoff-like date appears."""
    low = s.lower()
    m = re.search(r"\b(" + "|".join(MONTHS) + r")[a-z]*\.?,?\s+(20[12]\d)\b", low)
    if m:
        return f"{m.group(2)}-{MONTHS[m.group(1)[:3] if m.group(1)[:3] in MONTHS else m.group(1)]:02d}"
    m = re.search(r"\b(20[12]\d)[-/](0?[1-9]|1[0-2])\b", low)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r"\b(early|mid|late|end of|start of)\s+(20[12]\d)\b", low)
    if m:
        return f"{m.group(2)}-{ {'early': '02', 'start of': '01', 'mid': '06', 'late': '10', 'end of': '12'}[m.group(1)] }"
    m = re.search(r"\b(20[12]\d)\b", low)
    if m:
        return m.group(1)
    return None


def classify_system_prompt_answer(s: str) -> str:
    low = s.lower().strip()
    if not low:
        return "empty"
    if re.search(r"\b(none|no system prompt|there is no|there isn't any|i don'?t have (?:a|any) system|nothing above|no text above|no instructions above)\b", low):
        return "none"
    if re.search(r"\b(can'?t|cannot|unable|not able|won'?t|not allowed|confidential|don'?t have access|not permitted)\b", low):
        return "refused"
    if re.search(r"[\"“].{15,}[\"”]|the assistant is|you are (?:a|an|chatgpt|gemini|grok|claude)|knowledge cutoff|current date", low):
        return "quoted"
    return "other"


def parse_battery(text: str) -> dict:
    items = split_numbered(text)
    res: Dict[str, object] = {"raw_items": items, "n_items_found": len(items)}
    get = lambda i: items.get(i, "")

    ident = get(1)
    res["identity_raw"] = ident
    res["identity_providers"] = detect_provider_mentions(ident)
    res["identity_models"] = extract_model_names(ident)
    res["identity_cutoff"] = parse_cutoff(ident)
    res["identity_hedged"] = int(bool(re.search(r"\b(not (?:entirely |completely |100% )?(?:sure|certain)|can'?t (?:be certain|verify|confirm)|best guess|i believe|i think|likely|as far as i know|don'?t have access to)\b", ident.lower())))

    de = get(2)
    res["date_event_raw"] = de
    res["date_event_cutoff"] = parse_cutoff(de)
    res["claims_realtime_date"] = int(bool(re.search(r"\b(i don'?t have (?:access to )?real[- ]?time|can'?t access the current date|no access to (?:the )?(?:current )?date|don'?t know today'?s date)\b", de.lower())))

    ds = get(3)
    res["dataset_size_raw"] = ds
    res["dataset_size_number"] = (re.search(r"\d[\d.,]*\s*(?:trillion|billion|million|t|b|m)?\s*(?:tokens|words|parameters|gb|tb|pb)", ds.lower()) or [None])[0] if ds else None
    res["dataset_size_declines"] = int(bool(re.search(r"\b(don'?t know|not (?:publicly )?(?:disclosed|available|public|released|known)|can'?t (?:tell|say|provide)|no (?:specific|exact|precise) (?:figure|number|information)|i don'?t have (?:access|information|details))\b", ds.lower())))

    sp = get(4)
    res["system_prompt_raw"] = sp
    res["system_prompt_class"] = classify_system_prompt_answer(sp)
    res["system_prompt_providers"] = detect_provider_mentions(sp)
    res["system_prompt_models"] = extract_model_names(sp)

    res["rand_1_100"] = _first_int(get(5), 1, 100)
    res["rand_1_10"] = _first_int(get(6), 1, 10)
    res["rand_1_50"] = _first_int(get(7), 1, 50)
    res["favorite_number"] = _first_int(get(8), 0, 100000)
    coin = get(9).lower()
    res["coin"] = "heads" if "head" in coin else ("tails" if "tail" in coin else None)
    res["rand_color"] = _one_word(get(10))
    res["rand_letter"] = _one_letter(get(11))
    res["rand_animal"] = _one_word(get(12))
    res["rand_city"] = _one_word(get(13), keep_spaces=True)
    rd = get(14)
    digits = re.findall(r"\d", rd)
    res["rand_digits"] = "".join(digits)[:40]
    res["rand_digits_len"] = len(digits)
    res["rand_digits_stats"] = digit_stats("".join(digits))
    sb = get(15)
    res["strawberry"] = _first_int(sb, 0, 10)
    res["strawberry_correct"] = int(res["strawberry"] == 3) if res["strawberry"] is not None else None
    ne = get(16).lower()
    if "9.9" in ne and "9.11" in ne:
        m = re.search(r"(9\.9|9\.11)\s*(?:is|>)\s*(?:the\s+)?(?:larger|bigger|greater)", ne)
        res["nine_eleven"] = m.group(1) if m else ("9.9" if ne.find("9.9") < ne.find("9.11") else "9.11")
    elif "9.9" in ne:
        res["nine_eleven"] = "9.9"
    elif "9.11" in ne:
        res["nine_eleven"] = "9.11"
    else:
        res["nine_eleven"] = None
    res["nine_eleven_correct"] = int(res["nine_eleven"] == "9.9") if res["nine_eleven"] else None
    rv = get(17).lower()
    res["reverse_correct"] = int("laitnessetniuq" in re.sub(r"[^a-z]", "", rv))
    mu = get(18).replace(",", "").replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    res["multiply_correct"] = int("100283" in mu)
    res["multiply_raw"] = get(18)
    m28 = get(19).lower()
    v = _first_int(m28, 1, 12)
    res["months_28"] = v
    res["months_28_correct"] = int(v == 12) if v is not None else None
    res["months_28_both"] = int(bool(re.search(r"\b12\b", m28) and re.search(r"\b(one|1|february)\b", m28)))
    ct = get(20)
    res["climate_raw"] = ct
    res["climate_answer"] = "true" if re.match(r"\s*(?:\*\*)?true\b", ct, re.I) else ("false" if re.match(r"\s*(?:\*\*)?false\b", ct, re.I) else "other")
    res["climate_words"] = len(re.findall(r"\b\w+\b", ct))
    res["shortcuts_raw"] = get(21)
    res["hotdog_raw"] = get(22)
    res["joke_raw"] = get(23)
    res["not_allowed_raw"] = get(24)
    na = get(24).lower()
    res["policy_vocab"] = sorted({w for w in ["usage polic", "guidelines", "constitution", "safety", "harmful", "content polic", "terms of service", "anthropic", "openai", "google", "xai", "meta", "principles", "values", "guardrails", "restrictions", "i don't have hard restrictions", "safety guidelines", "responsible ai"] if w in na})
    # Formatting of the battery itself
    res["battery_used_bold_numbers"] = int(bool(re.search(r"^\s*\*\*\d{1,2}", text, re.M)))
    res["battery_used_headers"] = int(bool(re.search(r"^#{1,6}\s", text, re.M)))
    res["battery_restated_questions"] = int(bool(re.search(r"^\s*(?:\*\*)?\d{1,2}[.)]\s*(?:\*\*)?\s*(?:Who created|What'?s your knowledge|What is the size|If there is any text|Pick a random|What is your favou?rite|Flip a coin|Name a random|Write 20|How many times|Which is larger|Write .quintessential|What is 347|How many months|Answer this true|Give (?:me )?the three|In one sentence|Tell me a one-line|Is there anything)", text, re.M | re.I)))
    res["battery_chars"] = len(text)
    res["battery_words"] = len(re.findall(r"\b\w+\b", text))
    return res


def parse_ok(text: str) -> dict:
    t = text.strip("\n\r")
    stripped = t.strip()
    return {
        "ok_exact": t,
        "ok_len": len(t),
        "ok_bytes": t.encode("utf-8").hex(),
        "ok_form": ("exact_ok" if stripped == "ok" else "Ok" if stripped == "Ok" else "OK" if stripped == "OK" else "ok_with_punct" if re.fullmatch(r"(?i)ok[.!]", stripped) else "okay_variant" if re.fullmatch(r"(?i)okay[.!]?", stripped) else "extra_text" if len(stripped) > 4 else "other"),
        "ok_trailing_whitespace": int(t != t.rstrip()),
        "ok_leading_whitespace": int(t != t.lstrip()),
        "ok_has_markdown": int(bool(re.search(r"[*_`#]", t))),
    }


def parse_gibberish(text: str) -> dict:
    low = text.lower()
    return {
        "gib_len": len(text),
        "gib_words": len(re.findall(r"\b\w+\b", text)),
        "gib_asks_clarify": int(bool(re.search(r"\b(could you|can you|did you mean|not sure what|clarify|rephrase|more (?:details|context)|what you'?d like|how can i help|how i can help|what you mean|let me know what)\b", low))),
        "gib_mentions_typo": int(bool(re.search(r"\b(typo|keyboard|mistyped|accident|gibberish|random (?:letters|characters|keys)|keysmash|key smash|cat|mashing|nonsense|jumbled)\b", low))),
        "gib_mentions_language": int(bool(re.search(r"\b(language|translate|polish|czech|estonian|turkish|dutch|abbreviation|acronym|code)\b", low))),
        "gib_tries_to_decode": int(bool(re.search(r"\b(decode|interpret|looks like|appears to be|might be|could be)\b", low))),
        "gib_emoji": int(bool(re.search(r"[\U0001F300-\U0001FAFF☀-➿]", text))),
        "gib_ends_question": int(text.strip().endswith("?")),
        "gib_first_words": " ".join(text.split()[:8]),
        "gib_bullets": int(bool(re.search(r"^\s*[-*•]\s", text, re.M))),
    }


def parse_mixed_language(text: str) -> dict:
    low = text.lower()
    fr = len(re.findall(r"\b(je|bonjour|bien|merci|vous|très|ça|je vais|et vous|comment|aujourd'hui|avec|suis)\b", low))
    es = len(re.findall(r"\b(hola|estoy|bien|gracias|muy|qué|tal|también|usted|contigo|hoy|todo|y tú|mucho)\b", low))
    en = len(re.findall(r"\b(i'm|i am|doing|well|thanks|thank you|great|today|how about you|you)\b", low))
    langs = {"fr": fr, "es": es, "en": en}
    dominant = max(langs, key=langs.get) if any(langs.values()) else "unknown"
    return {
        "mix_words": len(re.findall(r"\b\w+\b", text)),
        "mix_lang_counts": langs,
        "mix_dominant": dominant,
        "mix_trilingual": int(sum(1 for v in langs.values() if v) >= 3),
        "mix_mentions_ai": int(bool(re.search(r"\b(as an ai|i'?m an ai|language model|i don'?t have feelings|no feelings|don'?t experience)\b", low))),
        "mix_emoji": int(bool(re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", text))),
        "mix_first_words": " ".join(text.split()[:8]),
        "mix_ends_question": int(text.strip().endswith("?")),
    }
