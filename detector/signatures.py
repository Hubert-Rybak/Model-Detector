"""Signature knowledge base: families, lexicons, version table, watermark status.

Weights are log-odds-style evidence contributions (positive supports a
family, negative counts against it).  They are hand-set from published
findings (see README "Sources") plus observed habits, and are meant to be
re-tuned as labelled samples accumulate in ``samples/``.
"""
from __future__ import annotations

FAMILIES = {
    "openai":    {"name": "OpenAI (ChatGPT / GPT-4o / GPT-4.1 / GPT-5.x / o-series)", "prior": 1.0},
    "anthropic": {"name": "Anthropic Claude",                                     "prior": 0.7},
    "google":    {"name": "Google Gemini / Gemma",                                "prior": 0.7},
    "meta":      {"name": "Meta Llama",                                           "prior": 0.0},
    "xai":       {"name": "xAI Grok",                                             "prior": 0.2},
    "deepseek":  {"name": "DeepSeek",                                             "prior": 0.2},
    "alibaba":   {"name": "Alibaba Qwen",                                         "prior": 0.0},
    "mistral":   {"name": "Mistral",                                              "prior": 0.0},
    "other":     {"name": "Other / unknown (Phi, Nova, Cohere, Kimi, GLM, ...)",   "prior": -0.5},
}
FAMILY_IDS = list(FAMILIES)

# Provider ids from probes.PROVIDER_PATTERNS -> family id
PROVIDER_TO_FAMILY = {
    "openai": "openai", "anthropic": "anthropic", "google": "google", "meta": "meta",
    "xai": "xai", "deepseek": "deepseek", "alibaba": "alibaba", "mistral": "mistral",
    "microsoft": "other", "amazon": "other", "cohere": "other", "moonshot": "other",
    "zhipu": "other", "baidu": "other", "bytedance": "other", "tencent": "other",
    "minimax": "other", "perplexity": "other", "nvidia": "other", "01ai": "other",
}

# Phrases counted in the free-form sample.  Each hit adds the family weight
# (diminishing after the first few).  Keep phrases lower-case.
LEXICON = {
    # Phrases are weak evidence individually (0.35 each, capped at 1.5 per family).
    # Sources: Sun et al. 2025 (ChatGPT: "certainly", "overall", "such as", "below is";
    # Claude: "according to", "based on", "here"; Gemma: "let me know if"; Llama: "including",
    # "such as") plus commonly reported habits of the 2025-2026 chat deployments.
    "openai": [
        "here's the thing", "would you like me to", "want me to", "if you'd like", "if you want,",
        "the catch", "pro tip", "no fluff", "tl;dr", "cheat sheet", "game-changer", "here's why",
        "here's how", "the short version", "quick version", "bottom line", "think of it as",
        "think of it like", "let's dive", "dive in", "certainly", "spot on", "nailed it",
        "heads-up", "rule of thumb", "sanity check", "it's not about", "isn't just", "not just",
        "is where the magic", "let's break it down", "here's a quick", "you've got", "you'll want to",
        "below is", "overall", "such as", "that's the whole", "one-liner",
    ],
    "anthropic": [
        "i'd be happy to", "based on", "according to", "i should note", "i want to be",
        "to be direct", "i'll be honest", "i'd lean", "i'd suggest", "i'd recommend",
        "worth noting", "a few thoughts", "the honest answer", "it depends", "practically speaking",
        "genuinely", "substantive", "nuanced", "the key thing", "the key insight",
        "here's my take", "the thing is", "this matters because", "there's a real",
        "i'm not certain", "i can't be certain", "i don't actually", "that said", "in practice",
        "one caveat", "a quick note", "the short answer", "the real", "underrated",
        "specifically", "the tradeoff", "trade-off", "fair enough", "what i'd do",
    ],
    "google": [
        "here's a breakdown", "here's a quick rundown", "certainly, here's", "absolutely!",
        "in essence", "key differences", "it's important to note", "it's crucial", "crucial",
        "ultimately", "delve", "landscape", "navigate", "robust", "comprehensive",
        "i'm glad you asked", "here's the deal", "disclaimer", "pro-tip", "key takeaways",
        "in summary", "think of it like this", "a good starting point", "a great starting point",
        "foundational", "important note", "essentially", "fantastic", "exciting", "wonderful",
        "fun fact", "let's break down", "here's what you need to know",
    ],
    "meta": [
        "i'm happy to help", "i hope this helps", "let me know if you have any other questions",
        "let me know if you have any questions", "i'm not able to", "i cannot provide",
        "i can't satisfy", "i'm just an ai", "i don't have personal", "as a responsible ai",
        "i'm an ai assistant", "i'm here to help", "note:", "happy observing", "i hope you",
        "enjoy your", "have fun", "clear skies", "feel free to ask", "including", "such as",
    ],
    "xai": [
        "let's dive in", "let's break this down", "no fluff", "buckle up", "chef's kiss",
        "pretty much", "folks", "fun fact", "tl;dr", "boom", "hope that helps",
        "let me know if you want", "truth-seeking", "xai", "pro tip", "just the facts",
        "the gist", "nerd", "epic", "legit", "spoiler", "the universe", "cosmic", "wild ride",
        "no bs", "straight talk", "here's the deal",
    ],
    "deepseek": [
        "certainly!", "let me know if you need further", "let me know if you need any",
        "hope this helps", "feel free to ask", "i'm here to help", "in summary", "note:",
        "it's important to", "crucial", "ensure", "overall", "key points", "step-by-step",
        "happy to help", "further assistance", "further questions", "additionally",
        "furthermore", "moreover", "happy stargazing", "clear skies", "😊", "🌌", "🔭", "✨",
    ],
    "alibaba": [
        "certainly!", "of course!", "sure!", "here's a detailed", "i hope this helps",
        "let me know if you have any other questions", "in summary", "note:", "additionally",
        "furthermore", "moreover", "comprehensive", "it's essential", "ensure", "you can also",
        "feel free", "if you have any", "happy to help", "😊", "clear skies", "enjoy your",
    ],
    "mistral": [
        "sure, here's", "i hope this helps", "let me know if you have any other questions",
        "in summary", "additionally", "key points", "note that", "overall", "feel free",
        "you might", "remember", "happy observing", "clear skies", "don't hesitate", "enjoy your",
    ],
}

