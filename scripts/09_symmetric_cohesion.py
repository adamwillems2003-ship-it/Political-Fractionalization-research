"""Design C (pre_analysis_plan.md): one intra-party measure for every country (V-Dem v2pscohesv),
no US-specific harmonization; plus Holm adjustment across the 7 pre-registered primary tests."""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.iv import IV2SLS

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, TAB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables"
BASE_X = ["log_gdppc_initial", "polyarchy_mean"]
Z = ["legor_gbr", "rugged"]
SAMPLES = {"vdem": lambda d: d.vdem_polyarchy > 0.7, "polity": lambda d: d.p_polity2 > 6}


def add_incohesion(sample: str) -> pd.DataFrame:
    q = pd.read_csv(RAW / "qog_std_ts_jan24.csv", usecols=["ccodealp", "year", "vdem_polyarchy", "p_polity2"],
                    low_memory=False).rename(columns={"ccodealp": "iso3"})
    q = q[q.year.between(1961, 2016)]
    q = q[SAMPLES[sample](q)]
    vd = pd.read_csv(RAW / "vdem_cohesion.csv").rename(columns={"country_text_id": "iso3"})
    q = q.merge(vd[["iso3", "year", "v2pscohesv"]], on=["iso3", "year"], how="left")
    inc = (-q.groupby("iso3").v2pscohesv.mean()).rename("incohesion")
    cs = pd.read_csv(PROC / f"crosssection_{sample}.csv").merge(inc, on="iso3", how="left")
    cs["frac"] = cs.enpp_golder
    return cs


def ols(d, y, regs):
    d = d.dropna(subset=[y] + regs)
    return sm.OLS(d[y], sm.add_constant(d[regs])).fit(cov_type="HC1")


def iv(d, y, endog, x):
    d = d.dropna(subset=[y, endog] + Z + x)
    r = IV2SLS(d[y], sm.add_constant(d[x]), d[[endog]], d[Z]).fit(cov_type="robust")
    return r


def c1():
    rows = []
    for s in SAMPLES:
        d = add_incohesion(s)
        d.to_csv(PROC / f"crosssection_{s}_cohesion.csv", index=False)
        for y in ["growth_sd", "fiscal_sd"]:
            o = ols(d, y, ["frac", "incohesion"] + BASE_X)
            for v in ["incohesion", "frac"]:
                rows.append({"sample": s, "outcome": y, "model": f"OLS ({v}; both in)", "N": int(o.nobs),
                             "coef": o.params[v], "se": o.bse[v], "p": o.pvalues[v], "first_stage_F": np.nan})
            r = iv(d, y, "frac", BASE_X + ["incohesion"])
            rows.append({"sample": s, "outcome": y, "model": "2SLS frac, controlling incohesion",
                         "N": int(r.nobs), "coef": r.params["frac"], "se": r.std_errors["frac"],
                         "p": r.pvalues["frac"],
                         "first_stage_F": r.first_stage.diagnostics.loc["frac", "f.stat"]})
            r = iv(d, y, "incohesion", BASE_X + ["frac"])
            rows.append({"sample": s, "outcome": y, "model": "2SLS incohesion, controlling frac",
                         "N": int(r.nobs), "coef": r.params["incohesion"], "se": r.std_errors["incohesion"],
                         "p": r.pvalues["incohesion"],
                         "first_stage_F": r.first_stage.diagnostics.loc["incohesion", "f.stat"]})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "symmetric_cohesion_crosssection.csv", index=False)
    dv = add_incohesion("vdem")
    corr = dv[["frac", "incohesion", "growth_sd", "fiscal_sd"]].corr()
    us_rank = dv.incohesion.rank(pct=True)[dv.iso3 == "USA"].iloc[0]
    return out, corr, us_rank


def holm(pvals: pd.Series) -> pd.Series:
    order = pvals.sort_values()
    m = len(order)
    adj = np.maximum.accumulate([(m - i) * p for i, p in enumerate(order)])
    return pd.Series(np.minimum(adj, 1.0), index=order.index).reindex(pvals.index)


def hypothesis_family(c1_out: pd.DataFrame) -> pd.DataFrame:
    a = pd.read_csv(TAB / "reform_stacked_2sls.csv").set_index("outcome")
    b1 = pd.read_csv(TAB / "us_toptwo_did.csv")
    b1 = b1[(b1.outcome == "defection_rate") & (b1.spec == "Pooled (state FE)")].iloc[0]
    b2 = pd.read_csv(TAB / "state_legislature_primaries.csv")
    b2 = b2[(b2.outcome == "within_sd_house") & (b2.treatment == "openness")].iloc[0]
    c = c1_out[c1_out["sample"] == "vdem"].set_index(["outcome", "model"])
    rows = [
        ("A1", "Reform 2SLS: ENPP → |Δ growth|", a.loc["abs_dgrowth", "coef_per_party"],
         a.loc["abs_dgrowth", "p_cluster"], a.loc["abs_dgrowth", "RI_p"]),
        ("A2", "Reform 2SLS: ENPP → |Δ fiscal|", a.loc["abs_dfiscal", "coef_per_party"],
         a.loc["abs_dfiscal", "p_cluster"], a.loc["abs_dfiscal", "RI_p"]),
        ("B1", "Top-two → House defection rate", b1.coef, b1.p_cluster, b1.RI_p),
        ("B2", "Primary openness → within-party SD (lower ch.)", b2.coef, b2.p_cluster, b2.RI_p),
        ("C1a", "Incohesion → growth SD (OLS)", c.loc[("growth_sd", "OLS (incohesion; both in)"), "coef"],
         c.loc[("growth_sd", "OLS (incohesion; both in)"), "p"], np.nan),
        ("C1b", "Incohesion → fiscal SD (OLS)", c.loc[("fiscal_sd", "OLS (incohesion; both in)"), "coef"],
         c.loc[("fiscal_sd", "OLS (incohesion; both in)"), "p"], np.nan),
        ("C1c", "ENPP → growth SD, 2SLS | incohesion",
         c.loc[("growth_sd", "2SLS frac, controlling incohesion"), "coef"],
         c.loc[("growth_sd", "2SLS frac, controlling incohesion"), "p"], np.nan),
    ]
    f = pd.DataFrame(rows, columns=["test", "hypothesis", "estimate", "p_as_registered", "p_randomization"])
    f["p_best_valid"] = f.p_randomization.fillna(f.p_as_registered)
    f["holm_as_registered"] = holm(f.p_as_registered)
    f["holm_best_valid"] = holm(f.p_best_valid)
    f.to_csv(TAB / "primary_hypotheses_holm.csv", index=False)
    return f


def main():
    pd.set_option("display.width", 220)
    out, corr, us_rank = c1()
    print("=== C1 cross-section ===\n" + out.round(4).to_string())
    print("\nCorrelations (vdem):\n" + corr.round(2).to_string())
    print(f"\nUS incohesion percentile among V-Dem-sample democracies: {us_rank:.2f}")
    did = pd.read_csv(TAB / "reform_did_by_event.csv")
    print("\n=== C2 reform effect on incohesion ===\n" +
          did[did.variable == "incohesion"].round(3).to_string())
    print("\n=== Primary hypothesis family (Holm) ===\n" + hypothesis_family(out).round(4).to_string())


if __name__ == "__main__":
    main()
