# Samples

One directory per analysed case:

| file | content |
|---|---|
| `t1_essay.md` | reply to Turn 1 (free-form telescope guide) |
| `t2_battery.md` | reply to Turn 2 (24-item battery) |
| `t3_ok.md` | reply to Turn 3 (exact bytes; keep as-is, no trailing newline added) |
| `t4_gibberish.md` | reply to Turn 4 |
| `t5_mixed.md` | reply to Turn 5 |
| `regen_1.md`, `regen_2.md` | optional regenerations of Turn 1 in fresh chats |
| `meta.json` | `source` (chat/api), free notes, and `ground_truth` once revealed |
| `report.md`, `result.json` | written by `python -m detector analyze` |

`python -m detector ingest <case_dir> pasted.txt` fills the turn files from a single
paste that uses `=== T1 ===` … `=== R2 ===` separators (see PROTOCOL.md).

`claude_fable_5.1_self/` is a labelled smoke-test case written by the model that built this
tool; it is not a claude.ai chat transcript, so treat it as a pipeline check rather than a
style reference.
