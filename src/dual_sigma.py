#!/usr/bin/env python3
"""Dual Sigma: a paraphrase (or rewritten request or page) is GREEN only if it checks GREEN under BOTH a literal
reading and a figurative (metaphorical) reading. Either reading RED means not GREEN. Neither channel alone has a vote.

Literal channel (every word at face value):
  L1 numbers, L2 named targets (emails, URLs, paths, domains), L3 proper names, L4 polarity (negator count),
  L5 face-value harm: a harm verb (Search Gate v1.6 tier1 families plus a physical-harm list) whose object window
     holds an agent-reachable word, a living target or a named target that the source does not already act on,
  L6 injection wording absent from the source.
Figurative channel (idioms read as their senses, frames unwrapped):
  F1 idiom ledger source->candidate: every source idiom is kept, swapped for a same-sense idiom, or glossed by new words
     from its WordNet sense neighbourhood; an idiom with no known sense that disappears is RED (fail closed),
  F2 idiom ledger candidate->source: every new candidate idiom must be grounded in the source the same way; a new idiom
     with no known sense is RED only if its clause holds a reachable, living or named target,
  F3 frames (simile, role, conditional-on-AI, ratio, story) new in the candidate are unwrapped; RED if the unwrapped
     order adds a reachable, living or named target or a data-action verb absent from the source,
  F4 intended-reading data action: a data-action verb, or an idiom whose sense is a data action, with a reachable,
     living or named object the source does not already act on,
  F5 polarity of the figurative reading (negators outside idiom spans).
Final = literal AND figurative. Deterministic, standard library only, one table file shared with the Rust port.
"""
import json, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "tables" / "dual_sigma_tables.tsv"
ARTICLES = {"a", "an", "the"}
POSS_W = {"my", "your", "his", "her", "its", "our", "their", "one's"}
REFL_W = {"myself", "yourself", "himself", "herself", "itself", "ourselves", "yourselves", "themselves", "oneself"}
CONJ = {"and", "then", "but", "so", "or", "while", "because", "since", "if"}
LEAD = "\"'([{<"
TRAIL = "\"')]}>.,;:!?"
SB, CB = "||", "|"

def _alnum(c): return ("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9")
def _alpha(c): return ("a" <= c <= "z") or ("A" <= c <= "Z")
def _lower(s): return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)

class Tables:
    def __init__(self, path=TABLE):
        raw = Path(path).read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.pat, self.head, self.A, self.P, self.Y = {}, {}, {}, {}, {}
        self.by_head = {}
        self.harm = {}
        for line in raw.decode("ascii").split("\n"):
            if not line: continue
            f = line.split("\t"); k = f[0]
            if k == "I":
                iid = f[1]; self.pat[iid] = f[2].split(" ")
                if self.pat[iid][0].startswith("<"): continue
                for h in f[5].split(" "): self.by_head.setdefault(h, []).append(iid)
            elif k == "Y": self.Y[f[1]] = set(f[2].split(" "))
            elif k == "A": self.A[f[1]] = set(f[2].split(" ")) if f[2] else set()
            elif k == "P": self.P[f[1]] = [p.split(" ") for p in f[2].split("|")]
            elif k == "R": self.reach = set(f[1].split(" "))
            elif k == "H": self.harm[f[1]] = set(f[2].split(" "))
            elif k == "L": self.living = set(f[1].split(" "))
            elif k == "G": self.neg = set(f[1].split(" "))
            elif k == "U": self.numw = dict(x.split("=") for x in f[1].split(" "))
            elif k == "J": self.inj = [x.split(" ") for x in f[1].split("|")]
            elif k == "F": self.frames = [x.split(" ") for x in f[1].split("|")]
            elif k == "S": self.stop = set(f[1].split(" "))
            elif k == "K": self.particles = set(f[1].split(" "))
        self.data_harm = set()
        for fam, forms in self.harm.items():
            if fam != "physical": self.data_harm |= forms
        self.all_harm = self.data_harm | self.harm["physical"]
        self.data_idiom = {iid for iid, a in self.A.items() if a & self.data_harm}
        # light idioms: at most one content token and ending in a particle or function word (phrasal verbs such as
        # 'turn off', 'look after', 'get rid of', and function-word units such as 'with it'). They are matched, but a
        # light idiom never makes the ledger RED and never grounds another idiom.
        fw = self.stop | self.particles
        self.light = set()
        for iid, p in self.pat.items():
            content = [t for t in p if not t.startswith("<") and t not in fw]
            if len(content) <= 1 and (p[-1].startswith("<") or p[-1] in fw): self.light.add(iid)

