"""Block 2b-e: patterns, backtest, sizing, value over time.
Timeline: patterns are FOUND on Nov 2025-Apr 2026 (month index 0-5) and BACKTESTED on May-Oct 2026 (6-11).
Nothing from the test months is used to define a pattern, its account/VAT or its member clients.
Groups come from grouping.py (bank_text only, method chosen by fewest merges then precision; vendor_true only labels/evaluates).
Run: python grouping.py && python analyze_patterns.py -> output/patterns.json, sizing.json, value.json"""
import json, os
from datetime import date, timedelta
import pandas as pd
import grouping

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

MIN_TOUCHED, CONSISTENT, HIT_MIN, LOW_AMOUNT = 3, 0.90, 0.95, 1000
FIND_END = 6  # months 0-5 find, 6-11 test
N_TEST = 6
# "equal" = every touch costs the same (case: hours per client unchanged => an approved suggestion costs about the same as a touched posting)
# "split" = suggestion_accepted and rule_to_journal cost half of a manually touched posting. Mid = 1 min (equal) / 0.5 and 1 min (split).
MODELS = {"equal": {lv: {h: m for h in ("suggestion_accepted", "rule_to_journal", "manual")} for lv, m in (("low", .5), ("mid", 1), ("high", 2))},
          "split": {lv: {"suggestion_accepted": m / 2, "rule_to_journal": m / 2, "manual": m} for lv, m in (("low", .5), ("mid", 1), ("high", 2))}}
APPROVAL = {"expected": .5, "conservative": .3}
KILL_HOURS = 2.0
HANDLINGS = ["suggestion_accepted", "rule_to_journal", "manual"]
PAUSE_RATE = 0.05
RISK_ORDER = {"low": 0, "medium": 1, "not_suggested": 2}

df = grouping.load()
df, ai_status, _ = grouping.add_groups(df, log=lambda *_: None)
df["mi"] = (df.date.str[:4].astype(int) - 2025) * 12 + df.date.str[5:7].astype(int) - 11
ev = json.load(open(os.path.join(HERE, "eval", "grouping_eval.json"), encoding="utf-8"))
primary = ev["selected_method"]
methods = {"rule_based": "g_rule", "ai": "g_ai"} if df.g_ai.notna().any() else {"rule_based": "g_rule"}


def spread_examples(p, k=3):
    """Up to k touched postings per client, spread over the test months (the prototype picks 5, the chosen bookkeeper's clients first)."""
    import numpy as np
    out = []
    for c, x in p[p.touched].sort_values("date").groupby("client_id"):
        for i in np.linspace(0, len(x) - 1, min(k, len(x))).round().astype(int):
            r = x.iloc[i]; out.append(dict(date=r.date, bank_text=r.bank_text, amount=float(r.amount), client_id=c))
    return sorted(out, key=lambda e: e["date"])


