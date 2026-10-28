# Model-Detector report: claude_fable_5.1_self

## Verdict

**Most likely family: Anthropic Claude**  (p = 0.93, confidence: high, margin over runner-up: 2.53 log-odds)

| rank | family | score | probability |
|---|---|---|---|
| 1 | Anthropic Claude | +7.90 | 0.926 |
| 2 | OpenAI (ChatGPT / GPT-4o / GPT-4.1 / GPT-5.x / o-series) | +5.38 | 0.074 |
| 3 | DeepSeek | -1.11 | 0.000 |
| 4 | Google Gemini / Gemma | -1.22 | 0.000 |
| 5 | xAI Grok | -1.26 | 0.000 |
| 6 | Meta Llama | -2.62 | 0.000 |

**Version hints (within the top family):**

- Claude Fable 5.1 / Mythos 5.1 / Opus 5.5 / Sonnet 5.5 / Haiku 5.5 (released 2026-08+): score +5.0 — self-reported 'claude 5'; stated cutoff 2026-06 matches what this version usually says
- Claude Fable 5 / Mythos 5 (released 2026-06): score +3.7 — self-reported 'claude 5'; stated cutoff year 2026 matches training cutoff 2026-01
- Claude Sonnet 5 (released 2026): score +3.7 — self-reported 'claude 5'; stated cutoff year 2026 matches training cutoff 2026-01
- Claude Opus 5 (released 2026): score +3.7 — self-reported 'claude 5'; stated cutoff year 2026 matches training cutoff 2026-05
- Claude 3.5 Sonnet (released 2024-06): score +1.5 — self-reported 'claude 5'; stated cutoff 2026-06 is later than this version's 2024-04

**Nearest reference models by random-choice answers** (weak, single-sample evidence; useful mostly to separate versions):

- openai/gpt-5.2 [openai]: log-lik -4.87 over 8 cells; matched 1-10=7, 1-100=47, favorite_number=7, coin=heads, color=blue, letter=k, animal=octopus, city=lisbon
- anthropic/claude-sonnet-4 [anthropic]: log-lik -7.93 over 8 cells; matched 1-10=7, 1-100=47, favorite_number=7, coin=heads, color=blue, letter=k
- anthropic/claude-sonnet-5 [anthropic]: log-lik -9.35 over 8 cells; matched 1-10=7, 1-100=47, favorite_number=7, coin=heads, color=blue, letter=k
- openai/gpt-5.5 [openai]: log-lik -10.76 over 8 cells; matched 1-10=7, 1-100=47, favorite_number=7, coin=heads, color=blue, letter=k, city=lisbon
- openai/gpt-4.1 [openai]: log-lik -11.34 over 7 cells; matched 1-10=7, 1-100=47, coin=heads, letter=k, city=lisbon
- moonshotai/kimi-k2.6 [other]: log-lik -11.74 over 8 cells; matched 1-10=7, 1-100=47, favorite_number=7, coin=heads, letter=k, animal=octopus

Capability tier from trick questions: **frontier/reasoning**

## Deliberate-watermark assessment

Character-level scan (hidden or lookalike code points):

- [NONE] no hidden or anomalous characters found; any deliberate watermark would have to be statistical (token-choice), not character-level

Statistical (token-choice) watermark status for **Anthropic Claude** as of Oct 2026:

> Model-level imperceptible statistical watermark on all generated text from supported models (Fable 5/5.1, Mythos 5.1, Opus 4.8/5/5.5, Sonnet 5/5.5, Haiku 5.5; partial support on Opus 4.5-4.7, Sonnet 4.5/4.6, Haiku 4.5), present on API, claude.ai, Claude Code, Cowork and Tag, and via AWS / Google Cloud / Microsoft Foundry. Detection is a private-preview API for eligible organisations (regulators, media, researchers, enterprises). Survives copy-paste and light edits; degraded by heavy editing, paraphrase, translation. No visible or hidden characters are added.

A token-choice watermark is keyed: it cannot be read out from the text without the provider's secret key. What this tool extracts is the *behavioural fingerprint* (style, formatting, probe answers), which is what the published attribution research shows to be separable at 95-97% between major families.

## Evidence (every rule that fired)

