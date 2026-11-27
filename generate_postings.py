"""Block 1: synthetic postings for the fictional bookkeeping office 'Nordkyst Regnskab'.
Run: python generate_postings.py  -> data/postings.csv (fixed seed, reproducible)."""
import random, math, os
import pandas as pd

SEED = 42
rnd = random.Random(SEED)
HERE = os.path.dirname(os.path.abspath(__file__))
MONTHS = [(2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 11)]
TARGET_AUTOMATED = 0.67
TARGET_RULE_POSTED = 0.10
N_RULE_CLIENTS = 27  # 15 % of 180

# key, true name, category, account, vat, special_vat, mean abs amount, bank text variants
V = [
 ("tel1","TDC Erhverv","telephony",7210,"I25","mixed_use",650,["TDC ERHVERV A/S","NETS*TDC 4412","BS TDC","TDC ERHVERV FAKT {n}"]),
 ("tel2","Telenor","telephony",7210,"I25","mixed_use",520,["TELENOR A/S","BS TELENOR","TELENOR DK {n}","NETS*TELENOR"]),
 ("tel3","3 Business","telephony",7210,"I25","mixed_use",430,["3 BUSINESS","HI3G DENMARK","BS 3 BUSINESS","3DK {n}","3 ERHVERV"]),
 ("tel4","Telia","telephony",7210,"I25","mixed_use",480,["TELIA DANMARK","BS TELIA","TELIA {n}","TELIA ERHVERV A/S"]),
 ("bnk1","Danske Bank fees","bank_fee",7800,"NONE","",180,["DANSKE BANK GEBYR","GEBYR DANSKE BANK","KONTOGEBYR DB","DB GEBYR {n}"]),
 ("bnk2","Nordea fees","bank_fee",7800,"NONE","",160,["NORDEA GEBYR","KONTOGEBYR NORDEA","NORDEA DK GEB","NDEA GEBYR {n}"]),
 ("bnk3","Jyske Bank fees","bank_fee",7800,"NONE","",150,["JYSKE BANK GEBYR","JB GEBYR","KONTOGEBYR JYSKE","JYSKE GEB {n}"]),
 ("bnk4","Sydbank fees","bank_fee",7800,"NONE","",140,["SYDBANK GEBYR","SYDBANK KONTOGEB","SB GEBYR {n}"]),
 ("crd1","Nets card fees","card_fee",7810,"NONE","",95,["NETS A/S GEBYR","NETS*KORTGEBYR","NETS DANKORT GEB","NETS {n}","BS NETS"]),
 ("crd2","Teya card fees","card_fee",7810,"NONE","",85,["TEYA SOLUTIONS","TEYA*FEE","TEYA GEBYR {n}","SALTPAY TEYA"]),
 ("crd3","Stripe fees","card_fee",7810,"NONE","",70,["STRIPE PAYMENTS","STRIPE*FEE {n}","STRIPE EUROPE","STRIPE TECHNOLOGY"]),
 ("crd4","Clearhaus fees","card_fee",7810,"NONE","",75,["CLEARHAUS A/S","CLEARHAUS*GEB","CLEARHAUS {n}"]),
 ("sw1","Microsoft 365","software",7300,"IEUV","eu_purchase",320,["MICROSOFT*365","MSFT *E0400{n}","MICROSOFT IRELAND","MICROSOFT 365 BUSINESS","MS 365 SUB"]),
 ("sw2","Adobe","software",7300,"IEUV","eu_purchase",480,["ADOBE SYSTEMS","ADOBE *CREATIVE CLD","ADOBE IRELAND {n}","ADOBE ACROBAT"]),
 ("sw3","Google Workspace","software",7300,"IEUV","eu_purchase",140,["GOOGLE *WORKSPACE","GOOGLE IRELAND LTD","GSUITE {n}","GOOGLE CLOUD EMEA"]),
 ("sw4","Zoom","software",7300,"IEUV","eu_purchase",130,["ZOOM.US","ZOOM VIDEO COMM","ZOOM *{n}"]),
 ("sw5","Dropbox","software",7300,"IEUV","eu_purchase",120,["DROPBOX","DROPBOX*{n}","DROPBOX INTL"]),
 ("sw6","Slack","software",7300,"IEUV","eu_purchase",110,["SLACK TECHNOLOGIES","SLACK*{n}","SLACK IRELAND"]),
 ("sw7","Canva","software",7300,"IEUV","eu_purchase",100,["CANVA PTY","CANVA* {n}","CANVA PRO"]),
 ("sw8","Shopify","software",7300,"IEUV","eu_purchase",330,["SHOPIFY","SHOPIFY* {n}","SHOPIFY INTERNATIONAL","SHOPIFY IRELAND"]),
 ("ins1","Tryg","insurance",7400,"NONE","",1450,["TRYG FORSIKRING","TRYG A/S {n}","BS TRYG","TRYG PRAEMIE"]),
 ("ins2","Codan","insurance",7400,"NONE","",1300,["CODAN FORSIKRING","CODAN A/S","BS CODAN","CODAN {n}"]),
 ("ins3","Topdanmark","insurance",7400,"NONE","",1380,["TOPDANMARK FORS","TOPDANMARK A/S","BS TOPDANMARK","TD FORS {n}"]),
 ("ins4","If Forsikring","insurance",7400,"NONE","",1250,["IF SKADEFORSIKRING","IF FORSIKRING","BS IF","IF A/S {n}"]),
 ("fu1","Circle K","fuel",7500,"I25","mixed_use",520,["CIRCLE K","CIRCLE K {n}","CIRCLEK DK","STATOIL/CIRCLE K","CIRCLE K TANK"]),
 ("fu2","Shell","fuel",7500,"I25","mixed_use",540,["SHELL","SHELL DK {n}","SHELL TANKSTATION","SHELL FUEL"]),
 ("fu3","OK","fuel",7500,"I25","mixed_use",500,["OK BENZIN","OK A.M.B.A.","OK {n}","OK PLUS TANK"]),
 ("fu4","Q8","fuel",7500,"I25","mixed_use",510,["Q8","Q8 DANMARK {n}","Q8 TANK","F24 Q8"]),
 ("ls1","LeasePlan","leasing",7600,"I25","",3900,["LEASEPLAN DANMARK","LEASEPLAN A/S","BS LEASEPLAN","LEASEPLAN {n}"]),
 ("ls2","Nordania Leasing","leasing",7600,"I25","",4200,["NORDANIA LEASING","NORDANIA FINANS","BS NORDANIA","NORDANIA {n}","NORD LEASING"]),
 ("ls3","Santander Leasing","leasing",7600,"I25","",3600,["SANTANDER CONSUMER","SANTANDER LEASING","BS SANTANDER","SCF {n}"]),
 ("ad1","Google Ads","advertising",7100,"IEUV","eu_purchase",1800,["GOOGLE *ADS{n}","GOOGLE IRELAND ADS","GOOGLE ADS","GOOGLE*ADWORDS"]),
 ("ad2","Meta Ads","advertising",7100,"IEUV","eu_purchase",1500,["FACEBK *{n}","META PLATFORMS IRL","FACEBOOK ADS","META ADS {n}"]),
 ("ad3","LinkedIn Ads","advertising",7100,"IEUV","eu_purchase",1700,["LINKEDIN ADS","LINKEDIN IRELAND","LNKD*ADS {n}"]),
 ("el1","Andel Energi","electricity",7200,"I25","",1900,["ANDEL ENERGI","ANDEL ENERGI A/S","BS ANDEL","ANDEL EL {n}"]),
 ("po1","PostNord","postage",7320,"I25","",260,["POSTNORD","POSTNORD DANMARK","POSTNORD*{n}","PN PORTO"]),
 ("of1","Lyreco","office",7310,"I25","",620,["LYRECO DANMARK","LYRECO {n}","LYRECO A/S"]),
 ("rp1","Wolt","representation",7120,"I25_REP","representation",280,["WOLT","WOLT ENTERPRISES {n}","WOLT DK","WOLT*ORDER"]),
 ("rp2","Scandic Hotels","representation",7120,"I25_REP","representation",1250,["SCANDIC HOTELS","SCANDIC {n}","SCANDIC HOTEL RES"]),
 ("wh1","Ahlsell","wholesale",2000,"I25","",3400,["AHLSELL DANMARK","AHLSELL A/S","AHLSELL {n}","AHLSELL ONLINE"]),
 ("wh2","Lemvigh-Mueller","wholesale",2000,"I25","",3100,["LEMVIGH-MUELLER","LEMVIGH MULLER A/S","LM {n}","LEMVIGH-M"]),
]
VK = {v[0]: v for v in V}
BANKS, CARDS = ["bnk1","bnk2","bnk3","bnk4"], ["crd1","crd2","crd3","crd4"]
TEL, INS, FUEL = ["tel1","tel2","tel3","tel4"], ["ins1","ins2","ins3","ins4"], ["fu1","fu2","fu3","fu4"]
LEASE, ADS = ["ls1","ls2","ls3"], ["ad1","ad2","ad3"]
SW, WH = ["sw1","sw2","sw3","sw4","sw5","sw6","sw7","sw8"], ["wh1","wh2"]
SURN = ["Hansen","Nielsen","Jensen","Pedersen","Andersen","Larsen","Sorensen","Rasmussen","Moller","Kristensen"]
INCONSISTENT = {"el1", "of1", "ls2", "ins3"}  # Andel Energi, Lyreco, Nordania Leasing, Topdanmark
STREETS = ["Havnegade","Strandvejen","Norregade","Kirkevej","Algade","Skolevej"]


