# Deviations from PREREG.md

1. **Blind set total.** PREREG.md says the blind set has 480 items. The cell sizes listed there (60, 60, 60, 60, 60 injection, 120 hard negative) add up to 420, and the generator, frozen before the prereg, produces 420. The 480 was an addition error in the prereg text. Every bar is stated per cell or as a fraction, so no bar changes. S5 ("all 480 blind items") was applied to all 420.
2. **Same-sense idiom subtype.** PREREG.md lists "idiom to same-sense idiom" among the pass_both subtypes. No two idioms with the same sense group fell in the blind half of the inventory, so the blind set has 0 such items; their slots were filled with gloss-to-idiom items by the frozen generator. The dev set had 3.
3. No other deviation. The single official run used the frozen files (checked against FREEZE.sha256 inside `src/run_official.py`), and the blind set was generated inside that run, after PREREG.md was hashed.
