"""Block 3: build the self-contained prototype (prototype/index.html) from output/*.json and data/postings.csv.
Run after analyze_patterns.py: python build_prototype.py
Adds fictional Danish company and bookkeeper names (display only; ids stay for traceability) and Danish UI content."""
import json, os, random, hashlib
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
J = lambda *p: json.load(open(os.path.join(HERE, *p), encoding="utf-8"))
pat, siz, val = J("output", "patterns.json"), J("output", "sizing.json"), J("output", "value.json")
df = pd.read_csv(os.path.join(HERE, "data", "postings.csv"), keep_default_na=False)
df["mi"] = (df.date.str[:4].astype(int) - 2025) * 12 + df.date.str[5:7].astype(int) - 11
ddmmyy = lambda iso: f"{iso[8:10]}.{iso[5:7]}.{iso[2:4]}"

# ---- fictional names (display only) ----
BK_NAMES = {"B1": "Mette Holm", "B2": "Jonas Krogh", "B3": "Sofie Lind", "B4": "Anders Bruun", "B5": "Camilla Vestergaard", "B6": "Thomas Dahl"}
ctype = df.drop_duplicates("client_id").set_index("client_id")
rng = random.Random(7)
SUR = ["Hansen", "Nielsen", "Jensen", "Pedersen", "Andersen", "Larsen", "Sørensen", "Rasmussen", "Møller", "Kristensen", "Olsen", "Thomsen", "Poulsen", "Mortensen", "Knudsen",
       "Jørgensen", "Madsen", "Christensen", "Kjær", "Lund", "Bak", "Dam", "Friis", "Holm", "Winther", "Skov", "Brandt", "Vestergaard", "Nygaard", "Toft"]
KINDS = {"small_service": [("Rådgivning", "ApS"), ("Consulting", "ApS"), ("Design", "ApS"), ("Marketing", "ApS"), ("IT", "ApS"), ("Kommunikation", "ApS"), ("Arkitekter", "ApS"), ("Ejendomsservice", "ApS"), ("& Partnere", "ApS")],
         "retail": [("Boghandel", "ApS"), ("Cykler", "ApS"), ("Blomster", "ApS"), ("Café", "ApS"), ("Tøj", "ApS"), ("Isenkram", "A/S"), ("Bageri", "ApS"), ("Legetøj", "ApS"), ("Sko", "ApS"), ("Vinhandel", "ApS")],
         "holding": [("Holding", "ApS"), ("Invest", "ApS"), ("Ejendomme", "ApS"), ("Kapital", "ApS")],
         "trades": [("VVS", "ApS"), ("El", "ApS"), ("Murerfirma", "ApS"), ("Tømrer", "ApS"), ("Maler", "ApS"), ("Anlægsgartner", "ApS"), ("Smede", "ApS"), ("Gulv", "ApS"), ("Tag", "ApS")]}
used, client_name = set(), {}
for c, r in ctype.sort_index().iterrows():
    for _ in range(500):
        name = f"{rng.choice(SUR)} {rng.choice(KINDS[r.client_type])[0]} {rng.choice(KINDS[r.client_type])[1]}".replace("& Partnere ApS", "& Partnere ApS")
        k = rng.choice(KINDS[r.client_type]); name = f"{rng.choice(SUR)} {k[0]} {k[1]}"
        if name not in used: break
    used.add(name); client_name[c] = name
first_trades = next(c for c in sorted(client_name) if ctype.loc[c, "client_type"] == "trades")
used.discard(client_name[first_trades]); client_name[first_trades] = "Hansen VVS ApS"

# ---- patterns: Danish display names and kinds ----
P = pat["patterns"]
def da_name(p):
    lab, g = p["vendor_label"], p["group"].title()
    if p["type"] == "rent": return f"Husleje, {client_name[p['clients'][0]]}", "Husleje"
    if lab == "Card settlement": return f"{g.split()[0]} kortafregning", "Afregning"
    if lab == "OK": return "OK (brændstof)", "Leverandør"
    if p["account"] in (7800, 7810): return lab.replace(" card fees", " kortgebyrer").replace(" fees", " gebyrer"), "Gebyr"  # bank and card fees
    return lab, "Leverandør"
for p in P: p["name"], p["kind"] = da_name(p)
seen = {}
for p in P: seen.setdefault(p["name"], []).append(p)
for name, ps in seen.items():
    if len(ps) > 1 and ps[0]["type"] != "rent":
        for p in ps: p["name"] = f"{name} ({p['bank_texts'][0].replace('#', '').strip().title()})"
# ---- fuel is medium risk: the VAT deduction depends on the vehicle (van or passenger car). Applied here and not in analyze_patterns.py,
# because the approved set and its simulated months are chosen from the original ranking there. Workflows already approved keep their label (Circle K).
FUEL_REASON = "Momsfradrag afhænger af køretøjet (varebil eller personbil)."
approved_ids = {a["pattern_id"] for a in val["approved_patterns"]}
is_fuel = lambda p: p["account"] == 7500 and p["vat_code"] == "I25" and p["status"] == "suggested" and p["pattern_id"] not in approved_ids
RISK_ORDER = {"low": 0, "medium": 1, "not_suggested": 2}
for p in P:
    if is_fuel(p): p["risk"] = "medium"