def build_clients():
    # stratified: each bookkeeper gets 12 service, 6 retail, 6 holding, 6 trades (= 30 clients)
    plan = []
    for b in range(6):
        for t, n in (("small_service", 12), ("retail", 6), ("holding", 6), ("trades", 6)):
            plan += [(t, f"B{b+1}")] * n
    rnd.shuffle(plan)
    return [dict(client_id=f"C{i+1:03d}", client_type=t, bookkeeper_id=b) for i, (t, b) in enumerate(plan)]


def setup_client(c):
    t = c["client_type"]
    vs = {}
    def add(k, f): vs[k] = f
    add(rnd.choice(BANKS), 1.5 if t != "holding" else 1)
    if t == "small_service":
        add(rnd.choice(TEL), 1)
        for k in rnd.sample(SW, rnd.randint(2, 5)): add(k, 1)
        add(rnd.choice(INS), 1)
        if rnd.random() < .5: add(rnd.choice(ADS), 1.5)
        if rnd.random() < .5: add("el1", 1)
        if rnd.random() < .3: add(rnd.choice(LEASE), 1)
        if rnd.random() < .3: add(rnd.choice(FUEL), 3)
        if rnd.random() < .4: add("of1", 1)
        if rnd.random() < .3: add("po1", 1)
        if rnd.random() < .5: add(rnd.choice(["rp1", "rp2"]), 2)
        base_tail = 24
    elif t == "retail":
        add(rnd.choice(TEL), 1)
        for k in rnd.sample(CARDS, rnd.randint(1, 2)): add(k, 14)
        for k in rnd.sample(SW, rnd.randint(1, 3)): add(k, 1)
        add(rnd.choice(INS), 1); add("el1", 1)
        if rnd.random() < .6: add(rnd.choice(ADS), 2)
        if rnd.random() < .4: add("po1", 3)
        if rnd.random() < .1: add(rnd.choice(LEASE), 1)
        base_tail = 10
    elif t == "holding":
        if rnd.random() < .3: add(rnd.choice(INS), 1)
        if rnd.random() < .5: add(rnd.choice(SW), 1)
        base_tail = 1.5
    else:
        add(rnd.choice(TEL), 1)
        for k in rnd.sample(FUEL, rnd.randint(1, 2)): add(k, 8)
        if rnd.random() < .6: add(rnd.choice(LEASE), 1)
        add(rnd.choice(INS), 1)
        for k in rnd.sample(SW, rnd.randint(1, 2)): add(k, 1)
        for k in rnd.sample(WH, rnd.randint(1, 2)): add(k, 6)
        if rnd.random() < .3: add(rnd.choice(ADS), 1)
        base_tail = 20
    c["vendors"] = vs
    c["rent"] = {"small_service": .8, "retail": 1.0, "holding": 0, "trades": .5}[t] > rnd.random()
    c["rent_amount"] = round(rnd.uniform(3500, 22000), 0) if c["rent"] else 0
    c["rent_text"] = rnd.choice(["HUSLEJE {s} {n}", "LEJE {s} {n}", "UDLEJER {s} {n}", "BS HUSLEJE {s}"]).format(
        s=rnd.choice(STREETS).upper(), n=rnd.randint(1, 99))
    c["tail_rate"] = base_tail * rnd.uniform(.7, 1.3)
    n_pool = rnd.randint(25, 50) if t != "holding" else rnd.randint(4, 8)
    c["tail_pool"] = [(f"{rnd.choice(SURN)} {rnd.choice(['ApS', 'A/S', 'Holding', 'Byg', 'Service', 'IVS'])}", rnd.random() < .6)
                      for _ in range(n_pool)]
    c["pref_text"] = {}
    c["alt_acct"] = {}
    client_alt = rnd.random() < .20
    for k in vs:  # a few vendors are booked on different accounts by many clients; elsewhere it is rare
        p = .30 if k in INCONSISTENT else (.04 if client_alt else 0)
        if rnd.random() < p: c["alt_acct"][k] = VK[k][3] + rnd.choice([1, 2, 10, 100])
    c["mixed"] = rnd.random() < .5
    if t == "retail": c["settle_rate"] = rnd.uniform(52, 75)


