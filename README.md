# Political Fractionalization and Macroeconomic Stability

Replication pipeline and critical assessment of the research design in
[`docs/research_design.md`](docs/research_design.md): does party-system fractionalization
(with the US measured by an *Internal* Effective Number of Parties) cause macroeconomic volatility,
identified by 2SLS with colonial legal origin and terrain ruggedness as instruments?

**Findings, critique and all design choices are in [`RESULTS.md`](RESULTS.md).**

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash run_all.sh        # ~3 min; downloads ~130 MB into data/raw/ (git-ignored)
```

| Step | Script | Output |
|---|---|---|
| Download | `scripts/01_download_data.py` | `data/raw/` |
| US IENP per Congress | `scripts/02_build_ienp.py` | `data/processed/us_ienp_by_congress.csv`, `us_caucus_bloc_shares.csv` |
| Country cross-section | `scripts/03_build_crosssection.py` | `data/processed/crosssection_{vdem,polity}.csv` |
| Estimation & robustness | `scripts/04_estimate.py` | `output/tables/*.csv` |
| Figures | `scripts/05_figures.py` | `output/figures/*.png` |

## Data sources

| Component | Variable | Source |
|---|---|---|
| Global fractionalization | `gol_enpp` (Golder ENPP) | Quality of Government Standard TS, Jan 2024 |
| Democracy filter / control | `vdem_polyarchy`, `p_polity2` | QoG (V-Dem, Polity V) |
| Growth, initial wealth | `wdi_gdpgr`, `mad_gdppc` | QoG (World Bank WDI, Maddison) |
| Fiscal balance | `GGXCNL_NGDP` (general govt net lending, % GDP) | IMF DataMapper API |
| Instruments | `legor_*` (La Porta legal origin), `rugged` | Nunn & Puga (2012) |
| US roll-call ideal points | DW-NOMINATE dim 1–2, House | Voteview `HSall_members.csv` |
| US caucus rosters (104th–115th) | Freedom, Liberty, Tea Party, RSC, Main Street, Progressive, Blue Dog, New Dem, Populist | Clarke (2020, AJPS), Harvard Dataverse doi:10.7910/DVN/SYYMJ0 |

Not used: CLEA (blocked to automated access; replaced by Golder ENPP, same Laakso-Taagepera
formula) and MARPOR (requires an API key; only needed for the design's secondary
"ideological platforms" layer).
