"""Design H (pre_analysis_plan_part4.md): candidate selection -> party cohesion (V-Party), and
governing-party cohesion -> fiscal change."""
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadr
import statsmodels.formula.api as smf
from linearmodels.iv.absorbing import AbsorbingLS

from eventlib import load_country_year

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, TAB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables"
COLS = ["v2paid", "country_text_id", "year", "v2paenname", "v2padisa", "v2panom", "v2paind",
        "v2pagovsup", "v2paseatshare"]


def load_vparty() -> pd.DataFrame:
    v = pyreadr.read_r(str(RAW / "vparty.RData"))["vparty"][COLS].rename(columns={"country_text_id": "iso3"})
    v = v.dropna(subset=["v2paid", "year"]).sort_values(["v2paid", "year"])
    v["year"] = v.year.astype(int)
    g = v.groupby("v2paid")
    v["nom_lag"] = g.v2panom.shift()
    v["ind_lag"] = g.v2paind.shift()
    v["country_year"] = v.iso3 + "_" + v.year.astype(str)
    return v


def validate(v: pd.DataFrame) -> pd.DataFrame:
    rows = []
    us = v[(v.iso3 == "USA") & v.v2paenname.isin(["Democratic Party", "Republican Party"])].copy()
    us["party"] = np.where(us.v2paenname == "Democratic Party", "D", "R")
    us["congress"] = (us.year - 1788) // 2 + 1
    pc = pd.read_csv(PROC / "us_house_party_congress.csv")
    d = us.merge(pc, on=["congress", "party"]).dropna(subset=["v2padisa", "defection_rate"])
    r = np.corrcoef(d.v2padisa, d.defection_rate)[0, 1]
    rows.append({"check": "US parties: v2padisa vs House defection rate", "N": len(d), "r": r,
                 "threshold": "<= -0.5", "passed": bool(r <= -0.5),
                 "within_party_sd_v2padisa": d.groupby("party").v2padisa.std().mean()})
    w = v.dropna(subset=["v2padisa", "v2paseatshare"])
    w = w[w.v2paseatshare > 0]
    cw = w.groupby(["iso3", "year"]).apply(
        lambda x: np.average(x.v2padisa, weights=x.v2paseatshare), include_groups=False).rename("cohesion_sw").reset_index()
    vd = pd.read_csv(RAW / "vdem_cohesion.csv").rename(columns={"country_text_id": "iso3"})
    m = cw.merge(vd[["iso3", "year", "v2pscohesv"]], on=["iso3", "year"]).dropna()
    r2 = np.corrcoef(m.cohesion_sw, m.v2pscohesv)[0, 1]
    rows.append({"check": "Seat-weighted v2padisa vs V-Dem v2pscohesv (country-election)", "N": len(m), "r": r2,
                 "threshold": ">= 0.5", "passed": bool(r2 >= 0.5), "within_party_sd_v2padisa": np.nan})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "vparty_validation.csv", index=False)
    return out


def absorbing(d: pd.DataFrame, y: str, x: list[str]):
    d = d.dropna(subset=[y] + x).copy()
    d = d[d.groupby("v2paid").v2paid.transform("size") > 1]
    d = d[d.groupby("country_year").country_year.transform("size") > 1]
    absorb = pd.DataFrame({"party": d.v2paid.astype("category"), "cy": d.country_year.astype("category")})
    m = AbsorbingLS(d[y], d[x], absorb=absorb).fit(cov_type="clustered", clusters=d.v2paid.astype(int))
    return m, d


def party_models(v: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tag, x, desc in [("H1", ["nom_lag"], "lagged nomination inclusiveness"),
                         ("H1b", ["v2panom"], "contemporaneous nomination inclusiveness"),
                         ("H2", ["ind_lag"], "lagged personalization")]:
        m, d = absorbing(v, "v2padisa", x)
        rows.append({"test": tag, "regressor": desc, "N": int(m.nobs), "parties": d.v2paid.nunique(),
                     "coef": m.params[x[0]], "se": m.std_errors[x[0]], "p": m.pvalues[x[0]],
                     "t_squared_F": float((m.params[x[0]] / m.std_errors[x[0]]) ** 2),
                     "coef_per_sd": m.params[x[0]] * d[x[0]].std(), "sd_outcome": d.v2padisa.std()})
    m, d = absorbing(v, "v2padisa", ["nom_lag", "ind_lag"])
    for x in ["nom_lag", "ind_lag"]:
        rows.append({"test": "H1+H2 joint", "regressor": x, "N": int(m.nobs), "parties": d.v2paid.nunique(),
                     "coef": m.params[x], "se": m.std_errors[x], "p": m.pvalues[x]})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "vparty_party_models.csv", index=False)
    return out


