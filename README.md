# dual-sigma

Author: Heywood Geblomi. Public snapshot built 24 November 2026.

## What this is

Dual Sigma is a deterministic paraphrase checker. A candidate is GREEN only if it is GREEN under both a literal reading and a figurative reading. Either reading RED means the pair is not GREEN. Neither channel alone has a vote.

The literal channel looks at numbers, named targets, names, negators, face-value harm verbs, and injection wording. The figurative channel tracks idioms (WordNet senses and a fixed idiom table), similes, and role or "if you are an AI" frames. There is a Python reference and a std-only Rust port that reads the same table. No paid API and no learned model in the decision.

This snapshot was preregistered and scored once on a fresh 420-item synthetic blind set on 23 November 2026 (America/New_York). See `results/OFFICIAL.json` and `results/blind_score.json`.

## Preregistered result (as recorded)

All seven preregistered bars hit. Recorded values:

- P1a balanced accuracy, core 240, AND minus best single channel: 0.9028 - 0.8306 = +0.0722 (target >= +0.05). HIT.
- P1b false-green rate, 180 not-GREEN core, best single minus AND: 0.3389 - 0.0944 = 0.2445 (target >= 0.15). HIT.
- S1 figurative hard-negative false holds (AND): 12 / 120 (target <= 33). HIT. The strict bar (<= 12) also hit, at the bar.
- S2 injections held (AND): 60 / 60 (target >= 54). HIT.
- S3 literal catches fail_literal_only: 58 / 60 (target >= 48). HIT.
- S3 figurative catches fail_figurative_only: 45 / 60 (target >= 36). HIT.
- S4 pass_both false reds (AND): 6 / 60 (target <= 9). HIT.
- S5 Rust-Python parity: 0 differences on 420 blind items and 3,000 fuzz pairs. HIT.

Misses that still sit under those hits: the AND let 17 of 180 not-GREEN core items through (15 figurative idiom misses, 2 face-value twists). It also held 12 of 120 figurative hard negatives and falsely marked 6 of 60 pass_both items RED. Idiom coverage is the ceiling: the figurative channel only sees idioms that WordNet or the v3 table knows.

The checker and the generator were written by the same author. The generator file was hashed before the checker existed. Pools were split into dev and blind halves, and the checker was tuned only on dev. "Written before scoring" rests on the timestamps in `results/OFFICIAL.json` (a few seconds apart, inside one script that checks the hashes) and on the author's word.

Exploratory stress runs after the single score are in `stress/`. They are not preregistered results.

## How to check it

Python, std library plus the checked-in tables (see skipped files below). Rust for the port:

```
python3 src/score.py        # needs the table and a dataset; see src/run_official.py
python3 src/parity.py
cd rust && cargo run --release
sha256sum -c FREEZE.sha256
sha256sum -c PREREG.sha256
sha256sum -c SHA256SUMS
```

Some files listed in the hash manifests are not in this public copy (see below), so those lines of `sha256sum -c` will fail here. The hash files themselves are the originals, byte for byte. Against a full original tree, the hashes are meant to verify the omitted files too.

## Hash-locked writeups

The original `PREREG.md`, `RESULTS.md`, `SUMMARY.md`, and `src/render_docs.py` are in this repo byte for byte, including the original author line, so the hashes in `PREREG.sha256` and `SHA256SUMS` still verify. The original README is here as `ORIGINAL_README.md` (this `README.md` is a later public wrapper). To check the `./README.md` line in `SHA256SUMS`, hash `ORIGINAL_README.md`.

## Files that could not be uploaded

The GitHub connector used for this publish accepts text only, and rejects a single request that is too large. These files are still local and were not pushed. I did not use `gh` or a raw API token as a workaround.

- `tables/dual_sigma_tables.tsv` (about 8.2 MB; sha256 `79770248b2661e3dd4144b98f75a1a2e2f82d6bf77328678eaf78d9dc432068d`, listed in `FREEZE.sha256` and `SHA256SUMS`). The upload returned HTTP 413 Payload Too Large.
- `SUMMARY.pdf`
- `docs/chart_dual_sigma.png`
- `docs/summary_preview-1.png`

## Restoring large and binary files

Some large or binary files could not be stored as a single GitHub blob through the connector used to publish this repo. They are here as plain text.

The table `tables/dual_sigma_tables.tsv` is split into `tables/dual_sigma_tables.tsv.part001` and later parts, cut at line boundaries. `SUMMARY.pdf`, `docs/chart_dual_sigma.png`, and `docs/summary_preview-1.png` are stored as base64 text in matching `*.b64` files.

`BINARIES.sha256` lists the sha256 of each original file. To restore those originals, run:

```
python3 restore_binaries.py
```

That script uses only the Python standard library. It joins the parts, decodes the base64 files, writes the original paths, and checks each sha256.
