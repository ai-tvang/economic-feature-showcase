"""Block 2a: group bank texts into payee groups using bank_text ONLY. vendor_true is used solely for evaluation.
Two methods: rule-based normalisation (regex) and AI (one batch to `claude -p --model sonnet`).
Run: python grouping.py [--refresh]   -> eval/ai_mapping.json, eval/grouping_eval.json"""
import json, os, re, shutil, subprocess, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(HERE, "eval")
TRANSFER = re.compile(r"^(OVERF\. FRA|OVERF\. TIL|BETALING|FI )")  # counterparty transfers: not a vendor pattern
RENT = re.compile(r"\b(HUSLEJE|LEJE|UDLEJER)\b")
NOISE = {"A/S", "APS", "DK", "DANMARK", "DENMARK", "BS", "ERHVERV", "FAKT", "LTD", "A.M.B.A.", "PTY", "INC", "THE", "AND"}


def mask(text): return re.sub(r"\d+", "#", text.upper())


def rule_group(masked):
    """Regex normalisation: strip digits, payment prefixes (NETS*, BS) and legal/noise words; key = first two tokens."""
    if TRANSFER.match(masked): return None
    if RENT.search(masked): return "RENT"
    t = re.sub(r"^[A-Z]+\*", lambda m: "" if m.group(0) in ("NETS*", "PBS*") else m.group(0), masked)  # NETS*TDC -> TDC
    toks = [x for x in re.split(r"[^A-Z0-9Æ ØÅ/.]+|\s+", t.replace("*", " ")) if x and x != "#"]
    toks = [x.replace("#", "") for x in toks]
    toks = [x for x in toks if x and x not in NOISE and not re.fullmatch(r"E\d+|\d+", x)]
    if not toks or len("".join(toks)) < 3: return None
    return " ".join(toks[:2])


