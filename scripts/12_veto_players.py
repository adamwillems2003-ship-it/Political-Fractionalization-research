"""Design E (pre_analysis_plan_part3.md): veto-player predictions in a country-year panel."""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from eventlib import load_country_year

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, TAB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables"


def cabinet_panel() -> pd.DataFrame:
    c = pd.read_csv(RAW / "parlgov" / "view_cabinet.csv", parse_dates=["start_date"])
    c = c[c.caretaker == 0]
    cab = c[c.cabinet_party == 1].groupby(["country_name_short", "cabinet_id", "start_date"]).agg(
        n_cab_parties=("party_id", "nunique"),
        lr_max=("left_right", "max"), lr_min=("left_right", "min"),
        cab_seats=("seats", "sum"), seats_total=("election_seats_total", "first"),
    ).reset_index()
    pm = c[(c.cabinet_party == 1) & (c.prime_minister == 1)].groupby("cabinet_id").left_right.first()
    cab["pm_lr"] = cab.cabinet_id.map(pm)
    cab["cab_range"] = cab.lr_max - cab.lr_min
    cab["single_party"] = (cab.n_cab_parties == 1).astype(int)
    cab["minority"] = (cab.cab_seats < cab.seats_total / 2).astype(int)
    rows = []
    for iso, g in cab.sort_values("start_date").groupby("country_name_short"):
        for year in range(1961, 2024):
            prior = g[g.start_date <= pd.Timestamp(f"{year}-01-01")]
            if prior.empty:
                continue
            r = prior.iloc[-1]
            rows.append({"iso3": iso, "year": year, "n_cab_parties": r.n_cab_parties,
                         "cab_range": r.cab_range, "single_party": r.single_party,
                         "minority": r.minority, "pm_lr": r.pm_lr})
    p = pd.DataFrame(rows).sort_values(["iso3", "year"])
    p["pm_swing"] = p.groupby("iso3").pm_lr.diff().abs()
    return p


def fit(formula: str, d: pd.DataFrame):
    return smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": d.iso3})


def main():
    pd.set_option("display.width", 220)
    panel = load_country_year(1961, 2023)
    cab = cabinet_panel()
    mp = pd.read_csv(PROC / "marpor_country_year.csv")[["iso3", "year", "polarization"]]
    d = panel.merge(cab, on=["iso3", "year"], how="left").merge(mp, on=["iso3", "year"], how="left")
    d.to_csv(PROC / "veto_player_panel.csv", index=False)
    fe = " + C(iso3) + C(year)"
    specs = [
        ("E1", "abs_dfiscal", "n_cab_parties", "abs_dfiscal ~ n_cab_parties" + fe,
         lambda x: x[x.year.between(1980, 2022)]),
        ("E2", "abs_dfiscal", "cab_range", "abs_dfiscal ~ cab_range" + fe,
         lambda x: x[x.year.between(1980, 2022)]),
        ("E3", "abs_dfiscal", "h_polcon3", "abs_dfiscal ~ h_polcon3" + fe,
         lambda x: x[x.year.between(1980, 2016) & (x.polyarchy > 0.5)]),
        ("E4", "abs_dgrowth", "polarization:single_party",
         "abs_dgrowth ~ polarization * single_party" + fe, lambda x: x[x.year.between(1961, 2016)]),
        ("E5", "abs_dfiscal", "pm_swing:single_party",
         "abs_dfiscal ~ pm_swing * single_party" + fe, lambda x: x[x.year.between(1981, 2022)]),
        ("E1-growth", "abs_dgrowth", "n_cab_parties", "abs_dgrowth ~ n_cab_parties" + fe,
         lambda x: x[x.year.between(1961, 2022)]),
        ("E2-growth", "abs_dgrowth", "cab_range", "abs_dgrowth ~ cab_range" + fe,
         lambda x: x[x.year.between(1961, 2022)]),
        ("E3-growth", "abs_dgrowth", "h_polcon3", "abs_dgrowth ~ h_polcon3" + fe,
         lambda x: x[x.year.between(1961, 2016) & (x.polyarchy > 0.5)]),
        ("E4-fiscal", "abs_dfiscal", "polarization:single_party",
         "abs_dfiscal ~ polarization * single_party" + fe, lambda x: x[x.year.between(1980, 2016)]),
        ("X1 within-country incohesion (exploratory)", "abs_dfiscal", "incohesion",
         "abs_dfiscal ~ incohesion" + fe, lambda x: x[x.year.between(1980, 2022) & (x.polyarchy > 0.5)]),
        ("X2 incohesion | polcon3 (exploratory)", "abs_dfiscal", "incohesion",
         "abs_dfiscal ~ incohesion + h_polcon3" + fe, lambda x: x[x.year.between(1980, 2016) & (x.polyarchy > 0.5)]),
    ]
    rows = []
    for tag, y, term, f, sel in specs:
        vars_ = [v for v in ["n_cab_parties", "cab_range", "h_polcon3", "polarization", "single_party",
                             "pm_swing", "incohesion"] if v in f]
        dd = sel(d).dropna(subset=[y] + vars_)
        m = fit(f, dd)
        row = {"test": tag, "outcome": y, "term": term, "N": int(m.nobs), "countries": dd.iso3.nunique(),
               "coef": m.params[term], "se": m.bse[term], "p": m.pvalues[term],
               "outcome_mean": dd[y].mean()}
        if ":" in term:
            a = term.split(":")[0]
            row["main_effect_" + a] = m.params[a]
            row["main_effect_p"] = m.pvalues[a]
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "veto_player_panel.csv", index=False)
    print(out.round(4).to_string())
    print("\n=== Between vs within decomposition of incohesion (exploratory) ===")
    print(decompose(d).round(4).to_string())