def build_patterns(df, gcol):
    d = df[df.in_scope & df[gcol].notna()].copy()
    d["grp"] = d[gcol].where(d[gcol] != "RENT", "RENT|" + d.client_id)  # rent is client-specific
    find = d[(d.mi < FIND_END) & (d.special_vat == "")]  # ---- discovery window only ----
    ct = find[find.touched].groupby(["client_id", "grp"]).size()
    tup = find.groupby(["client_id", "grp", "account", "vat_code"]).size().rename("n").reset_index()
    tup["share"] = tup.n / tup.groupby(["client_id", "grp"]).n.transform("sum")
    top = tup.sort_values("n", ascending=False).drop_duplicates(["client_id", "grp"])
    top = top[top.share >= CONSISTENT].set_index(["client_id", "grp"])
    elig = top[top.index.isin(ct[ct >= MIN_TOUCHED].index)].reset_index()
    pt = (elig.groupby(["grp", "account", "vat_code"]).agg(k=("client_id", "nunique"), n=("n", "sum")).reset_index()
          .sort_values(["k", "n"], ascending=False).drop_duplicates("grp"))
    members = elig[elig.grp.isin(pt.grp)][["client_id", "grp"]]
    pool = d.merge(members, on=["client_id", "grp"]).merge(pt[["grp", "account", "vat_code"]].rename(
        columns={"account": "p_acc", "vat_code": "p_vat"}), on="grp")
    pool_ns = pool[pool.special_vat == ""].copy()  # special_vat postings never go into a suggestion
    pool_ns["hit"] = (pool_ns.account == pool_ns.p_acc) & (pool_ns.vat_code == pool_ns.p_vat)
    test = pool_ns[pool_ns.mi >= FIND_END]
    special_test = pool[(pool.special_vat != "") & (pool.mi >= FIND_END)]
    ptup = pt.set_index("grp")
    rows = []
    for g, p in test.groupby("grp"):
        sp = special_test[special_test.grp == g]
        tp = p[p.touched]
        sv = tp[tp.hit]
        acc, vat = ptup.loc[g, ["account", "vat_code"]]
        rows.append(dict(
            group=g.split("|")[0], scope="client" if g.startswith("RENT|") else "portfolio", key=g,
            vendor_label=p.vendor_true.map(grouping.truth).value_counts().index[0],  # evaluation label only
            type="rent" if g.startswith("RENT|") else ("revenue" if acc == 1000 else "shared_vendor"),
            account=int(acc), vat_code=vat, found_on="2025-11..2026-04", backtest_on="2026-05..2026-10",
            clients=sorted(p.client_id.unique()), n_clients=int(p.client_id.nunique()),
            postings_test=len(p), touched_per_month=len(tp) / N_TEST, hit_rate=float(p.hit.mean()),
            saved_per_month=len(sv) / N_TEST,
            saved_by_handling={h: int((sv.handling == h).sum()) / N_TEST for h in HANDLINGS},
            saved_by_bookkeeper={b: len(x) / N_TEST for b, x in sv.groupby("bookkeeper_id")},
            saved_by_client={c: len(x) / N_TEST for c, x in sv.groupby("client_id")},
            special_vat_appears=bool(len(sp)), special_vat_share=float(len(sp) / (len(sp) + len(p))),
            avg_abs_amount=float(p.amount.abs().mean()), median_abs_amount=float(p.amount.abs().median()),
            bank_texts=sorted(p.masked.unique())[:8], accounts_seen=sorted(map(int, p.account.unique())),
            examples=spread_examples(p)))
    P = pd.DataFrame(rows)

    def risk(r):
        if r.hit_rate < HIT_MIN: return "not_suggested"
        return "low" if (r.avg_abs_amount < LOW_AMOUNT and not r.special_vat_appears) else "medium"
    P["risk"] = P.apply(risk, axis=1)
    P["status"] = P.risk.map(lambda x: "not_suggested" if x == "not_suggested" else "suggested")
    # rank by the lower 95 % (Wilson) bound of the hit rate, so 100 % on 3 postings does not outrank 99 % on 1,000
    z = 1.96
    P["hit_rate_lower_bound"] = ((P.hit_rate + z * z / (2 * P.postings_test) - z * ((P.hit_rate * (1 - P.hit_rate) + z * z / (4 * P.postings_test)) / P.postings_test) ** .5)
                                 / (1 + z * z / P.postings_test))
    P["_o"] = list(zip(P.risk.map(RISK_ORDER), -P.hit_rate_lower_bound, -P.saved_per_month))
    P = P.sort_values("_o").drop(columns="_o").reset_index(drop=True)
    P.insert(0, "pattern_id", [f"PT{i+1:03d}" for i in range(len(P))])
    P["safety_rank"] = range(1, len(P) + 1)
    return P, pool_ns


def scenarios(P, df):
    t = df[df.touched & (df.mi >= FIND_END)]
    touches = t.groupby("bookkeeper_id").size() / N_TEST
    bks = sorted(df.bookkeeper_id.unique())
    sugg = P[(P.status == "suggested") & ~P.special_vat_appears & (P.type != "revenue")]
    sets = {"ceiling": (P[P.status == "suggested"], 1.0),  # ceiling: every pattern with hit rate >= 95 %
            "expected": (sugg, APPROVAL["expected"]), "conservative": (sugg, APPROVAL["conservative"])}
    res = {}
    for name, (S, share) in sets.items():
        per_bk = {b: sum(r.get(b, 0) for r in S.saved_by_bookkeeper) * share for b in bks}
        hand = {h: S.saved_by_handling.map(lambda x: x[h]).sum() * share for h in HANDLINGS}
        tot = sum(hand.values())
        x = dict(approval_share=share, n_patterns=int(len(S)), saved_per_month_office=tot, saved_by_handling=hand,
                 per_bookkeeper={}, hours_office={}, hours_mid_from_rule_to_journal_ASSUMPTION={},
                 assumption_note="rule_to_journal gain assumes a bank workflow can post directly (not only to the journal)")
        for model, levels in MODELS.items():
            x["hours_office"][model] = {}
            x["hours_mid_from_rule_to_journal_ASSUMPTION"][model] = hand["rule_to_journal"] * levels["mid"]["rule_to_journal"] / 60
            for lvl, mm in levels.items():
                mps = sum(hand[h] * mm[h] for h in HANDLINGS) / tot if tot else 0
                x["hours_office"][model][lvl] = tot * mps / 60
                for b in bks:
                    pb = x["per_bookkeeper"].setdefault(b, dict(touches_per_month=float(touches[b]), saved_per_month=per_bk[b],
                                                                share_of_touches=per_bk[b] / float(touches[b]), hours={}))
                    pb["hours"].setdefault(model, {})[lvl] = per_bk[b] * mps / 60
        x["mean_hours_mid"] = {m: x["hours_office"][m]["mid"] / len(bks) for m in MODELS}
        x["mean_hours_mid_excl_rule_to_journal"] = {m: (x["hours_office"][m]["mid"] - x["hours_mid_from_rule_to_journal_ASSUMPTION"][m]) / len(bks) for m in MODELS}
        x["mean_share_of_touches"] = tot / float(touches.sum())
        res[name] = x
    c = res["conservative"]
    res["kill_check"] = {}
    for m in MODELS:
        cons = [v["hours"][m]["mid"] for v in c["per_bookkeeper"].values()]
        res["kill_check"][m] = dict(threshold_hours=KILL_HOURS, basis="conservative scenario, mid minutes, per bookkeeper per month",
                                    min_hours=min(cons), mean_hours=sum(cons) / len(cons),
                                    mean_hours_excl_rule_to_journal=c["mean_hours_mid_excl_rule_to_journal"][m],
                                    below_threshold=[b for b, v in zip(bks, cons) if v < KILL_HOURS],
                                    verdict="KILL" if sum(cons) / len(cons) < KILL_HOURS else "PASS")
    return res


