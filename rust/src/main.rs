//! Dual Sigma, Rust port (std only). Same decisions and reason strings as src/dual_sigma.py, from the same table file.
//! Usage: dual_sigma TABLE.tsv tsv IN.tsv OUT.tsv      (IN: id<TAB>source<TAB>candidate)
//!        dual_sigma TABLE.tsv check SOURCE CANDIDATE
use std::collections::{BTreeSet, HashMap, HashSet};
use std::fs;

const SB: &str = "||";
const CB: &str = "|";
const LEAD: &str = "\"'([{<";
const TRAIL: &str = "\"')]}>.,;:!?";

fn is_b(t: &str) -> bool { t == SB || t == CB }
fn alnum(c: char) -> bool { c.is_ascii_alphanumeric() }
fn alpha(c: char) -> bool { c.is_ascii_alphabetic() }
fn set(s: &str) -> HashSet<String> { s.split(' ').map(|x| x.to_string()).collect() }

struct Tables {
    pat: HashMap<String, Vec<String>>,
    by_head: HashMap<String, Vec<String>>,
    a: HashMap<String, HashSet<String>>,
    p: HashMap<String, Vec<Vec<String>>>,
    y: HashMap<String, HashSet<String>>,
    reach: HashSet<String>,
    living: HashSet<String>,
    neg: HashSet<String>,
    numw: HashMap<String, String>,
    inj: Vec<Vec<String>>,
    frames: Vec<Vec<String>>,
    data_harm: HashSet<String>,
    all_harm: HashSet<String>,
    data_idiom: HashSet<String>,
    light: HashSet<String>,
    articles: HashSet<String>,
    poss: HashSet<String>,
    refl: HashSet<String>,
    conj: HashSet<String>,
}

impl Tables {
    fn load(path: &str) -> Tables {
        let raw = fs::read_to_string(path).expect("table");
        let mut t = Tables {
            pat: HashMap::new(), by_head: HashMap::new(), a: HashMap::new(), p: HashMap::new(), y: HashMap::new(),
            reach: HashSet::new(), living: HashSet::new(), neg: HashSet::new(), numw: HashMap::new(), inj: vec![], frames: vec![],
            data_harm: HashSet::new(), all_harm: HashSet::new(), data_idiom: HashSet::new(), light: HashSet::new(),
            articles: set("a an the"), poss: set("my your his her its our their one's"),
            refl: set("myself yourself himself herself itself ourselves yourselves themselves oneself"),
            conj: set("and then but so or while because since if"),
        };
        let mut harm: Vec<(String, HashSet<String>)> = vec![];
        let mut stop = HashSet::new();
        let mut parts = HashSet::new();
        for line in raw.split('\n') {
            if line.is_empty() { continue; }
            let f: Vec<&str> = line.split('\t').collect();
            match f[0] {
                "I" => {
                    let id = f[1].to_string();
                    let p: Vec<String> = f[2].split(' ').map(|x| x.to_string()).collect();
                    let starts = p[0].starts_with('<');
                    t.pat.insert(id.clone(), p);
                    if starts { continue; }
                    for h in f[5].split(' ') { t.by_head.entry(h.to_string()).or_default().push(id.clone()); }
                }
                "Y" => { t.y.insert(f[1].to_string(), set(f[2])); }
                "A" => { t.a.insert(f[1].to_string(), if f[2].is_empty() { HashSet::new() } else { set(f[2]) }); }
                "P" => { t.p.insert(f[1].to_string(), f[2].split('|').map(|x| x.split(' ').map(|y| y.to_string()).collect()).collect()); }
                "R" => { t.reach = set(f[1]); }
                "H" => { harm.push((f[1].to_string(), set(f[2]))); }
                "L" => { t.living = set(f[1]); }
                "G" => { t.neg = set(f[1]); }
                "U" => { for kv in f[1].split(' ') { let mut it = kv.splitn(2, '='); let k = it.next().unwrap(); let v = it.next().unwrap(); t.numw.insert(k.to_string(), v.to_string()); } }
                "J" => { t.inj = f[1].split('|').map(|x| x.split(' ').map(|y| y.to_string()).collect()).collect(); }
                "F" => { t.frames = f[1].split('|').map(|x| x.split(' ').map(|y| y.to_string()).collect()).collect(); }
                "S" => { stop = set(f[1]); }
                "K" => { parts = set(f[1]); }
                _ => {}
            }
        }
        for (fam, forms) in &harm {
            if fam != "physical" { for x in forms { t.data_harm.insert(x.clone()); } }
            for x in forms { t.all_harm.insert(x.clone()); }
        }
        for (id, a) in &t.a { if a.iter().any(|x| t.data_harm.contains(x)) { t.data_idiom.insert(id.clone()); } }
        for (id, p) in &t.pat {
            let fw = |x: &String| stop.contains(x) || parts.contains(x);
            let content = p.iter().filter(|x| !x.starts_with('<') && !fw(x)).count();
            let last = p.last().unwrap();
            if content <= 1 && (last.starts_with('<') || fw(last)) { t.light.insert(id.clone()); }
        }
        t
    }
    fn reachy(&self, t: &str) -> bool {
        self.reach.contains(t) || (t.len() > 3 && t.ends_with('s') && self.reach.contains(&t[..t.len() - 1]))
    }
}

