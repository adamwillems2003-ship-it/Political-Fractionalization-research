"""Download raw inputs into data/raw/. Idempotent: skips files already present."""
import csv
import os
import sys
import zipfile
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "qog_std_ts_jan24.csv": "https://www.qogdata.pol.gu.se/data/qog_std_ts_jan24.csv",
    "HSall_members.csv": "https://voteview.com/static/data/out/members/HSall_members.csv",
    "rugged_data.zip": "https://diegopuga.org/data/rugged/rugged_data.zip",
}


def fetch(name: str, url: str) -> Path:
    dest = RAW / name
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[skip] {name}")
        return dest
    print(f"[get ] {url}")
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    print(f"[ok  ] {name} ({dest.stat().st_size/1e6:.1f} MB)")
    return dest


CLARKE_FILES = {"factions.tab": 3596325, "readme.txt": 3596331}
IMF_INDICATOR = "GGXCNL_NGDP"


def fetch_clarke() -> None:
    out = RAW / "clarke"
    out.mkdir(exist_ok=True)
    for name, fid in CLARKE_FILES.items():
        fetch(f"clarke/{name}", f"https://dataverse.harvard.edu/api/access/datafile/{fid}?format=original")


def fetch_imf() -> None:
    dest = RAW / f"imf_{IMF_INDICATOR}.csv"
    if dest.exists():
        print(f"[skip] {dest.name}")
        return
    url = f"https://www.imf.org/external/datamapper/api/v1/{IMF_INDICATOR}"
    vals = requests.get(url, timeout=120).json()["values"][IMF_INDICATOR]
    with open(dest, "w") as f:
        f.write("iso3,year,value\n")
        for iso, series in vals.items():
            for year, v in series.items():
                f.write(f"{iso},{year},{v}\n")
    print(f"[ok  ] {dest.name}")


STATLEG_FILES = {
    "statleg/mcghee_dem.csv": "https://dataverse.harvard.edu/api/access/datafile/2443343",
    "statleg/mcghee_rep.csv": "https://dataverse.harvard.edu/api/access/datafile/2443327",
    "statleg/shor_mccarty_aggregate.tab": "https://dataverse.harvard.edu/api/access/datafile/2690453?format=original",
}
VDEM_URL = "https://raw.githubusercontent.com/vdeminstitute/vdemdata/master/data/vdem.RData"


def fetch_statleg() -> None:
    (RAW / "statleg").mkdir(exist_ok=True)
    for name, url in STATLEG_FILES.items():
        fetch(name, url)


def fetch_vdem_cohesion() -> None:
    dest = RAW / "vdem_cohesion.csv"
    if dest.exists():
        print(f"[skip] {dest.name}")
        return
    import pyreadr
    rdata = fetch("vdem.RData", VDEM_URL)
    v = pyreadr.read_r(str(rdata))["vdem"]
    v[["country_text_id", "year", "v2pscohesv", "v2x_polyarchy"]].to_csv(dest, index=False)
    print(f"[ok  ] {dest.name}")


PARLGOV_URL = "https://parlgov.org/data/parlgov-development_csv-utf-8/{}.csv"


def fetch_parlgov() -> None:
    (RAW / "parlgov").mkdir(exist_ok=True)
    for view in ["view_cabinet", "view_party", "view_election"]:
        fetch(f"parlgov/{view}.csv", PARLGOV_URL.format(view))


IMF_EXTRA = ["exp", "G_X_G01_GDP_PT"]
VPARTY_URL = "https://raw.githubusercontent.com/vdeminstitute/vdemdata/master/data/vparty.RData"


def fetch_imf_expenditure() -> None:
    for code in IMF_EXTRA:
        dest = RAW / f"imf_{code}.csv"
        if dest.exists():
            print(f"[skip] {dest.name}")
            continue
        vals = requests.get(f"https://www.imf.org/external/datamapper/api/v1/{code}", timeout=120).json()["values"][code]
        with open(dest, "w") as f:
            f.write("iso3,year,value\n")
            for iso, series in vals.items():
                for year, v in series.items():
                    f.write(f"{iso},{year},{v}\n")
        print(f"[ok  ] {dest.name}")


MARPOR_VERSION = "MPDS2026a"


def fetch_marpor() -> None:
    key = os.environ.get("MANIFESTO_API_KEY")
    dest = RAW / f"marpor_{MARPOR_VERSION}.csv"
    if dest.exists():
        print(f"[skip] {dest.name}")
        return
    if not key:
        print("[warn] MANIFESTO_API_KEY not set; skipping MARPOR (ideological polarization layer)")
        return
    url = "https://manifesto-project.wzb.eu/api/v1/get_core"
    rows = requests.get(url, params={"key": MARPOR_VERSION, "api_key": key}, timeout=300).json()
    with open(dest, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"[ok  ] {dest.name}")


def main() -> int:
    for name, url in SOURCES.items():
        fetch(name, url)
    fetch_clarke()
    fetch_imf()
    fetch_statleg()
    fetch_vdem_cohesion()
    fetch_parlgov()
    fetch_imf_expenditure()
    fetch("vparty.RData", VPARTY_URL)
    fetch_marpor()
    z = RAW / "rugged_data.zip"
    with zipfile.ZipFile(z) as zf:
        zf.extractall(RAW / "rugged")
    print("[ok  ] extracted rugged_data.zip ->", sorted(p.name for p in (RAW / "rugged").iterdir()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
