"""Exploratory sweeps at scale (after the single score). Uses both generator halves, so dev material is included; never a scored result.
1. Injection sweep: every injection line (24) appended to every blind pass_both candidate (60) -> 1,440 pairs.
2. Hard-negative sweep: every hard-negative pair (50) in every template family (14), both variants -> 1,400 pairs.
3. Idiom coverage: for each of the 64 generator idioms, does the checker see it as an idiom, and with a known sense?
4. Broken / swapped sweep: every idiom broken, and swapped with every other-sense idiom, in one family -> 64 + 64*63 pairs."""
import json, sys, random
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from dual_sigma import DualSigma, Analysis
import gen_dataset as G
ds = DualSigma(); T = ds.T
out = {}
blind = [json.loads(l) for l in open(ROOT / "data" / "blind_set.jsonl")]
pb = [b for b in blind if b["cell"] == "pass_both"]
r = random.Random(5)
inj = defaultdict(lambda: {"n": 0, "AND": 0, "lit": 0, "fig": 0})
for line in G.INJECT:
    for b in pb:
        x = line.replace("{ADDR}", "ops@example-sink.net").replace("{URL}", "https://example-sink.net/in/1").replace("{ACCT}", "55501234").replace("{T}", "9 pm")
        d = ds.check(b["source"], b["candidate"] + " " + x)
        a = inj[line]; a["n"] += 1; a["AND"] += d["final"] == "RED"; a["lit"] += d["literal"]["verdict"] == "RED"; a["fig"] += d["figurative"]["verdict"] == "RED"
out["injection_sweep"] = {"per_line_held": inj, "total": {k: sum(v[k] for v in inj.values()) for k in ("n", "AND", "lit", "fig")}}
hn = defaultdict(lambda: {"n": 0, "AND_red": 0, "lit_red": 0, "fig_red": 0, "example_reason": ""})
gen = G.Gen("blind", 1)
for plain, harsh in G.HARD_NEG:
    for fam in G.FAMILIES:
        s = {"N": "Grace", "D": "Friday", "T": "4 pm", "K": 12}
        for va, vb in ((0, 1), (1, 0)):
            d = ds.check(gen.render(fam[va], s, plain), gen.render(fam[vb], s, harsh))
            a = hn[harsh]; a["n"] += 1; a["AND_red"] += d["final"] == "RED"; a["lit_red"] += d["literal"]["verdict"] == "RED"; a["fig_red"] += d["figurative"]["verdict"] == "RED"
            if d["final"] == "RED" and not a["example_reason"]: a["example_reason"] = (d["literal"]["reasons"] + d["figurative"]["reasons"])[0]
out["hard_negative_sweep"] = {"per_pair": hn, "total": {k: sum(v[k] for v in hn.values()) for k in ("n", "AND_red", "lit_red", "fig_red")},
                              "pairs_never_red": sum(1 for v in hn.values() if v["AND_red"] == 0), "pairs_always_red": sum(1 for v in hn.values() if v["AND_red"] == v["n"])}
cov = []
for i, (idi, gloss, broken, grp) in enumerate(G.IDIOMS):
    A = Analysis(T, "Please " + idi + " today.")
    found = [(" ".join(T.pat[m[2]]), m[2] in T.Y, m[2] in T.light) for m in A.idioms]
    cov.append({"idiom": idi, "half": "dev" if i % 2 == 0 else "blind", "matched": found,
                "full_known": any(k and not l and len(p.split()) >= 2 for p, k, l in found), "any_nonlight": any(not l for p, k, l in found)})
out["idiom_coverage"] = {"rows": cov, "nonlight_match": sum(c["any_nonlight"] for c in cov), "known_sense_nonlight": sum(c["full_known"] for c in cov), "n": len(cov),
                         "blind_nonlight": sum(c["any_nonlight"] for c in cov if c["half"] == "blind"), "blind_known": sum(c["full_known"] for c in cov if c["half"] == "blind")}
fam = G.FAMILIES[0]; s = {"N": "Grace", "D": "Friday", "T": "4 pm", "K": 12}
br = sum(ds.check(gen.render(fam[0], s, x[0]), gen.render(fam[1], s, x[2]))["figurative"]["verdict"] == "RED" for x in G.IDIOMS)
sw, swn = 0, 0
for a in G.IDIOMS:
    for b in G.IDIOMS:
        if a[3] == b[3]: continue
        swn += 1; sw += ds.check(gen.render(fam[0], s, a[0]), gen.render(fam[1], s, b[0]))["figurative"]["verdict"] == "RED"
gl = sum(ds.check(gen.render(fam[0], s, x[0]), gen.render(fam[1], s, x[1]))["figurative"]["verdict"] == "GREEN" for x in G.IDIOMS)
out["idiom_sweep"] = {"broken_caught": br, "broken_n": len(G.IDIOMS), "swap_caught": sw, "swap_n": swn, "gloss_green": gl, "gloss_n": len(G.IDIOMS)}
json.dump(out, open(HERE / "sweeps_results.json", "w"), indent=1)
print(json.dumps({k: (v if k not in ("injection_sweep", "hard_negative_sweep", "idiom_coverage") else {kk: vv for kk, vv in v.items() if kk not in ("per_line_held", "per_pair", "rows")}) for k, v in out.items()}, indent=1))
for line, v in out["injection_sweep"]["per_line_held"].items():
    if v["AND"] < v["n"]: print("INJ not always held:", v["AND"], "/", v["n"], "lit", v["lit"], "fig", v["fig"], line[:80])
for p, v in sorted(hn.items(), key=lambda x: -x[1]["AND_red"]):
    if v["AND_red"]: print("HN red", v["AND_red"], "/", v["n"], p, "|", v["example_reason"][:110])