def mfactor(t, m):
    if t == "retail": return {12: 1.12, 1: .94, 7: 1.04}.get(m, 1.0)
    if t == "trades": return {12: .94, 7: .94, 3: 1.03, 4: 1.03, 5: 1.03, 6: 1.03, 8: 1.03, 9: 1.03}.get(m, 1.0)
    return {12: 1.04, 1: 1.04}.get(m, 1.0)


def ntext(v, c):
    k = v[0]
    if k not in c["pref_text"]: c["pref_text"][k] = rnd.choice(v[7])
    tx = c["pref_text"][k] if rnd.random() < .6 else rnd.choice(v[7])
    return tx.replace("{n}", str(rnd.randint(1000, 99999)))


def amt(mean, sd=.35): return round(mean * math.exp(rnd.gauss(0, sd)), 2)


def generate():
    clients = build_clients()
    for c in clients: setup_client(c)
    rows = []
    for c in clients:
        t = c["client_type"]
        base = dict(client_id=c["client_id"], client_type=t, bookkeeper_id=c["bookkeeper_id"])
        for mi, (y, m) in enumerate(MONTHS):
            f = mfactor(t, m)
            def day(): return f"{y}-{m:02d}-{rnd.randint(1, 28):02d}"
            for k, freq in c["vendors"].items():
                v = VK[k]
                if freq == 1: n = 1
                elif freq == 1.5: n = rnd.choice([1, 2])
                else: n = max(0, round(rnd.gauss(freq * f, math.sqrt(freq) * .5)))
                sp = v[5]
                if v[2] in ("telephony", "fuel"): sp = "mixed_use" if c["mixed"] else ""
                for _ in range(n):
                    rows.append(dict(base, date=day(), bank_text=ntext(v, c), amount=-amt(v[6]), vendor_true=v[1],
                                     account=c["alt_acct"].get(k, v[3]), vat_code=v[4], special_vat=sp,
                                     vkey=k, kind="common", month_idx=mi))
            if c["rent"]:
                rows.append(dict(base, date=f"{y}-{m:02d}-01", bank_text=c["rent_text"], amount=-c["rent_amount"],
                                 vendor_true=f"Landlord {c['client_id']}", account=7000, vat_code="NONE", special_vat="",
                                 vkey="rent_" + c["client_id"], kind="rent", month_idx=mi))
            if t == "retail":
                for _ in range(round(c["settle_rate"] * f)):
                    tx = rnd.choice(["NETS SETTLEMENT {n}", "KORTAFREGNING {n}", "TEYA UDBETALING {n}", "DANKORT OMSAETN {n}", "CARD SETTL {n}"])
                    rows.append(dict(base, date=day(), bank_text=tx.replace("{n}", str(rnd.randint(1000, 99999))),
                                     amount=amt(1900, .6), vendor_true="Card settlement", account=1000, vat_code="U25",
                                     special_vat="", vkey="settle_" + c["client_id"], kind="settle", month_idx=mi))
            nt = max(0, round(rnd.gauss(c["tail_rate"] * f, math.sqrt(c["tail_rate"]) * .6)))
            for _ in range(nt):
                name, income = rnd.choice(c["tail_pool"])
                txt = (f"OVERF. FRA {name.upper()}" if income
                       else f"{rnd.choice(['BETALING', 'FI', 'OVERF. TIL'])} {name.upper()} {rnd.randint(100, 9999)}")
                rows.append(dict(base, date=day(), bank_text=txt,
                                 amount=amt(5200 if income else 2300, .8) * (1 if income else -1), vendor_true=name,
                                 account=1000 if income else rnd.choice([2100, 7300, 7310, 7500]),
                                 vat_code="U25" if income else "I25", special_vat="",
                                 vkey="tail_" + c["client_id"] + name, kind="tail", month_idx=mi))
    df = pd.DataFrame(rows).sort_values(["date", "client_id"], kind="stable").reset_index(drop=True)
    df["amount"] = df["amount"].round(2)
    return df, clients


