"""Figures for Part II: measure validation, electoral-reform synthetic controls, top-two event study."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, TAB, FIG = (ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables",
                       ROOT / "output" / "figures")

SURFACE, INK, INK2, GRID, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
S1, S2 = "#2a78d6", "#eb6834"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "font.size": 10, "axes.titlesize": 10.5,
    "axes.titleweight": "bold", "legend.frameon": False,
})


def fig_validation():
    mem = pd.read_csv(PROC / "us_house_defections_member.csv")
    ch = mem.groupby("congress").defection_rate.mean().rename("defection").reset_index()
    ch["year"] = 1789 + 2 * (ch.congress - 1)
    ienp = pd.read_csv(PROC / "us_ienp_by_congress.csv").merge(ch, on="congress")
    vd = pd.read_csv(RAW / "vdem_cohesion.csv")
    ch_years = pd.concat([ch.assign(year=ch.year + k) for k in (0, 1)])
    vd = vd[vd.country_text_id == "USA"][["year", "v2pscohesv"]].merge(ch_years[["year", "defection"]], on="year")
    pc = pd.read_csv(PROC / "us_house_party_congress.csv")
    panels = [
        (pc.nom_within_sd, pc.defection_rate, "Within-party SD of NOMINATE (party × Congress)", True),
        (vd.v2pscohesv, vd.defection, "V-Dem party cohesion, US (year)", True),
        (ienp.ienp_silhouette, ienp.defection, "IENP, k-means silhouette (Congress)", True),
        (ienp.ienp_gap, ienp.defection, "IENP, k-means gap statistic (Congress)", False),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8), sharey=True)
    for ax, (x, y, title, ok) in zip(axes, panels):
        r = np.corrcoef(x, y)[0, 1]
        ax.scatter(x, y * 100, s=22, color=S1 if ok else NEUTRAL, edgecolor=SURFACE, linewidth=0.8)
        ax.set_title(title, loc="left", fontsize=9.5)
        ax.text(0.03, 0.95, f"r = {r:.2f}  ·  {'validated' if ok else 'fails |r| ≥ 0.5'}",
                transform=ax.transAxes, va="top", fontsize=9, color=INK2)
    axes[0].set_ylabel("House party-unity defection rate (%)")
    fig.suptitle("Which fragmentation measures track actual roll-call defections? (rule fixed in pre-analysis plan)",
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "measure_validation.png", dpi=200)
    plt.close(fig)


def fig_synth():
    paths = pd.read_csv(PROC / "reform_synthetic_paths.csv")
    sc = pd.read_csv(TAB / "reform_synthetic_control.csv").set_index(["event", "var"])
    events = ["NZL96", "ITA94", "JPN96", "ITA06"]
    names = {"NZL96": "New Zealand 1996 (FPTP→MMP)", "ITA94": "Italy 1994 (PR→mixed)",
             "JPN96": "Japan 1996 (SNTV→mixed)", "ITA06": "Italy 2006 (mixed→PR+bonus)"}
    rows = [("enpp", "ENPP"), ("sd5_growth", "5-yr SD of growth (pp)")]
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.4))
    for j, ev in enumerate(events):
        for i, (var, lab) in enumerate(rows):
            ax = axes[i, j]
            d = paths[(paths.event == ev) & (paths["var"] == var)]
            ax.axvline(0, color=NEUTRAL, lw=0.8, ls="--")
            if d.empty:
                ax.text(0.5, 0.5, "insufficient data", ha="center", transform=ax.transAxes, color=INK2)
                continue
            ax.plot(d.tau, d.synthetic, color=NEUTRAL, lw=1.6, label="Synthetic control")
            ax.plot(d.tau, d.treated, color=S1, lw=1.8, label="Reforming country")
            r = sc.loc[(ev, var)]
            ax.text(0.03, 0.95, f"post-mean gap {r.att_mean_post:+.2f}\nplacebo p (|gap|) = {r.placebo_p_att_restricted:.2f}",
                    transform=ax.transAxes, va="top", fontsize=8.5, color=INK2,
                    bbox=dict(facecolor=SURFACE, edgecolor="none", alpha=0.9, pad=1.5))
            if i == 0:
                ax.set_title(names[ev], loc="left")
            if j == 0:
                ax.set_ylabel(lab)
            if i == 1:
                ax.set_xlabel("Years from first election under new rules")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", ncol=2, fontsize=9)
    fig.suptitle("Electoral reforms move party counts, but not growth volatility",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(FIG / "reform_synthetic_controls.png", dpi=200)
    plt.close(fig)


def fig_toptwo():
    es = pd.read_csv(TAB / "us_toptwo_event_study.csv")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(-0.5, color=NEUTRAL, lw=0.8, ls="--")
    for st, c, off, lab in [("WA", S1, -0.08, "Washington (top-two from 2008)"),
                            ("CA", S2, 0.08, "California (top-two from 2012)")]:
        d = es[es.state == st]
        x = d.rel_congress + off
        ax.errorbar(x, d.coef * 100, yerr=1.96 * d.se * 100, fmt="o", ms=5, color=c, ecolor=c,
                    elinewidth=1.2, capsize=0, label=lab)
    ax.set_xlabel("Congress relative to first top-two election (−1 = reference; endpoints binned)")
    ax.set_ylabel("Δ defection rate vs other states (pp)")
    ax.set_title("Top-two primaries: defections were already rising before adoption", loc="left")
    ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIG / "toptwo_event_study.png", dpi=200)
    plt.close(fig)


def main():
    fig_validation()
    fig_synth()
    fig_toptwo()


if __name__ == "__main__":
    main()