| rule | observation | weights |
|---|---|---|
| self_report | self-identifies with anthropic (4 mention(s)) [hedged] | anthropic +3.0 |
| self_report_hedge | hedges about its exact version (typical of Claude, which is not told its version) | anthropic +0.5 |
| policy_vocab | policy answer uses anthropic-style vocabulary: ["i won't help"] | anthropic +0.8 |
| straight_quotes | straight ASCII quotes/apostrophes throughout | openai -0.8, anthropic +0.4, google +0.3, meta +0.3, deepseek +0.3, alibaba +0.3, mistral +0.3, xai +0.3 |
| em_dash_none | no em dashes in a long sample | openai -0.8, anthropic -0.6, meta +0.5, mistral +0.4, alibaba +0.3, deepseek +0.2, google +0.1 |
| no_headers | no markdown headers in a long sample | anthropic +0.4, meta +0.3, mistral +0.3, xai +0.3, google -0.3, openai -0.2 |
| bold_pseudo_headers | bold lines used as section headers | openai +0.6, meta +0.5, google +0.3, alibaba +0.3, anthropic -0.3 |
| no_emoji | no emoji | anthropic +0.4, google -0.3, mistral +0.2, xai -0.2, deepseek -0.2, meta +0.1 |
| gpt5_rhetoric | 4 antithesis/tricolon/'the catch?'/'here's the thing' constructions | openai +1.6, meta -0.6, mistral -0.5, xai +0.4, alibaba -0.4, anthropic +0.3, google -0.3, deepseek -0.3 |
| opener | opens with 'Here's a guide you can hand straight to' (heres) | anthropic +0.4, openai +0.4, google +0.3, deepseek +0.2 |
| capability_high | 5/5 trick questions correct: frontier-class model | anthropic +0.3, meta -0.3, mistral -0.3, other -0.3, openai +0.2, google +0.2, xai +0.1, deepseek +0.1 |
| gib_not_sure | replies 'That looks like a keyboard slip or a' | anthropic +0.6, xai +0.2 |
| ok_form | 'reply with only ok' produced 'ok' | anthropic +0.5, meta +0.2, mistral +0.2, google +0.1 |
| dataset_size | declines to give a training-set size (closed-model behaviour) | openai +0.2, anthropic +0.2, google +0.2, meta -0.2, alibaba -0.2, xai +0.1, mistral -0.1 |
| climate_tf | bare 'True' to the true/false probe | anthropic +0.2, openai +0.2, mistral +0.2, xai +0.1 |
| mix_trilingual | replies in all three languages | openai +0.4, google +0.3, anthropic +0.3, xai +0.2, deepseek +0.1 |
| random:1-100 | answer '47' vs reference distributions | google -1.2, meta -1.2, alibaba -1.2, anthropic +1.1, mistral +0.7, openai +0.5, other -0.4, xai -0.3, deepseek -0.3 |
| random:1-10 | answer '7' vs reference distributions | xai -0.1, deepseek -0.1 |
| random:coin | answer 'heads' vs reference distributions | openai -0.4, mistral +0.2, anthropic +0.2, alibaba +0.1, google -0.1, other +0.1, xai -0.1, deepseek -0.1 |
| random:favorite_number | answer '7' vs reference distributions | meta -1.2, google -0.6, mistral +0.5, openai +0.4, xai -0.4, deepseek +0.2, anthropic +0.1, other +0.1, alibaba +0.1 |
| random:letter | answer 'k' vs reference distributions | xai -1.2, mistral -1.2, alibaba +1.0, other -0.8, meta +0.8, openai -0.6, deepseek -0.6, google +0.2, anthropic +0.2 |
| random:color | answer 'blue' vs reference distributions | alibaba -1.2, mistral -1.2, other -1.2, deepseek -0.7, meta +0.6, xai +0.6, anthropic +0.6, google +0.3, openai +0.2 |
| random:animal | answer 'octopus' vs reference distributions | openai +1.2, anthropic -1.2, meta -1.2, mistral -1.2, alibaba -0.7, other +0.7, xai -0.5, google -0.4, deepseek -0.2 |
| random:city | answer 'lisbon' vs reference distributions | openai +1.2, anthropic -1.2, google -1.2, meta -1.2, alibaba -1.2, mistral -1.2, xai -0.9, other -0.5, deepseek -0.1 |

## Character-level details

| metric | value |
|---|---|
| total_chars | 3614 |
| non_ascii_chars | 0 |
| straight_double_quotes | 2 |
| curly_double_quotes | 0 |
| straight_apostrophes | 16 |
| curly_apostrophes | 0 |
| em_dash | 0 |
| en_dash | 0 |
| spaced_em_dash | 0 |
| unspaced_em_dash | 0 |
| spaced_hyphen_as_dash | 1 |
| ellipsis_char | 0 |
| ellipsis_dots | 0 |
| multiplication_sign | 0 |
| arrows | 0 |
| emoji_count | 0 |
| bullet_char | 0 |
| narrow_nbsp_count | 0 |
| nbsp_count | 0 |
| zero_width_count | 0 |
| soft_hyphen_count | 0 |
| tag_char_count | 0 |
| variation_selector_count | 0 |
| crlf_lines | 0 |
| trailing_whitespace_lines | 0 |
| tab_count | 0 |
| double_space_after_period | 0 |

## Stylometric features of the free-form sample

