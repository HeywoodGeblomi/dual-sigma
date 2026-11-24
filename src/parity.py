"""Rust-Python parity: run both cores on the same pairs and compare every TSV field (verdicts, reasons, notes).
Usage: python3 parity.py SET.jsonl OUT_PREFIX"""
import json, sys, subprocess, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
inp, pre = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(inp) if l.strip()]
tsv = pre + ".in.tsv"
with open(tsv, "w") as f:
    for r in rows: f.write("\t".join([r["id"], r["source"].replace("\t", " ").replace("\n", " "), r["candidate"].replace("\t", " ").replace("\n", " ")]) + "\n")
subprocess.run([sys.executable, str(ROOT / "src" / "dual_sigma.py"), "tsv", tsv, pre + ".py.tsv"], check=True)
subprocess.run([str(ROOT / "rust" / "target" / "release" / "dual_sigma"), str(ROOT / "tables" / "dual_sigma_tables.tsv"), "tsv", tsv, pre + ".rs.tsv"], check=True)
a = open(pre + ".py.tsv").read().split("\n"); b = open(pre + ".rs.tsv").read().split("\n")
diff = [(x, y) for x, y in zip(a, b) if x != y]
res = {"records": len(rows), "lines_py": len(a), "lines_rs": len(b), "differences": len(diff) + abs(len(a) - len(b)),
       "py_sha256": hashlib.sha256(open(pre + ".py.tsv", "rb").read()).hexdigest(), "rs_sha256": hashlib.sha256(open(pre + ".rs.tsv", "rb").read()).hexdigest(),
       "first_diffs": diff[:5]}
json.dump(res, open(pre + ".parity.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "first_diffs"}))
for x, y in diff[:3]: print("PY:", x, "\nRS:", y)