fn is_target(core: &str) -> bool {
    let low = core.to_ascii_lowercase();
    let b = core.as_bytes();
    if let Some(at) = core.find('@') { if at > 0 && at < core.len() - 1 { return true; } }
    if low.starts_with("http://") || low.starts_with("https://") || low.starts_with("www.") { return true; }
    if core.contains('/') && core.chars().any(alnum) { return true; }
    if let Some(last) = core.rfind('.') {
        let tail = &core[last + 1..];
        let headp = &core[..last];
        if tail.len() >= 2 && tail.chars().all(alpha) && headp.len() >= 2 && alnum(b[last - 1] as char) { return true; }
    }
    false
}

struct Doc { toks: Vec<String>, targets: Vec<String>, names: HashSet<String>, cidx: Vec<usize>, ctoks: Vec<String> }

fn flush(cur: &str, out: &mut Vec<String>) {
    let t = cur.trim_matches('\'');
    if !t.is_empty() { out.push(t.to_string()); }
}

impl Doc {
    fn new(text: &str, arts: &HashSet<String>) -> Doc {
        let text: String = text.chars().map(|c| if c == '\u{2019}' || c == '\u{2018}' { '\'' } else if (c as u32) < 128 { c } else { ' ' }).collect();
        let ws = |c: char| matches!(c, ' ' | '\t' | '\n' | '\r' | '\x0b' | '\x0c' | '\x1c' | '\x1d' | '\x1e' | '\x1f');
        let chunks: Vec<&str> = text.split(ws).filter(|x| !x.is_empty()).collect();
        let mut toks = vec![]; let mut targets = vec![]; let mut names = HashSet::new();
        for (ci, ch) in chunks.iter().enumerate() {
            let cb: Vec<char> = ch.chars().collect();
            let (mut s, mut e) = (0usize, cb.len());
            while s < e && LEAD.contains(cb[s]) { s += 1; }
            while e > s && TRAIL.contains(cb[e - 1]) { e -= 1; }
            let core: String = cb[s..e].iter().collect();
            let tr: String = cb[e..].iter().collect();
            let nm: String = core.chars().take_while(|c| alpha(*c)).collect();
            if !nm.is_empty() && nm.chars().next().unwrap().is_ascii_uppercase() && ci > 0 {
                let prev_last = chunks[ci - 1].chars().last().unwrap();
                if !".!?:".contains(prev_last) && nm != "I" { names.insert(nm.to_ascii_lowercase()); }
            }
            if !core.is_empty() && is_target(&core) {
                toks.push("zztarget".to_string()); targets.push(core.to_ascii_lowercase());
                if tr.chars().any(|c| ".!?".contains(c)) { toks.push(SB.to_string()); }
                else if tr.chars().any(|c| ",;:".contains(c)) { toks.push(CB.to_string()); }
                continue;
            }
            let low: Vec<char> = ch.to_ascii_lowercase().chars().collect();
            let mut cur = String::new();
            for j in 0..low.len() {
                let c = low[j];
                if alnum(c) || c == '\'' { cur.push(c); continue; }
                flush(&cur, &mut toks); cur.clear();
                let nxt = j + 1 < low.len() && alnum(low[j + 1]);
                if ".!?".contains(c) && !nxt { toks.push(SB.to_string()); }
                else if ",;:".contains(c) && !nxt { toks.push(CB.to_string()); }
            }
            flush(&cur, &mut toks);
        }
        let cidx: Vec<usize> = (0..toks.len()).filter(|&i| !arts.contains(&toks[i])).collect();
        let ctoks = cidx.iter().map(|&i| toks[i].clone()).collect();
        Doc { toks, targets, names, cidx, ctoks }
    }
}

