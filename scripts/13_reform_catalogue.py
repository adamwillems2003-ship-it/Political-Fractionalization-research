"""Design F (pre_analysis_plan_part3.md): every electoral-system family change in the Bormann-Golder
DES codes, pooled in a stacked 2SLS with an a priori (Duverger) direction instrument."""
from pathlib import Path

import pandas as pd

from eventlib import Event, StackedDesign, load_country_year

ROOT = Path(__file__).resolve().parents[1]
TAB, PROC = ROOT / "output" / "tables", ROOT / "data" / "processed"
TAU_MIN, TAU_MAX = -8, 10
YEAR_MIN, YEAR_MAX = 1966, 2015
TOWARD_PR = {(1, 3), (1, 2), (3, 2)}
SAMPLES = {"broad": 0.5, "clean": 0.7}
OUTCOMES = ["abs_dgrowth", "abs_dfiscal", "sd5_growth", "sd5_fiscal"]


def catalogue(panel: pd.DataFrame) -> pd.DataFrame:
    d = panel.dropna(subset=["gol_est"]).sort_values(["iso3", "year"]).copy()
    d["prev"] = d.groupby("iso3").gol_est.shift()
    d["prev_year"] = d.groupby("iso3").year.shift()
    ch = d[d.prev.notna() & (d.gol_est != d.prev) & (d.prev_year == d.year - 1)
           & d.year.between(YEAR_MIN, YEAR_MAX)].copy()
    poly = panel.set_index(["iso3", "year"]).polyarchy
    ch["polyarchy_pre"] = [poly.get((i, y - 1)) for i, y in zip(ch.iso3, ch.year)]
    ch["direction"] = [1 if (int(a), int(b)) in TOWARD_PR else -1 for a, b in zip(ch.prev, ch.gol_est)]
    ch["from_to"] = ch.prev.astype(int).astype(str) + "->" + ch.gol_est.astype(int).astype(str)
    ch["year"] = ch.year.astype(int)
    return ch[["iso3", "year", "from_to", "direction", "polyarchy_pre"]].reset_index(drop=True)


def build_events(panel, cat, poly_min) -> list[Event]:
    changes = panel.dropna(subset=["gol_est"]).sort_values(["iso3", "year"])
    changes = changes[changes.groupby("iso3").gol_est.diff().fillna(0) != 0][["iso3", "year"]]
    poly = panel.pivot(index="year", columns="iso3", values="polyarchy")
    events = []
    for r in cat[cat.polyarchy_pre > poly_min].itertuples():
        years = tuple(range(r.year + TAU_MIN, r.year + TAU_MAX + 1))
        busy = set(changes[changes.year.between(years[0], years[-1])].iso3)
        pre = poly.loc[r.year - 1] if (r.year - 1) in poly.index else pd.Series(dtype=float)
        ctrl = tuple(c for c in pre.index if pre[c] > 0.5 and c not in busy and c != r.iso3)
        events.append(Event(f"{r.iso3}{r.year}", r.iso3, int(r.direction), int(r.year) + 1,
                            years, ctrl, (int(r.year),)))
    return events


def main():
    pd.set_option("display.width", 220)
    panel = load_country_year(1958, 2023)
    panel.loc[panel.year > 2016, ["enpp", "gol_est"]] = float("nan")
    cat = catalogue(panel)
    cat.to_csv(PROC / "reform_catalogue.csv", index=False)
    print(f"catalogue: {len(cat)} events; broad={int((cat.polyarchy_pre > 0.5).sum())} "
          f"clean={int((cat.polyarchy_pre > 0.7).sum())}")
    print(cat.round(2).to_string())
    rows, per = [], []
    for s, pmin in SAMPLES.items():
        design = StackedDesign(panel, build_events(panel, cat, pmin))
        for y in OUTCOMES:
            e = design.estimate("enpp", y)
            if not e:
                continue
            pe = e.pop("per_event")
            pe["outcome"], pe["sample"] = y, s
            per.append(pe)
            rows.append({"sample": s, "outcome": y, **e})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "reform_catalogue_stacked.csv", index=False)
    pe = pd.concat(per)
    pe.to_csv(TAB / "reform_catalogue_by_event.csv", index=False)
    print("\n=== Design F: stacked 2SLS, ENPP -> outcome (instrument: Duverger direction x post) ===")
    print(out.round(4).to_string())
    print("\n=== Per event (broad sample, |Δ growth|) ===")
    print(pe[(pe["sample"] == "broad") & (pe.outcome == "abs_dgrowth")].round(3).to_string())


if __name__ == "__main__":
    main()
