# Pre-analysis plan: credible tests of fractionalization → macro volatility

Written and committed **before** any outcome regression for designs A–C was run. Measures,
samples, estimators and the primary hypothesis family are fixed here. Anything not listed is
exploratory and is labelled as such in the write-up.

Why this plan exists: the cross-sectional 2SLS in `RESULTS.md` Part I relied on time-invariant
instruments with doubtful exclusion and a US measure whose value depended on post-hoc choices.
The designs below use within-unit policy changes instead, together with measures validated
against observed legislative behaviour.

## Validated measure of intra-party fragmentation (used in B and C)

**Party-unity defection rate.**
- A *party-unity vote* is a roll call where a majority of voting Democrats opposes a majority of
  voting Republicans (the CQ definition). Only Yea/Nay votes count (Voteview `cast_code` 1–6).
- A member's defection rate in a Congress is the share of their party-unity votes cast against
  their own party's majority.
- Members with fewer than 20 party-unity votes are dropped, as are independents and third
  parties.
- Coverage: House, Congresses 87–117 (1961–2022).

**Validation rule (fixed now).** A candidate fragmentation measure counts as *validated* if its
correlation with the House mean defection rate (party × Congress, or year for country-level
measures) is at least |0.5| in the expected sign. Candidates:
- within-party SD of Nokken-Poole dim-1 scores (expected +);
- the IENP variants from `scripts/02_build_ienp.py` (expected +);
- V-Dem `v2pscohesv` legislative party cohesion for the US (expected −).

Measures that fail are still reported, and analyses that depend on them are labelled exploratory.

## Design A: national electoral-system reforms

**Events.** Year 0 is the first general election under the new rules:

| Event | Reform | Year 0 |
|---|---|---|
| NZL96 | FPTP → MMP | 1996 |
| ITA94 | PR → mixed (Mattarellum) | 1994 |
| JPN96 | SNTV → mixed | 1996 |
| ITA06 | Mixed → PR with majority bonus (Porcellum) | 2006 |

**Window and controls.**
- Event time τ ∈ [−8, +10]. τ = 0 (the transition year) is excluded from post-period indicators;
  post means τ ≥ 1. Years are limited to 1980–2016.
- Clean controls: 18 democracies with no change of electoral-system family in 1980–2016: AUS, AUT,
  BEL, CAN, CHE, DEU, DNK, ESP, FIN, GBR, IRL, ISL, LUX, NLD, NOR, PRT, SWE, USA. France and
  Greece are excluded because of frequent reforms.

**First stage.** ENPP (Golder, via QoG). Secondary first-stage outcomes: V-Dem `v2pscohesv` and
MARPOR polarization.

**Outcomes.**
- Primary, annual:
  - Y1 = |Δ real GDP growth| (pp, WDI);
  - Y2 = |Δ general-government net lending, % GDP| (pp, IMF).
- Secondary: 5-year trailing SD of growth, 5-year trailing SD of fiscal balance, and the levels of
  growth and fiscal balance.

**Estimators.**
1. **Stacked event study.** One stack per event: the treated country plus clean controls within
   the window. Fixed effects for stack × country and stack × year. Event-time × treated dummies,
   with τ = −1 as the reference. SEs clustered by country.
2. **Stacked 2SLS (primary).** Y on ENPP, with ENPP instrumented by the four post × treated_e
   indicators and the same fixed effects. The coefficient is the effect per effective party.
   Report the cluster-robust first-stage F and the Anderson-Rubin set.
3. **Synthetic control** for each event, applied to ENPP and to the two 5-year trailing SDs.
   - Donor weights are nonnegative, sum to one, and fit all pre-period values of that outcome.
   - Inference by in-space placebo: the rank of the treated unit's post/pre RMSPE ratio among all
     donors.

## Design B: US primary-rule changes

**B1. Top-two primaries and House members.**
- Units: member × Congress, Congresses 105–117.
- Treated: Washington from the 111th Congress (first elected under top-two in 2008) and California
  from the 113th (2012). Louisiana is excluded (jungle-primary history).
- Primary outcome: party-unity defection rate. Secondary: |Nokken-Poole dim 1|.
- Main specification: treated-state × post indicator with state FE and party × Congress FE;
  separate WA and CA terms plus a pooled term; SEs clustered by state.
- Variants:
  - member fixed effects (within-incumbent change);
  - event study by Congress relative to the reform (−4…+4).
- Randomization inference: placebo assignment of the WA and CA timing to every never-treated state.

**B2. Primary openness in state legislatures.**
- Units: state × party × year, 1993–2011, lower chambers (upper chambers secondary).
- Primary openness comes from the McGhee et al. (2014) coding of the most recent election before
  year t. Openness index: closed 0, semi-closed 1, semi-open 2, open 3, top-two/blanket/nonpartisan
  4. Alternative: the binary `openall`.
- Outcome: within-party SD of Shor-McCarty NP scores (`h_dem_sd`, `h_rep_sd`).
- Specification: TWFE with state × party FE and party × year FE; SEs clustered by state.
- Exploratory unless within-party SD passes the validation rule above.

## Design C: symmetric intra-party measurement

The same measure is applied to every country; the US-only IENP is dropped. The measure is V-Dem
`v2pscohesv` (legislative party cohesion), with incohesion = −`v2pscohesv`.

**C1. Cross-section** (V-Dem > 0.7 sample from Part I, with the US coded at Golder ENPP):
- OLS of each volatility outcome on ENPP + mean incohesion;
- 2SLS for ENPP controlling for incohesion;
- 2SLS for incohesion instrumented by legal origin + ruggedness (report F).

**C2. Reform panel:** incohesion as a first-stage outcome in Design A.

## Primary hypothesis family (Holm-adjusted across these 7 tests, two-sided α = 0.05)

| # | Test |
|---|---|
| A1 | Stacked 2SLS, ENPP → Y1 |
| A2 | Stacked 2SLS, ENPP → Y2 |
| B1 | Pooled top-two → defection rate |
| B2 | Primary openness → within-party SD (lower chambers) |
| C1a | Incohesion → growth SD (OLS, cross-section) |
| C1b | Incohesion → fiscal SD (OLS, cross-section) |
| C1c | ENPP → growth SD, 2SLS controlling incohesion |