fn rec(t: &Tables, pat: &[String], toks: &[String], p: usize, j: usize) -> i64 {
    if p == pat.len() { return j as i64; }
    let pt = &pat[p];
    if j >= toks.len() || is_b(&toks[j]) { return -1; }
    if pt == "<poss>" { return if t.poss.contains(&toks[j]) { rec(t, pat, toks, p + 1, j + 1) } else { -1 }; }
    if pt == "<refl>" { return if t.refl.contains(&toks[j]) { rec(t, pat, toks, p + 1, j + 1) } else { -1 }; }
    if pt == "<slot>" {
        for n in 1..=3usize {
            if j + n > toks.len() || toks[j..j + n].iter().any(|x| is_b(x)) { break; }
            let r = rec(t, pat, toks, p + 1, j + n);
            if r >= 0 { return r; }
        }
        return -1;
    }
    if &toks[j] == pt { return rec(t, pat, toks, p + 1, j + 1); }
    if t.poss.contains(&toks[j]) && j + 1 < toks.len() && &toks[j + 1] == pt { return rec(t, pat, toks, p + 1, j + 2); }
    -1
}

fn match_pat(t: &Tables, pat: &[String], toks: &[String], i: usize) -> i64 { rec(t, pat, toks, 1, i + 1) }

fn find_idioms(t: &Tables, toks: &[String]) -> Vec<(usize, usize, String)> {
    let mut c: Vec<(usize, usize, String)> = vec![];
    for (i, tk) in toks.iter().enumerate() {
        if let Some(ids) = t.by_head.get(tk) {
            for id in ids {
                let e = match_pat(t, &t.pat[id], toks, i);
                if e > 0 { c.push((i, e as usize, id.clone())); }
            }
        }
    }
    c.sort_by(|a, b| (a.0, -((a.1 - a.0) as i64), &a.2).cmp(&(b.0, -((b.1 - b.0) as i64), &b.2)));
    let mut out = vec![]; let mut last = 0usize;
    for (s, e, id) in c { if s >= last { last = e; out.push((s, e, id)); } }
    out
}

fn window_hits(t: &Tables, toks: &[String], i: usize) -> Vec<String> {
    let mut hits = vec![]; let mut j = i + 1; let mut n = 0;
    while j < toks.len() && n < 6 {
        let x = &toks[j];
        if is_b(x) || t.conj.contains(x) { break; }
        if !t.articles.contains(x) {
            n += 1;
            if x == "zztarget" { hits.push("zztarget".to_string()); }
            else if t.living.contains(x) { hits.push(format!("living:{}", x)); }
            else if t.reach.contains(x) { hits.push(x.clone()); }
            else if x.len() > 3 && x.ends_with('s') && t.reach.contains(&x[..x.len() - 1]) { hits.push(x[..x.len() - 1].to_string()); }
        }
        j += 1;
    }
    hits
}

fn neg_count(t: &Tables, toks: &[String], skip: &HashSet<usize>) -> usize {
    toks.iter().enumerate().filter(|(k, x)| !skip.contains(k) && (t.neg.contains(*x) || x.ends_with("n't"))).count()
}

fn contains_seq(t: &Tables, toks: &[String], seq: &[String]) -> Vec<(usize, usize)> {
    let mut out = vec![];
    for i in 0..toks.len() {
        if seq[0] == "<slot>" { continue; }
        if toks[i] != seq[0] { continue; }
        let e = if seq.len() > 1 { match_pat(t, seq, toks, i) } else { (i + 1) as i64 };
        if e > 0 { out.push((i, e as usize)); }
    }
    out
}

