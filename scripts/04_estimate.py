"""Cross-sectional 2SLS: effect of party-system fractionalization on macroeconomic volatility.

Endogenous: frac (mean ENPP over democratic years; US uses IENP).
Instruments: British legal origin (legor_gbr) and terrain ruggedness (Nunn & Puga 2012).
All inference is heteroskedasticity-robust (HC1).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.iv import IV2SLS, IVLIML

ROOT = Path(__file__).resolve().parents[1]
PROC, TAB = ROOT / "data" / "processed", ROOT / "output" / "tables"
TAB.mkdir(parents=True, exist_ok=True)

BASE_X = ["log_gdppc_initial", "polyarchy_mean"]
EXT_X = BASE_X + ["dist_coast", "cont_europe", "cont_africa", "cont_asia", "americas"]
Z_MAIN = ["legor_gbr", "rugged"]
Z_LEGAL_FULL = ["legor_gbr", "legor_deu", "legor_sca", "legor_soc", "rugged"]
OUTCOMES = {"growth_sd": "SD of real GDP growth", "fiscal_sd": "SD of fiscal balance (% GDP)",
            "growth_mean": "Mean real GDP growth"}
US_VARIANTS = ["ienp_gap", "ienp_silhouette", "ienp_k3", "ienp_k4", "ienp_k5",
               "ienp_gmm_within_party", "ienp_caucus", "enpp_golder"]


def load(sample: str) -> pd.DataFrame:
    d = pd.read_csv(PROC / f"crosssection_{sample}.csv")
    d["americas"] = d.cont_north_america + d.cont_south_america
    return d


def prep(d, y, endog, z, x):
    cols = [y, endog] + z + x
    d = d.dropna(subset=cols)
    d = d.loc[:, ~d.columns.duplicated()]
    keep_x = [c for c in x if d[c].std() > 0]
    keep_z = [c for c in z if d[c].std() > 0]
    return d, keep_z, keep_x


def iv(d, y, endog="frac", z=Z_MAIN, x=BASE_X, est=IV2SLS):
    d, z, x = prep(d, y, endog, z, x)
    exog = sm.add_constant(d[x], has_constant="add")
    return est(d[y], exog, d[[endog]], d[z]).fit(cov_type="robust"), d, z, x


def ols(d, y, regs):
    d = d.dropna(subset=[y] + regs)
    return sm.OLS(d[y], sm.add_constant(d[regs])).fit(cov_type="HC1")


def anderson_rubin_ci(d, y, endog, z, x, grid=np.linspace(-6, 6, 2401), alpha=0.05):
    exog = sm.add_constant(d[z + x], has_constant="add")
    accepted = []
    for b in grid:
        r = sm.OLS(d[y] - b * d[endog], exog).fit(cov_type="HC1")
        if r.f_test(np.eye(len(exog.columns))[1:1 + len(z)]).pvalue > alpha:
            accepted.append(b)
    if not accepted:
        return "empty"
    lo, hi = min(accepted), max(accepted)
    contiguous = len(accepted) == int(round((hi - lo) / (grid[1] - grid[0]))) + 1
    edge = lo <= grid[0] or hi >= grid[-1]
    s = f"[{lo:.2f}, {hi:.2f}]"
    if edge:
        s += " (unbounded)"
    if not contiguous:
        s += " (disjoint)"
    return s


def summarize(label, res, d, z, x, y, endog="frac", ar=True):
    fs = res.first_stage.diagnostics.loc[endog]
    try:
        j = res.wooldridge_overid.pval if len(z) > 1 else np.nan
    except Exception:
        j = np.nan
    return {
        "spec": label,
        "N": int(res.nobs),
        "coef": res.params[endog],
        "se": res.std_errors[endog],
        "p": res.pvalues[endog],
        "ci_lo": res.conf_int().loc[endog, "lower"],
        "ci_hi": res.conf_int().loc[endog, "upper"],
        "first_stage_F": fs["f.stat"],
        "partial_R2": fs["partial.rsquared"],
        "overid_p": j,
        "AR_95CI": anderson_rubin_ci(d, y, endog, z, x) if ar else "",
    }


def main_table(d, sample):
    rows, fs_rows = [], []
    for y, ylab in OUTCOMES.items():
        o = ols(d.dropna(subset=Z_MAIN), y, ["frac"] + BASE_X)
        r2sls, dd, z, x = iv(d, y)
        rliml, *_ = iv(d, y, est=IVLIML)
        rf = ols(dd, y, z + x)
        fs = ols(dd, "frac", z + x)
        rows.append({
            "outcome": ylab, "N": int(r2sls.nobs),
            "OLS": o.params["frac"], "OLS_se": o.bse["frac"], "OLS_p": o.pvalues["frac"],
            "2SLS": r2sls.params["frac"], "2SLS_se": r2sls.std_errors["frac"], "2SLS_p": r2sls.pvalues["frac"],
            "LIML": rliml.params["frac"], "LIML_se": rliml.std_errors["frac"],
            "first_stage_F": r2sls.first_stage.diagnostics.loc["frac", "f.stat"],
            "overid_p": r2sls.wooldridge_overid.pval,
            "wu_hausman_p": r2sls.wu_hausman().pval,
            "AR_95CI": anderson_rubin_ci(dd, y, "frac", z, x),
            "RF_legor_gbr": rf.params["legor_gbr"], "RF_legor_gbr_p": rf.pvalues["legor_gbr"],
            "RF_rugged": rf.params["rugged"], "RF_rugged_p": rf.pvalues["rugged"],
        })
        if y == "growth_sd":
            for v in z + x:
                fs_rows.append({"regressor": v, "coef": fs.params[v], "se": fs.bse[v], "p": fs.pvalues[v]})
            fs_rows.append({"regressor": "R2", "coef": fs.rsquared, "se": np.nan, "p": np.nan})
    pd.DataFrame(rows).to_csv(TAB / f"main_{sample}.csv", index=False)
    pd.DataFrame(fs_rows).to_csv(TAB / f"first_stage_{sample}.csv", index=False)
    return pd.DataFrame(rows), pd.DataFrame(fs_rows)


def robustness(dv, dp, y="growth_sd"):
    specs = []

    def add(label, d, **kw):
        res, dd, z, x = iv(d, y, **kw)
        specs.append(summarize(label, res, dd, z, x, y, endog=kw.get("endog", "frac")))

    add("Baseline (V-Dem>0.7, legor_gbr+rugged, base controls)", dv)
    add("Sample: Polity2>6", dp)
    for v in US_VARIANTS:
        d = dv.copy()
        d.loc[d.iso3 == "USA", "frac"] = d.loc[d.iso3 == "USA", v]
        add(f"US measure: {v}", d)
    add("Drop USA", dv[dv.iso3 != "USA"])
    add("log(frac)", dv, endog="log_frac")
    add("Drop frac > 6 (Brazil, Belgium, Ecuador)", dv[dv.frac <= 6])
    add("Instrument: legor_gbr only", dv, z=["legor_gbr"])
    add("Instrument: rugged only", dv, z=["rugged"])
    add("Instruments: all legal origins + rugged", dv, z=Z_LEGAL_FULL)
    add("Controls: none", dv, x=[])
    add("Controls: extended (+dist_coast, continents)", dv, x=EXT_X)
    add("Polity2>6, extended controls", dp, x=EXT_X)
    add("LIML estimator", dv, est=IVLIML)
    out = pd.DataFrame(specs)
    out.to_csv(TAB / f"robustness_{y}.csv", index=False)
    return out


def conley_bounds(d, y="growth_sd", deltas=(0.0, 0.25, 0.5, 1.0)):
    """Union-of-CI bounds (Conley, Hansen & Rossi 2012) allowing legor_gbr a direct effect |delta|."""
    rows = []
    for dmax in deltas:
        lo, hi = np.inf, -np.inf
        for delta in np.linspace(-dmax, dmax, 21) if dmax > 0 else [0.0]:
            dd = d.copy()
            dd[y] = dd[y] - delta * dd.legor_gbr
            res, *_ = iv(dd, y)
            ci = res.conf_int().loc["frac"]
            lo, hi = min(lo, ci["lower"]), max(hi, ci["upper"])
        rows.append({"max_direct_effect_of_legor_gbr": dmax, "ci_lo": lo, "ci_hi": hi,
                     "excludes_zero": lo > 0 or hi < 0})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / f"conley_bounds_{y}.csv", index=False)
    return out


def leave_one_out(d, y="growth_sd"):
    rows = []
    base, dd, *_ = iv(d, y)
    for iso in dd.iso3:
        r, *_ = iv(d[d.iso3 != iso], y)
        rows.append({"dropped": iso, "coef": r.params["frac"], "p": r.pvalues["frac"],
                     "first_stage_F": r.first_stage.diagnostics.loc["frac", "f.stat"]})
    out = pd.DataFrame(rows).sort_values("coef")
    out.to_csv(TAB / f"leave_one_out_{y}.csv", index=False)
    return base.params["frac"], out


def exclusion_diagnostics(d):
    """Do the instruments predict other plausible channels to volatility? (They should not, ideally.)"""
    rows = []
    for v, lab in [("q_rule_law", "Rule of law (2000)"), ("log_gdppc_initial", "log initial GDP pc"),
                   ("european_descent", "% European descent"), ("polyarchy_mean", "Mean V-Dem polyarchy"),
                   ("dist_coast", "Distance to coast")]:
        r = ols(d, v, Z_MAIN)
        rows.append({"dependent": lab, "N": int(r.nobs),
                     "legor_gbr": r.params["legor_gbr"], "legor_gbr_p": r.pvalues["legor_gbr"],
                     "rugged": r.params["rugged"], "rugged_p": r.pvalues["rugged"],
                     "joint_p": r.f_test("legor_gbr = 0, rugged = 0").pvalue})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "exclusion_diagnostics.csv", index=False)
    return out


def us_measure_validation():
    us = pd.read_csv(PROC / "us_ienp_by_congress.csv")
    cols = ["enpp_nominal", "ienp_gap", "ienp_silhouette", "ienp_k3", "ienp_k4", "ienp_k5",
            "ienp_gmm_within_party", "ienp_caucus"]
    summary = us[us.year_start.between(1961, 2016)][cols].agg(["mean", "min", "max", "std"]).T
    summary.to_csv(TAB / "us_ienp_summary.csv")
    corr = us[us.ienp_caucus.notna() & (us.year_start <= 2016)][cols].corr()
    corr.to_csv(TAB / "us_ienp_correlations_104_114.csv")
    return summary, corr


def main():
    pd.set_option("display.width", 250)
    dv, dp = load("vdem"), load("polity")
    for s, d in [("vdem", dv), ("polity", dp)]:
        m, fs = main_table(d, s)
        print(f"\n=== MAIN ({s}) ===\n{m.round(3).to_string()}\n--- first stage ({s}) ---\n{fs.round(3).to_string()}")
    print("\n=== ROBUSTNESS growth_sd ===\n" + robustness(dv, dp).round(3).to_string())
    print("\n=== ROBUSTNESS fiscal_sd ===\n" + robustness(dv, dp, y="fiscal_sd").round(3).to_string())
    print("\n=== CONLEY BOUNDS ===\n" + conley_bounds(dv).round(3).to_string())
    for y in ["growth_sd", "fiscal_sd"]:
        b, loo = leave_one_out(dv, y)
        print(f"\n=== LEAVE-ONE-OUT {y} (baseline {b:.3f}) ===")
        print(f"coef range [{loo.coef.min():.3f}, {loo.coef.max():.3f}]; share p<0.05: {(loo.p < 0.05).mean():.2f}")
        print(pd.concat([loo.head(3), loo.tail(3)]).round(3).to_string())
    print("\n=== EXCLUSION DIAGNOSTICS ===\n" + exclusion_diagnostics(dv).round(3).to_string())
    s, c = us_measure_validation()
    print("\n=== US IENP 1961-2016 ===\n" + s.round(2).to_string())
    print("\n=== US IENP correlations (Congress 104-114) ===\n" + c.round(2).to_string())


if __name__ == "__main__":
    main()
