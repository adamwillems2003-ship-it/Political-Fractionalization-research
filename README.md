# Political Fractionalization and Macroeconomic Stability

Does party-system fragmentation cause macroeconomic volatility?

- **Part I** replicates and stress-tests the original design in
  [`docs/research_design.md`](docs/research_design.md): cross-country 2SLS with colonial legal
  origin and terrain ruggedness as instruments, and the US measured by an *Internal* Effective
  Number of Parties.
- **Part II** runs three pre-registered, more credible designs
  ([`docs/pre_analysis_plan.md`](docs/pre_analysis_plan.md)):
  - national electoral reforms;
  - US primary-rule changes, with a fragmentation measure validated against roll-call defections;
  - one intra-party cohesion measure applied to every country.
- **Part III** runs a second pre-registered round
  ([`docs/pre_analysis_plan_part3.md`](docs/pre_analysis_plan_part3.md)):
  - anti-defection laws as shocks to party discipline;
  - direct veto-player tests (ParlGov cabinets, Henisz POLCON);
  - a systematic catalogue of 22 electoral reforms (Bormann & Golder codes).

**Findings, critique, design choices and deviations are in [`RESULTS.md`](RESULTS.md).**

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MANIFESTO_API_KEY=...   # optional; enables the MARPOR polarization layer
bash run_all.sh                # ~10 min; downloads ~800 MB into data/raw/ (git-ignored)
```

Keep the API key in your shell or a git-ignored `.env`; it is never written to the repository.

| Step | Script | Output |
|---|---|---|
| Download | `scripts/01_download_data.py` | `data/raw/` |
| US IENP per Congress | `scripts/02_build_ienp.py` | `data/processed/us_ienp_by_congress.csv` |
| Platform polarization | `scripts/02b_build_marpor.py` | `data/processed/marpor_*.csv` |
| Country cross-section | `scripts/03_build_crosssection.py` | `data/processed/crosssection_{vdem,polity}.csv` |
| Part I estimation | `scripts/04_estimate.py` | `output/tables/` |
| Part I figures | `scripts/05_figures.py` | `output/figures/` |
| Roll-call defections + measure validation | `scripts/06_build_defections.py` | `data/processed/us_house_defections_member.csv`, `output/tables/measure_validation.csv` |
| Design A: electoral reforms | `scripts/07_electoral_reforms.py` | `output/tables/reform_*.csv` |
| Design B: US primaries | `scripts/08_us_primaries.py` | `output/tables/us_toptwo_*.csv`, `state_legislature_*.csv` |
| Design C + Holm family | `scripts/09_symmetric_cohesion.py` | `output/tables/symmetric_cohesion_crosssection.csv`, `primary_hypotheses_holm.csv` |
| Part II figures | `scripts/10_figures_designs.py` | `output/figures/` |
| Shared stacked-event / RI engine | `scripts/eventlib.py` | — |
| Design D: anti-defection laws | `scripts/11_antidefection.py` | `output/tables/antidefection_*.csv` |
| Design E: veto-player panel | `scripts/12_veto_players.py` | `output/tables/veto_player_panel.csv`, `incohesion_between_within.csv` |
| Design F: electoral-reform catalogue | `scripts/13_reform_catalogue.py` | `data/processed/reform_catalogue.csv`, `output/tables/reform_catalogue_*.csv` |
| Part III Holm family + figures | `scripts/14_part3_summary.py` | `output/tables/part3_primary_holm.csv`, `output/figures/part3_*.png` |

## Data sources

| Component | Variable | Source |
|---|---|---|
| Global fractionalization | `gol_enpp` (Golder ENPP) | Quality of Government Standard TS, Jan 2024 |
| Democracy filter / control | `vdem_polyarchy`, `p_polity2` | QoG (V-Dem, Polity V) |
| Growth, initial wealth | `wdi_gdpgr`, `mad_gdppc` | QoG (World Bank WDI, Maddison) |
| Fiscal balance | `GGXCNL_NGDP` (general govt net lending, % GDP) | IMF DataMapper API |
| Instruments | `legor_*` (La Porta legal origin), `rugged` | Nunn & Puga (2012) |
| US ideal points | DW-NOMINATE and Nokken-Poole, House | Voteview `HSall_members.csv` |
| US roll-call votes (87th–117th) | member votes → party-unity defections | Voteview `H{congress}_votes.csv` |
| US caucus rosters (104th–115th) | Freedom, Liberty, Tea Party, RSC, Main Street, Progressive, Blue Dog, New Dem, Populist | Clarke (2020, AJPS), Harvard Dataverse doi:10.7910/DVN/SYYMJ0 |
| Ideological platforms | `rile`, `absseat`, `totseats` | Manifesto Project MPDS2026a (API key) |
| Party cohesion, all countries | `v2pscohesv` | V-Dem (via `vdeminstitute/vdemdata`) |
| State primary types 1992–2010 | closed … top-two | McGhee et al. (2014, AJPS), Harvard Dataverse doi:10.7910/DVN/UDUJEI |
| Cabinets (37 countries) | party composition, PM, `left_right` | ParlGov (development release, `view_cabinet.csv`) |
| Formal veto points | `h_polcon3` (Henisz POLCON III) | QoG |
| Electoral-system family | `gol_est` (Bormann & Golder DES) | QoG |
| Anti-defection law dates | 14 adoptions and repeals | Hand-coded from the legal record: `data/reference/anti_defection_events.csv` (sources per row) |
| State-legislature party spread | `h_dem_sd`, `h_rep_sd`, `s_*_sd` | Shor & McCarty (2011), Harvard Dataverse doi:10.7910/DVN/K7ELHW |

Not used: CLEA (blocked to automated access). It is replaced by Golder ENPP, which uses the same
Laakso-Taagepera formula and matches MARPOR seat counts at r = 0.93.