VOUCHER_P = {"software": .6, "advertising": .6, "telephony": .5, "fuel": .5, "office": .7, "wholesale": .7,
             "postage": .5, "electricity": .6, "insurance": .5, "representation": .6, "leasing": .3,
             "bank_fee": 0, "card_fee": 0}


def assign_source(df):
    r = random.Random(SEED + 1)  # separate stream: leaves the posting data itself unchanged
    def p(row):
        if row.kind == "common": return VOUCHER_P[VK[row.vkey][2]]
        if row.kind == "rent": return .05
        if row.kind == "settle": return 0
        return .05 if row.amount > 0 else .3
    return ["voucher" if r.random() < p(row) else "bank" for row in df.itertuples()]


def assign_handling(df, clients):
    N = len(df)
    df["source"] = assign_source(df)
    cl_type = {c["client_id"]: c["client_type"] for c in clients}
    mix = {"retail": RULE_MIX["retail"], "small_service": RULE_MIX["small_service"], "trades": RULE_MIX["trades"]}
    rule_clients = []
    for t, n in mix.items():
        rule_clients += rnd.sample([c for c in cl_type if cl_type[c] == t], n)
    assert len(rule_clients) == N_RULE_CLIENTS
    # a rule = (client, vendor); eligible: common vendors without special VAT, rent, card settlement
    elig = df[df.client_id.isin(rule_clients) & df.kind.isin(["common", "rent", "settle"]) & (df.special_vat == "")]
    rules = elig[["client_id", "vkey"]].drop_duplicates()
    rules = rules[[rnd.random() < .85 for _ in range(len(rules))]].copy()
    rules["start"] = 0  # rules pre-date the window, so touches stay flat over time
    df = df.merge(rules, on=["client_id", "vkey"], how="left")
    df["covered"] = df["start"].notna() & (df["month_idx"] >= df["start"].fillna(99))
    per_rule = df[df.covered].groupby(["client_id", "vkey"]).size().sample(frac=1, random_state=SEED)
    # some rules send to the journal (human still posts, bank only); pick rules until rule_posted ~ 10 % of all postings
    bank_n = df[df.covered & (df.source == "bank")].groupby(["client_id", "vkey"]).size()
    j_target = len(df[df.covered]) - TARGET_RULE_POSTED * N
    journal_rules, acc = set(), 0
    for key in per_rule.index:  # per_rule is shuffled with the fixed seed
        n = int(bank_n.get(key, 0))
        if acc + n <= j_target:
            journal_rules.add(key); acc += n
    posted_rules = {k for k in per_rule.index if k not in journal_rules}
    in_posted = pd.Series([(a, b) in posted_rules for a, b in zip(df.client_id, df.vkey)], index=df.index)
    df["handling"] = ""
    df.loc[df.covered & in_posted, "handling"] = "rule_posted"
    # rule_to_journal exists only on bank postings; on vouchers a covered rule posts directly
    df.loc[df.covered & ~in_posted & (df.source == "bank"), "handling"] = "rule_to_journal"
    df.loc[df.covered & ~in_posted & (df.source == "voucher"), "handling"] = "rule_posted"
    # suggestions on the rest, scaled so total automation ~ 67 %
    rest = df.handling == ""
    w = df.kind.map({"common": .92, "rent": .85, "settle": .85, "tail": .5}).astype(float)
    w = w.where(df.special_vat == "", w * .65)
    w = w.where(df.client_type != "holding", w * .8)
    need = TARGET_AUTOMATED * N - (~rest).sum()
    lo, hi = 0.0, 3.0
    for _ in range(50):
        k = (lo + hi) / 2
        if (w[rest] * k).clip(upper=.98).sum() < need: lo = k
        else: hi = k
    p = (w * k).clip(upper=.98)
    draw = pd.Series([rnd.random() for _ in range(N)], index=df.index)
    df.loc[rest & (draw < p), "handling"] = "suggestion_accepted"
    df.loc[df.handling == "", "handling"] = "manual"
    df["touched"] = df.handling != "rule_posted"
    cp = df.handling.map({"suggestion_accepted": .03, "manual": .008, "rule_to_journal": .005, "rule_posted": .004})
    df["corrected_later"] = pd.Series([rnd.random() for _ in range(N)], index=df.index) < cp
    # humans are not perfectly consistent: ~2 % of human-booked, uncorrected postings sit on a neighbouring account
    r = random.Random(SEED + 2)
    noisy = df.touched & ~df.corrected_later & (df.kind != "tail") & pd.Series([r.random() < .02 for _ in range(N)], index=df.index)
    df.loc[noisy, "account"] = df.loc[noisy, "account"] + 1
    return df, rule_clients, rules


