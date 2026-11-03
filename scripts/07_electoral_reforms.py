"""Design A (pre_analysis_plan.md): national electoral reforms as within-country shocks to ENPP.

Stacked event study / stacked 2SLS with stack x country and stack x year fixed effects, plus
synthetic control per event with in-space placebo inference.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.iv import IV2SLS
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, TAB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables"

EVENTS = {"NZL96": ("NZL", 1996), "ITA94": ("ITA", 1994), "JPN96": ("JPN", 1996), "ITA06": ("ITA", 2006)}
CONTROLS = ["AUS", "AUT", "BEL", "CAN", "CHE", "DEU", "DNK", "ESP", "FIN", "GBR", "IRL", "ISL",
            "LUX", "NLD", "NOR", "PRT", "SWE", "USA"]
TAU_MIN, TAU_MAX = -8, 10
YEAR_MIN, YEAR_MAX = 1980, 2016
FIRST_STAGE = {"enpp": "ENPP (Golder)", "incohesion": "Party incohesion (−V-Dem v2pscohesv)",
               "polarization": "Platform polarization (MARPOR)"}
OUTCOMES = {"abs_dgrowth": "|Δ growth| (pp)", "abs_dfiscal": "|Δ fiscal balance| (pp)",
            "sd5_growth": "5-yr SD growth", "sd5_fiscal": "5-yr SD fiscal balance",
            "growth": "Growth", "fiscal": "Fiscal balance"}
SC_OUTCOMES = ["enpp", "sd5_growth", "sd5_fiscal"]
SEED = 20261102


def load_panel() -> pd.DataFrame:
    q = pd.read_csv(RAW / "qog_std_ts_jan24.csv", usecols=["ccodealp", "year", "gol_enpp", "wdi_gdpgr"],
                    low_memory=False).rename(columns={"ccodealp": "iso3", "gol_enpp": "enpp", "wdi_gdpgr": "growth"})
    countries = sorted(set(CONTROLS) | {iso for iso, _ in EVENTS.values()})
    q = q[q.iso3.isin(countries) & q.year.between(1970, YEAR_MAX)]
    imf = pd.read_csv(RAW / "imf_GGXCNL_NGDP.csv").rename(columns={"value": "fiscal"})
    vd = pd.read_csv(RAW / "vdem_cohesion.csv").rename(columns={"country_text_id": "iso3"})
    vd["incohesion"] = -vd.v2pscohesv
    mp = pd.read_csv(PROC / "marpor_country_year.csv")[["iso3", "year", "polarization"]]
    p = (q.merge(imf, on=["iso3", "year"], how="left")
          .merge(vd[["iso3", "year", "incohesion"]], on=["iso3", "year"], how="left")
          .merge(mp, on=["iso3", "year"], how="left")
          .sort_values(["iso3", "year"]))
    g = p.groupby("iso3")
    p["abs_dgrowth"] = g.growth.diff().abs()
    p["abs_dfiscal"] = g.fiscal.diff().abs()
    p["sd5_growth"] = g.growth.transform(lambda s: s.rolling(5, min_periods=5).std())
    p["sd5_fiscal"] = g.fiscal.transform(lambda s: s.rolling(5, min_periods=5).std())
    return p[p.year.between(YEAR_MIN, YEAR_MAX)]


def stack(p: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for ev, (iso, y0) in EVENTS.items():
        s = p[p.iso3.isin(CONTROLS + [iso]) & p.year.between(y0 + TAU_MIN, y0 + TAU_MAX)].copy()
        s = s[s.year != y0]
        s["event"] = ev
        s["tau"] = s.year - y0
        s["treated"] = (s.iso3 == iso).astype(int)
        frames.append(s)
    s = pd.concat(frames, ignore_index=True)
    for ev in EVENTS:
        s[f"post_{ev}"] = ((s.event == ev) & (s.treated == 1) & (s.tau >= 1)).astype(float)
    s["unit"] = s.event + "_" + s.iso3
    s["time"] = s.event + "_" + s.year.astype(str)
    return s


def demean(df: pd.DataFrame, cols: list[str], tol=1e-8, max_iter=500) -> pd.DataFrame:
    """Two-way within transformation (unit, time) by alternating projections; works for unbalanced panels."""
    out = df[cols].astype(float).copy()
    for _ in range(max_iter):
        prev = out.copy()
        out = out - out.groupby(df.unit).transform("mean")
        out = out - out.groupby(df.time).transform("mean")
        if (out - prev).abs().max().max() < tol:
            break
    return out


def stacked_2sls(s: pd.DataFrame, y: str, endog: str = "enpp", events=tuple(EVENTS)):
    z = [f"post_{e}" for e in events]
    d = s[s.event.isin(events)].dropna(subset=[y, endog]).copy()
    dm = demean(d, [y, endog] + z)
    keep = [c for c in z if dm[c].abs().sum() > 0]
    res = IV2SLS(dm[y], None, dm[[endog]], dm[keep]).fit(cov_type="clustered", clusters=d.iso3)
    fs = IV2SLS(dm[endog], dm[keep], None, None).fit(cov_type="unadjusted")
    return res, fs, d, dm, keep


def per_event_did(s: pd.DataFrame, var: str, ev: str) -> float:
    d = s[(s.event == ev)].dropna(subset=[var])
    post = d[f"post_{ev}"].to_numpy()
    if post.sum() == 0:
        return np.nan
    X = np.column_stack([post, pd.get_dummies(d.iso3, drop_first=True).to_numpy(float),
                         pd.get_dummies(d.year).to_numpy(float)])
    beta, *_ = np.linalg.lstsq(X, d[var].to_numpy(float), rcond=None)
    return float(beta[0])


def placebo_did(s: pd.DataFrame, var: str, ev: str) -> tuple[float, float, int]:
    """Conley-Taber style: compare the treated DiD to the same DiD with each control as fake treated."""
    actual = per_event_did(s, var, ev)
    d0 = s[(s.event == ev) & (s.treated == 0)]
    plac = []
    for c in CONTROLS:
        d = d0.copy()
        d["treated"] = (d.iso3 == c).astype(int)
        d[f"post_{ev}"] = ((d.treated == 1) & (d.tau >= 1)).astype(float)
        b = per_event_did(d, var, ev)
        if not np.isnan(b):
            plac.append(b)
    plac = np.array(plac)
    p = (1 + np.sum(np.abs(plac) >= abs(actual))) / (1 + len(plac)) if len(plac) else np.nan
    return actual, p, len(plac)


def pooled_ri(s: pd.DataFrame, y: str, n_draws=2000) -> tuple[float, float]:
    """Exploratory (not in PAP): sign-aligned pooled Wald ratio sum_e sign(pi_e) rho_e / sum_e |pi_e|,
    with randomization inference drawing one placebo control per event."""
    def stat(assign):
        num, den = 0.0, 0.0
        for ev, iso in assign.items():
            d = s[s.event == ev].copy()
            if iso is not None:
                d = d[d.treated == 0]
                d["treated"] = (d.iso3 == iso).astype(int)
                d[f"post_{ev}"] = ((d.treated == 1) & (d.tau >= 1)).astype(float)
            pi = per_event_did(d.dropna(subset=["enpp"]), "enpp", ev)
            rho = per_event_did(d.dropna(subset=[y]), y, ev)
            if np.isnan(pi) or np.isnan(rho):
                continue
            num += np.sign(pi) * rho
            den += abs(pi)
        return num / den if den > 0 else np.nan

    actual = stat({ev: None for ev in EVENTS})
    rng = np.random.default_rng(SEED)
    draws = [stat({ev: rng.choice(CONTROLS) for ev in EVENTS}) for _ in range(n_draws)]
    draws = np.array([x for x in draws if np.isfinite(x)])
    return actual, (1 + np.sum(np.abs(draws) >= abs(actual))) / (1 + len(draws))


def synth_weights(y_treat_pre: np.ndarray, Y_donor_pre: np.ndarray) -> np.ndarray:
    big = 1e3 * max(1.0, np.abs(Y_donor_pre).max())
    A = np.vstack([Y_donor_pre, big * np.ones(Y_donor_pre.shape[1])])
    b = np.append(y_treat_pre, big)
    w, _ = nnls(A, b)
    return w / w.sum()


def synth_event(p: pd.DataFrame, ev: str, var: str):
    iso, y0 = EVENTS[ev]
    pre_years = list(range(max(y0 + TAU_MIN, YEAR_MIN), y0))
    post_years = list(range(y0 + 1, min(y0 + TAU_MAX, YEAR_MAX) + 1))
    wide = p.pivot(index="year", columns="iso3", values=var)
    wide = wide.loc[pre_years + [y0] + post_years]
    donors = [c for c in CONTROLS if c in wide and wide[c].loc[pre_years + post_years].notna().all()]
    if iso not in wide or wide[iso].loc[pre_years + post_years].isna().any() or len(donors) < 5:
        return None

    def fit(unit, pool):
        w = synth_weights(wide[unit].loc[pre_years].to_numpy(), wide[pool].loc[pre_years].to_numpy())
        synth = wide[pool].to_numpy() @ w
        gap = wide[unit].to_numpy() - synth
        idx = {yr: i for i, yr in enumerate(wide.index)}
        pre = np.sqrt(np.mean(gap[[idx[t] for t in pre_years]] ** 2))
        post = np.sqrt(np.mean(gap[[idx[t] for t in post_years]] ** 2))
        att = np.mean(gap[[idx[t] for t in post_years]])
        return synth, gap, pre, post, att, dict(zip(pool, w))

    synth, gap, pre, post, att, w = fit(iso, donors)
    ratios = [post / pre if pre > 0 else np.inf]
    placebo_att = []
    for d in donors:
        _, _, pr, po, at, _ = fit(d, [x for x in donors if x != d])
        ratios.append(po / pr if pr > 0 else np.inf)
        if pr <= 2 * pre:
            placebo_att.append(abs(at))
    p_val = np.mean(np.array(ratios) >= ratios[0])
    # Exploratory: |ATT| rank among placebos with comparable pre-fit (Abadie et al. 2010 restriction).
    p_att = (1 + sum(a >= abs(att) for a in placebo_att)) / (1 + len(placebo_att))
    path = pd.DataFrame({"event": ev, "var": var, "year": wide.index, "tau": wide.index - y0,
                         "treated": wide[iso].to_numpy(), "synthetic": synth})
    top = sorted(w.items(), key=lambda kv: -kv[1])[:3]
    return {"event": ev, "var": var, "pre_rmspe": pre, "post_rmspe": post, "att_mean_post": att,
            "placebo_p": p_val, "placebo_p_att_restricted": p_att, "n_restricted": len(placebo_att),
            "n_donors": len(donors),
            "top_donors": ", ".join(f"{k} {v:.2f}" for k, v in top if v > 0.01)}, path


def main():
    pd.set_option("display.width", 250)
    p = load_panel()
    s = stack(p)
    s.to_csv(PROC / "reform_stacked_panel.csv", index=False)

    rows = []
    for v in list(FIRST_STAGE) + list(OUTCOMES):
        for ev in EVENTS:
            b, pv, n = placebo_did(s, v, ev)
            rows.append({"variable": v, "event": ev, "did": b, "placebo_p": pv, "n_placebos": n})
    did = pd.DataFrame(rows)
    did.to_csv(TAB / "reform_did_by_event.csv", index=False)
    print("=== Per-event DiD (treated vs clean controls), placebo p ===")
    print(did.pivot(index="variable", columns="event", values="did").round(3).to_string())
    print(did.pivot(index="variable", columns="event", values="placebo_p").round(3).to_string())

    iv_rows = []
    for y in OUTCOMES:
        res, fs, d, dm, z = stacked_2sls(s, y)
        ri_stat, ri_p = pooled_ri(s, y) if y in ("abs_dgrowth", "abs_dfiscal") else (np.nan, np.nan)
        iv_rows.append({
            "outcome": y, "N": int(res.nobs), "coef_per_party": res.params["enpp"],
            "se_cluster": res.std_errors["enpp"], "p_cluster": res.pvalues["enpp"],
            "first_stage_F_unadjusted": fs.f_statistic.stat / len(z),
            "RI_wald_ratio": ri_stat, "RI_p": ri_p,
        })
    for drop in EVENTS:
        keep = tuple(e for e in EVENTS if e != drop)
        for y in ("abs_dgrowth", "abs_dfiscal"):
            res, fs, *_ = stacked_2sls(s, y, events=keep)
            iv_rows.append({"outcome": f"{y} (drop {drop})", "N": int(res.nobs),
                            "coef_per_party": res.params["enpp"], "se_cluster": res.std_errors["enpp"],
                            "p_cluster": res.pvalues["enpp"],
                            "first_stage_F_unadjusted": fs.f_statistic.stat / len(keep)})
    iv = pd.DataFrame(iv_rows)
    iv.to_csv(TAB / "reform_stacked_2sls.csv", index=False)
    print("\n=== Stacked 2SLS (effect per effective party) ===\n" + iv.round(3).to_string())

    sc_rows, paths = [], []
    for ev in EVENTS:
        for v in SC_OUTCOMES:
            r = synth_event(p, ev, v)
            if r:
                sc_rows.append(r[0])
                paths.append(r[1])
    sc = pd.DataFrame(sc_rows)
    sc.to_csv(TAB / "reform_synthetic_control.csv", index=False)
    pd.concat(paths).to_csv(PROC / "reform_synthetic_paths.csv", index=False)
    print("\n=== Synthetic control ===\n" + sc.round(3).to_string())

    pre = s[(s.treated == 1) & s.tau.between(-8, -1)]
    trend = pre.groupby("event").apply(lambda g: np.polyfit(g.tau, g.enpp, 1)[0] if g.enpp.notna().sum() > 2 else np.nan,
                                       include_groups=False)
    print("\nPre-period ENPP trend in treated unit (parties/year):\n" + trend.round(3).to_string())
    trend.rename("pre_trend_enpp_per_year").to_csv(TAB / "reform_pretrends.csv")


if __name__ == "__main__":
    main()