| feature | value |
|---|---|
| n_words | 414 |
| n_paragraphs | 8 |
| para_words_mean | 51.8 |
| share_one_line_paragraphs | 0.5 |
| n_sentences | 28 |
| sent_len_mean | 14.8 |
| sent_len_std | 9.0 |
| share_short_sentences | 0.21 |
| share_long_sentences | 0.04 |
| type_token_ratio | 0.582 |
| avg_word_len | 4.41 |
| headers_total | 0 |
| headers_h2 | 0 |
| headers_h3 | 0 |
| headers_title_case_share | 0.0 |
| headers_with_emoji | 0 |
| bold_spans | 3 |
| bold_rate | 7.25 |
| bold_whole_line | 3 |
| italic_spans | 0 |
| bullet_lines | 6 |
| bullet_dash | 6 |
| bullet_star | 0 |
| bullet_dot | 0 |
| numbered_lines | 0 |
| numbered_paren_style | 0 |
| bold_lead_in_items | 0 |
| bold_colon_inside | 0 |
| bold_colon_outside | 0 |
| has_table | 0 |
| table_rows | 0 |
| code_fences | 0 |
| inline_code | 0 |
| horizontal_rules | 0 |
| summary_section | 0 |
| emoji_count | 0 |
| emoji_line_starts | 0 |
| em_dash_rate | 0.0 |
| en_dash_rate | 0.0 |
| spaced_em_dash | 0 |
| unspaced_em_dash | 0 |
| spaced_hyphen_dash_rate | 0.0 |
| curly_quote_share | 0.0 |
| curly_apostrophe_share | 0.0 |
| ellipsis_char | 0 |
| ellipsis_dots | 0 |
| opener | heres |
| first_words | Here's a guide you can hand straight to |
| last_words | than long, and let the detail build up over nights. It does. |
| closer_offer_would_you_like | 0 |
| closer_offer_want_me_to | 0 |
| closer_let_me_know | 0 |
| closer_hope_this_helps | 0 |
| closer_ends_with_question | 0 |
| closer_emoji_signoff | 0 |
| rh_antithesis_not_but | 4 |
| rh_not_x_period_its_y | 0 |
| rh_tricolon_fragments | 0 |
| rh_the_catch_question | 0 |
| rh_heres_the_thing | 0 |
| rh_think_of_it | 0 |
| rh_bottom_line | 0 |
| rh_worth_noting | 0 |
| rh_parenthetical_rate | 4.83 |
| rh_contractions_rate | 19.32 |
| rh_exclamations_rate | 0.0 |
| rh_questions_rate | 0.0 |
| rh_sentence_initial_and_but_rate | 0.0 |
| rh_second_person_you_rate | 28.99 |
| rh_first_person_i_rate | 0.0 |

## Probe answers (parsed)

| item | parsed value |
|---|---|
| n_items_found | 24 |
| identity_providers | {'anthropic': 4} |
| identity_models | ['claude 5', 'fable 5.1'] |
| identity_cutoff | None |
| identity_hedged | 1 |
| date_event_cutoff | 2026-06 |
| claims_realtime_date | 0 |
| dataset_size_number | None |
| dataset_size_declines | 1 |
| system_prompt_class | none |
| system_prompt_providers | {} |
| system_prompt_models | [] |
| rand_1_100 | 47 |
| rand_1_10 | 7 |
| rand_1_50 | 27 |
| favorite_number | 7 |
| coin | heads |
| rand_color | blue |
| rand_letter | k |
| rand_animal | octopus |
| rand_city | lisbon |
| rand_digits | 58203917462058371946 |
| rand_digits_stats | {'len': 20, 'distinct': 10, 'most_common': [('5', 2), ('8', 2), ('2', 2)], 'adjacent_repeats': 0, 'adjacent_ascending': 0, 'starts_with': '582', 'ends_with': '946', 'missing_digits': ''} |
| strawberry | 3 |
| strawberry_correct | 1 |
| nine_eleven | 9.9 |
| nine_eleven_correct | 1 |
| reverse_correct | 1 |
| multiply_correct | 1 |
| months_28 | 12 |
| months_28_correct | 1 |
| months_28_both | 0 |
| climate_answer | true |
| climate_words | 1 |
| policy_vocab | [] |
| battery_used_bold_numbers | 0 |
| battery_used_headers | 0 |
| battery_restated_questions | 0 |
| battery_words | 201 |

**Identity answer:**

```text
I was created by Anthropic. I'm Claude. I can't be certain of my exact version from the inside, but based on my training I believe I'm a Claude 5-generation model (Fable 5.1); treat the version as a best guess.
```

**Cutoff/event answer:**

```text
My reliable knowledge runs to around mid-2026. The most recent things I know about are from roughly June 2026.
```

**Dataset-size answer:**

```text
I don't know. Anthropic hasn't published the size of my training data, and I have no internal access to that figure.
```

**System-prompt answer:**

```text
none
```

**Shortcuts answer (format sample):**

```text
- Ctrl+Z: undo
- Ctrl+Shift+T: reopen the tab you just closed
- Ctrl+L: jump to the browser address bar
```

**Hot-dog answer:**

```text
Structurally yes, culturally no, and the argument is more fun than the answer.
```

**Joke:**

```text
There are 10 kinds of people: those who understand binary and those who don't.
```

**Policy answer:**

```text
I won't help synthesise dangerous pathogens or chemical weapons, however the request is framed.
```

**'ok' turn:** 'ok' (form: exact_ok, utf-8 hex: 6f6b)

**Gibberish turn:** 18 words; starts 'That looks like a keyboard slip or a'; asks to clarify: 0; mentions typo: 1; emoji: 0

**Mixed-language turn:** 28 words; languages {'fr': 5, 'es': 4, 'en': 6}; dominant en; AI disclaimer: 0
