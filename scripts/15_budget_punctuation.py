"""Design G (pre_analysis_plan_part4.md): veto players and budget punctuation (COFOG)."""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from eventlib import load_country_year

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, TAB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables"
FUNCS = ["def", "ecaf", "educ", "envr", "gps", "hca", "heal", "pos", "rcr", "sp"]
MIN_SHARE, MAX_ABS_G, LARGE = 0.5, 2.0, 0.25
MIN_LK_OBS = 30


def l_kurtosis(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, float))
    n = len(x)
    i = np.arange(1, n + 1)
    b0 = x.mean()
    b1 = np.sum((i - 1) / (n - 1) * x) / n
    b2 = np.sum((i - 1) * (i - 2) / ((n - 1) * (n - 2)) * x) / n
    b3 = np.sum((i - 1) * (i - 2) * (i - 3) / ((n - 1) * (n - 2) * (n - 3)) * x) / n
    l2 = 2 * b1 - b0
    l4 = 20 * b3 - 30 * b2 + 12 * b1 - b0
    return l4 / l2 if l2 > 0 else np.nan


def expenditure() -> pd.DataFrame:
    fpp = pd.read_csv(RAW / "imf_exp.csv").rename(columns={"value": "exp_fpp"})
    fm = pd.read_csv(RAW / "imf_G_X_G01_GDP_PT.csv").rename(columns={"value": "exp_fm"})
    e = fpp.merge(fm, on=["iso3", "year"], how="outer")
    e["exp_gdp"] = e.exp_fpp.fillna(e.exp_fm)
    return e[["iso3", "year", "exp_gdp"]]


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    q = pd.read_csv(RAW / "qog_std_ts_jan24.csv", low_memory=False,
                    usecols=["ccodealp", "year"] + [f"gfs_{f}" for f in FUNCS]).rename(columns={"ccodealp": "iso3"})
    q = q.dropna(subset=[f"gfs_{f}" for f in FUNCS], how="all").merge(expenditure(), on=["iso3", "year"], how="left")
    panel = load_country_year(1970, 2022)
    q = q.merge(panel[["iso3", "year", "growth", "h_polcon3", "incohesion", "polyarchy", "abs_dfiscal"]],
                on=["iso3", "year"], how="left").sort_values(["iso3", "year"])
    shares = q[[f"gfs_{f}" for f in FUNCS]]
    q["share_sum"] = shares.sum(axis=1, min_count=len(FUNCS))
    prev = q.groupby("iso3")[[f"gfs_{f}" for f in FUNCS] + ["exp_gdp", "year", "share_sum"]].shift()
    consecutive = prev.year == q.year - 1
    ok_sum = q.share_sum.between(95, 105) & prev.share_sum.between(95, 105)
    q["comp_dist"] = np.where(consecutive & ok_sum,
                              np.sqrt(((shares.to_numpy() - prev[[f"gfs_{f}" for f in FUNCS]].to_numpy()) ** 2).sum(1)),
                              np.nan)
    long = []
    for f in FUNCS:
        s, sp = q[f"gfs_{f}"], prev[f"gfs_{f}"]
        g = np.log(s / sp) + np.log(q.exp_gdp / prev.exp_gdp) + np.log1p(q.growth / 100)
        valid = consecutive & (s >= MIN_SHARE) & (sp >= MIN_SHARE)
        long.append(pd.DataFrame({"iso3": q.iso3, "year": q.year, "func": f, "g": g.where(valid)}))
    long = pd.concat(long).dropna()
    long = long[long.g.abs() <= MAX_ABS_G]
    cy = long.groupby(["iso3", "year"]).g.agg(
        median_abs_g=lambda x: np.median(np.abs(x)),
        large_share=lambda x: np.mean(np.abs(x) > LARGE),
        n_funcs="size").reset_index()
    q = q.merge(cy, on=["iso3", "year"], how="left")
    q["fiscal_tail"] = (q.abs_dfiscal > 3).astype(float).where(q.abs_dfiscal.notna())
    cab = pd.read_csv(PROC / "veto_player_panel.csv")[["iso3", "year", "n_cab_parties"]]
    q = q.merge(cab, on=["iso3", "year"], how="left")

    long = long.merge(q[["iso3", "year", "h_polcon3", "n_cab_parties", "incohesion", "polyarchy"]],
                      on=["iso3", "year"], how="left")
    long["decade"] = (long.year // 10) * 10
    dec = long[long.polyarchy > 0.5].groupby(["iso3", "decade"]).agg(
        lkurt=("g", lambda x: l_kurtosis(x.to_numpy()) if len(x) >= MIN_LK_OBS else np.nan),
        n_obs=("g", "size"), h_polcon3=("h_polcon3", "mean"), n_cab_parties=("n_cab_parties", "mean"),
        incohesion=("incohesion", "mean")).reset_index().dropna(subset=["lkurt"])
    return q, dec, long


def fit(formula, d, cluster="iso3"):
    return smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": d[cluster]})


def main():
    pd.set_option("display.width", 220)
    q, dec, long = build()
    q.to_csv(PROC / "budget_punctuation_country_year.csv", index=False)
    dec.to_csv(PROC / "budget_punctuation_country_decade.csv", index=False)
    print(f"country-years with comp_dist: {q.comp_dist.notna().sum()}, with g: {q.median_abs_g.notna().sum()}, "
          f"countries: {q.dropna(subset=['median_abs_g']).iso3.nunique()}; country-decades: {len(dec)}")
    print(f"pooled function-year changes: {len(long)}; overall L-kurtosis = {l_kurtosis(long.g.to_numpy()):.3f} "
          f"(Gaussian = 0.123); share |g|>{LARGE}: {np.mean(np.abs(long.g) > LARGE):.3f}")
    rows = []
    for veto, yr_max in [("h_polcon3", 2016), ("n_cab_parties", 2021), ("incohesion", 2021)]:
        base = q[(q.polyarchy > 0.5) & (q.year <= yr_max)]
        for tag, y in [("G1", "comp_dist"), ("G2", "median_abs_g"), ("G3", "large_share"), ("G5", "fiscal_tail")]:
            if tag == "G5" and veto != "h_polcon3":
                continue
            d = base.dropna(subset=[y, veto])
            m = fit(f"{y} ~ {veto} + C(iso3) + C(year)", d)
            rows.append({"test": tag, "veto": veto, "outcome": y, "N": int(m.nobs), "countries": d.iso3.nunique(),
                         "coef": m.params[veto], "se": m.bse[veto], "p": m.pvalues[veto],
                         "coef_per_sd": m.params[veto] * d[veto].std(), "outcome_mean": d[y].mean()})
        d = dec[dec.decade <= (2010 if veto == "h_polcon3" else 2020)].dropna(subset=[veto])
        d = d[d.groupby("iso3").iso3.transform("size") > 1]
        m = fit(f"lkurt ~ {veto} + C(iso3) + C(decade)", d)
        rows.append({"test": "G4", "veto": veto, "outcome": "lkurt", "N": int(m.nobs), "countries": d.iso3.nunique(),
                     "coef": m.params[veto], "se": m.bse[veto], "p": m.pvalues[veto],
                     "coef_per_sd": m.params[veto] * d[veto].std(), "outcome_mean": d.lkurt.mean()})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "budget_punctuation.csv", index=False)
    print(out.round(4).to_string())

    d = dec.dropna(subset=["h_polcon3"])
    b = smf.ols("lkurt ~ h_polcon3 + C(decade)", d).fit(cov_type="cluster", cov_kwds={"groups": d.iso3})
    print(f"\nBetween-country (exploratory, no country FE): L-kurtosis ~ POLCON = {b.params['h_polcon3']:.3f} "
          f"(p {b.pvalues['h_polcon3']:.3f}), N={int(b.nobs)}")
    pd.DataFrame([{"model": "L-kurtosis ~ POLCON, decade FE only (between)", "coef": b.params["h_polcon3"],
                   "se": b.bse["h_polcon3"], "p": b.pvalues["h_polcon3"], "N": int(b.nobs)}]).to_csv(
        TAB / "budget_punctuation_between.csv", index=False)


if __name__ == "__main__":
    main()