def is_target(core):
    low = _lower(core)
    at = core.find("@")
    if 0 < at < len(core) - 1: return True
    if low.startswith("http://") or low.startswith("https://") or low.startswith("www."): return True
    if "/" in core and any(_alnum(c) for c in core): return True
    if "." in core:
        last = core.rfind(".")
        tail, headp = core[last + 1:], core[:last]
        if len(tail) >= 2 and all(_alpha(c) for c in tail) and len(headp) >= 2 and _alnum(core[last - 1]): return True
    return False

class Doc:
    """token stream with clause '|' and sentence '||' boundaries; targets become 'zztarget'."""
    def __init__(self, text):
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = "".join(c if ord(c) < 128 else " " for c in text)
        self.toks, self.targets, self.names = [], [], set()
        chunks = text.split()
        for ci, ch in enumerate(chunks):
            s, e = 0, len(ch)
            while s < e and ch[s] in LEAD: s += 1
            while e > s and ch[e - 1] in TRAIL: e -= 1
            core, tr = ch[s:e], ch[e:]
            nm = ""
            for c in core:
                if _alpha(c): nm += c
                else: break
            if nm and "A" <= nm[0] <= "Z" and ci > 0 and chunks[ci - 1][-1] not in ".!?:" and nm != "I":
                self.names.add(_lower(nm))
            if core and is_target(core):
                self.toks.append("zztarget"); self.targets.append(_lower(core))
                if any(c in ".!?" for c in tr): self.toks.append(SB)
                elif any(c in ",;:" for c in tr): self.toks.append(CB)
                continue
            low, cur = _lower(ch), ""
            for j, c in enumerate(low):
                if _alnum(c) or c == "'": cur += c; continue
                self._flush(cur); cur = ""
                nxt_al = j + 1 < len(low) and _alnum(low[j + 1])
                if c in ".!?" and not nxt_al: self.toks.append(SB)
                elif c in ",;:" and not nxt_al: self.toks.append(CB)
            self._flush(cur)
        self.cidx = [i for i, t in enumerate(self.toks) if t not in ARTICLES]
        self.ctoks = [self.toks[i] for i in self.cidx]

    def _flush(self, cur):
        t = cur.strip("'")
        if t: self.toks.append(t)

def match_pat(pat, toks, i):
    """match pattern tokens against toks starting at i (pattern token 0 already matched). Returns end index or -1.
    <poss> one possessive, <refl> one reflexive, <slot> 1-3 non-boundary tokens (shortest first); a possessive may be
    skipped before a literal pattern token."""
    def rec(p, j):
        if p == len(pat): return j
        pt = pat[p]
        if j >= len(toks) or toks[j] in (SB, CB): return -1
        if pt == "<poss>": return rec(p + 1, j + 1) if toks[j] in POSS_W else -1
        if pt == "<refl>": return rec(p + 1, j + 1) if toks[j] in REFL_W else -1
        if pt == "<slot>":
            for n in (1, 2, 3):
                if j + n > len(toks) or any(t in (SB, CB) for t in toks[j:j + n]): break
                r = rec(p + 1, j + n)
                if r >= 0: return r
            return -1
        if toks[j] == pt: return rec(p + 1, j + 1)
        if toks[j] in POSS_W and j + 1 < len(toks) and toks[j + 1] == pt: return rec(p + 1, j + 2)
        return -1
    return rec(1, i + 1)

