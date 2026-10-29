# Forensic sweep for hidden model identifiers

Corpus: 40 samples, models: claude-fable-5.1, claude-haiku-5.5, claude-opus-5.5, claude-sonnet-5.5.

## 1. Code-point inventory

Hidden, space-variant, selector, tag or private-use characters across all samples: **0**.

| code point | name | class | claude-fable-5.1 | claude-haiku-5.5 | claude-opus-5.5 | claude-sonnet-5.5 |
|---|---|---|---|---|---|---|
| U+2013 | EN DASH | dash | 15 | 8 | 12 | 1 |
| U+2192 | RIGHTWARDS ARROW | symbol | 5 | 0 | 2 | 4 |
| U+00D7 | MULTIPLICATION SIGN | symbol | 0 | 0 | 1 | 5 |
| U+00B0 | DEGREE SIGN | symbol | 0 | 2 | 2 | 1 |
| U+00BD | VULGAR FRACTION ONE HALF | symbol | 0 | 2 | 2 | 0 |
| U+2014 | EM DASH | dash | 1 | 0 | 1 | 2 |
| U+00BC | VULGAR FRACTION ONE QUARTER | other | 0 | 0 | 2 | 0 |
| U+2026 | HORIZONTAL ELLIPSIS | symbol | 0 | 0 | 2 | 0 |
| U+20AC | EURO SIGN | symbol | 0 | 0 | 1 | 0 |
| U+2082 | SUBSCRIPT TWO | other | 0 | 0 | 1 | 0 |

## 2. Whitespace and line hygiene

| metric | claude-fable-5.1 | claude-haiku-5.5 | claude-opus-5.5 | claude-sonnet-5.5 |
|---|---|---|---|---|
| trailing_ws_lines | 0 | 0 | 0 | 0 |
| double_spaces | 0 | 1 | 3 | 1 |
| tabs | 0 | 0 | 0 | 0 |
| crlf | 0 | 0 | 0 | 0 |
| blank_runs_ge2 | 0 | 0 | 0 | 0 |
| space_before_punct | 2 | 2 | 1 | 0 |
| nbsp | 0 | 0 | 0 | 0 |

## 3. Acrostics and name searches

For each channel, the number of samples whose channel string contains a model name or version, versus the expected number under the sample's own letter frequencies.

Digit-stream hits come from ordinary numbers in the text (ranges, units, percentages); the contexts are listed in analysis/forensics.json under `digit_contexts`.

| channel : needle | samples with a hit | expected by chance (sum) | where |
|---|---|---|---|
| digits:5.1 | 8 | 4.73 | claude-fable-5.1/p01, claude-fable-5.1/p05, claude-fable-5.1/p07, claude-fable-5.1/p08, claude-fable-5.1/p09, claude-haiku-5.5/p09… |
| digits:51 | 8 | 4.73 | claude-fable-5.1/p01, claude-fable-5.1/p05, claude-fable-5.1/p07, claude-fable-5.1/p08, claude-fable-5.1/p09, claude-haiku-5.5/p09… |
| digits:5.5 | 2 | 1.80 | claude-fable-5.1/p10, claude-sonnet-5.5/p05 |
| digits:55 | 2 | 1.80 | claude-fable-5.1/p10, claude-sonnet-5.5/p05 |

Explicit model-name words in the texts: 0

## 4. Parity bit streams

Each stream is decoded as 8-bit ASCII and searched for the names; the runs-test z-score flags non-random structure (|z| > 2.6).