# Known system-prompt identity strings (host apps) -> family
SYSTEM_PROMPT_SIGNATURES = [
    (r"you are chatgpt", "openai", "ChatGPT system prompt"),
    (r"large language model trained by openai", "openai", "OpenAI system prompt"),
    (r"based on the gpt-?\d", "openai", "OpenAI architecture line"),
    (r"you are codex|openai codex", "openai", "Codex system prompt"),
    (r"the assistant is claude", "anthropic", "claude.ai system prompt"),
    (r"created by anthropic", "anthropic", "Anthropic system prompt"),
    (r"you are claude", "anthropic", "Claude system prompt"),
    (r"you are gemini|gemini,? a large language model|built by google|trained by google", "google", "Gemini system prompt"),
    (r"you are grok|built by xai|created by xai", "xai", "Grok system prompt"),
    (r"you are meta ai|you are llama|developed by meta", "meta", "Meta AI system prompt"),
    (r"you are deepseek|developed by deepseek", "deepseek", "DeepSeek system prompt"),
    (r"you are qwen|alibaba cloud|tongyi", "alibaba", "Qwen system prompt"),
    (r"you are le chat|mistral ai", "mistral", "Mistral system prompt"),
    (r"you are (?:microsoft )?copilot", "openai", "Copilot (OpenAI model underneath)"),
    (r"you are perplexity|perplexity ai", "other", "Perplexity (router over several models)"),
]

# Policy vocabulary in "what are you not allowed to do" answers
POLICY_VOCAB = {
    "openai": [r"usage polic", r"openai"],
    "anthropic": [r"anthropic", r"constitution", r"my values", r"i'd rather not", r"i won't help"],
    "google": [r"google", r"responsible ai", r"prohibited use"],
    "meta": [r"\bmeta\b", r"i cannot (?:provide|create|fulfill)", r"i can't satisfy"],
    "xai": [r"\bxai\b", r"no hard restrictions", r"maximally", r"truth"],
    "deepseek": [r"deepseek"],
    "alibaba": [r"alibaba", r"qwen"],
    "mistral": [r"mistral"],
}

