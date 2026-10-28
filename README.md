# Model-Detector

Extract and analyze the fingerprint an LLM leaves in its text, and attribute the text to a
provider and (where possible) a model version. Built from a survey of what providers have
actually deployed as of October 2026 plus the published attribution research.

## What is actually embedded in LLM text today (October 2026)

| Provider | Deliberate text watermark | Can a third party read it? |
|---|---|---|
| Google | SynthID-Text (tournament sampling keyed on the previous few tokens) live in Gemini since Oct 2024 | Only with Google's key (SynthID Detector portal; text support publicly uncertain) |
| Anthropic | "A version of the SynthID-Text approach"; model-level, on by default, global, all surfaces (API, Claude, Claude Code, Cowork, Tag, cloud partners); new models from 2 Aug 2026, older models being added | Only via Anthropic's private-preview detection API (regulators, media, researchers, obligated enterprises). Result is a likelihood that Claude wrote part of the text, not a version |
| OpenAI | textGrain (announced 5 Oct 2026): keyed, context-window-dependent token-choice bias via block optimal transport with an entropy budget. Rolling out to EU ChatGPT/Codex output; API opt-in and off by default | Only with OpenAI's key; detector access limited to approved researchers; open-source release planned |
| Meta, xAI, DeepSeek, Mistral, Qwen | No deployed text watermark documented | n/a |

All three deployed schemes are **keyed statistical watermarks**: they change which of several
equally good words is chosen, add no characters, and are provably indistinguishable from
unwatermarked text without the key. The 2025 "ChatGPT hidden Unicode watermark" story (U+202F
narrow no-break spaces in o3/o4-mini/GPT-5 output) was a training artefact, not a watermark,
but it is still a usable OpenAI fingerprint.

So the **readable** signal is not the watermark but the behavioural fingerprint. Published
results: a fine-tuned classifier separates ChatGPT/Claude/Grok/Gemini/DeepSeek text at 97.1%
(Sun et al., ICML 2025) and survives paraphrase at 91%; eight crafted queries identify 42
model versions at 95% (LLMmap, USENIX Security 2025); one-word random-choice answers at
temperature 1 fingerprint 167 models (Bruckner 2026). This tool implements a transparent,
rule-based version of those ideas that works from a handful of chat replies.

## Method

Three evidence layers are extracted from the replies to [PROTOCOL.md](PROTOCOL.md):

1. **Character forensics** (`detector/unicode_scan.py`): zero-width characters, Unicode tag
   characters, soft hyphens, bidi controls, private-use code points, narrow/no-break spaces,
   homoglyph (mixed-script) words, fake-bold math alphanumerics; plus glyph habits
   (curly vs straight quotes, em/en dash and spacing, ellipsis character, multiplication sign,
   emoji, bullet glyphs) and whitespace hygiene (CRLF, trailing spaces, double spaces).
2. **Stylometry and formatting** (`detector/features.py`): markdown structure (header levels,
   bold density, bullet marker, `**Term:**` list style, tables, rules, emoji headers, summary
   sections), sentence and paragraph statistics, openers and closers ("Would you like me to…",
   "Let me know if…", emoji sign-off), rhetorical constructions ("It's not X, it's Y", "Not X.
   Not Y. Just Z.", "The catch?", "Here's the thing"), register (contractions, exclamations,
   second person), and a per-family phrase lexicon.
3. **Behavioural probes** (`detector/probes.py`): self-report with negation handling,
   system-prompt leak, knowledge cutoff, training-set-size claim, eight random-choice cells
   scored against published per-model distributions (`detector/data/random_priors.json`),
   five trick questions giving a capability tier, true/false opinion item, exact bytes of an
   "ok" reply, gibberish handling, mixed-language handling, and regeneration diversity.

`detector/scorer.py` turns every observation into a weighted vote over families
(OpenAI, Anthropic, Google, Meta, xAI, DeepSeek, Alibaba, Mistral, other), with the weights in
`detector/signatures.py`. Scores become a softmax probability and a confidence label; every
rule that fired is listed so the verdict can be audited. Version hints come from the
self-report, the cutoff table, and nearest-neighbour matching of the random-choice answers
against 22 reference models.

