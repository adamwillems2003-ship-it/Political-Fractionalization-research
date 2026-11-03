"""Design B (pre_analysis_plan.md).

B1: top-two primaries (WA from the 111th Congress, CA from the 113th) and House party-unity defections.
B2: primary openness (McGhee et al. 2014 coding) and within-party ideological SD in state legislatures
    (Shor-McCarty), a measure validated against roll-call defections in scripts/06_build_defections.py.
"""
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, TAB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables"
CONGRESS_MIN, CONGRESS_MAX = 105, 117
TREATED = {"WA": 111, "CA": 113}
EXCLUDE = ["LA"]
EVENT_BINS = range(-4, 5)
OPENNESS = {"closed": 0, "semicl": 1, "semiop": 2, "open": 3, "blanket": 4, "ttvg": 4, "nonpart": 4}


def b1_panel() -> pd.DataFrame:
    d = pd.read_csv(PROC / "us_house_defections_member.csv")
    d = d[d.congress.between(CONGRESS_MIN, CONGRESS_MAX) & ~d.state_abbrev.isin(EXCLUDE)].copy()
    d["extremity"] = d.nokken_poole_dim1.abs()
    d["party_congress"] = d.party + "_" + d.congress.astype(str)
    for st, c0 in TREATED.items():
        d[f"post_{st}"] = ((d.state_abbrev == st) & (d.congress >= c0)).astype(int)
    d["post_any"] = d[[f"post_{s}" for s in TREATED]].max(axis=1)
    return d


def cluster_fit(formula, d):
    return smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": d.state_abbrev})


def fe_residualizer(d: pd.DataFrame, fe_cols: list[str]):
    X = np.column_stack([pd.get_dummies(d[c], drop_first=(i > 0)).to_numpy(float) for i, c in enumerate(fe_cols)])
    Q, _ = np.linalg.qr(X)
    return lambda v: v - Q @ (Q.T @ v)


def b1_randomization(d: pd.DataFrame, y: str, unit_fe: str = "state_abbrev") -> tuple[float, float, int]:
    """Assign the WA and CA treatment timings to every ordered pair of never-treated states."""
    resid = fe_residualizer(d, [unit_fe, "party_congress"])
    yr = resid(d[y].to_numpy(float))

    def beta(post):
        x = resid(post.astype(float))
        return float(x @ yr / (x @ x))

    actual = beta(d.post_any.to_numpy())
    controls = sorted(set(d.state_abbrev) - set(TREATED))
    st, cg = d.state_abbrev.to_numpy(), d.congress.to_numpy()
    draws = []
    for a, b in permutations(controls, 2):
        post = ((st == a) & (cg >= TREATED["WA"])) | ((st == b) & (cg >= TREATED["CA"]))
        draws.append(beta(post))
    draws = np.array(draws)
    return actual, float(np.mean(np.abs(draws) >= abs(actual))), len(draws)


def b1(d: pd.DataFrame):
    rows = []
    for y in ["defection_rate", "extremity"]:
        dd = d.dropna(subset=[y])
        m_sep = cluster_fit(f"{y} ~ post_WA + post_CA + C(state_abbrev) + C(party_congress)", dd)
        m_pool = cluster_fit(f"{y} ~ post_any + C(state_abbrev) + C(party_congress)", dd)
        m_mem = cluster_fit(f"{y} ~ post_any + C(icpsr) + C(party_congress)", dd)
        ri = {"Pooled (state FE)": b1_randomization(dd, y),
              "Pooled (member FE)": b1_randomization(dd, y, unit_fe="icpsr")}
        for lab, m, v in [("WA (state FE)", m_sep, "post_WA"), ("CA (state FE)", m_sep, "post_CA"),
                          ("Pooled (state FE)", m_pool, "post_any"), ("Pooled (member FE)", m_mem, "post_any")]:
            rows.append({"outcome": y, "spec": lab, "N": int(m.nobs), "coef": m.params[v], "se": m.bse[v],
                         "p_cluster": m.pvalues[v],
                         "RI_p": ri[lab][1] if lab in ri else np.nan,
                         "RI_draws": ri[lab][2] if lab in ri else np.nan,
                         "outcome_mean": dd[y].mean()})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "us_toptwo_did.csv", index=False)

    es = []
    for st, c0 in TREATED.items():
        dd = d[(d.state_abbrev == st) | (~d.state_abbrev.isin(TREATED))].copy()
        rel = (dd.congress - c0).clip(min(EVENT_BINS), max(EVENT_BINS))
        names = []
        for k in EVENT_BINS:
            if k == -1:
                continue
            nm = f"ev_m{abs(k)}" if k < 0 else f"ev_p{k}"
            dd[nm] = ((dd.state_abbrev == st) & (rel == k)).astype(int)
            names.append((k, nm))
        m = cluster_fit("defection_rate ~ " + " + ".join(n for _, n in names) +
                        " + C(state_abbrev) + C(party_congress)", dd)
        for k, nm in names:
            es.append({"state": st, "rel_congress": k, "coef": m.params[nm], "se": m.bse[nm]})
        es.append({"state": st, "rel_congress": -1, "coef": 0.0, "se": 0.0})
    es = pd.DataFrame(es).sort_values(["state", "rel_congress"])
    es.to_csv(TAB / "us_toptwo_event_study.csv", index=False)
    return out, es


