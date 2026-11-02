"""Figures: US IENP by construction method, and 2SLS robustness coefficient plot."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, TAB, FIG = ROOT / "data" / "processed", ROOT / "output" / "tables", ROOT / "output" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

SURFACE, INK, INK2, GRID, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "legend.frameon": False,
})


def label_end(ax, x, y, text, color):
    ax.annotate(text, (x, y), xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=9, color=INK2)
    ax.plot([x], [y], "o", ms=4, color=color)


def fig_us_ienp():
    us = pd.read_csv(PROC / "us_ienp_by_congress.csv")
    us = us[us.year_start <= 2016]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)

    ax = axes[0]
    series = [("enpp_nominal", "Nominal parties", NEUTRAL), ("ienp_gap", "k-means, gap statistic", S1),
              ("ienp_silhouette", "k-means, silhouette", S2), ("ienp_caucus", "Caucus rosters", S3)]
    for col, lab, c in series:
        s = us.dropna(subset=[col])
        ax.plot(s.year_start, s[col], color=c, lw=1.6, label=lab, drawstyle="steps-post")
    ax.set_title("Data-driven constructions disagree")
    ax.set_ylabel("Effective number of blocs (Laakso-Taagepera)")
    ax.legend(loc="upper left", fontsize=8.5)

    ax = axes[1]
    for col, k, c in [("ienp_k3", 3, S1), ("ienp_k4", 4, S2), ("ienp_k5", 5, S3)]:
        ax.axhline(k, color=NEUTRAL, lw=0.8, ls="--")
        ax.plot(us.year_start, us[col], color=c, lw=1.6, label=f"k = {k}", drawstyle="steps-post")
        label_end(ax, us.year_start.iloc[-1], us[col].iloc[-1], f"k = {k}", c)
    ax.text(us.year_start.iloc[0], 5.08, "dashed: mechanical ceiling N ≤ k", fontsize=8.5, color=INK2)
    ax.set_title("Fixed k: the value is set by the researcher")
    ax.legend(loc="upper left", fontsize=8.5, bbox_to_anchor=(0, 0.93))
    for a in axes:
        a.set_xlabel("First year of Congress (House)")
        a.set_ylim(0.8, 7.6)
    fig.suptitle("US House: Internal Effective Number of Parties by construction method, 1947–2016",
                 fontsize=12, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "us_ienp_methods.png", dpi=200)
    plt.close(fig)


def fig_robustness(y, title):
    r = pd.read_csv(TAB / f"robustness_{y}.csv")
    drop = ("Instrument: rugged only", "log(frac)", "US measure: ienp_gap")
    r = r[~r.spec.str.startswith(drop)].iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.5, 7))
    for i, row in r.iterrows():
        base = i == len(r) - 1
        ax.plot([row.ci_lo, row.ci_hi], [i, i], color=NEUTRAL, lw=1.4, solid_capstyle="round")
        ax.plot(row.coef, i, "o", ms=8 if base else 6, color=S1, mec=SURFACE, mew=1.5)
    ax.axvline(0, color=INK2, lw=0.9)
    ax.set_yticks(range(len(r)))
    ax.set_yticklabels([f"{s}  (F={f:.1f})" for s, f in zip(r.spec, r.first_stage_F)], fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("2SLS coefficient on fractionalization, with 95% CI (HC1)")
    ax.set_title(title, loc="left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.text(0.01, 0.012, "Not shown: ruggedness-only instrument (first-stage F = 0.4) and log(frac) "
             "(different units); both in output/tables. F = robust first-stage F.",
             fontsize=8, color=INK2)
    fig.savefig(FIG / f"robustness_{y}.png", dpi=200)
    plt.close(fig)


def main():
    fig_us_ienp()
    fig_robustness("growth_sd", "Effect on GDP-growth volatility: 2SLS across specifications")
    fig_robustness("fiscal_sd", "Effect on fiscal-balance volatility: 2SLS across specifications")


if __name__ == "__main__":
    main()
