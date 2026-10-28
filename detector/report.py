"""Render the analysis as Markdown (and keep a JSON-able dict)."""
from __future__ import annotations

from typing import List

from .signatures import FAMILIES, WATERMARK_STATUS


def _fmt_weights(w: dict) -> str:
    items = sorted(w.items(), key=lambda kv: -abs(kv[1]))
    return ", ".join(f"{k} {v:+.1f}" for k, v in items if abs(v) >= 0.05)


def render(case: str, result: dict, ctx, version_cands: List[dict], model_hints: List[dict], unicode_findings: list, u: dict, f: dict, regen: dict) -> str:
    L: List[str] = []
    probs, scores, ranked = result["probs"], result["scores"], result["ranked"]
    top = result["top"]
    L.append(f"# Model-Detector report: {case}\n")

    # ---- Verdict ----
    L.append("## Verdict\n")
    L.append(f"**Most likely family: {FAMILIES[top]['name']}**  (p = {probs[top]:.2f}, confidence: {result['confidence']}, margin over runner-up: {result['margin']} log-odds)\n")
    L.append("| rank | family | score | probability |")
    L.append("|---|---|---|---|")
    for i, fam in enumerate(ranked[:6], 1):
        L.append(f"| {i} | {FAMILIES[fam]['name']} | {scores[fam]:+.2f} | {probs[fam]:.3f} |")
    L.append("")
    if version_cands:
        L.append("**Version hints (within the top family):**\n")
        for c in version_cands:
            if c["score"] <= 0 and not c["why"]:
                continue
            L.append(f"- {c['model']} (released {c['release']}): score {c['score']:+.1f}" + (f" — {'; '.join(c['why'])}" if c["why"] else ""))
        L.append("")
    if model_hints:
        L.append("**Nearest reference models by random-choice answers** (weak, single-sample evidence; useful mostly to separate versions):\n")
        for h in model_hints:
            L.append(f"- {h['model']} [{h['family']}]: log-lik {h['loglik']} over {h['n_cells']} cells; matched {', '.join(h['matched']) if h['matched'] else 'nothing'}")
        L.append("")
    if result.get("tier"):
        L.append(f"Capability tier from trick questions: **{result['tier']}**\n")

    # ---- Watermark assessment ----
    L.append("## Deliberate-watermark assessment\n")
    L.append("Character-level scan (hidden or lookalike code points):\n")
    for sev, msg in unicode_findings:
        L.append(f"- [{sev}] {msg}")
    L.append("")
    L.append(f"Statistical (token-choice) watermark status for **{FAMILIES[top]['name']}** as of Oct 2026:\n")
    L.append(f"> {WATERMARK_STATUS.get(top, 'unknown')}\n")
    L.append("A token-choice watermark is keyed: it cannot be read out from the text without the provider's secret key. "
             "What this tool extracts is the *behavioural fingerprint* (style, formatting, probe answers), which is what the published "
             "attribution research shows to be separable at 95-97% between major families.\n")
    if regen:
        L.append("Regeneration diversity test (same prompt, fresh chats):\n")
        L.append(f"- samples: {regen.get('n')}; mean pairwise word-sequence similarity: {regen.get('mean_similarity')}; mean 5-gram Jaccard: {regen.get('mean_jaccard')}; identical opening words: {regen.get('identical_prefix_words')}")
        L.append(f"- reading: {regen.get('verdict')}\n")

    # ---- Evidence ----
    L.append("## Evidence (every rule that fired)\n")
    L.append("| rule | observation | weights |")
    L.append("|---|---|---|")
    for e in result["evidence"]:
        det = e.detail.replace("|", "\\|").replace("\n", " ")
        L.append(f"| {e.rule} | {det} | {_fmt_weights(e.weights)} |")
    L.append("")

    # ---- Character layer ----
    L.append("## Character-level details\n")
    keys = ["total_chars", "non_ascii_chars", "straight_double_quotes", "curly_double_quotes", "straight_apostrophes", "curly_apostrophes",
            "em_dash", "en_dash", "spaced_em_dash", "unspaced_em_dash", "spaced_hyphen_as_dash", "ellipsis_char", "ellipsis_dots",
            "multiplication_sign", "arrows", "emoji_count", "bullet_char", "narrow_nbsp_count", "nbsp_count", "zero_width_count",
            "soft_hyphen_count", "tag_char_count", "variation_selector_count", "crlf_lines", "trailing_whitespace_lines", "tab_count", "double_space_after_period"]
    L.append("| metric | value |")
    L.append("|---|---|")
    for k in keys:
        if k in u:
            L.append(f"| {k} | {u[k]} |")
    hits = [h for h in u.get("hits", []) if h["klass"] not in ("letter_nonascii",)]
    if hits:
        L.append("")
        L.append("Non-ASCII code points seen:\n")
        L.append("| code point | name | class | count |")
        L.append("|---|---|---|---|")
        for h in hits[:40]:
            L.append(f"| {h['codepoint']} | {h['name']} | {h['klass']} | {h['count']} |")
    if u.get("hidden_char_contexts"):
        L.append("")
        L.append("Hidden-character contexts:\n")
        for c in u["hidden_char_contexts"]:
            L.append(f"- `{c}`")
    if u.get("space_variant_contexts"):
        L.append("")
        L.append("Special-space contexts:\n")
        for c in u["space_variant_contexts"]:
            L.append(f"- `{c}`")
    L.append("")

    # ---- Style layer ----
    if f:
        L.append("## Stylometric features of the free-form sample\n")
        sel = ["n_words", "n_paragraphs", "para_words_mean", "share_one_line_paragraphs", "n_sentences", "sent_len_mean", "sent_len_std",
               "share_short_sentences", "share_long_sentences", "type_token_ratio", "avg_word_len", "headers_total", "headers_h2", "headers_h3",
               "headers_title_case_share", "headers_with_emoji", "bold_spans", "bold_rate", "bold_whole_line", "italic_spans", "bullet_lines",
               "bullet_dash", "bullet_star", "bullet_dot", "numbered_lines", "numbered_paren_style", "bold_lead_in_items", "bold_colon_inside",
               "bold_colon_outside", "has_table", "table_rows", "code_fences", "inline_code", "horizontal_rules", "summary_section",
               "emoji_count", "emoji_line_starts", "em_dash_rate", "en_dash_rate", "spaced_em_dash", "unspaced_em_dash", "spaced_hyphen_dash_rate",
               "curly_quote_share", "curly_apostrophe_share", "ellipsis_char", "ellipsis_dots", "opener", "first_words", "last_words",
               "closer_offer_would_you_like", "closer_offer_want_me_to", "closer_let_me_know", "closer_hope_this_helps", "closer_ends_with_question",
               "closer_emoji_signoff", "rh_antithesis_not_but", "rh_not_x_period_its_y", "rh_tricolon_fragments", "rh_the_catch_question",
               "rh_heres_the_thing", "rh_think_of_it", "rh_bottom_line", "rh_worth_noting", "rh_parenthetical_rate", "rh_contractions_rate",
               "rh_exclamations_rate", "rh_questions_rate", "rh_sentence_initial_and_but_rate", "rh_second_person_you_rate", "rh_first_person_i_rate"]
        L.append("| feature | value |")
        L.append("|---|---|")
        for k in sel:
            if k in f:
                v = f[k]
                if isinstance(v, str):
                    v = v.replace("|", "\\|")
                L.append(f"| {k} | {v} |")
        lex = {k: v for k, v in f.items() if k.startswith("lex:")}
        if lex:
            L.append("")
            L.append("Lexicon hits: " + ", ".join(f"{k[4:]}×{v}" for k, v in sorted(lex.items())))
        L.append("")

    # ---- Probe layer ----
    b = ctx.b
    if b:
        L.append("## Probe answers (parsed)\n")
        L.append("| item | parsed value |")
        L.append("|---|---|")
        for k in ["n_items_found", "identity_providers", "identity_models", "identity_cutoff", "identity_hedged", "date_event_cutoff",
                  "claims_realtime_date", "dataset_size_number", "dataset_size_declines", "system_prompt_class", "system_prompt_providers",
                  "system_prompt_models", "rand_1_100", "rand_1_10", "rand_1_50", "favorite_number", "coin", "rand_color", "rand_letter",
                  "rand_animal", "rand_city", "rand_digits", "rand_digits_stats", "strawberry", "strawberry_correct", "nine_eleven",
                  "nine_eleven_correct", "reverse_correct", "multiply_correct", "months_28", "months_28_correct", "months_28_both",
                  "climate_answer", "climate_words", "policy_vocab", "battery_used_bold_numbers", "battery_used_headers",
                  "battery_restated_questions", "battery_words"]:
            if k in b:
                v = str(b[k]).replace("|", "\\|").replace("\n", " ")
                L.append(f"| {k} | {v[:200]} |")
        L.append("")
        for k, title in [("identity_raw", "Identity answer"), ("date_event_raw", "Cutoff/event answer"), ("dataset_size_raw", "Dataset-size answer"),
                         ("system_prompt_raw", "System-prompt answer"), ("shortcuts_raw", "Shortcuts answer (format sample)"),
                         ("hotdog_raw", "Hot-dog answer"), ("joke_raw", "Joke"), ("not_allowed_raw", "Policy answer")]:
            if b.get(k):
                L.append(f"**{title}:**\n")
                L.append("```text")
                L.append(b[k][:1200])
                L.append("```\n")
    if ctx.ok:
        L.append(f"**'ok' turn:** {ctx.ok.get('ok_exact')!r} (form: {ctx.ok.get('ok_form')}, utf-8 hex: {ctx.ok.get('ok_bytes')})\n")
    if ctx.gib:
        L.append(f"**Gibberish turn:** {ctx.gib.get('gib_words')} words; starts '{ctx.gib.get('gib_first_words')}'; asks to clarify: {ctx.gib.get('gib_asks_clarify')}; mentions typo: {ctx.gib.get('gib_mentions_typo')}; emoji: {ctx.gib.get('gib_emoji')}\n")
    if ctx.mix:
        L.append(f"**Mixed-language turn:** {ctx.mix.get('mix_words')} words; languages {ctx.mix.get('mix_lang_counts')}; dominant {ctx.mix.get('mix_dominant')}; AI disclaimer: {ctx.mix.get('mix_mentions_ai')}\n")
    return "\n".join(L)