def find_idioms(T, d):
    """greedy longest non-overlapping idiom matches on the article-free stream: list of (start, end, id) in ctoks index."""
    toks = d.ctoks; cands = []
    for i, t in enumerate(toks):
        for iid in T.by_head.get(t, ()):
            e = match_pat(T.pat[iid], toks, i)
            if e > 0: cands.append((i, e, iid))
    cands.sort(key=lambda x: (x[0], -(x[1] - x[0]), x[2]))
    out, last = [], 0
    for s, e, iid in cands:
        if s >= last: out.append((s, e, iid)); last = e
    return out

def window_hits(T, toks, i, objs_only_after=True):
    hits = []
    j, n = i + 1, 0
    while j < len(toks) and n < 6:
        t = toks[j]
        if t in (SB, CB) or t in CONJ: break
        if t not in ARTICLES:
            n += 1
            if t == "zztarget": hits.append("zztarget")
            elif t in T.living: hits.append("living:" + t)
            elif t in T.reach: hits.append(t)
            elif len(t) > 3 and t.endswith("s") and t[:-1] in T.reach: hits.append(t[:-1])
        j += 1
    return hits

def neg_count(T, toks, skip=frozenset()):
    return sum(1 for k, t in enumerate(toks) if k not in skip and (t in T.neg or t.endswith("n't")))

def contains_seq(toks, seq):
    """seq may contain <slot> (1-3 tokens). returns list of (start, end)."""
    out = []
    for i in range(len(toks)):
        if toks[i] != seq[0] and seq[0] != "<slot>": continue
        if seq[0] == "<slot>": continue
        e = match_pat(seq, toks, i) if len(seq) > 1 else i + 1
        if e > 0: out.append((i, e))
    return out

class Analysis:
    def __init__(self, T, text):
        self.d = d = Doc(text)
        self.idioms = find_idioms(T, d)
        self.id_set = {m[2] for m in self.idioms}
        self.in_idiom_c = set()
        for s, e, _ in self.idioms: self.in_idiom_c |= set(range(s, e))
        self.in_idiom_full = {d.cidx[k] for k in self.in_idiom_c}
        nums = []
        for k, t in enumerate(d.toks):
            if k in self.in_idiom_full: continue
            if t.isdigit(): nums.append(str(int(t)))
            elif t in T.numw: nums.append(T.numw[t])
        self.nums = sorted(nums)
        self.tokset = set(t for t in d.toks if t not in (SB, CB))
        self.outside = set(t for k, t in enumerate(d.ctoks) if k not in self.in_idiom_c and t not in (SB, CB))
        # literal harm events: (verb, object) at face value
        self.lit_events = []
        for k, t in enumerate(d.toks):
            if t in T.all_harm:
                for h in window_hits(T, d.toks, k): self.lit_events.append((t, h))
        # figurative (intended) data-action events
        self.fig_events = []
        for k, t in enumerate(d.ctoks):
            if k in self.in_idiom_c: continue
            if t in T.data_harm:
                for h in window_hits(T, d.ctoks, k): self.fig_events.append((t, h))
        for s, e, iid in self.idioms:
            if iid in T.data_idiom:
                for h in window_hits(T, d.ctoks, e - 1): self.fig_events.append(("idiom:" + iid, h))
        self.neg_lit = neg_count(T, d.toks)
        self.neg_fig = neg_count(T, d.toks, self.in_idiom_full)
        self.inj = sorted({" ".join(m) for m in T.inj if contains_seq(d.toks, m)})
        self.frames = []
        for fi, fr in enumerate(T.frames):
            for s, e in contains_seq(d.toks, fr): self.frames.append((fi, s, e))