EXC_CLIENT = "C087"   # simulated exception: an approved rent workflow at one of B2's clients
EXC_DATE = "2026-10-27"


def simulate_value(P, df, pool):
    """The 3 safest patterns plus one client's rent pattern are approved from May 2026; the rest stay open suggestions.
    Simulated exception (overlay, not in postings.csv): in October a payment to a new payee, about 3x the client's normal rent,
    arrives for the rent workflow; the workflow holds it back for that client."""
    sug = P[P.status == "suggested"].sort_values("safety_rank")
    rent = sug[(sug.type == "rent") & sug.clients.map(lambda c: list(c) == [EXC_CLIENT])]
    assert len(rent) == 1, "rent pattern for the exception client not found"
    approved = pd.concat([sug.head(3), rent])
    opened = sug[~sug.pattern_id.isin(approved.pattern_id)]
    months = [f"{2025 + (10 + i) // 12}-{(10 + i) % 12 + 1:02d}" for i in range(12)]
    ap = pool.merge(approved[["key", "pattern_id", "hit_rate"]], left_on="grp", right_on="key")
    ap = ap[ap.touched & (ap.mi >= FIND_END)].copy()
    ap["p_corr"] = (~ap.hit).astype(float)
    base_auto = df[df.handling == "rule_posted"].groupby("mi").size().reindex(range(12), fill_value=0)
    tot = df.groupby("mi").size()
    series, by_pat = [], {}
    for mi in range(12):
        lv = ap[ap.mi == mi]
        corr = float(lv.p_corr.sum())
        for pid, x in lv.groupby("pattern_id"):
            by_pat.setdefault(pid, {})[months[mi]] = dict(auto_posted=len(x), corrections=round(float(x.p_corr.sum()), 1),
                                                          correction_rate=round(float(x.p_corr.mean()), 4), status="active")
        series.append(dict(month=months[mi], postings=int(tot[mi]), auto_before=int(base_auto[mi]), auto_from_suggestions=len(lv),
                           auto_total=int(base_auto[mi]) + len(lv), pct_auto_posted=(int(base_auto[mi]) + len(lv)) / int(tot[mi]) * 100,
                           touches=int(tot[mi]) - int(base_auto[mi]) - len(lv), touches_per_client=(int(tot[mi]) - int(base_auto[mi]) - len(lv)) / 180,
                           corrections=round(corr, 1)))
    rp = rent.iloc[0]
    own = df[(df.client_id == EXC_CLIENT) & df.bank_text.isin(rp.bank_texts)]
    usual = float(own.amount.abs().median())
    held = round(usual * 3 / 100) * 100
    opn = opened[["pattern_id", "group", "risk", "n_clients", "saved_per_month", "hit_rate", "avg_abs_amount"]]
    return dict(approval_month=months[6], approved_patterns=[dict(pattern_id=r.pattern_id, group=r.group, risk=r.risk, clients=r.n_clients) for r in approved.itertuples()],
                exception=dict(pattern_id=rp.pattern_id, client=EXC_CLIENT, bank_text=rp.bank_texts[0], date=EXC_DATE, usual_amount=usual, held_amount=float(held),
                               ratio=round(held / usual, 2), rent_postings=int(len(own)), account=int(rp.account),
                               note="Simulated overlay: not in postings.csv and not counted in any series."),
                open_suggestions_oct=dict(count=int(len(opn)), by_risk=opn.risk.value_counts().to_dict(),
                                          items=opn.round(4).to_dict("records")),
                months=series, corrections_by_pattern=by_pat,
                note="Simulation overlay on the real series: before May nothing changes; corrections = actual backtest misses.")


