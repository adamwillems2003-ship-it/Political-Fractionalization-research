"""Collapse the country-year panel to one row per country (between-effects design).

Only democratic country-years enter the averages: V-Dem polyarchy > 0.7 (primary sample) or
Polity2 > 6 (alternative sample). Window: 1961-2016 (WDI growth starts 1961; Golder ENPP ends 2016).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"

YEAR_MIN, YEAR_MAX = 1961, 2016
MIN_YEARS_GROWTH = 10
MIN_YEARS_FISCAL = 8
SAMPLES = {
    "vdem": lambda d: d.vdem_polyarchy > 0.7,
    "polity": lambda d: d.p_polity2 > 6,
}
IENP_VARIANTS = ["ienp_gap", "ienp_silhouette", "ienp_k3", "ienp_k4", "ienp_k5",
                 "ienp_gmm_within_party", "ienp_caucus", "enpp_nominal"]
NP_COLS = ["isocode", "rugged", "dist_coast", "q_rule_law", "european_descent", "tropical",
           "lat", "rgdppc_1950_m", "legor_gbr", "legor_fra", "legor_deu", "legor_sca", "legor_soc",
           "cont_africa", "cont_asia", "cont_europe", "cont_oceania", "cont_north_america",
           "cont_south_america"]
QOG_COLS = ["ccodealp", "cname", "year", "gol_enpp", "p_polity2", "vdem_polyarchy",
            "mad_gdppc", "wdi_gdpgr"]


def load_panel() -> pd.DataFrame:
    q = pd.read_csv(RAW / "qog_std_ts_jan24.csv", usecols=QOG_COLS, low_memory=False)
    q = q[q.year.between(YEAR_MIN, YEAR_MAX)].rename(columns={"ccodealp": "iso3"})
    imf = pd.read_csv(RAW / "imf_GGXCNL_NGDP.csv").rename(columns={"value": "fiscal_balance"})
    q = q.merge(imf, on=["iso3", "year"], how="left")

    us = pd.read_csv(OUT / "us_ienp_by_congress.csv")
    us_years = pd.concat([us.assign(year=us.year_start), us.assign(year=us.year_start + 1)])
    us_years = us_years[["year"] + IENP_VARIANTS].assign(iso3="USA")
    return q.merge(us_years, on=["iso3", "year"], how="left")


def collapse(panel: pd.DataFrame, sample: str) -> pd.DataFrame:
    d = panel[SAMPLES[sample](panel)].copy()
    rows = []
    for iso, g in d.groupby("iso3"):
        g = g.sort_values("year")
        enpp = g.gol_enpp.dropna()
        growth = g.wdi_gdpgr.dropna()
        if len(enpp) < MIN_YEARS_GROWTH or len(growth) < MIN_YEARS_GROWTH:
            continue
        fiscal = g.fiscal_balance.dropna()
        gdppc = g.mad_gdppc.dropna()
        row = {
            "iso3": iso,
            "country": g.cname.iloc[0],
            "n_dem_years": len(g),
            "first_dem_year": int(g.year.min()),
            "enpp_golder": enpp.mean(),
            "growth_sd": growth.std(),
            "growth_mean": growth.mean(),
            "fiscal_sd": fiscal.std() if len(fiscal) >= MIN_YEARS_FISCAL else np.nan,
            "fiscal_mean": fiscal.mean() if len(fiscal) >= MIN_YEARS_FISCAL else np.nan,
            "polyarchy_mean": g.vdem_polyarchy.mean(),
            "log_gdppc_initial": np.log(gdppc.iloc[0]) if len(gdppc) else np.nan,
        }
        for v in IENP_VARIANTS:
            row[v] = g[v].mean() if g[v].notna().any() else np.nan
        rows.append(row)
    cs = pd.DataFrame(rows)

    np_data = pd.read_stata(RAW / "rugged" / "rugged_data.dta")[NP_COLS].rename(columns={"isocode": "iso3"})
    unmatched = sorted(set(cs.iso3) - set(np_data.iso3))
    if unmatched:
        print(f"[{sample}] no Nunn-Puga match for: {unmatched}")
    cs = cs.merge(np_data, on="iso3", how="left")

    is_us = cs.iso3 == "USA"
    cs["frac"] = cs.enpp_golder
    cs.loc[is_us, "frac"] = cs.loc[is_us, "ienp_gap"]
    cs["log_frac"] = np.log(cs.frac)
    cs["log_rugged"] = np.log1p(cs.rugged)
    return cs


def main() -> None:
    panel = load_panel()
    for s in SAMPLES:
        cs = collapse(panel, s)
        cs.to_csv(OUT / f"crosssection_{s}.csv", index=False)
        print(f"[{s}] countries={len(cs)} with fiscal={cs.fiscal_sd.notna().sum()} "
              f"with instruments={cs.legor_gbr.notna().sum()}")
        us = cs[cs.iso3 == "USA"]
        print(us[["first_dem_year", "n_dem_years", "enpp_golder", "ienp_gap", "ienp_silhouette",
                  "ienp_caucus", "growth_sd"]].round(2).to_string())
        print(cs.sort_values("frac", ascending=False)[["country", "frac", "growth_sd"]].head(6).round(2).to_string())
        print(cs[["frac", "growth_sd", "fiscal_sd", "rugged", "legor_gbr", "log_gdppc_initial",
                  "polyarchy_mean"]].describe().round(2).to_string())


if __name__ == "__main__":
    main()