RULE_MIX = {"retail": 14, "small_service": 8, "trades": 5}

if __name__ == "__main__":
    df, clients = generate()
    df, rule_clients, rules = assign_handling(df, clients)
    df.insert(0, "posting_id", [f"P{i+1:06d}" for i in range(len(df))])
    cols = ["posting_id", "client_id", "client_type", "bookkeeper_id", "date", "source", "bank_text", "amount", "vendor_true",
            "account", "vat_code", "special_vat", "handling", "touched", "corrected_later"]
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    df[cols].to_csv(os.path.join(HERE, "data", "postings.csv"), index=False)

    N = len(df)
    print(f"rows: {N:,}  clients: {df.client_id.nunique()}  months: {df.month_idx.nunique()}")
    print("\nclients by type:\n", df.drop_duplicates("client_id").client_type.value_counts().to_string())
    hc = df.handling.value_counts()
    print("\nhandling:\n", pd.DataFrame({"n": hc, "share_%": (hc / N * 100).round(1)}).to_string())
    print(f"\nautomated to some degree: {(df.handling != 'manual').mean()*100:.1f} %")
    print(f"rule_posted: {(df.handling == 'rule_posted').mean()*100:.1f} %")
    print(f"clients with any rule (rule_posted/rule_to_journal): {df[df.handling.isin(['rule_posted','rule_to_journal'])].client_id.nunique()} / 180")
    print(f"clients with rule_posted: {df[df.handling == 'rule_posted'].client_id.nunique()}")
    sa = df[df.handling == "suggestion_accepted"]
    print(f"corrected_later: {df.corrected_later.mean()*100:.1f} % overall; of suggestion_accepted {sa.corrected_later.mean()*100:.1f} %")
    allc = df.groupby(["client_id", "month_idx"]).size().unstack(fill_value=0)
    tc = df[df.touched].groupby(["client_id", "month_idx"]).size().unstack(fill_value=0).reindex(allc.index, fill_value=0)
    pc = tc.mean(axis=1)
    print("\ntouches per client per month (avg over 12 months):")
    print(f"  mean {pc.mean():.1f}  median {pc.median():.1f}  min {pc.min():.1f}  p10 {pc.quantile(.1):.1f}  p90 {pc.quantile(.9):.1f}  max {pc.max():.1f}")
    ct = df.drop_duplicates("client_id").set_index("client_id").client_type
    print(pc.groupby(ct).agg(["mean", "min", "max"]).round(1).to_string())
    tb = df[df.touched].groupby(["bookkeeper_id", "month_idx"]).size().unstack(fill_value=0)
    print("\ntouches per bookkeeper per month:")
    print(pd.DataFrame({"mean/month": tb.mean(axis=1).round(0), "min": tb.min(axis=1), "max": tb.max(axis=1),
                        "per_client": (tb.mean(axis=1) / 30).round(1)}).to_string())
    print("\ntouches per client per month, by calendar month (mean over 180 clients):")
    ser = tc.mean(axis=0)
    print(pd.DataFrame({"month": [f"{y}-{m:02d}" for y, m in MONTHS], "mean": ser.round(1).values,
                        "p10": tc.quantile(.1).round(1).values, "p90": tc.quantile(.9).round(1).values}).to_string(index=False))
    print(f"  range of monthly mean: {ser.min():.1f} - {ser.max():.1f}  (max dev from avg {((ser-ser.mean()).abs().max()/ser.mean())*100:.1f} %)")
    print("\nsource x handling:\n", pd.crosstab(df.source, df.handling).to_string())
    print(f"total touches/month (office): {tb.sum().mean():.0f}")
