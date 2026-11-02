"""Build the US Internal Effective Number of Parties (IENP) per House Congress.

Primary: k-means on DW-NOMINATE (dim1, dim2) with k chosen by the Tibshirani gap statistic
(k=1..8, so "no factions beyond one bloc" is admissible). Alternatives: silhouette-chosen k,
fixed k in {3,4,5}, within-party Gaussian-mixture BIC, and Clarke (2020) caucus rosters.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

FIRST_CONGRESS, LAST_CONGRESS = 80, 115
K_MAX = 8
GAP_B = 20
SEED = 20261102
DEM, REP = 100, 200


def laakso_taagepera(labels: np.ndarray) -> float:
    _, counts = np.unique(labels, return_counts=True)
    s = counts / counts.sum()
    return float(1.0 / np.sum(s**2))


def kmeans_labels(X: np.ndarray, k: int) -> np.ndarray:
    if k == 1:
        return np.zeros(len(X), dtype=int)
    return KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X)


def within_dispersion(X: np.ndarray, labels: np.ndarray) -> float:
    return sum(((X[labels == c] - X[labels == c].mean(0)) ** 2).sum() for c in np.unique(labels))


def gap_statistic_k(X: np.ndarray, rng: np.random.Generator) -> int:
    lo, hi = X.min(0), X.max(0)
    gaps, sks = [], []
    for k in range(1, K_MAX + 1):
        logW = np.log(within_dispersion(X, kmeans_labels(X, k)))
        ref = []
        for _ in range(GAP_B):
            Xr = rng.uniform(lo, hi, size=X.shape)
            ref.append(np.log(within_dispersion(Xr, kmeans_labels(Xr, k))))
        ref = np.array(ref)
        gaps.append(ref.mean() - logW)
        sks.append(ref.std() * np.sqrt(1 + 1 / GAP_B))
    for k in range(1, K_MAX):
        if gaps[k - 1] >= gaps[k] - sks[k]:
            return k
    return K_MAX


def silhouette_k(X: np.ndarray) -> int:
    scores = {k: silhouette_score(X, kmeans_labels(X, k)) for k in range(2, K_MAX + 1)}
    return max(scores, key=scores.get)


def gmm_within_party_n(X: np.ndarray, party: np.ndarray) -> tuple[float, int]:
    labels = np.empty(len(X), dtype=object)
    total_k = 0
    for p in np.unique(party):
        Xp = X[party == p]
        if p == "O":
            labels[party == p] = "O"
            total_k += 1
            continue
        fits = [GaussianMixture(k, random_state=SEED, n_init=3).fit(Xp) for k in range(1, 6)]
        best = min(fits, key=lambda g: g.bic(Xp))
        labels[party == p] = [f"{p}_{l}" for l in best.predict(Xp)]
        total_k += best.n_components
    return laakso_taagepera(labels.astype(str)), total_k


def build_nominate_ienp() -> pd.DataFrame:
    m = pd.read_csv(RAW / "HSall_members.csv")
    m = m[(m.chamber == "House") & m.congress.between(FIRST_CONGRESS, LAST_CONGRESS)]
    m = m.dropna(subset=["nominate_dim1", "nominate_dim2"])
    rng = np.random.default_rng(SEED)
    rows = []
    for c, g in m.groupby("congress"):
        X = g[["nominate_dim1", "nominate_dim2"]].to_numpy()
        party = np.where(g.party_code == DEM, "D", np.where(g.party_code == REP, "R", "O"))
        k_gap = gap_statistic_k(X, rng)
        k_sil = silhouette_k(X)
        gmm_n, gmm_k = gmm_within_party_n(X, party)
        rows.append({
            "congress": c,
            "year_start": 1789 + 2 * (c - 1),
            "n_members": len(g),
            "enpp_nominal": laakso_taagepera(party),
            "k_gap": k_gap,
            "ienp_gap": laakso_taagepera(kmeans_labels(X, k_gap)),
            "k_silhouette": k_sil,
            "ienp_silhouette": laakso_taagepera(kmeans_labels(X, k_sil)),
            "ienp_k3": laakso_taagepera(kmeans_labels(X, 3)),
            "ienp_k4": laakso_taagepera(kmeans_labels(X, 4)),
            "ienp_k5": laakso_taagepera(kmeans_labels(X, 5)),
            "k_gmm_within_party": gmm_k,
            "ienp_gmm_within_party": gmm_n,
        })
        print(f"congress {c}: k_gap={k_gap} ienp_gap={rows[-1]['ienp_gap']:.2f} "
              f"k_sil={k_sil} gmm_k={gmm_k} ienp_gmm={gmm_n:.2f}")
    return pd.DataFrame(rows)


# Members in several caucuses are assigned to the most ideologically distinctive one.
CAUCUS_PRIORITY = {
    "R": ["hfc", "lib", "tea", "rsc", "rmsp"],
    "D": ["prog", "bdc", "new", "pop"],
}


def build_caucus_ienp() -> pd.DataFrame:
    f = pd.read_csv(RAW / "clarke" / "factions.tab")
    m = pd.read_csv(RAW / "HSall_members.csv", usecols=["congress", "chamber", "icpsr", "party_code"])
    m = m[m.chamber == "House"].drop(columns="chamber").drop_duplicates(["congress", "icpsr"])
    d = f.merge(m, on=["congress", "icpsr"], how="inner")
    d["party"] = np.where(d.party_code == DEM, "D", np.where(d.party_code == REP, "R", "O"))

    def bloc(r: pd.Series) -> str:
        for c in CAUCUS_PRIORITY.get(r.party, []):
            if r.get(c, 0) == 1:
                return f"{r.party}_{c}"
        return f"{r.party}_unaffiliated"

    d["bloc"] = d.apply(bloc, axis=1)
    out = d.groupby("congress").agg(
        ienp_caucus=("bloc", lambda b: laakso_taagepera(b.to_numpy())),
        caucus_n_members=("bloc", "size"),
    ).reset_index()
    shares = d.groupby(["congress", "bloc"]).size().unstack(fill_value=0)
    shares.div(shares.sum(1), axis=0).round(3).to_csv(OUT / "us_caucus_bloc_shares.csv")
    return out


def main() -> None:
    nom = build_nominate_ienp()
    cau = build_caucus_ienp()
    out = nom.merge(cau, on="congress", how="left")
    out.to_csv(OUT / "us_ienp_by_congress.csv", index=False)
    print(out.round(2).to_string())


if __name__ == "__main__":
    main()