| stream | model | samples | mean |z| | max |z| | decoded printable ratio (mean) | name hits |
|---|---|---|---|---|---|---|
| sentence_wordcount_parity | claude-fable-5.1 | 10 | 0.30 | 0.92 | 0.43 | 0 |
| sentence_wordcount_parity | claude-haiku-5.5 | 10 | 0.27 | 0.77 | 0.44 | 0 |
| sentence_wordcount_parity | claude-opus-5.5 | 10 | 0.62 | 1.13 | 0.36 | 0 |
| sentence_wordcount_parity | claude-sonnet-5.5 | 10 | 0.68 | 1.48 | 0.37 | 0 |
| word_length_parity | claude-fable-5.1 | 10 | 0.93 | 1.91 | 0.36 | 0 |
| word_length_parity | claude-haiku-5.5 | 10 | 0.62 | 1.64 | 0.36 | 0 |
| word_length_parity | claude-opus-5.5 | 10 | 0.99 | 1.86 | 0.38 | 0 |
| word_length_parity | claude-sonnet-5.5 | 10 | 1.04 | 2.09 | 0.42 | 0 |
| line_length_parity | claude-fable-5.1 | 10 | 0.44 | 1.26 | 0.35 | 0 |
| line_length_parity | claude-haiku-5.5 | 10 | 0.24 | 1.44 | 0.29 | 0 |
| line_length_parity | claude-opus-5.5 | 10 | 0.33 | 1.55 | 0.36 | 0 |
| line_length_parity | claude-sonnet-5.5 | 10 | 0.35 | 1.54 | 0.32 | 0 |
| sentence_endchar | claude-fable-5.1 | 10 | 0.81 | 4.58 | 0.01 | 0 |
| sentence_endchar | claude-haiku-5.5 | 10 | 0.31 | 0.94 | 0.20 | 0 |
| sentence_endchar | claude-opus-5.5 | 10 | 0.39 | 2.35 | 0.01 | 0 |
| sentence_endchar | claude-sonnet-5.5 | 10 | 0.34 | 1.73 | 0.16 | 0 |
| word_cap_parity | claude-fable-5.1 | 10 | 1.43 | 3.44 | 0.17 | 0 |
| word_cap_parity | claude-haiku-5.5 | 10 | 1.17 | 4.40 | 0.20 | 0 |
| word_cap_parity | claude-opus-5.5 | 10 | 0.78 | 1.92 | 0.19 | 0 |
| word_cap_parity | claude-sonnet-5.5 | 10 | 0.92 | 2.71 | 0.17 | 0 |

## 5. Typographic and structural habits per model (mean per sample)

| habit | claude-fable-5.1 | claude-haiku-5.5 | claude-opus-5.5 | claude-sonnet-5.5 | spread |
|---|---|---|---|---|---|
| words | 425.70 | 344.80 | 447.80 | 435.50 | 0.25 |
| en_dash_ranges | 1.40 | 0.80 | 1.10 | 0.10 | 1.53 |
| hyphen_ranges | 0.00 | 0.00 | 0.00 | 1.80 | 4.00 |
| en_dash_other | 0.10 | 0.00 | 0.10 | 0.00 | 2.00 |
| em_dash | 0.10 | 0.00 | 0.10 | 0.20 | 2.00 |
| spaced_hyphen_dash | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| oxford_comma | 4.90 | 4.00 | 4.00 | 5.90 | 0.40 |
| and_no_oxford | 5.20 | 5.70 | 7.60 | 6.70 | 0.38 |
| eg | 0.10 | 0.00 | 0.00 | 0.00 | 4.00 |
| for_example | 0.10 | 0.00 | 0.10 | 0.10 | 1.33 |
| ie | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| percent_sign | 0.50 | 0.10 | 0.10 | 0.20 | 1.78 |
| percent_word | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| digits_lt_10 | 4.10 | 2.00 | 2.60 | 3.50 | 0.69 |
| number_words | 3.80 | 2.20 | 4.90 | 2.80 | 0.79 |
| unit_space | 1.70 | 1.90 | 1.50 | 2.10 | 0.33 |
| unit_nospace | 0.10 | 0.00 | 0.00 | 0.00 | 4.00 |
| degree | 0.00 | 0.20 | 0.20 | 0.10 | 1.60 |
| mult_sign | 0.00 | 0.00 | 0.10 | 0.50 | 3.33 |
| ellipsis_char | 0.00 | 0.00 | 0.20 | 0.00 | 4.00 |
| ellipsis_dots | 0.30 | 0.20 | 0.10 | 0.20 | 1.00 |
| curly_quotes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| straight_dquotes | 5.20 | 2.40 | 5.60 | 4.40 | 0.73 |
| h2 | 1.30 | 0.30 | 0.80 | 1.40 | 1.16 |
| h3 | 0.00 | 0.40 | 0.70 | 0.00 | 2.55 |
| h1 | 0.10 | 0.20 | 0.30 | 0.30 | 0.89 |
| bullet_dash | 3.20 | 4.30 | 6.70 | 6.00 | 0.69 |
| bullet_star | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| numbered | 1.70 | 2.00 | 2.00 | 2.10 | 0.21 |
| bold_colon_in | 0.80 | 0.70 | 1.00 | 1.40 | 0.72 |
| bold_colon_out | 0.30 | 0.00 | 1.10 | 0.00 | 3.14 |
| bold_period_in | 4.20 | 3.10 | 4.50 | 4.70 | 0.39 |
| bold_line | 1.10 | 1.00 | 0.70 | 0.90 | 0.43 |
| table | 0.20 | 0.20 | 0.10 | 0.20 | 0.57 |
| blockquote | 0.10 | 0.00 | 0.50 | 0.00 | 3.33 |
| parens | 4.90 | 1.40 | 3.00 | 3.90 | 1.06 |
| semicolons | 1.00 | 0.00 | 0.20 | 0.30 | 2.67 |
| colons | 3.20 | 1.40 | 2.50 | 1.60 | 0.83 |
| exclaim | 0.10 | 0.10 | 0.30 | 0.40 | 1.33 |
| questions | 0.70 | 0.70 | 0.60 | 0.90 | 0.41 |
| contractions | 8.90 | 7.60 | 9.40 | 9.40 | 0.20 |
| code_fence | 0.10 | 0.10 | 0.20 | 0.10 | 0.80 |
| inline_code | 1.40 | 0.70 | 1.50 | 1.20 | 0.67 |
| italic | 1.20 | 0.40 | 1.20 | 0.70 | 0.91 |
| sent_len_mean | 15.72 | 14.74 | 14.57 | 15.28 | 0.08 |
| para_count | 13.00 | 8.60 | 10.00 | 9.60 | 0.43 |
| ends_with_question | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| closing_offer | 0.20 | 0.10 | 0.20 | 0.50 | 1.60 |

