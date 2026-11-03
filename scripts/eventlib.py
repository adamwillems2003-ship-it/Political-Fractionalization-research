"""Stacked event-study / 2SLS with exact randomization inference.

Each stack (one event + its clean controls) is an independent two-way-FE block, so a pooled
estimate under any assignment of "treated" units is a ratio of per-stack sums. Per-stack
projections are precomputed once; RI draws then cost almost nothing.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.iv import IV2SLS

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"


def load_country_year(year_min=1960, year_max=2023) -> pd.DataFrame:
    q = pd.read_csv(RAW / "qog_std_ts_jan24.csv", low_memory=False,
                    usecols=["ccodealp", "year", "gol_enpp", "gol_est", "wdi_gdpgr", "h_polcon3"]
                    ).rename(columns={"ccodealp": "iso3", "gol_enpp": "enpp", "wdi_gdpgr": "growth"})
    q = q.dropna(subset=["iso3"])
    imf = pd.read_csv(RAW / "imf_GGXCNL_NGDP.csv").rename(columns={"value": "fiscal"})
    vd = pd.read_csv(RAW / "vdem_cohesion.csv").rename(
        columns={"country_text_id": "iso3", "v2x_polyarchy": "polyarchy"})
    vd["incohesion"] = -vd.v2pscohesv
    p = (vd[["iso3", "year", "incohesion", "polyarchy"]]
         .merge(q, on=["iso3", "year"], how="outer")
         .merge(imf, on=["iso3", "year"], how="left"))
    p = p[p.year.between(year_min - 6, year_max)].sort_values(["iso3", "year"])
    p.loc[p.year > 2023, "fiscal"] = np.nan
    g = p.groupby("iso3")
    p["abs_dgrowth"] = g.growth.diff().abs()
    p["abs_dfiscal"] = g.fiscal.diff().abs()
    p["sd5_growth"] = g.growth.transform(lambda s: s.rolling(5, min_periods=5).std())
    p["sd5_fiscal"] = g.fiscal.transform(lambda s: s.rolling(5, min_periods=5).std())
    return p[p.year.between(year_min, year_max)].reset_index(drop=True)


@dataclass
class Event:
    event_id: str
    iso3: str
    direction: int
    post_year: int
    years: tuple
    controls: tuple
    drop_years: tuple = ()


def _fe_projector(units: np.ndarray, years: np.ndarray):
    D = np.column_stack([pd.get_dummies(units).to_numpy(float),
                         pd.get_dummies(years, drop_first=True).to_numpy(float)])
    Q, _ = np.linalg.qr(D)
    return lambda v: v - Q @ (Q.T @ v)


class StackedDesign:
    def __init__(self, panel: pd.DataFrame, events: list[Event]):
        self.panel = panel.set_index(["iso3", "year"]).sort_index()
        self.events = events

    def _stack_frame(self, ev: Event) -> pd.DataFrame:
        units = (ev.iso3,) + tuple(c for c in ev.controls if c != ev.iso3)
        idx = pd.MultiIndex.from_product([units, [y for y in ev.years if y not in ev.drop_years]],
                                         names=["iso3", "year"])
        f = self.panel.reindex(idx).reset_index()
        f["post"] = (f.year >= ev.post_year).astype(float)
        return f

    def precompute(self, x: str, y: str) -> list[dict]:
        """Per stack: residualized x, y on the common non-missing sample, and per-unit z stats."""
        out = []
        for ev in self.events:
            f = self._stack_frame(ev).dropna(subset=[x, y])
            if f[f.iso3 == ev.iso3].empty or f.iso3.nunique() < 3:
                continue
            resid = _fe_projector(f.iso3.to_numpy(), f.year.to_numpy())
            xr, yr = resid(f[x].to_numpy(float)), resid(f[y].to_numpy(float))
            stats = {}
            for u in f.iso3.unique():
                z = ev.direction * ((f.iso3 == u) & (f.post == 1)).to_numpy(float)
                if z.sum() == 0 or (z != 0).sum() == len(z):
                    continue
                zr = resid(z)
                pre_rows = ((f.iso3 == u) & (f.post == 0)).sum()
                if pre_rows == 0:
                    continue
                stats[u] = (zr @ xr, zr @ yr, zr @ zr)
            if ev.iso3 not in stats:
                continue
            out.append({"event": ev, "frame": f, "xr": xr, "yr": yr, "stats": stats,
                        "controls": [u for u in stats if u != ev.iso3]})
        return out

    @staticmethod
    def pooled(pre: list[dict], assign: dict | None = None) -> dict:
        ax = ay = bz = 0.0
        for s in pre:
            u = s["event"].iso3 if assign is None else assign[s["event"].event_id]
            sx, sy, sz = s["stats"][u]
            ax, ay, bz = ax + sx, ay + sy, bz + sz
        return {"first_stage": ax / bz, "reduced_form": ay / bz, "iv": ay / ax if ax != 0 else np.nan}

    def estimate(self, x: str, y: str, n_draws=2000, seed=20261102) -> dict:
        pre = self.precompute(x, y)
        if not pre:
            return {}
        est = self.pooled(pre)
        rng = np.random.default_rng(seed)
        fs_d, rf_d = [], []
        for _ in range(n_draws):
            assign = {s["event"].event_id: rng.choice(s["controls"]) for s in pre}
            r = self.pooled(pre, assign)
            fs_d.append(r["first_stage"])
            rf_d.append(r["reduced_form"])
        fs_d, rf_d = np.array(fs_d), np.array(rf_d)
        est.update({
            "n_events": len(pre),
            "N": int(sum(len(s["frame"]) for s in pre)),
            "RI_p_first_stage": float(np.mean(np.abs(fs_d) >= abs(est["first_stage"]))),
            "RI_p_reduced_form": float(np.mean(np.abs(rf_d) >= abs(est["reduced_form"]))),
        })
        est.update(self._cluster_iv(pre))
        est["per_event"] = self.per_event(pre)
        return est

    @staticmethod
    def _cluster_iv(pre: list[dict]) -> dict:
        rows = []
        for s in pre:
            f, ev = s["frame"], s["event"]
            z = ev.direction * ((f.iso3 == ev.iso3) & (f.post == 1)).to_numpy(float)
            resid = _fe_projector(f.iso3.to_numpy(), f.year.to_numpy())
            rows.append(pd.DataFrame({"y": s["yr"], "x": s["xr"], "z": resid(z), "cl": f.iso3.to_numpy()}))
        d = pd.concat(rows, ignore_index=True)
        r = IV2SLS(d.y, None, d[["x"]], d[["z"]]).fit(cov_type="clustered", clusters=d.cl)
        fs = IV2SLS(d.x, d[["z"]], None, None).fit(cov_type="unadjusted")
        return {"iv_se_cluster": float(r.std_errors["x"]), "iv_p_cluster": float(r.pvalues["x"]),
                "first_stage_F_unadjusted": float(fs.f_statistic.stat)}

    @staticmethod
    def per_event(pre: list[dict]) -> pd.DataFrame:
        rows = []
        for s in pre:
            ev = s["event"]
            fs = {u: v[0] / v[2] for u, v in s["stats"].items()}
            rf = {u: v[1] / v[2] for u, v in s["stats"].items()}
            ctrl = s["controls"]
            rows.append({
                "event": ev.event_id, "direction": ev.direction, "n_controls": len(ctrl),
                "first_stage": fs[ev.iso3],
                "p_first_stage": (1 + sum(abs(fs[c]) >= abs(fs[ev.iso3]) for c in ctrl)) / (1 + len(ctrl)),
                "reduced_form": rf[ev.iso3],
                "p_reduced_form": (1 + sum(abs(rf[c]) >= abs(rf[ev.iso3]) for c in ctrl)) / (1 + len(ctrl)),
            })
        return pd.DataFrame(rows)