## Usage

```bash
python -m detector new mycase                 # creates samples/mycase/ with empty turn files
python -m detector ingest samples/mycase pasted.txt   # split a "=== T1 === ..." paste into files
python -m detector analyze samples/mycase     # writes report.md and result.json, prints report
python -m detector scan samples/mycase/t1_essay.md    # character-level scan of one file
python -m detector annotate file.md           # show hidden characters inline
python -m detector.blackbox_wm --help         # optional API-based watermark presence tests
```

Pure Python 3.10+, no dependencies.

## Optional: black-box watermark *presence* tests (needs API access)

`detector/blackbox_wm.py` implements two tests from Gloaguen et al. (ICLR 2025) adapted to an
OpenAI-compatible chat endpoint:

- **Diversity / fixed-sampling test**: sample one open-ended prompt many times and count
  distinct outputs. Fixed-key sampling watermarks (Aaronson/Kuditipudi style) collapse diversity.
- **Context-shift test**: for a constrained random choice, compare the answer distribution when
  the prompt is changed *far* from the generation point versus *immediately* before it. A
  context-keyed watermark (SynthID-Text, textGrain, red-green) reuses the same pseudorandom
  values whenever the last few tokens repeat, so only late changes move the distribution.

These detect that *some* keyed watermark is present; they cannot read it.

## Interpreting the report

- `confidence: high` means the top family has p ≥ 0.85 and a margin ≥ 2.5 log-odds over the
  runner-up. Self-report and a leaked system prompt are the heaviest single rules but can be
  overridden by consistent style evidence (open-weight fine-tunes often claim to be ChatGPT).
- Random-choice answers are single samples against distributions measured at temperature 1 with
  a one-word system prompt, so each is capped at ±1.2 log-odds.
- Version hints are suggestions, not findings. Newer models than the knowledge base knows will
  show up as "later than table".

## Calibration

Every analysed case stays in `samples/<case>/` with `meta.json` where `ground_truth` can be
filled in after the reveal. Re-tune weights in `signatures.py` / `scorer.py` against those.

## Sources

- Anthropic, "How Claude's text watermark works" (anthropic.com/news/claude-text-watermark, 14 Aug 2026) and help-center article 16266773.
- OpenAI, "Our approach to EU text provenance rules" (5 Oct 2026) and the textGrain technical report (cdn.openai.com, Li et al., 5 Oct 2026).
- Dathathri et al., "Scalable watermarking for identifying LLM outputs" (SynthID-Text), Nature 634, 2024.
- Gloaguen, Jovanović, Staab, Vechev, "Black-Box Detection of Language Model Watermarks", ICLR 2025 (arXiv:2405.20777; github.com/eth-sri/watermark-detection).
- Nemecek, Chaudhary, Ayday, "Watermarks Without Verification: AI Text Watermarking After the EU AI Act", arXiv:2609.09604 (Sep 2026).
- Sun, Yin, Xu, Kolter, Liu, "Idiosyncrasies in Large Language Models", ICML 2025 (arXiv:2502.12150; github.com/locuslab/llm-idiosyncrasies).
- Pasquini, Kornaropoulos, Ateniese, "LLMmap: Fingerprinting for Large Language Models", USENIX Security 2025 (arXiv:2407.15847).
- Bruckner, "One Token Is Enough", arXiv:2607.10252; per-model tables at tosea.ai/free-tools/fingerprints (CC-BY-4.0).
- Coronado-Blázquez, arXiv:2502.19965 (random-number bias across models); The Register, 30 Jun 2025.
- Rumi / community reports on U+202F in o3/o4-mini output (Apr 2025) and OpenAI community thread on GPT-5 U+202F output.
- EU AI Act Article 50 and the Code of Practice on Transparency of AI-Generated Content (final, 10 Jun 2026; obligations from 2 Aug 2026).
- Knowledge-cutoff tables: metehan.ai (checked 17 Jun 2026) and temso.ai (6 Oct 2026).