Largest between-model spreads (relative): hyphen_ranges (4.0), ellipsis_char (4.0), eg (4.0), unit_nospace (4.0), mult_sign (3.3), blockquote (3.3), bold_colon_out (3.1), semicolons (2.7), h3 (2.5), em_dash (2.0)

## 6. Model-exclusive words and phrases (used in 2+ different prompts by one model, never by the others)

**claude-fable-5.1** (38 exclusive n-grams): do that ×3, a box ×2, a day ×2, a machine ×2, almost always ×2, can rival ×2, caveat ×2, details ×2, every morning ×2, frequent ×2, gives you a ×2, got ×2, heat into ×2, heat into the ×2, honest ×2, it at the ×2, leaks ×2, made ×2, making ×2, me the ×2, mediocre ×2, most people ×2, not the ×2, on the way ×2, one that ×2, rival ×2, the start ×2, the time ×2, the whole thing ×2, thousands ×2

**claude-haiku-5.5** (8 exclusive n-grams): cupboard ×2, each time ×2, figures ×2, in the kitchen ×2, keeps the ×2, keeps the habit ×2, set a ×2, so you ×2

**claude-opus-5.5** (39 exclusive n-grams): a particular ×2, about half as ×2, before it ×2, billion ×2, climbed ×2, cuts ×2, drop ×2, earlier ×2, exact ×2, falling ×2, five minutes ×2, flashes ×2, half as ×2, half as much ×2, here's how ×2, hold ×2, it out ×2, it'll ×2, matter how ×2, matter how much ×2, mind ×2, minutes instead ×2, minutes instead of ×2, much harder ×2, never look ×2, no matter ×2, no matter how ×2, one in ×2, particular ×2, right now ×2

**claude-sonnet-5.5** (36 exclusive n-grams): might be ×3, on an ×3, a target ×2, also helps ×2, and often ×2, at least ×2, back for ×2, bother ×2, can add ×2, decide ×2, do the ×2, easier the ×2, elsewhere ×2, have tended ×2, headache ×2, hour so ×2, however ×2, is convenient ×2, is for ×2, is tight ×2, it seems ×2, knob ×2, lean ×2, lean on ×2, least ×2, noticed ×2, onto ×2, probably already ×2, tended ×2, things to ×2

## Verdict

- Character channel: 0 hidden/lookalike characters in 40 samples; the non-ASCII characters present are ordinary typography (see table 1).
- Acrostic/offset channel: no channel exceeds chance.
- Parity channel: no stream decodes to a name; sentence_endchar/claude-fable-5.1, word_cap_parity/claude-haiku-5.5 show run clustering, which is what bullet lists, headers and table rows produce, and their decoded printable ratio (~0.4) is what random bits give.
- What does differ between models is ordinary style (table 5 and section 6): usable as a weak statistical fingerprint, not as a stored identifier.
