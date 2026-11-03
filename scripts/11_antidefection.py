"""Design D (pre_analysis_plan_part3.md): anti-defection laws as shocks to party discipline."""
from pathlib import Path

import numpy as np
import pandas as pd

from eventlib import Event, StackedDesign, load_country_year

ROOT = Path(__file__).resolve().parents[1]
REF, TAB, PROC = ROOT / "data" / "reference", ROOT / "output" / "tables", ROOT / "data" / "processed"
TAU_MIN, TAU_MAX = -6, 6
POLYARCHY_MIN = 0.5
OUTCOMES = ["abs_dfiscal", "abs_dgrowth", "sd5_fiscal", "sd5_growth"]


def build_events(panel: pd.DataFrame) -> list[Event]:
    ev = pd.read_csv(REF / "anti_defection_events.csv")
    treated = set(ev.iso3)
    poly = panel.pivot(index="year", columns="iso3", values="polyarchy")
    events = []
    for r in ev.itertuples():
        years = tuple(range(r.first_post_year + TAU_MIN, r.first_post_year + TAU_MAX + 1))
        w = poly.reindex(years)
        ok = [c for c in w.columns if c not in treated and w[c].notna().any() and (w[c].dropna() > POLYARCHY_MIN).all()]
        drop = tuple(range(r.event_year, r.first_post_year))
        events.append(Event(f"{r.iso3}{r.event_year}", r.iso3, int(r.direction), int(r.first_post_year),
                            years, tuple(ok), drop))
    return events


def main():
    pd.set_option("display.width", 220)
    panel = load_country_year(1975, 2023)
    events = build_events(panel)
    design = StackedDesign(panel, events)
    rows, per = [], []
    for y in OUTCOMES:
        e = design.estimate("incohesion", y)
        pe = e.pop("per_event")
        pe["outcome"] = y
        per.append(pe)
        rows.append({"outcome": y, **e})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "antidefection_stacked.csv", index=False)
    pe = pd.concat(per)
    pe.to_csv(TAB / "antidefection_by_event.csv", index=False)
    print("=== Design D: stacked signed 2SLS, incohesion -> outcome ===")
    print(out.round(4).to_string())
    print("\n=== Per event (first stage = incohesion; RF = outcome) ===")
    print(pe[pe.outcome == "abs_dfiscal"].round(3).to_string())

    for drop in [e.event_id for e in events]:
        d = StackedDesign(panel, [e for e in events if e.event_id != drop])
        r = d.estimate("incohesion", "abs_dfiscal", n_draws=500)
        print(f"drop {drop}: iv={r['iv']:.3f} fs={r['first_stage']:.3f} RI_p_rf={r['RI_p_reduced_form']:.3f}")


if __name__ == "__main__":
    main()
