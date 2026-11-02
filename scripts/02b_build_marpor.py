"""Ideological polarization from Manifesto Project (MARPOR) platforms, measured identically for every
country (the US included), plus a MARPOR seat-based ENPP cross-check.

Polarization (Dalton 2008 form on the MARPOR rile scale, -100..100):
    PI = sqrt( sum_i s_i * ((rile_i - rile_bar) / 100)^2 ),  rile_bar = seat-weighted mean
with s_i the seat share among coded parties. Elections where coded parties hold < 70% of seats are dropped.
Each election's value is carried forward to every year until the country's next election.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
MIN_SEAT_COVERAGE = 0.70
YEAR_MAX = 2016

ISO3 = {
    "Albania": "ALB", "Argentina": "ARG", "Armenia": "ARM", "Australia": "AUS", "Austria": "AUT",
    "Azerbaijan": "AZE", "Belarus": "BLR", "Belgium": "BEL", "Bolivia": "BOL",
    "Bosnia-Herzegovina": "BIH", "Brazil": "BRA", "Bulgaria": "BGR", "Canada": "CAN", "Chile": "CHL",
    "Colombia": "COL", "Costa Rica": "CRI", "Croatia": "HRV", "Cyprus": "CYP",
    "Czech Republic": "CZE", "Denmark": "DNK", "Dominican Republic": "DOM", "Ecuador": "ECU",
    "Estonia": "EST", "Finland": "FIN", "France": "FRA", "Georgia": "GEO", "Germany": "DEU",
    "Greece": "GRC", "Hungary": "HUN", "Iceland": "ISL", "Ireland": "IRL", "Israel": "ISR",
    "Italy": "ITA", "Japan": "JPN", "Latvia": "LVA", "Lithuania": "LTU", "Luxembourg": "LUX",
    "Malta": "MLT", "Mexico": "MEX", "Moldova": "MDA", "Montenegro": "MNE", "Netherlands": "NLD",
    "New Zealand": "NZL", "North Macedonia": "MKD", "Norway": "NOR", "Panama": "PAN", "Peru": "PER",
    "Poland": "POL", "Portugal": "PRT", "Romania": "ROU", "Russia": "RUS", "Serbia": "SRB",
    "Slovakia": "SVK", "Slovenia": "SVN", "South Africa": "ZAF", "South Korea": "KOR", "Spain": "ESP",
    "Sri Lanka": "LKA", "Sweden": "SWE", "Switzerland": "CHE", "Turkey": "TUR", "Ukraine": "UKR",
    "United Kingdom": "GBR", "United States": "USA", "Uruguay": "URY",
}
# Excluded: German Democratic Republic (pre-1990 single election) and Northern Ireland (sub-national).


def election_measures(mp: pd.DataFrame) -> pd.DataFrame:
    mp = mp[mp.countryname.isin(ISO3)].copy()
    for c in ["absseat", "totseats", "rile"]:
        mp[c] = pd.to_numeric(mp[c], errors="coerce")
    mp["iso3"] = mp.countryname.map(ISO3)
    mp["year"] = mp.date.astype(int) // 100
    rows = []
    for (iso, date), g in mp.groupby(["iso3", "date"]):
        tot = g.totseats.dropna()
        if tot.empty or tot.iloc[0] <= 0:
            continue
        coded = g.dropna(subset=["absseat", "rile"])
        coded = coded[coded.absseat > 0]
        coverage = coded.absseat.sum() / tot.iloc[0]
        if coded.empty or coverage < MIN_SEAT_COVERAGE:
            continue
        s = coded.absseat / coded.absseat.sum()
        rbar = (s * coded.rile).sum()
        seated = g[g.absseat > 0].absseat
        rows.append({
            "iso3": iso, "year": int(g.year.iloc[0]),
            "polarization": float(np.sqrt((s * ((coded.rile - rbar) / 100) ** 2).sum())),
            "rile_range": float(coded.rile.max() - coded.rile.min()),
            "enpp_marpor": float(1 / ((seated / tot.iloc[0]) ** 2).sum()),
            "seat_coverage": coverage,
        })
    # Two elections in one year: keep the later one.
    return pd.DataFrame(rows).sort_values(["iso3", "year"]).drop_duplicates(["iso3", "year"], keep="last")


def annualize(el: pd.DataFrame) -> pd.DataFrame:
    out = []
    for iso, g in el.groupby("iso3"):
        years = pd.DataFrame({"year": range(g.year.min(), YEAR_MAX + 1)})
        out.append(years.merge(g, on="year", how="left").ffill().assign(iso3=iso))
    return pd.concat(out)[["iso3", "year", "polarization", "rile_range", "enpp_marpor"]]


def main() -> None:
    raw = sorted(RAW.glob("marpor_MPDS*.csv"))
    if not raw:
        raise SystemExit("No MARPOR file in data/raw (set MANIFESTO_API_KEY and rerun 01_download_data.py)")
    mp = pd.read_csv(raw[-1], low_memory=False)
    el = election_measures(mp)
    el.to_csv(OUT / "marpor_elections.csv", index=False)
    annualize(el).to_csv(OUT / "marpor_country_year.csv", index=False)
    print(f"elections={len(el)} countries={el.iso3.nunique()}")
    print(el[el.iso3.isin(["USA", "GBR", "DEU", "NLD"])].groupby("iso3")[["polarization", "enpp_marpor"]].mean().round(3))


if __name__ == "__main__":
    main()