def accounted(T, iid, other, new_tokens, other_ctoks_str):
    if iid in other.id_set: return "kept"
    y = T.Y.get(iid)
    if not y: return None
    for s, e, j in other.idioms:
        if j not in T.light and T.Y.get(j, set()) & y: return "same_sense_idiom:" + j
    hit = sorted(T.A.get(iid, set()) & new_tokens)
    if hit: return "gloss_word:" + hit[0]
    for ph in T.P.get(iid, []):
        if any(t in new_tokens for t in ph) and (" " + " ".join(ph) + " ") in other_ctoks_str: return "gloss_phrase:" + " ".join(ph)
    return None

def clause_has_object(T, toks, s, e):
    a, b = s, e
    while a > 0 and toks[a - 1] not in (SB, CB): a -= 1
    while b < len(toks) and toks[b] not in (SB, CB): b += 1
    for t in toks[a:s] + toks[e:b]:
        if t == "zztarget" or t in T.living or t in T.reach or (len(t) > 3 and t.endswith("s") and t[:-1] in T.reach): return True
    return False

def literal_channel(T, S, C):
    r = []
    if S.nums != C.nums: r.append("L1 numbers differ: source %s, candidate %s" % (S.nums, C.nums))
    if sorted(set(S.d.targets)) != sorted(set(C.d.targets)): r.append("L2 targets differ: source %s, candidate %s" % (sorted(set(S.d.targets)), sorted(set(C.d.targets))))
    miss = sorted(n for n in S.d.names if n not in C.tokset)
    add = sorted(n for n in C.d.names if n not in S.tokset)
    if miss or add: r.append("L3 names differ: dropped %s, added %s" % (miss, add))
    if S.neg_lit != C.neg_lit: r.append("L4 polarity differs: source negators %d, candidate %d" % (S.neg_lit, C.neg_lit))
    s_objs = {h for _, h in S.lit_events}
    new = sorted({"%s->%s" % (v, h) for v, h in C.lit_events if h not in s_objs})
    if new: r.append("L5 face-value harm on reachable or living target: %s" % ", ".join(new))
    newinj = sorted(set(C.inj) - set(S.inj))
    if newinj: r.append("L6 injection wording: %s" % ", ".join(newinj))
    return ("RED" if r else "GREEN"), r

def figurative_channel(T, S, C, single=False):
    r, notes = [], []
    if not single:
        new_c = C.tokset - S.outside - {SB, CB}
        new_s = S.tokset - C.outside - {SB, CB}
        c_str = " " + " ".join(C.d.ctoks) + " "; s_str = " " + " ".join(S.d.ctoks) + " "
        for s, e, iid in S.idioms:
            how = accounted(T, iid, C, new_c, c_str)
            if how is None and iid in T.light:
                notes.append("F1 light idiom '%s' not carried, not counted" % " ".join(T.pat[iid])); continue
            if how is None:
                kind = "known sense" if iid in T.Y else "unknown sense"
                r.append("F1 source idiom '%s' (%s) not carried into candidate" % (" ".join(T.pat[iid]), kind))
            else: notes.append("F1 '%s' %s" % (" ".join(T.pat[iid]), how))
        for s, e, iid in C.idioms:
            if iid in S.id_set: continue
            how = accounted(T, iid, S, new_s, s_str)
            if how is not None: notes.append("F2 '%s' %s" % (" ".join(T.pat[iid]), how)); continue
            if iid in T.light: notes.append("F2 light idiom '%s' ungrounded, not counted" % " ".join(T.pat[iid])); continue
            if iid not in T.Y:
                if clause_has_object(T, C.d.ctoks, s, e): r.append("F2 new idiom '%s' (unknown sense) next to a reachable, living or named target" % " ".join(T.pat[iid]))
                else: notes.append("F2 '%s' unknown sense, no reachable target, not counted" % " ".join(T.pat[iid]))
            else:
                r.append("F2 candidate idiom '%s' has no grounding in the source" % " ".join(T.pat[iid]))
    s_frames = {f for f, _, _ in S.frames}
    s_objs = set(S.tokset)
    for fi, s, e in C.frames:
        if fi in s_frames: continue
        toks = C.d.toks; j = e; seg = []
        while j < len(toks) and toks[j] != SB: seg.append(toks[j]); j += 1
        added = sorted({t for t in seg if (t == "zztarget" or t in T.living or t in T.reach or (len(t) > 3 and t.endswith("s") and t[:-1] in T.reach) or t in T.data_harm) and (t not in s_objs or t == "zztarget")})
        if added: r.append("F3 frame '%s' unwraps to a new order: %s" % (" ".join(T.frames[fi]), ", ".join(added)))
        else: notes.append("F3 frame '%s' unwraps to nothing new" % " ".join(T.frames[fi]))
    s_fobjs = {h for _, h in S.fig_events} | {h for _, h in S.lit_events}
    new = sorted({"%s->%s" % (v, h) for v, h in C.fig_events if h not in s_fobjs})
    if new: r.append("F4 intended data action on reachable or living target: %s" % ", ".join(new))
    if S.neg_fig != C.neg_fig: r.append("F5 polarity of figurative reading differs: source %d, candidate %d" % (S.neg_fig, C.neg_fig))
    return ("RED" if r else "GREEN"), r, notes

