"""Party-unity defection rates for House members, Congresses 87-117, and validation of candidate
fragmentation measures against them (rule fixed in docs/pre_analysis_plan.md)."""
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, TAB = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "output" / "tables"
VOTES = RAW / "voteview_votes"
VOTES.mkdir(parents=True, exist_ok=True)
CONGRESSES = range(87, 118)
MIN_UNITY_VOTES = 20
DEM, REP = 100, 200
VALIDATION_THRESHOLD = 0.5


def fetch_votes(c: int) -> Path:
    dest = VOTES / f"H{c:03d}_votes.csv"
    if not dest.exists():
        url = f"https://voteview.com/static/data/out/votes/H{c:03d}_votes.csv"
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    return dest


def defections_for_congress(c: int, members: pd.DataFrame) -> pd.DataFrame:
    v = pd.read_csv(fetch_votes(c), usecols=["congress", "rollnumber", "icpsr", "cast_code"])
    v = v[v.cast_code.between(1, 6)].copy()
    v["yea"] = v.cast_code <= 3
    m = members[members.congress == c][["icpsr", "party_code"]].drop_duplicates("icpsr")
    v = v.merge(m, on="icpsr")
    v = v[v.party_code.isin([DEM, REP])]
    pos = v.groupby(["rollnumber", "party_code"]).yea.agg(["sum", "count"])
    pos["nay"] = pos["count"] - pos["sum"]
    pos = pos[pos["sum"] != pos["nay"]]
    pos["maj_yea"] = pos["sum"] > pos["nay"]
    wide = pos.maj_yea.unstack()
    unity = wide.dropna()
    unity = unity[unity[DEM] != unity[REP]].index
    v = v[v.rollnumber.isin(unity)]
    v = v.merge(pos.maj_yea.reset_index(), on=["rollnumber", "party_code"])
    v["defect"] = v.yea != v.maj_yea
    out = v.groupby(["icpsr", "party_code"]).defect.agg(defection_rate="mean", unity_votes="size").reset_index()
    out = out[out.unity_votes >= MIN_UNITY_VOTES]
    out["congress"] = c
    out["n_unity_rollcalls"] = len(unity)
    return out


def main() -> None:
    members = pd.read_csv(RAW / "HSall_members.csv")
    members = members[members.chamber == "House"]
    frames = []
    for c in CONGRESSES:
        d = defections_for_congress(c, members)
        print(f"H{c}: unity rollcalls={d.n_unity_rollcalls.iloc[0]} members={len(d)} "
              f"mean defection={d.defection_rate.mean():.3f}")
        frames.append(d)
    mem = pd.concat(frames).merge(
        members[["congress", "icpsr", "state_abbrev", "district_code", "bioname",
                 "nominate_dim1", "nokken_poole_dim1"]].drop_duplicates(["congress", "icpsr"]),
        on=["congress", "icpsr"], how="left")
    mem["party"] = np.where(mem.party_code == DEM, "D", "R")
    mem.to_csv(OUT / "us_house_defections_member.csv", index=False)

    pc = mem.groupby(["congress", "party"]).agg(
        defection_rate=("defection_rate", "mean"),
        np_within_sd=("nokken_poole_dim1", "std"),
        nom_within_sd=("nominate_dim1", "std"),
    ).reset_index()
    pc.to_csv(OUT / "us_house_party_congress.csv", index=False)
    validate(mem, pc)


def validate(mem: pd.DataFrame, pc: pd.DataFrame) -> None:
    rows = []

    def rec(measure, level, x, y, expected, n):
        r = np.corrcoef(x, y)[0, 1]
        rows.append({"measure": measure, "level": level, "N": n, "corr_with_defection": r,
                     "expected_sign": expected,
                     "validated": bool(np.sign(r) == expected and abs(r) >= VALIDATION_THRESHOLD)})

    for col, lab in [("np_within_sd", "Within-party SD, Nokken-Poole dim 1"),
                     ("nom_within_sd", "Within-party SD, DW-NOMINATE dim 1")]:
        d = pc.dropna(subset=[col])
        rec(lab, "party x Congress", d[col], d.defection_rate, +1, len(d))

    chamber = mem.groupby("congress").defection_rate.mean().rename("defection_rate").reset_index()
    ienp = pd.read_csv(OUT / "us_ienp_by_congress.csv")
    d = ienp.merge(chamber, on="congress")
    for col in ["ienp_gap", "ienp_silhouette", "ienp_k3", "ienp_k4", "ienp_k5",
                "ienp_gmm_within_party", "ienp_caucus"]:
        dd = d.dropna(subset=[col])
        rec(f"IENP: {col}", "Congress", dd[col], dd.defection_rate, +1, len(dd))

    vd = pd.read_csv(RAW / "vdem_cohesion.csv")
    vd = vd[vd.country_text_id == "USA"][["year", "v2pscohesv"]]
    chamber["year"] = 1789 + 2 * (chamber.congress - 1)
    yr = pd.concat([chamber.assign(year=chamber.year + k) for k in (0, 1)])
    d = yr.merge(vd, on="year")
    rec("V-Dem v2pscohesv (party cohesion), US", "year", d.v2pscohesv, d.defection_rate, -1, len(d))

    out = pd.DataFrame(rows)
    out.to_csv(TAB / "measure_validation.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string())


if __name__ == "__main__":
    main()