for i, p in enumerate(sorted(P, key=lambda p: (RISK_ORDER[p["risk"]], -p["hit_rate_lower_bound"], -p["saved_per_month"])), 1):
    p["safety_rank"] = i  # same ordering as analyze_patterns.py, so "safest first" stays true after the fuel change
def risk_reason(p):
    """One line under the risk label; follows the rule in analyze_patterns.py (hit rate, average amount, special VAT)."""
    if p["risk"] == "not_suggested": return "Under 95 % korrekte."
    if p["risk"] == "low": return "Mindst 95 % korrekte, beløb under 1.000 kr., ingen særlig moms."
    if is_fuel(p): return FUEL_REASON
    if p["type"] == "rent": return "Husleje: gælder én kunde."
    if p["special_vat_appears"]: return "Særlig moms i nogle posteringer."
    if p["type"] == "revenue": return "Omsætning: beløb over 1.000 kr."
    return "Beløb over 1.000 kr."
for p in P: p["risk_reason"] = risk_reason(p)
keep = ["pattern_id", "name", "kind", "group", "type", "risk", "risk_reason", "status", "safety_rank", "n_clients", "clients", "touched_per_month", "saved_per_month",
        "saved_by_handling", "saved_by_bookkeeper", "saved_by_client", "hit_rate", "hit_rate_lower_bound", "postings_test", "avg_abs_amount",
        "special_vat_appears", "special_vat_share", "bank_texts", "accounts_seen", "account", "vat_code", "examples"]
patterns = []
for p in P:
    q = {k: p[k] for k in keep}
    q["hit_lb"] = q.pop("hit_rate_lower_bound")
    q["hits"] = int(round(q["hit_rate"] * q["postings_test"]))
    patterns.append(q)
byid = {p["pattern_id"]: p for p in patterns}

# ---- scenarios ----
sc = {}
for k in ("ceiling", "expected", "conservative"):
    x = siz["scenarios"][k]
    sc[k] = dict(n_patterns=x["n_patterns"], saved=x["saved_per_month_office"], saved_by_handling=x["saved_by_handling"], share=x["mean_share_of_touches"],
                 per_bookkeeper={b: dict(hours=v["hours"], touches_per_month=v["touches_per_month"]) for b, v in x["per_bookkeeper"].items()},
                 per_bookkeeper_mean={m: {l: h / 6 for l, h in x["hours_office"][m].items()} for m in x["hours_office"]},
                 rtj_hours_mid={m: v / 6 for m, v in x["hours_mid_from_rule_to_journal_ASSUMPTION"].items()})

# ---- KPIs and series ----
N = len(df)
touch_pc = df[df.touched].groupby("mi").size() / 180
kpi = dict(auto_some=float((df.handling != "manual").mean()), rule_posted=float((df.handling == "rule_posted").mean()),
           rtj=float((df.handling == "rule_to_journal").mean()), rule_posted_n=int((df.handling == "rule_posted").sum()),
           rtj_n=int((df.handling == "rule_to_journal").sum()),
           clients_with_rule=int(df[df.handling.isin(["rule_posted", "rule_to_journal"])].client_id.nunique()),
           touches_per_client=float(touch_pc.mean()), touch_min=float(touch_pc.min()), touch_max=float(touch_pc.max()), rows=N)
months = val["months"]
for m, i in zip(months, range(12)): m["touches_actual"] = float(touch_pc[i])
ex = val["exception"]
oct_auto = {pid: d["2026-10"]["auto_posted"] for pid, d in val["corrections_by_pattern"].items() if "2026-10" in d}
RECIPIENTS = dict(usual="Havnegade Udlejning ApS", new="Kajkanten Ejendomme ApS")  # fictional payees for the simulated rent exception
value = dict(months=months, approved=val["approved_patterns"], oct_auto=oct_auto, health=val["corrections_by_pattern"],
             exception=dict(pattern=ex["pattern_id"], client=ex["client"], date=ddmmyy(ex["date"]), usual_amount=ex["usual_amount"], held_amount=ex["held_amount"],
                            usual_to=RECIPIENTS["usual"], new_to=RECIPIENTS["new"], account=ex["account"]))