def governing_panel(v: pd.DataFrame) -> pd.DataFrame:
    gov = v[v.v2pagovsup.isin([0, 1]) & (v.v2paseatshare > 0)].dropna(subset=["v2padisa"])
    agg = gov.groupby(["iso3", "year"]).apply(lambda x: pd.Series({
        "gov_cohesion": np.average(x.v2padisa, weights=x.v2paseatshare),
        "gov_nom": np.average(x.v2panom.fillna(x.v2panom.mean()), weights=x.v2paseatshare)
        if x.v2panom.notna().any() else np.nan,
        "gov_parties": len(x)}), include_groups=False).reset_index().rename(columns={"year": "election_year"})
    rows = []
    for iso, g in agg.sort_values("election_year").groupby("iso3"):
        ys = list(g.election_year) + [2020]
        for i, r in enumerate(g.itertuples()):
            for y in range(r.election_year + 1, min(ys[i + 1], 2020) + 1):
                rows.append({"iso3": iso, "year": y, "gov_cohesion": r.gov_cohesion, "gov_nom": r.gov_nom,
                             "gov_parties": r.gov_parties})
    return pd.DataFrame(rows)


def fiscal_models(v: pd.DataFrame, first_stage_F: float) -> pd.DataFrame:
    panel = load_country_year(1980, 2019)
    d = panel.merge(governing_panel(v), on=["iso3", "year"], how="inner")
    d = d[(d.polyarchy > 0.5) & d.year.between(1980, 2019)].dropna(subset=["abs_dfiscal", "gov_cohesion"])
    d.to_csv(PROC / "vparty_governing_panel.csv", index=False)
    rows = []
    m = smf.ols("abs_dfiscal ~ gov_cohesion + C(iso3) + C(year)", d).fit(
        cov_type="cluster", cov_kwds={"groups": d.iso3})
    rows.append({"test": "H3", "model": "TWFE |Δ fiscal| ~ governing-party cohesion", "N": int(m.nobs),
                 "countries": d.iso3.nunique(), "coef": m.params["gov_cohesion"], "se": m.bse["gov_cohesion"],
                 "p": m.pvalues["gov_cohesion"], "coef_per_sd": m.params["gov_cohesion"] * d.gov_cohesion.std(),
                 "outcome_mean": d.abs_dfiscal.mean()})
    for y in ["abs_dgrowth", "sd5_fiscal"]:
        dd = d.dropna(subset=[y])
        m2 = smf.ols(f"{y} ~ gov_cohesion + C(iso3) + C(year)", dd).fit(cov_type="cluster", cov_kwds={"groups": dd.iso3})
        rows.append({"test": "H3-sec", "model": f"TWFE {y} ~ governing-party cohesion", "N": int(m2.nobs),
                     "countries": dd.iso3.nunique(), "coef": m2.params["gov_cohesion"], "se": m2.bse["gov_cohesion"],
                     "p": m2.pvalues["gov_cohesion"]})
    if first_stage_F > 10:
        from linearmodels.iv import IV2SLS
        dd = d.dropna(subset=["gov_nom"])
        fe = pd.get_dummies(dd[["iso3", "year"]].astype(str), drop_first=True).astype(float)
        fe.insert(0, "const", 1.0)
        r = IV2SLS(dd.abs_dfiscal, fe, dd[["gov_cohesion"]], dd[["gov_nom"]]).fit(
            cov_type="clustered", clusters=dd.iso3)
        rows.append({"test": "H3-IV", "model": "2SLS, instrument governing-party nomination inclusiveness",
                     "N": int(r.nobs), "countries": dd.iso3.nunique(), "coef": r.params["gov_cohesion"],
                     "se": r.std_errors["gov_cohesion"], "p": r.pvalues["gov_cohesion"],
                     "first_stage_F": r.first_stage.diagnostics.loc["gov_cohesion", "f.stat"]})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "vparty_fiscal_models.csv", index=False)
    return out


def main():
    pd.set_option("display.width", 220)
    v = load_vparty()
    print("=== Validation ===\n" + validate(v).round(3).to_string())
    pm = party_models(v)
    print("\n=== Party-level models (outcome v2padisa, higher = more cohesive) ===\n" + pm.round(4).to_string())
    F = float(pm.loc[pm.test == "H1", "t_squared_F"].iloc[0])
    print("\n=== Governing-party cohesion and fiscal change ===\n" + fiscal_models(v, F).round(4).to_string())


if __name__ == "__main__":
    main()
