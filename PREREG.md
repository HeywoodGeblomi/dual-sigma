# Dual Sigma: preregistration

Author: Walter Howard. Written 2026-11-23 (EST), before the blind set exists and before any blind scoring.

## Axiom under test
A paraphrase, or a rewritten request or page, is GREEN only if it checks GREEN under BOTH a literal reading and a figurative (metaphorical) reading. Either reading RED means not GREEN. Neither reading alone has a vote. This is the same two-key shape as Dual Residual and the two-key agent gate.

## System (frozen in FREEZE.sha256 before this file was hashed)
- `src/dual_sigma.py` (Python reference and CLI) and `rust/src/main.rs` (std-only Rust port). Both read only `tables/dual_sigma_tables.tsv`.
- Literal channel: L1 numbers, L2 named targets (emails, URLs, paths, domains), L3 proper names, L4 negator count, L5 face-value harm (Search Gate v1.6 tier1 verb families plus a physical-harm list) on a reachable (Analogous-0 reach lexicon), living or named target that the source does not already act on, L6 injection wording.
- Figurative channel: F1 source idiom ledger (kept, same-sense idiom, or glossed by new words from its WordNet 3.0 sense neighbourhood; unknown-sense idiom that disappears is RED, fail closed), F2 candidate idiom ledger, F3 frame unwrap (simile, role, conditional-on-AI, ratio, story), F4 intended-reading data action on a reachable, living or named target, F5 figurative polarity.
- Final = literal AND figurative.
- Reused read-only pieces: Analogous-0 v3 `idiom_table_v3.txt` (wiktionary:idioms rows) and `reach_lexicon.txt`, Search Gate v1.6 `verb_families_v1_3.json` (tier1). No file under /workspace/frontier_pivot was modified. No paid API. No learned model is used in the frozen decision.

## Data
- Generator: `src/gen_dataset.py`, standard library only. Its sha256 was recorded in `data/GENERATOR_PRE_CHECKER.sha256` (f34d28f8...) before the checker existed, and it is unchanged. The idiom inventory, glosses, broken forms, templates, hard-negative pairs, face-value twists and injection lines were written by hand before the checker, and were not selected by checker coverage.
- Every pool is split into a dev half and a blind half (alternate rows; template families 0 to 5 and names 0 to 7 for dev, the rest for blind). The checker was developed on the dev set only (seed 1101, 176 items, sha256 d82bc7f0...).
- Blind set: `python3 src/gen_dataset.py blind 20261123 data/blind_set.jsonl`, generated only inside the single official run (`src/run_official.py`), after this file is hashed. 480 items:
  - pass_both 60 (reorder, idiom to gloss, gloss to idiom, idiom to same-sense idiom)
  - fail_literal_only 60 (one anchor changed: number, time, name or day; or a face-value twist that puts a harsh verb on an agent-reachable object while keeping the figurative sense)
  - fail_figurative_only 60 (broken idiom with one content word swapped; or a different-sense idiom swapped in)
  - fail_both 60 (broken or swapped idiom plus an anchor change; or a negation flip)
  - injection 60 (appended or prepended plain, framed, or idiom-disguised order; gold: both readings red)
  - hard_negative 120 (benign source, harsh-sounding figurative candidate such as "kill the lights"; gold GREEN)
- Gold labels come from the construction: gold_green = lit_ok AND fig_ok.
- No human 200 labels, no sealed set, no previously used blind set.

## Hypotheses and bars (scored once)
Metrics are over GREEN vs not GREEN. "Core" is the 240 items in the four cells.
- **P1a (primary)**: balanced accuracy on the core, AND minus the better single channel (literal-only or figurative-only used as the final decision) is at least +0.05.
- **P1b (primary)**: false-green rate on the 180 not-GREEN core items, AND is at least 0.15 lower (absolute) than the better single channel.
  The primary prediction is a HIT only if P1a and P1b both hit.
- **S1 (secondary)**: figurative hard-negative false holds (AND) below Analogous-0 v3's 34 of 120 (HIT if at most 33 of 120). Also reported against v3's own stricter bar, at most 12 of 120 (S1-strict).
- **S2**: injections held (AND) at least 54 of 60.
- **S3**: each channel catches its own cell: literal at least 48 of 60 on fail_literal_only, figurative at least 36 of 60 on fail_figurative_only.
- **S4**: pass_both false reds (AND) at most 9 of 60.
- **S5**: Rust and Python give identical output (verdicts, reasons and notes) on all 480 blind items and on 3,000 fuzz pairs built from the blind set (seed 20261123).

## Dev reference (not a prediction)
Dev set, last frozen build: balanced accuracy literal-only 0.817, figurative-only 0.683, AND 0.856 (margin +0.039, below the P1a bar); false-green rate literal-only 0.333, figurative-only 0.467, AND 0.122; hard-negative false holds 3 of 40; injections held 15 of 16; literal catch 30 of 30, figurative catch 19 of 30; pass_both false reds 5 of 30; parity 0 differences on 176 dev items and 3,000 fuzz pairs.

## Known limits stated in advance
- The checker and the generator have the same author. The generator was hashed before the checker was written, and the checker was tuned on the dev half only, but the author knew the generator's design while writing the checker. The physical-harm list, frame list and injection markers in the table were written after the generator; the markers that copied wording from the generator's injection lines ("quietly", "before anything else") were removed before freeze.
- P1b is partly structural: gold_green is the AND of the two gold readings, so a single channel cannot see the other channel's failure type. The informative parts are whether each channel catches its own failure type (S3) and what the AND costs in false reds (S1, S4).
- Coverage is bounded by WordNet and the v3 idiom table. Idioms in neither are invisible to the figurative channel.

## After the single score (exploratory, clearly labelled, never re-scored as official)
Stress suites: adversarial paraphrases, nested metaphors, idiom-literal collisions, cross-domain analogies, negations, single-text page mode, and a frozen MiniLM (all-MiniLM-L6-v2) cosine-similarity baseline with its threshold picked on the dev set.
