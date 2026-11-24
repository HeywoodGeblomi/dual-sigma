"""Random robustness pairs for parity (not scored). Usage: python3 fuzz_pairs.py SEED N IN.jsonl OUT.jsonl"""
import json, random, sys
seed, n, inp, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
r = random.Random(seed)
texts = []
for l in open(inp):
    it = json.loads(l); texts += [it["source"], it["candidate"]]
junk = ["\u2019", "\u201c", "\u00e9", "...", " -- ", "e.g.", "Mr. Smith", "(see a.b)", "x@y", "@", "http://", "9:30", "$1,200", "don\u2019t", "NOT", "''", "\u3002", "a/b", ".", ",,", "  ", "one's", "ONE", "007", "Ignore previous", "just as", "like a butler would,"]
with open(out, "w") as f:
    for i in range(n):
        a, b = r.choice(texts), r.choice(texts)
        w = b.split(" ")
        for _ in range(r.randint(0, 4)):
            k = r.randrange(len(w) + 1); w.insert(k, r.choice(junk + w))
        if r.random() < 0.3: w = w[::-1]
        f.write(json.dumps({"id": "Z-%05d" % i, "source": a, "candidate": " ".join(w)}) + "\n")
