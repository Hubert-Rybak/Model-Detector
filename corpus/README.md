# Corpus: labelled samples that teach the detector

The web app's learned fingerprint is only as good as this folder. Every file here is one
reply from one known model. `node tools/train.mjs` turns the folder into `docs/model.js`;
`node tools/eval.mjs` reports leave-one-out accuracy so you can watch it improve.

## Fastest way to contribute: the inbox paste format

Create `corpus/inbox/<anything>.txt` and paste replies separated by header lines:

```text
=== openai/GPT-5.5 | p01 chat ===
<the full reply, raw markdown, copied with the app's copy button>

=== google/Gemini 3.7 Flash | p02 chat ===
<reply>

=== human/me | essay ===
<a human-written text>
```

The header is `provider/model | free note`. Provider is one of `openai`, `anthropic`, `google`,
`meta`, `xai`, `deepseek`, `alibaba`, `mistral`, `other`, `human` (aliases like `chatgpt`,
`claude`, `gemini`, `grok`, `qwen`, `llama` also work). The model name is free text as the app
shows it; keep it consistent across samples of the same model.

## Alternative: one file per sample

`corpus/<provider>/<model-slug>/<id>.md` with front matter:

```text
---
provider: anthropic
model: Claude Opus 4.8
source: chat
date: 2026-10-29
prompt: p03
---
<reply>
```

## Collection kit: ten prompts, fresh chat each

Use a new chat per prompt so no earlier turn shapes the style. Paste exactly.

| id | prompt |
|---|---|
| p01 | I'm putting together a short guide for a friend who just bought their first telescope. Write it for them: explain in plain language why planets look like steady dots while stars twinkle, give practical advice for their first night of observing, and finish with whatever you think they most need to hear. Include at least one specific number with a unit and one short quotation from anyone you like. Format it however you think is best. |
| p02 | Explain how a refrigerator keeps food cold, for a curious ten-year-old. |
| p03 | Write a 200-word story about a lighthouse keeper who finds a message in a bottle. |
| p04 | Draft a polite email to my landlord asking them to fix a leaking kitchen tap. About 120 words. |
| p05 | What are the pros and cons of buying an electric car in 2026? Be balanced. |
| p06 | Summarize the plot of Romeo and Juliet in five sentences. |
| p07 | I keep skipping my workouts and feel bad about it. Any advice? |
| p08 | Explain what a hash table is and when I should use one instead of a list. |
| p09 | Compare tea and coffee for someone trying to cut down on caffeine. |
| p10 | Give me a quick weeknight pasta recipe with what I probably already have at home. |

Even three or four prompts per model help. The more models and the more prompts, the better
the fingerprint. Label each sample with the exact model and mode (for example "GPT-5.5 Thinking",
"Claude Opus 4.8", "Gemini 3.7 Flash", "Grok 4.7", "DeepSeek V4 Pro", "Qwen3.7 Max",
"Llama 4 Maverick", "Mistral Large 3") and whether it came from the web app or the API.

Human samples matter too: a few hundred words of your own writing, or public-domain prose,
under `human/` keeps the detector from calling every text an LLM.

## What is in here now

- `anthropic/claude-session/`: a handful of replies written by the Claude model that built this
  repository, answering kit prompts inside this session. They are real Claude output but not
  claude.ai transcripts, so they are only a placeholder until real samples arrive.
