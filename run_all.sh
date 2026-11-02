#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python scripts/01_download_data.py
python scripts/02_build_ienp.py
if ls data/raw/marpor_MPDS*.csv >/dev/null 2>&1; then
  python scripts/02b_build_marpor.py
fi
python scripts/03_build_crosssection.py
python scripts/04_estimate.py
python scripts/05_figures.py
