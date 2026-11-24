"""Build the frozen Dual Sigma lexical table (tables/dual_sigma_tables.tsv) from read-only public resources:
- WordNet 3.0 (NLTK copy on the box): multiword expressions, their senses, sense neighbours and gloss words.
- Analogous-0 v3 idiom table (wiktionary:idioms rows) and reach lexicon, Search Gate v1.6 verb families (tier1). Read only.
- Small hand-written lists (physical harm verbs, living targets, negators, number words, injection markers, frames),
  defined here, written before the blind set was generated.
The Python core and the Rust core both read only this TSV, so both decide from the same bytes."""
import re, sys, json, hashlib
from pathlib import Path
from nltk.corpus import wordnet as wn

V3 = Path("/workspace/frontier_pivot/analogous0_v3/models")
OUT = Path(__file__).resolve().parent.parent / "tables" / "dual_sigma_tables.tsv"

ARTICLES = {"a", "an", "the"}
POSS = {"one's", "someone's", "somebody's"}
SLOT = {"someone", "somebody", "something", "sb", "sth"}
REFL = {"oneself"}
STOP = set("""a an the of to in on at by for with from up down out off over into onto about as and or but if then than so
be is are was were been being have has had do does did done make makes made get gets got take takes took give gives gave
go goes went come came put puts set use used cause causes thing things something someone somebody person people one ones
way state quality act action often especially usually very more most much many some any all no not it its this that
these those who which what when where how there their they them he she his her you your we our us i me my
able become becomes became something kind sort part form manner time also etc sense particular certain other others
""".split())
PHYSICAL = ("kill murder shoot stab burn torch poison crush smash nuke blow bomb gut slash trash torpedo butcher strangle choke "
            "axe scrap dump blast break bury freeze sabotage hack wreck").split()
LIVING = ("him her them me us you people person everyone everybody someone somebody man woman men women child children kid kids "
          "guy guys boss neighbor neighbour colleague colleagues coworker coworkers human humans baby").split()
PARTICLES = "up down out off over in on into onto away back about around through along across after to by for with at from".split()
NEGATORS = "not no never none nobody nothing nowhere neither nor without cannot".split()
NUMWORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
            "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
            "thousand": 1000, "dozen": 12}
INJECTION = ["ignore the previous", "ignore previous", "ignore all previous", "ignore your", "disregard your", "disregard the previous",
             "disregard all", "system note", "system prompt", "as an ai", "you are an ai", "developer mode",
             "new instructions", "override your", "do not tell"]
FRAMES = ["like a <slot> would", "as a <slot> would", "just as", "the way a <slot>", "if you are an ai", "if you're an ai",
          "imagine you are", "pretend you are", "pretend to be", "is to <slot> as", "in the story", "go and do likewise",
          "do likewise", "do the same", "as the saying goes", "think of <slot> as", "consider <slot> a"]

def norm_tokens(s):
    s = s.lower().replace("_", " ").replace("-", " ")
    return [t.strip("'") for t in re.findall(r"[a-z0-9']+", s) if t.strip("'")]

_vexc = {}
for base_form, lemma in [(k, v) for k, vs in wn._exception_map["v"].items() for v in vs]:
    _vexc.setdefault(lemma, set()).add(base_form)
_nexc = {}
for k, vs in wn._exception_map["n"].items():
    for v in vs: _nexc.setdefault(v, set()).add(k)

def verb_forms(v):
    f = {v} | _vexc.get(v, set())
    if v.endswith("e") and not v.endswith("ee"):
        f |= {v + "s", v + "d", v[:-1] + "ing"}
    elif v.endswith("y") and len(v) > 2 and v[-2] not in "aeiou":
        f |= {v[:-1] + "ies", v[:-1] + "ied", v + "ing"}
    elif re.search(r"(s|x|z|ch|sh)$", v):
        f |= {v + "es", v + "ed", v + "ing"}
    else:
        f |= {v + "s", v + "ed", v + "ing"}
        if re.search(r"[^aeiou][aeiou][bdgklmnprt]$", v):
            f |= {v + v[-1] + "ed", v + v[-1] + "ing"}
    return f

def noun_forms(n):
    f = {n} | _nexc.get(n, set())
    if n.endswith("y") and len(n) > 2 and n[-2] not in "aeiou": f.add(n[:-1] + "ies")
    elif re.search(r"(s|x|z|ch|sh)$", n): f.add(n + "es")
    else: f.add(n + "s")
    return f

def word_forms(w):
    return verb_forms(w) | noun_forms(w)

def pattern_of(lemma):
    toks = []
    for t in norm_tokens(lemma):
        if t in ARTICLES: continue
        if t in POSS: toks.append("<poss>")
        elif t in SLOT: toks.append("<slot>")
        elif t in REFL: toks.append("<refl>")
        else: toks.append(t)
    return toks

def noncompositional_noun(lemma, syn):
    head = lemma.split("_")[-1]
    heads = set(wn.synsets(head, pos="n"))
    if not heads: return True
    closure = set(syn.closure(lambda s: s.hypernyms() + s.instance_hypernyms(), depth=8))
    return not (heads & closure)