def ai_group(masked_texts, refresh=False, log=print):
    """One batch to claude -p. Cached in eval/ai_mapping.json. Returns (mapping or None, status)."""
    cache = os.path.join(EVAL, "ai_mapping.json")
    if os.path.exists(cache) and not refresh:
        m = json.load(open(cache, encoding="utf-8"))
        if set(masked_texts) <= set(m): return m, "cached"
    def call(texts):
        prompt = ("You group messy Danish bank transaction texts by payee. Digits are masked as #. "
                  "Return ONLY a JSON object mapping every input text exactly as given to a short canonical payee name "
                  "(upper case, e.g. \"TDC\"). Texts that are the same payee in different spellings, prefixes (NETS*, BS) or "
                  "abbreviations must get the same name. Payment-processor settlements and fees from the same company are "
                  "different groups (e.g. \"NETS FEES\" vs \"CARD SETTLEMENT\"). Rent or lease of premises -> \"RENT\". "
                  "Use null if you cannot tell. No prose, no code fences.\n\nTEXTS:\n" + json.dumps(texts, ensure_ascii=False))
        r = subprocess.run([shutil.which("claude") or "claude", "-p", "--model", "sonnet"], input=prompt, capture_output=True, text=True,
                           encoding="utf-8", timeout=600)
        if r.returncode != 0: raise RuntimeError(r.stderr[:300] or "non-zero exit")
        out = r.stdout.strip()
        out = re.sub(r"^```(?:json)?|```$", "", out, flags=re.M).strip()
        return json.loads(out[out.index("{"):out.rindex("}") + 1])
    try:
        probe = masked_texts[:10]
        pm = call(probe)
        if not all(t in pm for t in probe): raise RuntimeError("test of 10 texts: keys missing in answer")
        log(f"AI test with 10 texts OK ({len(pm)} keys)")
        m = call(masked_texts)
        miss = [t for t in masked_texts if t not in m]
        if miss: raise RuntimeError(f"{len(miss)} texts missing in answer")
        os.makedirs(EVAL, exist_ok=True)
        json.dump(m, open(cache, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        return m, "ok"
    except Exception as e:
        return None, f"FAILED ({type(e).__name__}: {e})"


def load():
    df = pd.read_csv(os.path.join(HERE, "data", "postings.csv"), keep_default_na=False)
    df["masked"] = df.bank_text.map(mask)
    return df


def truth(v): return "RENT" if v.startswith("Landlord") else v


def evaluate(df, col):
    """Per group, the majority true vendor is its label. precision = postings whose own vendor equals the group's
    label; coverage = postings that received a group (of all non-transfer postings); completeness = postings
    sitting in the largest group of their vendor (low = vendor split over many groups)."""
    d = df[df.in_scope].copy()
    d["true"] = d.vendor_true.map(truth)
    cov = d[col].notna().mean()
    g = d[d[col].notna()]
    label = g.groupby(col).true.agg(lambda s: s.value_counts().index[0])
    g = g.assign(label=g[col].map(label))
    prec = (g.label == g.true).mean()
    # unique-text view
    u = g.drop_duplicates("masked")
    prec_u = (u.label == u.true).mean()
    biggest = g.groupby(["true", col]).size().reset_index(name="n").sort_values("n", ascending=False).drop_duplicates("true")
    comp = biggest.n.sum() / len(g)
    # confusions: merges = a group holding >= 2 different vendors (dangerous); splits = a vendor spread over >= 2 groups (harmless)
    mixed = g.groupby(col).true.nunique()
    spl = g.groupby("true")[col].nunique()
    conf = dict(merges=int((mixed > 1).sum()), merged_groups=[dict(group=k, vendors=sorted(g[g[col] == k].true.unique())) for k in mixed[mixed > 1].index],
                postings_in_merged_groups_wrong_side=int((g.label != g.true).sum()),
                splits=int((spl > 1).sum()), extra_groups_from_splits=int((spl - 1).clip(lower=0).sum()))
    errs = u[u.label != u.true][["masked", col, "label", "true"]].head(10)
    return dict(confusions=conf, precision_postings=round(prec, 4), precision_unique_texts=round(prec_u, 4), coverage_postings=round(cov, 4),
                completeness=round(comp, 4), n_groups=int(g[col].nunique()), n_true_vendors=int(g.true.nunique()),
                example_errors=[dict(text=r.masked, predicted_group=r[col], group_main_vendor=r.label, true_vendor=r.true)
                                for _, r in errs.iterrows()])


def add_groups(df, refresh=False, log=print):
    df["in_scope"] = ~df.masked.map(lambda s: bool(TRANSFER.match(s)))
    uniq = sorted(df[df.in_scope].masked.unique())
    rg = {t: rule_group(t) for t in uniq}
    df["g_rule"] = df.masked.map(rg)
    am, status = ai_group(uniq, refresh, log)
    df["g_ai"] = df.masked.map(am) if am else None
    if am: df["g_ai"] = df.g_ai.where(df.in_scope)
    return df, status, len(uniq)


if __name__ == "__main__":
    df = load()
    df, status, nu = add_groups(df, refresh="--refresh" in sys.argv)
    print(f"unique masked texts in scope: {nu}; out of scope (counterparty transfers): {(~df.in_scope).sum():,} postings")
    print("AI status:", status)
    res = {"unique_texts_in_scope": nu, "ai_status": status, "rule_based": evaluate(df, "g_rule")}
    if df.g_ai.notna().any(): res["ai"] = evaluate(df, "g_ai")
    else: res["ai"] = None; print("AI grouping unavailable: continuing with rule-based grouping only")
    # choose method: fewest merges (dangerous), then highest precision
    cand = {k: res[k] for k in ("rule_based", "ai") if res.get(k)}
    res["selected_method"] = min(cand, key=lambda k: (cand[k]["confusions"]["merges"], -cand[k]["precision_postings"]))
    os.makedirs(EVAL, exist_ok=True)
    json.dump(res, open(os.path.join(EVAL, "grouping_eval.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for k in ("rule_based", "ai"):
        if res[k]: print(k, {a: b for a, b in res[k].items() if a != "example_errors"})
    print("selected:", res["selected_method"])
