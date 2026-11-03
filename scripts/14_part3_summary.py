"""Part III: Holm-adjusted primary family and figures (first-stage failures; within vs between)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, TAB, FIG = ROOT / "data" / "processed", ROOT / "output" / "tables", ROOT / "output" / "figures"
SURFACE, INK, INK2, GRID, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
S1, S2 = "#2a78d6", "#eb6834"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "font.size": 10, "axes.titlesize": 10.5,
    "axes.titleweight": "bold", "legend.frameon": False,
})


def holm(p: pd.Series) -> pd.Series:
    order = p.sort_values()
    adj = np.maximum.accumulate([(len(order) - i) * v for i, v in enumerate(order)])
    return pd.Series(np.minimum(adj, 1), index=order.index).reindex(p.index)


def family() -> pd.DataFrame:
    d = pd.read_csv(TAB / "antidefection_stacked.csv").set_index("outcome")
    e = pd.read_csv(TAB / "veto_player_panel.csv").set_index("test")
    f = pd.read_csv(TAB / "reform_catalogue_stacked.csv")
    fb = f[f["sample"] == "broad"].set_index("outcome")
    rows = [
        ("D1", "Anti-defection 2SLS: incohesion → |Δ fiscal|", d.loc["abs_dfiscal", "iv"],
         d.loc["abs_dfiscal", "RI_p_reduced_form"], "RI (reduced form)"),
        ("E1", "Cabinet parties → |Δ fiscal| (TWFE)", e.loc["E1", "coef"], e.loc["E1", "p"], "cluster"),
        ("E2", "Cabinet ideological range → |Δ fiscal| (TWFE)", e.loc["E2", "coef"], e.loc["E2", "p"], "cluster"),
        ("E3", "POLCON III → |Δ fiscal| (TWFE)", e.loc["E3", "coef"], e.loc["E3", "p"], "cluster"),
        ("E4", "Polarization × single-party → |Δ growth| (TWFE)", e.loc["E4", "coef"], e.loc["E4", "p"], "cluster"),
        ("F1", "Reform catalogue 2SLS: ENPP → |Δ growth|", fb.loc["abs_dgrowth", "iv"],
         fb.loc["abs_dgrowth", "RI_p_reduced_form"], "RI (reduced form)"),
        ("F2", "Reform catalogue 2SLS: ENPP → |Δ fiscal|", fb.loc["abs_dfiscal", "iv"],
         fb.loc["abs_dfiscal", "RI_p_reduced_form"], "RI (reduced form)"),
    ]
    out = pd.DataFrame(rows, columns=["test", "hypothesis", "estimate", "p", "inference"])
    out["holm"] = holm(out.p)
    out.to_csv(TAB / "part3_primary_holm.csv", index=False)
    return out


def fig_first_stages():
    d = pd.read_csv(TAB / "antidefection_by_event.csv")
    d = d[d.outcome == "abs_dfiscal"].copy()
    f = pd.read_csv(TAB / "reform_catalogue_by_event.csv")
    f = f[(f["sample"] == "broad") & (f.outcome == "abs_dgrowth")].copy()
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))
    panels = [
        (axes[0], f, "Electoral reforms (Bormann-Golder): ENPP change\naligned with Duverger direction",
         "Expected: > 0 (toward PR → more parties)", 1),
        (axes[1], d, "Anti-defection laws: party-incohesion change\naligned with tightening",
         "Expected: < 0 (tighter rules → more cohesion)", 1),
    ]
    for ax, t, title, note, _ in panels:
        t = t.copy()
        t["aligned"] = t.first_stage  # estimated on direction x post, so already aligned
        t = t.sort_values("aligned").reset_index(drop=True)
        colors = [S1 if p < 0.1 else NEUTRAL for p in t.p_first_stage]
        ax.axvline(0, color=INK2, lw=0.9)
        ax.scatter(t.aligned, range(len(t)), c=colors, s=40, edgecolor=SURFACE, linewidth=1, zorder=3)
        ax.set_yticks(range(len(t)))
        ax.set_yticklabels(t.event, fontsize=8.5)
        ax.grid(axis="y", visible=False)
        ax.set_title(title, loc="left")
        ax.set_xlabel(note)
    axes[0].text(0.99, 0.02, "blue: placebo p < 0.10", transform=axes[0].transAxes, ha="right",
                 fontsize=8.5, color=INK2)
    fig.suptitle("Neither shock moves the variable it is supposed to move",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "part3_first_stages.png", dpi=200)
    plt.close(fig)


def fig_within_between():
    e = pd.read_csv(TAB / "veto_player_panel.csv").set_index("test")
    w = pd.read_csv(TAB / "incohesion_between_within.csv")
    v = pd.read_csv(PROC / "veto_player_panel.csv")
    v = v[v.year.between(1980, 2022)]
    sd = {"n_cab_parties": v.n_cab_parties.std(), "cab_range": v.cab_range.std(),
          "h_polcon3": v.h_polcon3.std(), "incohesion": v[v.polyarchy > 0.5].incohesion.std()}
    rows = [
        ("Within: cabinet parties (E1)", e.loc["E1", "coef"] * sd["n_cab_parties"], e.loc["E1", "se"] * sd["n_cab_parties"], "within"),
        ("Within: cabinet ideological range (E2)", e.loc["E2", "coef"] * sd["cab_range"], e.loc["E2", "se"] * sd["cab_range"], "within"),
        ("Within: POLCON III (E3)", e.loc["E3", "coef"] * sd["h_polcon3"], e.loc["E3", "se"] * sd["h_polcon3"], "within"),
        ("Within: party incohesion, polyarchy>0.7", *(w.iloc[1][["coef", "se"]] * sd["incohesion"]), "within"),
        ("Between: party incohesion, polyarchy>0.7", *(w.iloc[0][["coef", "se"]] * sd["incohesion"]), "between"),
        ("Between: party incohesion, polyarchy>0.5", *(w.iloc[2][["coef", "se"]] * sd["incohesion"]), "between"),
        ("Between: POLCON III", *(w.iloc[5][["coef", "se"]] * sd["h_polcon3"]), "between"),
    ][::-1]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.axvline(0, color=INK2, lw=0.9)
    for i, (lab, b, se, kind) in enumerate(rows):
        c = S1 if kind == "within" else S2
        ax.plot([b - 1.96 * se, b + 1.96 * se], [i, i], color=c, lw=1.6, solid_capstyle="round")
        ax.plot(b, i, "o", ms=7, color=c, mec=SURFACE, mew=1.5,
                label={"within": "Within country (TWFE)", "between": "Between country (Mundlak)"}[kind])
    h, l = ax.get_legend_handles_labels()
    uniq = dict(zip(l, h))
    ax.legend(uniq.values(), uniq.keys(), loc="upper left", fontsize=8.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Effect on |Δ fiscal balance| (pp) per 1 SD of regressor, 95% CI (country-clustered)")
    ax.set_title("Veto-player stabilization appears between countries, not within them", loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "part3_within_between.png", dpi=200)
    plt.close(fig)


def main():
    pd.set_option("display.width", 200)
    print(family().round(4).to_string())
    fig_first_stages()
    fig_within_between()


if __name__ == "__main__":
    main()