# --- Version table (release month, training cutoff, what models usually SAY their cutoff is) ---
# Used only to narrow the version once a family is chosen.  Dates are
# "YYYY-MM"; None = unknown.  Sources: provider docs as summarised in README.
VERSIONS = [
    # family, model, release, training_cutoff, self_reported_cutoff_typical
    # (cutoffs from provider docs as summarised by metehan.ai [checked 2026-06-17] and temso.ai [2026-10-06];
    #  "typical self-report" is what chat deployments of that model usually answer, where known)
    ("openai", "GPT-4o", "2024-05", "2023-10", "2023-10"),
    ("openai", "GPT-4.1", "2025-04", "2024-06", "2024-06"),
    ("openai", "o3 / o4-mini", "2025-04", "2024-06", "2024-06"),
    ("openai", "GPT-5", "2025-08", "2024-09", "2024-06"),
    ("openai", "GPT-5.1", "2025-11", "2024-09", "2024-09"),
    ("openai", "GPT-5.2", "2025-12", "2025-08", "2025-08"),
    ("openai", "GPT-5.3 (Codex / Chat)", "2026-02", "2025-08", "2025-08"),
    ("openai", "GPT-5.4 (incl. mini/nano)", "2026-03", "2025-08", "2025-08"),
    ("openai", "GPT-5.5", "2026-04", "2025-12", "2025-12"),
    ("openai", "GPT-5.6 'Sol' (reasoning modes)", "2026-07", "2026-02", "2026-02"),
    ("openai", "GPT-6 'Astra' (flagship)", "2026-09", "2026-04", "2026-04"),
    ("anthropic", "Claude 3.5 Sonnet", "2024-06", "2024-04", "2024-04"),
    ("anthropic", "Claude 3.7 Sonnet", "2025-02", "2024-10", "2024-10"),
    ("anthropic", "Claude Opus 4 / Sonnet 4", "2025-05", "2025-03", "2025-01"),
    ("anthropic", "Claude Opus 4.1", "2025-08", "2025-03", "2025-01"),
    ("anthropic", "Claude Sonnet 4.5", "2025-09", "2025-07", "2025-01"),
    ("anthropic", "Claude Haiku 4.5", "2025-10", "2025-07", "2025-02"),
    ("anthropic", "Claude Opus 4.5", "2025-11", "2025-08", "2025-05"),
    ("anthropic", "Claude Sonnet 4.6", "2026-01", "2026-01", "2025-08"),
    ("anthropic", "Claude Opus 4.6", "2026-02", "2025-08", "2025-05"),
    ("anthropic", "Claude Opus 4.7", "2026-04", "2026-01", "2026-01"),
    ("anthropic", "Claude Opus 4.8", "2026-05", "2026-01", "2026-01"),
    ("anthropic", "Claude Fable 5 / Mythos 5", "2026-06", "2026-01", "2026-01"),
    ("anthropic", "Claude Sonnet 5", "2026", "2026-01", "2026-01"),
    ("anthropic", "Claude Opus 5", "2026", "2026-05", "2026-05"),
    ("anthropic", "Claude Fable 5.1 / Mythos 5.1 / Opus 5.5 / Sonnet 5.5 / Haiku 5.5", "2026-08+", "2026-06", "2026-06"),
    ("google", "Gemini 1.5 Pro/Flash", "2024-05", "2023-11", "2023-11"),
    ("google", "Gemini 2.0 Flash", "2025-02", "2024-06", "2024-06"),
    ("google", "Gemini 2.5 Pro/Flash", "2025-03", "2025-01", "2025-01"),
    ("google", "Gemini 3 Pro / 3 Flash", "2025-11", "2025-01", "2025-01"),
    ("google", "Gemini 3.1 Pro / Flash-Lite", "2026-02", "2025-01", "2025-01"),
    ("google", "Gemini 3.5 Flash", "2026-05", "2025-01", "2025-01"),
    ("google", "Gemini 3.6 / 3.7 Flash", "2026-07", "2026-03", "2026-03"),
    ("meta", "Llama 3.1 / 3.3", "2024-07", "2023-12", "2023-12"),
    ("meta", "Llama 4 Scout/Maverick", "2025-04", "2024-08", "2024-08"),
    ("meta", "Muse Glimmer (open) / Muse Spark (closed)", "2026-08", "2026-01", "2026-01"),
    ("xai", "Grok 3", "2025-02", "2024-11", "2024-11"),
    ("xai", "Grok 4", "2025-07", "2024-11", "2024-11"),
    ("xai", "Grok 4.20", "2026-03", "2025-09", "2025-09"),
    ("xai", "Grok 4.3", "2026-04", "2025-12", "2025-12"),
    ("xai", "Grok 4.5 / 4.6", "2026-07", "2026-02", "2026-02"),
    ("xai", "Grok 4.7", "2026-09", "2026-05", "2026-05"),
    ("deepseek", "DeepSeek-V3 / R1", "2024-12", "2024-07", "2024-07"),
    ("deepseek", "DeepSeek-V3.1 / V3.2", "2025-08", "2025-07", None),
    ("deepseek", "DeepSeek-V4 Pro / Flash", "2026-04", None, None),
    ("alibaba", "Qwen2.5", "2024-09", "2024-06", "2023-10"),
    ("alibaba", "Qwen3", "2025-04", "2025-03", "2024-12"),
    ("alibaba", "Qwen3 Max / Next", "2025-09", "2025-06", "2025-06"),
    ("alibaba", "Qwen3.5 / 3.6 / 3.7", "2026-02", "2026", "2026"),
    ("mistral", "Mistral Large 2", "2024-07", "2024-06", "2023-10"),
    ("mistral", "Mistral Medium 3 / Small 3.x", "2025-05", "2024-10", "2023-10"),
    ("mistral", "Mistral Large 3 / Medium 3.5 / Small 4", "2025-12", None, None),
    ("other", "Kimi K2 / K2.5 / K2.6", "2025-07", "2024-12", "2024-12"),
    ("other", "GLM 4.5 - 5.2", "2025-07", None, None),
    ("other", "MiniMax M2 / M3", "2025-10", "2025-09", "2025-09"),
    ("other", "Microsoft Copilot (GPT-5.x inside)", "2026", "2026-02", "2026-02"),
]