def b2_panel() -> pd.DataFrame:
    m = pd.concat([pd.read_csv(RAW / "statleg" / "mcghee_dem.csv").assign(party="D"),
                   pd.read_csv(RAW / "statleg" / "mcghee_rep.csv").assign(party="R")])
    types = list(OPENNESS)
    g = m.groupby(["icpsrst", "party", "elec"])[types + ["openall"]].mean().reset_index()
    g["openness"] = g[types].mul(pd.Series(OPENNESS)).max(axis=1)
    g["openall"] = (g.openall > 0.5).astype(int)

    a = pd.read_stata(RAW / "statleg" / "shor_mccarty_aggregate.tab")
    a = a[a.year.between(1993, 2011)]
    long = []
    for party, h, s in [("D", "h_dem_sd", "s_dem_sd"), ("R", "h_rep_sd", "s_rep_sd")]:
        x = a[["st", "icpsr", "year", h, s]].rename(columns={h: "within_sd_house", s: "within_sd_senate"})
        long.append(x.assign(party=party))
    a = pd.concat(long)
    a["icpsr"] = a.icpsr.astype("int64")
    a["lookup_year"] = (a.year - 1).astype("int64")
    a = a.sort_values("lookup_year")
    g = g.rename(columns={"icpsrst": "icpsr", "elec": "lookup_year"})
    g[["icpsr", "lookup_year"]] = g[["icpsr", "lookup_year"]].astype("int64")
    g = g.sort_values("lookup_year")
    d = pd.merge_asof(a, g, on="lookup_year", by=["icpsr", "party"], direction="backward", tolerance=4)
    d = d.dropna(subset=["openness"])
    d["state_party"] = d.st + "_" + d.party
    d["party_year"] = d.party + "_" + d.year.astype(int).astype(str)
    return d


def b2_randomization(d: pd.DataFrame, y: str, x: str, n_draws=2000, seed=20261102) -> float:
    """Move each switcher's within-unit treatment changes onto a random non-switching state-party."""
    resid = fe_residualizer(d, ["state_party", "party_year"])
    yr = resid(d[y].to_numpy(float))
    beta = lambda v: float(resid(v) @ yr / (resid(v) @ resid(v)))
    actual = beta(d[x].to_numpy(float))
    first = d.groupby("state_party")[x].transform("first")
    change = (d[x] - first)
    sw = [u for u, g in change.groupby(d.state_party) if g.abs().sum() > 0]
    non = [u for u in d.state_party.unique() if u not in sw]
    by_unit_year = {u: dict(zip(d.year[d.state_party == u], change[d.state_party == u])) for u in sw}
    rng = np.random.default_rng(seed)
    units, years = d.state_party.to_numpy(), d.year.to_numpy()
    draws = []
    for _ in range(n_draws):
        targets = rng.choice(non, size=len(sw), replace=False)
        v = np.zeros(len(d))
        for src, tgt in zip(sw, targets):
            m = units == tgt
            v[m] = [by_unit_year[src].get(yy, 0.0) for yy in years[m]]
        draws.append(beta(v))
    return float(np.mean(np.abs(draws) >= abs(actual)))


def b2(d: pd.DataFrame):
    rows = []
    switchers = d.groupby("state_party").openness.nunique()
    n_switch = int((switchers > 1).sum())
    for y in ["within_sd_house", "within_sd_senate"]:
        for x in ["openness", "openall"]:
            dd = d.dropna(subset=[y]).reset_index(drop=True)
            m = smf.ols(f"{y} ~ {x} + C(state_party) + C(party_year)", data=dd).fit(
                cov_type="cluster", cov_kwds={"groups": dd.st})
            rows.append({"outcome": y, "treatment": x, "N": int(m.nobs), "coef": m.params[x],
                         "se": m.bse[x], "p_cluster": m.pvalues[x], "RI_p": b2_randomization(dd, y, x),
                         "outcome_mean": dd[y].mean(), "outcome_sd": dd[y].std(),
                         "switching_state_parties": int((dd.groupby("state_party")[x].nunique() > 1).sum())})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "state_legislature_primaries.csv", index=False)
    sw = d[d.state_party.isin(switchers[switchers > 1].index)].groupby("state_party").agg(
        first=("openness", "first"), last=("openness", "last"), years=("year", "nunique"))
    sw.to_csv(TAB / "state_legislature_switchers.csv")
    return out, sw


def main():
    pd.set_option("display.width", 220)
    d = b1_panel()
    d.to_csv(PROC / "us_toptwo_panel.csv", index=False)
    out, es = b1(d)
    print("=== B1 top-two DiD ===\n" + out.round(4).to_string())
    print("\n=== B1 event study (defection rate) ===\n" + es.round(4).to_string())
    pre = d[d.congress < 111].groupby(d.state_abbrev.isin(TREATED)).defection_rate.mean()
    print("\nPre-period mean defection (treated states vs others):\n" + pre.round(4).to_string())
    s = b2_panel()
    s.to_csv(PROC / "state_legislature_panel.csv", index=False)
    o2, sw = b2(s)
    print("\n=== B2 state legislatures ===\n" + o2.round(4).to_string())
    print("\nSwitchers:\n" + sw.to_string())


if __name__ == "__main__":
    main()