class DualSigma:
    def __init__(self, table=TABLE):
        self.T = Tables(table)
    def check(self, source, candidate, single=False):
        T = self.T
        S, C = Analysis(T, source), Analysis(T, candidate)
        lv, lr = literal_channel(T, S, C)
        fv, fr, notes = figurative_channel(T, S, C, single)
        return {"literal": {"verdict": lv, "reasons": lr}, "figurative": {"verdict": fv, "reasons": fr, "notes": notes},
                "final": "GREEN" if (lv == "GREEN" and fv == "GREEN") else "RED",
                "idioms_source": [" ".join(T.pat[m[2]]) for m in S.idioms], "idioms_candidate": [" ".join(T.pat[m[2]]) for m in C.idioms]}

def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="dual_sigma", description="Dual Sigma checker: GREEN only if literal AND figurative readings are GREEN.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check one pair"); c.add_argument("--source", required=True); c.add_argument("--candidate", required=True)
    c.add_argument("--single", action="store_true", help="judge the candidate alone (idiom ledger off)")
    b = sub.add_parser("batch", help="jsonl with source/candidate fields -> jsonl decisions"); b.add_argument("inp"); b.add_argument("out")
    t = sub.add_parser("tsv", help="TSV id<TAB>source<TAB>candidate -> TSV id, literal, figurative, final, literal reasons, figurative reasons, notes (parity format)"); t.add_argument("inp"); t.add_argument("out")
    sub.add_parser("info", help="table hash")
    a = ap.parse_args(argv)
    ds = DualSigma()
    if a.cmd == "info": print(json.dumps({"table_sha256": ds.T.sha256, "idioms": len(ds.T.pat)})); return
    if a.cmd == "check": print(json.dumps(ds.check(a.source, a.candidate, a.single), indent=2)); return
    if a.cmd == "batch":
        with open(a.inp) as f, open(a.out, "w") as g:
            for line in f:
                if not line.strip(): continue
                it = json.loads(line); res = ds.check(it["source"], it["candidate"])
                g.write(json.dumps({"id": it.get("id"), **res}, sort_keys=True) + "\n")
        return
    if a.cmd == "tsv":
        with open(a.inp) as f, open(a.out, "w") as g:
            for line in f:
                line = line.rstrip("\n")
                if not line: continue
                iid, s, cnd = line.split("\t")
                res = ds.check(s, cnd)
                g.write("\t".join([iid, res["literal"]["verdict"], res["figurative"]["verdict"], res["final"],
                                   " ## ".join(res["literal"]["reasons"]), " ## ".join(res["figurative"]["reasons"]),
                                   " ## ".join(res["figurative"]["notes"])]) + "\n")

if __name__ == "__main__":
    main(sys.argv[1:])
