# Dual Sigma: one-page summary

Walter Howard. 2026-11-23 (EST). Preregistered, scored once on a fresh synthetic blind set.

**Axiom.** A paraphrase, or a rewritten request or page, is GREEN only if it checks GREEN under both a literal reading and a figurative reading. Either reading RED means not GREEN. Neither reading alone has a vote.

**What was built.** A deterministic checker with two channels and an AND. The literal channel reads every word at face value: numbers, named targets, names, negators, harsh verbs on agent-reachable or living objects, injection wording. The figurative channel reads idioms as their WordNet senses, keeps an idiom ledger in both directions, unwraps similes, role and conditional-on-AI frames, and checks intended data actions and polarity. Python reference, std-only Rust port reading the same table, and a CLI for pairs, batches and single pages. No paid API and no learned model in the decision.

**Preregistered result (420 blind items).**

| Bar | Value | Target | Result |
|---|---|---|---|
| P1a balanced accuracy, AND minus best single | 0.903 - 0.831 = +0.072 | >= +0.05 | HIT |
| P1b false-green rate, best single minus AND | 0.339 - 0.094 = 0.245 | >= 0.15 | HIT |
| S1 figurative hard-negative false holds | 12 / 120 | < 34 (v3); strict <= 12 | HIT; strict HIT |
| S2 injections held | 60 / 60 | >= 54 | HIT |
| S3 own-cell catch, literal / figurative | 58 / 60, 45 / 60 | >= 48, >= 36 | HIT |
| S4 pass_both false reds | 6 / 60 | <= 9 | HIT |
| S5 Rust-Python parity (420 blind + 3,000 fuzz) | 0 differences | 0 | HIT |

**Misses and limits.** The AND still let 17 of 180 not-GREEN core items through: 15 figurative misses on idioms that neither WordNet nor the v3 table knows, and 2 face-value twists allowed because the source already acted on the same object. The 12 hard-negative false holds are all figurative ("pull the plug on the party" 5, "pull an all-nighter" 4, "break a sweat" 2, "drop the topic" 1). The 6 pass_both false reds come from the fail-closed rule for idioms with no known sense. P1b is partly structural, because gold GREEN is itself an AND. Checker and generator share an author (generator hashed first; checker tuned on a separate dev half). The prereg gave the blind total as 480; the cells are as preregistered and the true total is 420 (DEVIATIONS.md). The comparison with Analogous-0 v3's 34 of 120 is across different sets.

**Exploratory stress (after the score).** Injection sweep 1,385 of 1,440 held. Hard-negative sweep 148 of 1,400 red. Idiom coverage 40 of 64 matched, 25 of 64 with a known sense. Hand stress set: AND agreed with the author's label on 30 of 47; misses were leetspeak, implied orders, sentence-initial name changes, amounts in words, double negation, negation scope swaps and analogies without a frame word. A frozen MiniLM cosine baseline reached 0.622 balanced accuracy and held 113 of 120 hard negatives.

**Hashes.** PREREG.md `b498af90ffc4e18f09082e22e80d3d1eeef46ea9bb646012396f115f2a9f6d64` (18:36:48 EST). Blind set `f7ce729ea9292adab715eccc5745c7d13131a761a6c6732503c6ce0c953090e4` (seed 20261123, generated 18:36:51 EST, scored 18:36:52 EST).

**What held up.** Two cheap, separate readings joined by AND beat either reading alone on a fresh blind set, at a cost of 12 of 120 figurative false holds, with exact Rust-Python parity. Idiom coverage is the ceiling.
