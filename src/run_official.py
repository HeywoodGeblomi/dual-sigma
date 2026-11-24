"""Single official scoring run. Checks FREEZE.sha256 and PREREG.sha256, generates the blind set with the
preregistered seed, hashes it, runs the Python core once, scores it, then runs Rust-Python parity on the blind set
and on 3,000 fuzz pairs. Refuses to run twice (results/OFFICIAL.json must not exist)."""
import json, subprocess, sys, hashlib, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return time.strftime("%Y-%m-%d %H:%M:%S %Z")
assert not (R / "OFFICIAL.json").exists(), "official run already done"
for line in (ROOT / "FREEZE.sha256").read_text().split("\n"):
    if line.strip():
        h, p = line.split("  ", 1); assert sha(ROOT / p) == h, "frozen file changed: " + p
h, p = (ROOT / "PREREG.sha256").read_text().split()[:2]; assert sha(ROOT / p) == h, "PREREG changed"
out = {"started": now(), "prereg_sha256": h, "freeze_sha256": sha(ROOT / "FREEZE.sha256")}
SEED = 20261123
blind = ROOT / "data" / "blind_set.jsonl"
subprocess.run([sys.executable, str(ROOT / "src" / "gen_dataset.py"), "blind", str(SEED), str(blind)], check=True)
out["blind_seed"] = SEED; out["blind_sha256"] = sha(blind); out["blind_generated"] = now()
subprocess.run([sys.executable, str(ROOT / "src" / "dual_sigma.py"), "batch", str(blind), str(R / "blind_decisions.jsonl")], check=True)
out["decisions_sha256"] = sha(R / "blind_decisions.jsonl"); out["scored"] = now()
subprocess.run([sys.executable, str(ROOT / "src" / "score.py"), str(blind), str(R / "blind_decisions.jsonl"), str(R / "blind_score.json")], check=True)
out["score_sha256"] = sha(R / "blind_score.json")
subprocess.run(["cargo", "build", "--release", "--offline"], cwd=ROOT / "rust", check=True, capture_output=True)
subprocess.run([sys.executable, str(ROOT / "src" / "parity.py"), str(blind), str(R / "parity_blind")], check=True)
subprocess.run([sys.executable, str(ROOT / "src" / "fuzz_pairs.py"), str(SEED), "3000", str(blind), str(R / "fuzz_blind.jsonl")], check=True)
subprocess.run([sys.executable, str(ROOT / "src" / "parity.py"), str(R / "fuzz_blind.jsonl"), str(R / "parity_fuzz")], check=True)
out["parity_blind"] = json.loads((R / "parity_blind.parity.json").read_text())["differences"]
out["parity_fuzz"] = json.loads((R / "parity_fuzz.parity.json").read_text())["differences"]
out["finished"] = now()
(R / "OFFICIAL.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