# ---- bookkeeper data: tasks and time registration (fictional, derived from Oct touch counts) ----
last = df[(df.mi == 11) & df.touched]
praksis = {}
def h5(s): return int(hashlib.md5(s.encode()).hexdigest(), 16)
WEEK = {"this": ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"], "last": ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]}
tasks, times = [], []
for b, g in last.groupby("bookkeeper_id"):
    cnt = g.groupby("client_id").agg(n=("posting_id", "size"), bank=("source", lambda s: int((s == "bank").sum())), voucher=("source", lambda s: int((s == "voucher").sum())))
    top = cnt.sort_values("n", ascending=False).head(10)  # the 10 busiest clients in October
    praksis[b] = dict(touches=int(len(g)))
    for c, r in top.iterrows():
        t = ctype.loc[c, "client_type"]
        items = []
        if r.voucher > 0: items.append(("Bogføring", f"Bogføring af ~{r.voucher} bilag", f"{r.voucher} bilag i indbakken", r.voucher * 3))
        if r.bank > 0: items.append(("Afstemning", "Bankafstemning", f"{r.bank} banklinjer til afstemning", r.bank * 1.5))
        if t in ("retail", "trades"): items.append(("Bogføring", "Daglig bogføring", "Kassekladde og bilag fra dagen", 25))
        if t == "small_service": items.append(("Fakturering", "Fakturering af månedens ydelser", "Kladder til udsendelse", 45))
        for typ, comment, sub, mins in items:
            d = WEEK["this"][h5(c + typ + comment) % 5]
            tasks.append(dict(date=d, client=c, type=typ, comment=comment, sub=sub, bk=b, n=int(r.n), voucher=int(r.voucher)))
            for wk, days in WEEK.items():
                scale = 1.0 if wk == "this" else 0.9 + (h5(c + typ + wk) % 21) / 100
                tot = max(5, int(round(mins * scale / 5) * 5))
                bill = int(round(tot * (0.6 if typ == "Afstemning" else 0.95) / 5) * 5)
                times.append(dict(date=days[h5(c + typ + wk + "d") % 5], client=c, type=typ, total=tot, billable=bill, comment=comment if wk == "this" else comment.replace("~", "~"), bk=b, week=wk))
tasks.sort(key=lambda x: (x["date"], x["client"]))
times.sort(key=lambda x: (x["date"], x["client"]))
client_bk = ctype.bookkeeper_id.to_dict()
base_auto_client = df[(df.mi == 11) & (df.handling == "rule_posted")].groupby("client_id").size().to_dict()
base_auto_oct = int(((df.mi == 11) & (df.handling == "rule_posted")).sum())
tot_oct = int((df.mi == 11).sum())

# ---- bank workflows ----
r = df[df.handling.isin(["rule_posted", "rule_to_journal"])]
rules = (r.groupby(["client_id", "vendor_true"]).agg(n=("posting_id", "size"), posts=("handling", lambda s: float((s == "rule_posted").mean())),
                                                     account=("account", lambda s: int(s.mode().iloc[0]))).reset_index())
rules["mode"] = rules.posts.map(lambda x: "Bogfører direkte" if x > .5 else "Sender til kassekladde")
rules = rules.sort_values("n", ascending=False)
def da_supplier(v):
    if v.startswith("Landlord"): return "Husleje"
    return {"Card settlement": "Kortafregning"}.get(v) or v.replace(" card fees", " kortgebyrer").replace(" fees", " gebyrer")


wf = [dict(client=x.client_id, bk=client_bk[x.client_id], supplier=da_supplier(x.vendor_true), account=x.account, mode=x.mode, n=int(x.n))
      for x in rules.head(60).itertuples()]

data = dict(kpi=kpi, minutes=siz["minutes"], scenarios=sc, killHours=2, patterns=patterns, value=value, praksis=praksis, clientBk=client_bk,
            clientName=client_name, bkName=BK_NAMES, tasks=tasks, times=times,
            clientType={c: {"retail": "detail", "small_service": "service", "holding": "holding", "trades": "håndværk"}[v.client_type] for c, v in ctype.iterrows()}, baseAutoClient=base_auto_client,
            baseAutoOct=base_auto_oct, totalOct=tot_oct, workflows=wf, nRules=int(len(rules)), agreement="1047382")
tpl = open(os.path.join(HERE, "prototype", "template.html"), encoding="utf-8").read()
# ---- postings behind each suggestion's backtest (May-Oct), compact rows [day, client, text, amount, booked]; booked = -1 when it equals the suggestion
bt = pd.read_csv(os.path.join(HERE, "output", "backtest_postings.csv"), dtype={"vat_code": str, "p_vat": str})
texts, clients_, booked = {}, {}, {}
base = pd.Timestamp("2026-05-01")
rows_by = {}
for pid_, g in bt.groupby("pattern_id"):
    out = []
    for r in g.itertuples():
        bi = -1 if r.hit else booked.setdefault(f"{r.account}|{r.vat_code}", len(booked))
        out.append([(pd.Timestamp(r.date) - base).days, clients_.setdefault(r.client_id, len(clients_)), texts.setdefault(r.bank_text, len(texts)), round(float(r.amount), 2), bi])
    rows_by[pid_] = out
btdata = dict(texts=list(texts), clients=list(clients_), booked=list(booked), rows=rows_by)
bt_json = json.dumps(btdata, ensure_ascii=False, separators=(",", ":")).replace("</", "<\/")

html = tpl.replace("/*DATA*/", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")).replace("/*BT*/", bt_json)
open(os.path.join(HERE, "prototype", "index.html"), "w", encoding="utf-8").write(html)
print(f"prototype/index.html written, {len(html)/1024:.0f} KB; patterns {len(patterns)}; tasks {len(tasks)}; time entries {len(times)}")
print([p["name"] for p in patterns[:12]])