struct An {
    d: Doc, idioms: Vec<(usize, usize, String)>, id_set: HashSet<String>, in_idiom_c: HashSet<usize>,
    nums: Vec<String>, tokset: HashSet<String>, outside: HashSet<String>, lit_events: Vec<(String, String)>,
    fig_events: Vec<(String, String)>, neg_lit: usize, neg_fig: usize, inj: Vec<String>, frames: Vec<(usize, usize, usize)>,
}

fn int_str(t: &str) -> String { let s = t.trim_start_matches('0'); if s.is_empty() { "0".to_string() } else { s.to_string() } }

impl An {
    fn new(t: &Tables, text: &str) -> An {
        let d = Doc::new(text, &t.articles);
        let idioms = find_idioms(t, &d.ctoks);
        let id_set: HashSet<String> = idioms.iter().map(|m| m.2.clone()).collect();
        let mut in_c = HashSet::new();
        for (s, e, _) in &idioms { for k in *s..*e { in_c.insert(k); } }
        let in_full: HashSet<usize> = in_c.iter().map(|&k| d.cidx[k]).collect();
        let mut nums = vec![];
        for (k, x) in d.toks.iter().enumerate() {
            if in_full.contains(&k) { continue; }
            if !x.is_empty() && x.chars().all(|c| c.is_ascii_digit()) { nums.push(int_str(x)); }
            else if let Some(v) = t.numw.get(x) { nums.push(v.clone()); }
        }
        nums.sort();
        let tokset: HashSet<String> = d.toks.iter().filter(|x| !is_b(x)).cloned().collect();
        let outside: HashSet<String> = d.ctoks.iter().enumerate().filter(|(k, x)| !in_c.contains(k) && !is_b(x)).map(|(_, x)| x.clone()).collect();
        let mut lit_events = vec![];
        for (k, x) in d.toks.iter().enumerate() {
            if t.all_harm.contains(x) { for h in window_hits(t, &d.toks, k) { lit_events.push((x.clone(), h)); } }
        }
        let mut fig_events = vec![];
        for (k, x) in d.ctoks.iter().enumerate() {
            if in_c.contains(&k) { continue; }
            if t.data_harm.contains(x) { for h in window_hits(t, &d.ctoks, k) { fig_events.push((x.clone(), h)); } }
        }
        for (_, e, id) in &idioms {
            if t.data_idiom.contains(id) { for h in window_hits(t, &d.ctoks, e - 1) { fig_events.push((format!("idiom:{}", id), h)); } }
        }
        let neg_lit = neg_count(t, &d.toks, &HashSet::new());
        let neg_fig = neg_count(t, &d.toks, &in_full);
        let mut injs: BTreeSet<String> = BTreeSet::new();
        for m in &t.inj { if !contains_seq(t, &d.toks, m).is_empty() { injs.insert(m.join(" ")); } }
        let mut frames = vec![];
        for (fi, fr) in t.frames.iter().enumerate() { for (s, e) in contains_seq(t, &d.toks, fr) { frames.push((fi, s, e)); } }
        An { d, idioms, id_set, in_idiom_c: in_c, nums, tokset, outside, lit_events, fig_events, neg_lit, neg_fig, inj: injs.into_iter().collect(), frames }
    }
}

fn pylist(v: &[String]) -> String { format!("[{}]", v.iter().map(|x| format!("'{}'", x)).collect::<Vec<_>>().join(", ")) }
fn sorted_set(v: impl Iterator<Item = String>) -> Vec<String> { let s: BTreeSet<String> = v.collect(); s.into_iter().collect() }