def decompose(d: pd.DataFrame) -> pd.DataFrame:
    """Mundlak: country-mean incohesion (between) vs deviation (within); and C1b with formal veto points."""
    rows = []
    for thr in (0.7, 0.5):
        dd = d[d.year.between(1980, 2022) & (d.polyarchy > thr)].dropna(subset=["abs_dfiscal", "incohesion"]).copy()
        dd["incoh_between"] = dd.groupby("iso3").incohesion.transform("mean")
        dd["incoh_within"] = dd.incohesion - dd.incoh_between
        m = fit("abs_dfiscal ~ incoh_between + incoh_within + C(year)", dd)
        for t in ["incoh_between", "incoh_within"]:
            rows.append({"model": f"Mundlak panel, |Δ fiscal|, polyarchy>{thr}", "term": t, "N": int(m.nobs),
                         "countries": dd.iso3.nunique(), "coef": m.params[t], "se": m.bse[t], "p": m.pvalues[t]})
    dd2 = dd.dropna(subset=["h_polcon3"]).copy()
    dd2["polcon_between"] = dd2.groupby("iso3").h_polcon3.transform("mean")
    m = fit("abs_dfiscal ~ incoh_between + incoh_within + polcon_between + C(year)", dd2)
    for t in ["incoh_between", "polcon_between"]:
        rows.append({"model": "Mundlak panel + country-mean POLCON", "term": t, "N": int(m.nobs),
                     "coef": m.params[t], "se": m.bse[t], "p": m.pvalues[t]})
    cs = pd.read_csv(PROC / "crosssection_vdem_cohesion.csv")
    pc = (d[d.year.between(1961, 2016)].groupby("iso3").h_polcon3.mean().rename("polcon_mean"))
    cs = cs.merge(pc, on="iso3", how="left").dropna(subset=["fiscal_sd", "incohesion", "polcon_mean",
                                                            "log_gdppc_initial", "polyarchy_mean"])
    import statsmodels.api as sm
    X = sm.add_constant(cs[["frac", "incohesion", "polcon_mean", "log_gdppc_initial", "polyarchy_mean"]])
    o = sm.OLS(cs.fiscal_sd, X).fit(cov_type="HC1")
    for t in ["incohesion", "polcon_mean"]:
        rows.append({"model": "C1b cross-section + mean POLCON", "term": t, "N": int(o.nobs),
                     "coef": o.params[t], "se": o.bse[t], "p": o.pvalues[t]})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "incohesion_between_within.csv", index=False)
    return out
    print("\nSD of regressors (ParlGov sample):")
    print(d[d.year.between(1980, 2022)][["n_cab_parties", "cab_range", "h_polcon3", "polarization", "pm_swing"]]
          .describe().loc[["mean", "std"]].round(3).to_string())


if __name__ == "__main__":
    main()
