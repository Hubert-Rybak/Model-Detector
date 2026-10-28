// Reference data for the Model-Detector web engine (hand-maintained).
// Families, deliberate-watermark status (as of Oct 2026), and phrase lexicons.

export const FAMILIES = {
  openai:    { name: "OpenAI (ChatGPT / GPT-4o / GPT-4.1 / GPT-5.x / o-series)", prior: 0.8 },
  anthropic: { name: "Anthropic Claude",                                      prior: 0.6 },
  google:    { name: "Google Gemini / Gemma",                                 prior: 0.6 },
  meta:      { name: "Meta Llama",                                            prior: 0.0 },
  xai:       { name: "xAI Grok",                                              prior: 0.2 },
  deepseek:  { name: "DeepSeek",                                              prior: 0.2 },
  alibaba:   { name: "Alibaba Qwen",                                          prior: 0.0 },
  mistral:   { name: "Mistral",                                               prior: 0.0 },
  other:     { name: "Other LLM (Phi, Nova, Kimi, GLM, Cohere, ...)",          prior: -0.3 },
  human:     { name: "Human-written / no LLM fingerprint",                    prior: 0.0 },
};
export const FAMILY_IDS = Object.keys(FAMILIES);

export const WATERMARK_STATUS = {
  openai: "textGrain (announced 2026-10-05): a keyed, context-window-dependent statistical bias of word choice (block optimal transport with an entropy budget). Rolling out to eligible ChatGPT and Codex output in the EU; the API is opt-in and OFF by default; the detector is limited to approved researchers and organisations. It adds no characters and cannot be read without OpenAI's key.",
  anthropic: "Model-level statistical watermark ('a version of the SynthID-Text approach', keyed on a few preceding words) on all text from supported Claude models since Aug 2026, across API, claude.ai, Claude Code, Cowork, Tag and cloud partners, with no opt-out. Detection is a private-preview API for regulators, media, researchers and obligated enterprises; it returns a likelihood that Claude wrote part of the text, not a version. Nothing is added to the characters.",
  google: "SynthID-Text (tournament sampling keyed on the previous few tokens) live in Gemini since Oct 2024. Verification only with Google's key via the SynthID Detector portal (text support publicly uncertain).",
  meta: "No deployed text watermark documented; self-hosted open weights cannot carry an inference-time watermark.",
  xai: "No text watermark announced; xAI did not sign the EU Code of Practice.",
  deepseek: "No text watermark documented.",
  alibaba: "No text watermark documented for Qwen.",
  mistral: "Signed the EU Code (reported) but no deployed text watermark documented.",
  other: "Unknown.",
  human: "Not applicable.",
};

// Weak per-family phrase lexicon (0.3 log-odds per distinct hit, capped at 1.5 per family).
export const LEXICON = {
  openai: ["here's the thing", "would you like me to", "want me to", "if you'd like", "if you want,", "the catch", "pro tip", "no fluff", "tl;dr", "cheat sheet", "game-changer", "here's why", "here's how", "the short version", "quick version", "bottom line", "think of it as", "think of it like", "let's dive", "dive in", "certainly", "spot on", "nailed it", "heads-up", "rule of thumb", "sanity check", "it's not about", "isn't just", "not just", "let's break it down", "here's a quick", "you've got", "you'll want to", "below is", "overall", "such as", "that's the whole", "one-liner"],
  anthropic: ["i'd be happy to", "based on", "according to", "i should note", "i want to be", "to be direct", "i'll be honest", "i'd lean", "i'd suggest", "i'd recommend", "worth noting", "a few thoughts", "the honest answer", "it depends", "practically speaking", "genuinely", "substantive", "nuanced", "the key thing", "the key insight", "here's my take", "the thing is", "this matters because", "there's a real", "i'm not certain", "i can't be certain", "i don't actually", "that said", "in practice", "one caveat", "a quick note", "the short answer", "the real", "underrated", "specifically", "the tradeoff", "trade-off", "fair enough", "what i'd do"],
  google: ["here's a breakdown", "here's a quick rundown", "certainly, here's", "absolutely!", "in essence", "key differences", "it's important to note", "it's crucial", "crucial", "ultimately", "delve", "landscape", "navigate", "robust", "comprehensive", "i'm glad you asked", "here's the deal", "disclaimer", "pro-tip", "key takeaways", "in summary", "think of it like this", "a good starting point", "a great starting point", "foundational", "important note", "essentially", "fantastic", "exciting", "wonderful", "fun fact", "let's break down", "here's what you need to know"],
  meta: ["i'm happy to help", "i hope this helps", "let me know if you have any other questions", "let me know if you have any questions", "i'm not able to", "i cannot provide", "i can't satisfy", "i'm just an ai", "i don't have personal", "as a responsible ai", "i'm an ai assistant", "i'm here to help", "note:", "i hope you", "enjoy your", "have fun", "feel free to ask", "including", "such as"],
  xai: ["let's dive in", "let's break this down", "no fluff", "buckle up", "chef's kiss", "pretty much", "folks", "fun fact", "tl;dr", "boom", "hope that helps", "let me know if you want", "truth-seeking", "xai", "pro tip", "just the facts", "the gist", "nerd", "epic", "legit", "spoiler", "the universe", "cosmic", "wild ride", "no bs", "straight talk", "here's the deal"],
  deepseek: ["certainly!", "let me know if you need further", "let me know if you need any", "hope this helps", "feel free to ask", "i'm here to help", "in summary", "note:", "it's important to", "crucial", "ensure", "overall", "key points", "step-by-step", "happy to help", "further assistance", "further questions", "additionally", "furthermore", "moreover", "😊", "🌌", "🔭", "✨"],
  alibaba: ["certainly!", "of course!", "sure!", "here's a detailed", "i hope this helps", "let me know if you have any other questions", "in summary", "note:", "additionally", "furthermore", "moreover", "comprehensive", "it's essential", "ensure", "you can also", "feel free", "if you have any", "happy to help", "😊", "enjoy your"],
  mistral: ["sure, here's", "i hope this helps", "let me know if you have any other questions", "in summary", "additionally", "key points", "note that", "overall", "feel free", "you might", "remember", "don't hesitate", "enjoy your"],
};