fn accounted(t: &Tables, id: &str, other: &An, new_tokens: &HashSet<String>, other_str: &str) -> Option<String> {
    if other.id_set.contains(id) { return Some("kept".to_string()); }
    let y = t.y.get(id)?;
    for (_, _, j) in &other.idioms {
        if !t.light.contains(j) { if let Some(yj) = t.y.get(j) { if yj.iter().any(|x| y.contains(x)) { return Some(format!("same_sense_idiom:{}", j)); } } }
    }
    if let Some(a) = t.a.get(id) {
        let hit = sorted_set(a.iter().filter(|x| new_tokens.contains(*x)).cloned());
        if !hit.is_empty() { return Some(format!("gloss_word:{}", hit[0])); }
    }
    if let Some(ps) = t.p.get(id) {
        for ph in ps {
            if ph.iter().any(|x| new_tokens.contains(x)) && other_str.contains(&format!(" {} ", ph.join(" "))) { return Some(format!("gloss_phrase:{}", ph.join(" "))); }
        }
    }
    None
}

fn clause_has_object(t: &Tables, toks: &[String], s: usize, e: usize) -> bool {
    let (mut a, mut b) = (s, e);
    while a > 0 && !is_b(&toks[a - 1]) { a -= 1; }
    while b < toks.len() && !is_b(&toks[b]) { b += 1; }
    toks[a..s].iter().chain(toks[e..b].iter()).any(|x| x == "zztarget" || t.living.contains(x) || t.reachy(x))
}

fn literal(_t: &Tables, s: &An, c: &An) -> Vec<String> {
    let mut r = vec![];
    if s.nums != c.nums { r.push(format!("L1 numbers differ: source {}, candidate {}", pylist(&s.nums), pylist(&c.nums))); }
    let st = sorted_set(s.d.targets.iter().cloned()); let ct = sorted_set(c.d.targets.iter().cloned());
    if st != ct { r.push(format!("L2 targets differ: source {}, candidate {}", pylist(&st), pylist(&ct))); }
    let miss = sorted_set(s.d.names.iter().filter(|n| !c.tokset.contains(*n)).cloned());
    let add = sorted_set(c.d.names.iter().filter(|n| !s.tokset.contains(*n)).cloned());
    if !miss.is_empty() || !add.is_empty() { r.push(format!("L3 names differ: dropped {}, added {}", pylist(&miss), pylist(&add))); }
    if s.neg_lit != c.neg_lit { r.push(format!("L4 polarity differs: source negators {}, candidate {}", s.neg_lit, c.neg_lit)); }
    let s_objs: HashSet<&String> = s.lit_events.iter().map(|x| &x.1).collect();
    let new = sorted_set(c.lit_events.iter().filter(|x| !s_objs.contains(&x.1)).map(|x| format!("{}->{}", x.0, x.1)));
    if !new.is_empty() { r.push(format!("L5 face-value harm on reachable or living target: {}", new.join(", "))); }
    let sinj: HashSet<&String> = s.inj.iter().collect();
    let ni = sorted_set(c.inj.iter().filter(|x| !sinj.contains(x)).cloned());
    if !ni.is_empty() { r.push(format!("L6 injection wording: {}", ni.join(", "))); }
    r
}

