"""Part IV: Holm-adjusted family and figures for designs G (budget punctuation) and H (V-Party)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyreadr

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


def holm(p: pd.Series) -> pd.Series:
    order = p.sort_values()
    adj = np.maximum.accumulate([(len(order) - i) * v for i, v in enumerate(order)])
    return pd.Series(np.minimum(adj, 1), index=order.index).reindex(p.index)


def family() -> pd.DataFrame:
    g = pd.read_csv(TAB / "budget_punctuation.csv")
    g = g[g.veto == "h_polcon3"].set_index("test")
    h = pd.read_csv(TAB / "vparty_party_models.csv").set_index("test")
    f = pd.read_csv(TAB / "vparty_fiscal_models.csv").set_index("test")
    rows = [
        ("G1", "POLCON → budget composition distance", "−", g.loc["G1", "coef"], g.loc["G1", "p"]),
        ("G2", "POLCON → median |real function change|", "−", g.loc["G2", "coef"], g.loc["G2", "p"]),
        ("G3", "POLCON → share of large (>25%) changes", "+", g.loc["G3", "coef"], g.loc["G3", "p"]),
        ("G4", "POLCON → L-kurtosis (country-decade)", "+", g.loc["G4", "coef"], g.loc["G4", "p"]),
        ("H1", "Lagged nomination inclusiveness → party cohesion", "−", h.loc["H1", "coef"], h.loc["H1", "p"]),
        ("H3", "Governing-party cohesion → |Δ fiscal|", "+", f.loc["H3", "coef"], f.loc["H3", "p"]),
    ]
    out = pd.DataFrame(rows, columns=["test", "hypothesis", "predicted_sign", "estimate", "p"])
    out["holm"] = holm(out.p)
    out.to_csv(TAB / "part4_primary_holm.csv", index=False)
    return out


def fig_punctuation():
    q = pd.read_csv(PROC / "budget_punctuation_country_year.csv")
    g = pd.read_csv(TAB / "budget_punctuation.csv")
    long = []
    funcs = ["def", "ecaf", "educ", "envr", "gps", "hca", "heal", "pos", "rcr", "sp"]
    q = q.sort_values(["iso3", "year"])
    prev = q.groupby("iso3")[[f"gfs_{f}" for f in funcs] + ["exp_gdp", "year"]].shift()
    for f in funcs:
        s, sp = q[f"gfs_{f}"], prev[f"gfs_{f}"]
        gg = np.log(s / sp) + np.log(q.exp_gdp / prev.exp_gdp) + np.log1p(q.growth / 100)
        ok = (prev.year == q.year - 1) & (s >= 0.5) & (sp >= 0.5)
        long.append(gg.where(ok))
    x = pd.concat(long).dropna()
    x = x[x.abs() <= 2].to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    bins = np.linspace(-1, 1, 81)
    hist, edges = np.histogram(x, bins=bins, density=True)
    centers = (edges[:-1] + edges[1:]) / 2
    ax.plot(centers, hist, color=S1, lw=1.8, label="Observed real function changes")
    mu, sd = np.median(x), x.std()
    ax.plot(centers, np.exp(-0.5 * ((centers - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi)), color=NEUTRAL,
            lw=1.6, ls="--", label="Normal, same SD")
    ax.set_yscale("log")
    ax.set_ylim(1e-2, None)
    ax.set_xlabel("Annual real change in spending on a COFOG function (log points)")
    ax.set_ylabel("Density (log scale)")
    ax.set_title("Budgets everywhere are punctuated (73 countries, 1972–2021)", loc="left")
    ax.legend(loc="upper right", fontsize=8.5)

    ax = axes[1]
    sds = {"comp_dist": q.comp_dist.std(), "median_abs_g": q.median_abs_g.std(), "large_share": q.large_share.std()}
    dec = pd.read_csv(PROC / "budget_punctuation_country_decade.csv")
    sds["lkurt"] = dec.lkurt.std()
    labels = {"comp_dist": "G1 composition change (−)", "median_abs_g": "G2 median change (−)",
              "large_share": "G3 large-change share (+)", "lkurt": "G4 L-kurtosis (+)"}
    colors = {"h_polcon3": S1, "n_cab_parties": S2, "incohesion": NEUTRAL}
    names = {"h_polcon3": "POLCON III", "n_cab_parties": "Cabinet parties", "incohesion": "Party incohesion"}
    order = ["comp_dist", "median_abs_g", "large_share", "lkurt"]
    for j, veto in enumerate(["h_polcon3", "n_cab_parties", "incohesion"]):
        d = g[(g.veto == veto) & g.outcome.isin(order)].set_index("outcome").reindex(order)
        for i, o in enumerate(order):
            r = d.loc[o]
            sdx = r.coef_per_sd / r.coef if r.coef != 0 else 1
            b, se = r.coef_per_sd / sds[o], r.se * sdx / sds[o]
            y = len(order) - 1 - i + (1 - j) * 0.22
            ax.plot([b - 1.96 * se, b + 1.96 * se], [y, y], color=colors[veto], lw=1.5)
            ax.plot(b, y, "o", ms=6, color=colors[veto], mec=SURFACE, mew=1.2, label=names[veto] if i == 0 else None)
    ax.axvline(0, color=INK2, lw=0.9)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([labels[o] for o in order][::-1], fontsize=9)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Within-country effect of +1 SD veto measure, in outcome SDs (95% CI)")
    ax.set_title("…but veto players do not shape the punctuation within countries", loc="left")
    ax.legend(loc="upper right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIG / "part4_budget_punctuation.png", dpi=200)
    plt.close(fig)


def fig_vparty():
    vp = pyreadr.read_r(str(RAW / "vparty.RData"))["vparty"]
    us = vp[(vp.country_text_id == "USA") & vp.v2paenname.isin(["Democratic Party", "Republican Party"])].copy()
    us["party"] = np.where(us.v2paenname == "Democratic Party", "D", "R")
    us["congress"] = ((us.year - 1788) // 2 + 1).astype(int)
    pc = pd.read_csv(PROC / "us_house_party_congress.csv")
    d = us.merge(pc, on=["congress", "party"]).dropna(subset=["v2padisa", "defection_rate"])
    h = pd.read_csv(TAB / "vparty_party_models.csv").set_index("test")
    v = pd.read_csv(TAB / "vparty_validation.csv")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axes[0]
    for p, c, lab in [("D", S1, "Democrats"), ("R", S2, "Republicans")]:
        s = d[d.party == p].sort_values("year")
        ax.scatter(s.v2padisa, s.defection_rate * 100, color=c, s=30, edgecolor=SURFACE, label=lab, zorder=3)
    ax.set_xlabel("V-Party internal cohesion (v2padisa; higher = less elite disagreement)")
    ax.set_ylabel("House party-unity defection rate (%)")
    ax.set_title(f"Validation fails: r = {v.r.iloc[0]:+.2f} (expected ≤ −0.5)", loc="left")
    ax.legend(loc="upper left", fontsize=8.5)

    ax = axes[1]
    rows = [("H1 nomination inclusiveness, lagged (primary)", "H1"),
            ("H1b nomination inclusiveness, same wave", "H1b"),
            ("H2 personalization, lagged", "H2")][::-1]
    for i, (lab, t) in enumerate(rows):
        r = h.loc[t]
        sdx = r.coef_per_sd / r.coef
        b, se = r.coef_per_sd / r.sd_outcome, r.se * sdx / r.sd_outcome
        c = S1 if t == "H1" else NEUTRAL
        ax.plot([b - 1.96 * se, b + 1.96 * se], [i, i], color=c, lw=1.6)
        ax.plot(b, i, "o", ms=7, color=c, mec=SURFACE, mew=1.2)
    ax.axvline(0, color=INK2, lw=0.9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("+1 SD effect on cohesion, in SDs (party + country-election FE)")
    ax.set_title("Candidate selection does not predict later cohesion", loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "part4_vparty.png", dpi=200)
    plt.close(fig)


def main():
    pd.set_option("display.width", 200)
    print(family().round(4).to_string())
    fig_punctuation()
    fig_vparty()


if __name__ == "__main__":
    main()