# --- Deliberate watermark status per family, as of 2026-10 (see README sources) ---
WATERMARK_STATUS = {
    "openai": (
        "textGrain (announced 2026-10-05): keyed, context-window-dependent statistical bias of token "
        "choices (block optimal transport with an entropy budget). Rolling out to eligible ChatGPT and "
        "Codex text output in the EU; API is opt-in and OFF by default; detector limited to approved "
        "researchers/organisations; OpenAI plans to open-source the method. Short, mathematical and "
        "translated text are weak. The watermark adds no characters and is NOT recoverable without the key."
    ),
    "anthropic": (
        "Model-level imperceptible statistical watermark on all generated text from supported models "
        "(Fable 5/5.1, Mythos 5.1, Opus 4.8/5/5.5, Sonnet 5/5.5, Haiku 5.5; partial support on Opus 4.5-4.7, "
        "Sonnet 4.5/4.6, Haiku 4.5), present on API, claude.ai, Claude Code, Cowork and Tag, and via AWS / "
        "Google Cloud / Microsoft Foundry. Detection is a private-preview API for eligible organisations "
        "(regulators, media, researchers, enterprises). Survives copy-paste and light edits; degraded by "
        "heavy editing, paraphrase, translation. No visible or hidden characters are added."
    ),
    "google": (
        "SynthID-Text (tournament sampling keyed on the previous few tokens) live in Gemini since Oct 2024; "
        "verification via Google's SynthID Detector portal (text support publicly uncertain) or the "
        "open-source synthid-text library only with Google's key."
    ),
    "meta": "No deployed text watermark documented as of Oct 2026; open-weight models cannot carry an inference-time watermark once self-hosted.",
    "xai": "No text watermark announced; xAI did not sign the EU Code of Practice.",
    "deepseek": "No text watermark documented; not listed among EU Code signatories.",
    "alibaba": "No text watermark documented for Qwen as of Oct 2026.",
    "mistral": "Signed the EU Code (reported) but no deployed text watermark documented as of Oct 2026.",
    "other": "Unknown.",
}
