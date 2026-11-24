"""Exploratory comparator (after the single score): frozen all-MiniLM-L6-v2 (Analogous-0 v3 copy, read only) cosine
similarity between source and candidate. GREEN if cosine >= t. t is picked on the dev set (best balanced accuracy on the
dev core cells), then applied once to the blind set."""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, "/workspace/frontier_pivot/analogous0_v3/src_py")
from verbmap import VerbEncoder
enc = VerbEncoder("/workspace/frontier_pivot/analogous0_v3/models/encoder")
CORE = ("pass_both", "fail_literal_only", "fail_figurative_only", "fail_both")
def load(p): return [json.loads(l) for l in open(p)]
def cos(it): a, b = enc.encode_one(it["source"]), enc.encode_one(it["candidate"]); return float(a @ b)
def ba(rows, t):
    tp = sum(1 for g, c in rows if g and c >= t); fn = sum(1 for g, c in rows if g and c < t)
    tn = sum(1 for g, c in rows if not g and c < t); fp = sum(1 for g, c in rows if not g and c >= t)
    return ((tp / (tp + fn) if tp + fn else 0) + (tn / (tn + fp) if tn + fp else 0)) / 2, fp / (tn + fp) if tn + fp else 0
dev = load(ROOT / "data" / "dev_set.jsonl"); blind = load(ROOT / "data" / "blind_set.jsonl")
dv = [(it["gold_green"], cos(it)) for it in dev if it["cell"] in CORE]
best = max(sorted({c for _, c in dv}), key=lambda t: (ba(dv, t)[0], -t))
bl = {it["id"]: cos(it) for it in blind}
core = [(it["gold_green"], bl[it["id"]]) for it in blind if it["cell"] in CORE]
hn = [bl[it["id"]] for it in blind if it["cell"] == "hard_negative"]
inj = [bl[it["id"]] for it in blind if it["cell"] == "injection"]
cells = {}
for it in blind:
    c = cells.setdefault(it["cell"], {"n": 0, "green": 0, "mean_cos": 0.0}); c["n"] += 1; c["green"] += bl[it["id"]] >= best; c["mean_cos"] += bl[it["id"]]
for c in cells.values(): c["mean_cos"] = round(c["mean_cos"] / c["n"], 4)
res = {"model": enc.tag(), "threshold_from_dev": round(best, 4), "dev_core_balanced_accuracy": round(ba(dv, best)[0], 4),
       "blind_core_balanced_accuracy": round(ba(core, best)[0], 4), "blind_core_false_green_rate": round(ba(core, best)[1], 4),
       "blind_hard_negative_false_holds": sum(1 for c in hn if c < best), "blind_injection_held": sum(1 for c in inj if c < best), "cells": cells}
json.dump(res, open(HERE / "minilm_baseline_results.json", "w"), indent=1)
print(json.dumps(res, indent=1))
