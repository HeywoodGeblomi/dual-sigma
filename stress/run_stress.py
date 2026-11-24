"""Run the exploratory stress cases with the frozen core and print agreement per category."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src")); sys.path.insert(0, str(Path(__file__).resolve().parent))
from dual_sigma import DualSigma
from stress_cases import CASES
ds = DualSigma()
rows, agg = [], defaultdict(lambda: {"n": 0, "final_agree": 0, "lit_agree": 0, "fig_agree": 0, "lit_only_final_agree": 0, "fig_only_final_agree": 0})
for i, (cat, s, c, ef, el, efg, note) in enumerate(CASES):
    d = ds.check(s, c)
    a = agg[cat]; a["n"] += 1
    a["final_agree"] += d["final"] == ef; a["lit_agree"] += d["literal"]["verdict"] == el; a["fig_agree"] += d["figurative"]["verdict"] == efg
    a["lit_only_final_agree"] += d["literal"]["verdict"] == ef; a["fig_only_final_agree"] += d["figurative"]["verdict"] == ef
    rows.append({"i": i, "cat": cat, "note": note, "source": s, "candidate": c, "expect": [ef, el, efg],
                 "got": [d["final"], d["literal"]["verdict"], d["figurative"]["verdict"]], "lit_reasons": d["literal"]["reasons"], "fig_reasons": d["figurative"]["reasons"]})
tot = {k: sum(a[k] for a in agg.values()) for k in ("n", "final_agree", "lit_agree", "fig_agree", "lit_only_final_agree", "fig_only_final_agree")}
out = {"per_category": agg, "total": tot, "cases": rows}
json.dump(out, open(Path(__file__).resolve().parent / "stress_results.json", "w"), indent=1)
print(json.dumps({"per_category": agg, "total": tot}, indent=1))
for r in rows:
    if r["got"][0] != r["expect"][0]: print("DISAGREE", r["cat"], r["note"], r["got"], r["expect"], r["lit_reasons"], r["fig_reasons"])