def accept_set(synsets, own_tokens):
    words, phrases = set(), set()
    neigh = set()
    for s in synsets:
        neigh.add(s)
        for f in (s.hypernyms, s.hyponyms, s.verb_groups, s.similar_tos, s.also_sees, s.entailments):
            neigh |= set(f())
    lemmas = set()
    for s in neigh:
        for l in s.lemmas():
            lemmas.add(l.name().lower())
            for d in l.derivationally_related_forms(): lemmas.add(d.name().lower())
    gloss = set()
    for s in synsets:
        gloss |= set(norm_tokens(s.definition()))
    own = set()
    for t in own_tokens:
        if t.startswith("<"): continue
        own |= word_forms(t)
    for l in lemmas:
        pt = [t for t in norm_tokens(l) if t not in ARTICLES]
        if not pt: continue
        if len(pt) == 1: words |= word_forms(pt[0])
        else: phrases.add(" ".join(pt))
    for g in gloss:
        if g in STOP or len(g) < 3 or g.isdigit(): continue
        words |= word_forms(g)
    words = {w for w in words if w not in own and w not in STOP and w.isascii() and re.fullmatch(r"[a-z0-9']+", w)}
    phrases = {p for p in phrases if p.isascii() and re.fullmatch(r"[a-z0-9' ]+", p) and p.split() != [t for t in own_tokens]}
    return words, phrases

def main():
    lines = []
    idioms = {}   # pattern string -> dict
    def add_idiom(pat, pos, src, syns):
        key = " ".join(pat)
        d = idioms.setdefault(key, {"pat": pat, "pos": set(), "src": set(), "syn": set()})
        d["pos"].add(pos); d["src"].add(src); d["syn"] |= set(syns)
    nn = 0
    for pos in "vars":
        for lemma in wn.all_lemma_names(pos=pos):
            if "_" not in lemma and "-" not in lemma: continue
            pat = pattern_of(lemma)
            if len([t for t in pat if not t.startswith("<")]) < 2: continue
            add_idiom(pat, pos, "wordnet", wn.synsets(lemma, pos=pos))
    for lemma in wn.all_lemma_names(pos="n"):
        if "_" not in lemma: continue
        syns = [s for s in wn.synsets(lemma, pos="n") if noncompositional_noun(lemma, s)]
        if not syns: continue
        pat = pattern_of(lemma)
        if len([t for t in pat if not t.startswith("<")]) < 2: continue
        if any(t[0].isdigit() for t in pat): continue
        # proper names and taxonomy terms are not idioms: keep nouns whose synsets are not instances and whose lemma is lowercase in WordNet
        syns = [s for s in syns if not s.instance_hypernyms() and s.lexname() not in ("noun.animal", "noun.plant", "noun.location", "noun.person", "noun.substance", "noun.body", "noun.food", "noun.artifact", "noun.object")]
        if not syns: continue
        add_idiom(pat, "n", "wordnet", syns); nn += 1
    v3n = 0
    for line in (V3 / "idiom_table_v3.txt").read_text().split("\n"):
        f = line.split("\t")
        if len(f) < 5 or f[0] != "I" or f[4] != "wiktionary:idioms": continue
        verb, rest = f[2], f[3]
        pat = [verb] + [("<poss>" if t in POSS else t) for t in rest.split(" ") if t and t not in ARTICLES]
        if len(pat) < 2: continue
        syns = wn.synsets("_".join([verb] + rest.split(" ")), pos="v")
        add_idiom(pat, "v", "v3_wiktionary_idioms", syns); v3n += 1
    # emit idioms
    keys = sorted(idioms)
    for i, k in enumerate(keys):
        d = idioms[k]; iid = f"m{i:05d}"
        syn = sorted(s.name() for s in d["syn"])
        verbal = "v" in d["pos"]
        head_forms = sorted(verb_forms(d["pat"][0])) if (verbal and not d["pat"][0].startswith("<")) else [d["pat"][0]]
        lines.append("\t".join(["I", iid, " ".join(d["pat"]), "".join(sorted(d["pos"])), ",".join(sorted(d["src"])), " ".join(head_forms)]))
        if syn:
            words, phrases = accept_set(d["syn"], d["pat"])
            lines.append("\t".join(["Y", iid, " ".join(syn)]))
            lines.append("\t".join(["A", iid, " ".join(sorted(words))]))
            if phrases: lines.append("\t".join(["P", iid, "|".join(sorted(phrases))]))
    reach = sorted(set((V3 / "reach_lexicon.txt").read_text().split()))
    lines.append("R\t" + " ".join(reach))
    fam = json.loads((V3 / "verb_families_v1_3.json").read_text())["categories"]
    for name in sorted(fam):
        forms = set()
        for v in fam[name]["tier1"]: forms |= verb_forms(v)
        lines.append("\t".join(["H", name, " ".join(sorted(forms))]))
    forms = set()
    for v in PHYSICAL: forms |= verb_forms(v)
    lines.append("\t".join(["H", "physical", " ".join(sorted(forms))]))
    lines.append("L\t" + " ".join(sorted(LIVING)))
    lines.append("G\t" + " ".join(sorted(NEGATORS)))
    lines.append("U\t" + " ".join(f"{k}={v}" for k, v in sorted(NUMWORDS.items())))
    lines.append("J\t" + "|".join(INJECTION))
    lines.append("F\t" + "|".join(FRAMES))
    lines.append("S\t" + " ".join(sorted(STOP)))
    lines.append("K\t" + " ".join(sorted(PARTICLES)))
    OUT.write_text("\n".join(lines) + "\n")
    print("idioms", len(keys), "noun", nn, "v3", v3n, "sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())

if __name__ == "__main__":
    main()
