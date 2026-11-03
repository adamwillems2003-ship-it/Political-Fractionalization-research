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
python scripts/06_build_defections.py
python scripts/07_electoral_reforms.py
python scripts/08_us_primaries.py
python scripts/09_symmetric_cohesion.py
python scripts/10_figures_designs.py
cd scripts
python 11_antidefection.py
python 12_veto_players.py
python 13_reform_catalogue.py
python 14_part3_summary.py
python 15_budget_punctuation.py
python 16_vparty.py
python 17_part4_summary.py