results = {m: (*build_patterns(df, col), None) for m, col in methods.items()}
for m in results:
    P_, pool_, _ = results[m]
    results[m] = (P_, pool_, scenarios(P_, df))
P, pool, sz = results[primary]
V = simulate_value(P, df, pool)

# postings behind each pattern's backtest (May-Oct), same rows as postings_test / hit_rate; read by the prototype's check panel
bt = pool[pool.mi >= FIND_END].merge(P[["key", "pattern_id"]], left_on="grp", right_on="key")
bt = bt[["pattern_id", "date", "client_id", "bank_text", "amount", "account", "vat_code", "p_acc", "p_vat", "hit"]].sort_values(["pattern_id", "date"])
bt.to_csv(os.path.join(OUT, "backtest_postings.csv"), index=False, encoding="utf-8")

json.dump(dict(grouping_method=primary, timeline=dict(find="2025-11..2026-04", backtest="2026-05..2026-10"),
               thresholds=dict(min_touched_per_client=MIN_TOUCHED, consistent_account_share=CONSISTENT, min_hit_rate=HIT_MIN, low_risk_avg_amount_dkk=LOW_AMOUNT),
               patterns=P.to_dict("records")), open(os.path.join(OUT, "patterns.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(dict(grouping_method=primary, minutes=MODELS, approval_share=APPROVAL, scenarios=sz,
               sensitivity_other_grouping={m: results[m][2] for m in results if m != primary}, grouping_eval=ev),
          open(os.path.join(OUT, "sizing.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(V, open(os.path.join(OUT, "value.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---------------- printed summary ----------------
print("grouping method:", primary)
for m in results:
    Pm, _, s = results[m]
    print(f"\n##### {m}: {len(Pm)} patterns | risk: {Pm.risk.value_counts().to_dict()}")
    for name in ("ceiling", "expected", "conservative"):
        x = s[name]; h = x["saved_by_handling"]
        print(f"{name:13s} patterns {x['n_patterns']:3d} saved/mo {x['saved_per_month_office']:6.0f} (sugg {h['suggestion_accepted']:.0f} / rtj {h['rule_to_journal']:.0f} / manual {h['manual']:.0f})  share {x['mean_share_of_touches']*100:.1f} %  "
              + "  ".join(f"{mo}: mid {x['mean_hours_mid'][mo]:.1f} h (excl rtj {x['mean_hours_mid_excl_rule_to_journal'][mo]:.1f})" for mo in MODELS))
    for mo, k in s["kill_check"].items(): print("kill", mo, k["verdict"], round(k["mean_hours"], 2), "excl rtj", round(k["mean_hours_excl_rule_to_journal"], 2), "min", round(k["min_hours"], 2), k["below_threshold"])
cols = ["pattern_id", "group", "vendor_label", "type", "risk", "n_clients", "touched_per_month", "hit_rate", "avg_abs_amount", "special_vat_appears"]
print("\nTop 10 by safety rank:"); print(P[P.status == "suggested"].head(10)[cols].round(3).to_string(index=False))
print("\nNot suggested:"); print(P[(P.status != "suggested") & (P.type != "rent")][cols + ["accounts_seen"]].round(3).to_string(index=False))
print("not suggested rent patterns:", int(((P.status != 'suggested') & (P.type == 'rent')).sum()))
for name in ("PostNord", "Lemvigh-Mueller"):
    for r in P[P.vendor_label == name].itertuples():
        print(f"  {name}: clients {r.n_clients}, touches/mo {r.touched_per_month:.1f}, saved/mo {r.saved_per_month:.1f}, hit {r.hit_rate*100:.1f} %, avg {r.avg_abs_amount:,.0f} DKK, risk {r.risk}")
print("\nValue sim: approved", [(a["pattern_id"], a["group"], a["risk"]) for a in V["approved_patterns"]], "exception", V["exception"])
for m in V["months"]: print(m["month"], f"auto {m['pct_auto_posted']:.1f} %", f"touches/client {m['touches_per_client']:.1f}", f"corr {m['corrections']}")
print("open suggestions Oct:", V["open_suggestions_oct"]["count"], V["open_suggestions_oct"]["by_risk"])