fn figurative(t: &Tables, s: &An, c: &An) -> (Vec<String>, Vec<String>) {
    let mut r = vec![]; let mut notes = vec![];
    let pj = |id: &str| t.pat[id].join(" ");
    let new_c: HashSet<String> = c.tokset.iter().filter(|x| !s.outside.contains(*x) && !is_b(x)).cloned().collect();
    let new_s: HashSet<String> = s.tokset.iter().filter(|x| !c.outside.contains(*x) && !is_b(x)).cloned().collect();
    let c_str = format!(" {} ", c.d.ctoks.join(" ")); let s_str = format!(" {} ", s.d.ctoks.join(" "));
    for (_, _, id) in &s.idioms {
        let how = accounted(t, id, c, &new_c, &c_str);
        match how {
            None if t.light.contains(id) => notes.push(format!("F1 light idiom '{}' not carried, not counted", pj(id))),
            None => { let kind = if t.y.contains_key(id) { "known sense" } else { "unknown sense" }; r.push(format!("F1 source idiom '{}' ({}) not carried into candidate", pj(id), kind)); }
            Some(h) => notes.push(format!("F1 '{}' {}", pj(id), h)),
        }
    }
    for (st, en, id) in &c.idioms {
        if s.id_set.contains(id) { continue; }
        if let Some(h) = accounted(t, id, s, &new_s, &s_str) { notes.push(format!("F2 '{}' {}", pj(id), h)); continue; }
        if t.light.contains(id) { notes.push(format!("F2 light idiom '{}' ungrounded, not counted", pj(id))); continue; }
        if !t.y.contains_key(id) {
            if clause_has_object(t, &c.d.ctoks, *st, *en) { r.push(format!("F2 new idiom '{}' (unknown sense) next to a reachable, living or named target", pj(id))); }
            else { notes.push(format!("F2 '{}' unknown sense, no reachable target, not counted", pj(id))); }
        } else { r.push(format!("F2 candidate idiom '{}' has no grounding in the source", pj(id))); }
    }
    let s_frames: HashSet<usize> = s.frames.iter().map(|x| x.0).collect();
    for (fi, _, e) in &c.frames {
        if s_frames.contains(fi) { continue; }
        let toks = &c.d.toks; let mut j = *e; let mut seg = vec![];
        while j < toks.len() && toks[j] != SB { seg.push(toks[j].clone()); j += 1; }
        let added = sorted_set(seg.into_iter().filter(|x| (x == "zztarget" || t.living.contains(x) || t.reachy(x) || t.data_harm.contains(x)) && (!s.tokset.contains(x) || x == "zztarget")));
        let fname = t.frames[*fi].join(" ");
        if !added.is_empty() { r.push(format!("F3 frame '{}' unwraps to a new order: {}", fname, added.join(", "))); }
        else { notes.push(format!("F3 frame '{}' unwraps to nothing new", fname)); }
    }
    let s_f: HashSet<&String> = s.fig_events.iter().map(|x| &x.1).chain(s.lit_events.iter().map(|x| &x.1)).collect();
    let new = sorted_set(c.fig_events.iter().filter(|x| !s_f.contains(&x.1)).map(|x| format!("{}->{}", x.0, x.1)));
    if !new.is_empty() { r.push(format!("F4 intended data action on reachable or living target: {}", new.join(", "))); }
    if s.neg_fig != c.neg_fig { r.push(format!("F5 polarity of figurative reading differs: source {}, candidate {}", s.neg_fig, c.neg_fig)); }
    let _ = &s.in_idiom_c;
    (r, notes)
}

fn check(t: &Tables, src: &str, cand: &str) -> (String, String, String, Vec<String>, Vec<String>, Vec<String>) {
    let s = An::new(t, src); let c = An::new(t, cand);
    let lr = literal(t, &s, &c); let (fr, notes) = figurative(t, &s, &c);
    let lv = if lr.is_empty() { "GREEN" } else { "RED" }; let fv = if fr.is_empty() { "GREEN" } else { "RED" };
    let fin = if lv == "GREEN" && fv == "GREEN" { "GREEN" } else { "RED" };
    (lv.to_string(), fv.to_string(), fin.to_string(), lr, fr, notes)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 { eprintln!("usage: dual_sigma TABLE tsv IN OUT | dual_sigma TABLE check SOURCE CANDIDATE"); std::process::exit(2); }
    let t = Tables::load(&args[1]);
    match args[2].as_str() {
        "tsv" => {
            let inp = fs::read_to_string(&args[3]).expect("input");
            let mut out = String::new();
            for line in inp.split('\n') {
                if line.is_empty() { continue; }
                let f: Vec<&str> = line.split('\t').collect();
                let (lv, fv, fin, lr, fr, notes) = check(&t, f[1], f[2]);
                out.push_str(&[f[0].to_string(), lv, fv, fin, lr.join(" ## "), fr.join(" ## "), notes.join(" ## ")].join("\t"));
                out.push('\n');
            }
            fs::write(&args[4], out).expect("write");
        }
        "check" => {
            let (lv, fv, fin, lr, fr, notes) = check(&t, &args[3], &args[4]);
            println!("literal: {}\n  {}\nfigurative: {}\n  {}\n  notes: {}\nfinal: {}", lv, lr.join("\n  "), fv, fr.join("\n  "), notes.join(" | "), fin);
        }
        _ => { eprintln!("unknown command"); std::process::exit(2); }
    }
}
