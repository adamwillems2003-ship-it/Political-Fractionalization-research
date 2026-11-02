# Results: Political Fractionalization and Macroeconomic Volatility

**Bottom line.** The data give no robust evidence that party-system fractionalization causes
macroeconomic volatility. The 2SLS point estimate for growth volatility is positive (+0.72 pp of
growth SD per additional effective party) but imprecise: p = 0.10, a first-stage F of 9.3, and a
weak-instrument-robust confidence set that includes zero. The fiscal-volatility estimate has the
*opposite* sign. Neither result survives the robustness checks. Two pieces of the original design
fail outright when tested:

- **The ruggedness instrument has no first-stage power** (F = 0.4).
- **The US "Internal ENP" is not a stable measurement.** Its value depends almost entirely on the
  clustering choice, and because the US is 1 of 56 observations it does not affect the
  cross-national estimate.

**Manifesto Project polarization layer (§4.5).** Seat-weighted ideological polarization from the
party platforms is measured the same way for every country. On it, the US sits at the 57th
percentile, unremarkable.

- **Western Europe and the Americas subsample:** in the ~40 countries MARPOR covers, the
  growth-volatility effect is conventionally significant (+0.7 to +1.0, p ≈ 0.02). But
  weak-instrument-robust intervals include zero, and adding continent controls removes the effect.
- **Polarization itself is *negatively* associated with growth volatility** in plain regressions
  without instruments. This survives continent controls, but the instruments cannot move
  polarization, so it stays a correlation.

---

## 1. First-principles critique of the original design

| # | Issue in `docs/research_design.md` | Severity | What I did |
|---|---|---|---|
| 1 | **Time-invariant instruments with country fixed effects.** Colonial origin and ruggedness do not vary within a country, so δᵢ absorbs them and β₁, β₂ are unidentified. The §3 spec cannot be estimated. | Fatal | Switched to a between-country cross-section (one row per country). Chosen with you. |
| 2 | **IENP and ENPP measure different things.** Formal parties can leave coalitions and bring down governments; US caucuses cannot. Roll-call ideal points also reflect leadership agenda control. Clustering measures how *separated* members are, not how *fragmented*. A blurred, overlapping Congress (1973–93) comes out as *one* bloc. | Severe | Built six IENP variants plus a caucus-roster version and compared them (§3). |
| 3 | **"US IENP ranges 3.2–4.5" is an artefact.** With fixed k the index cannot exceed k, so k = 4 gives about 3.7 and k = 5 about 4.6. Data-driven k gives about 2–3. | Severe | Fig. 1 right panel. |
| 4 | **Asymmetric harmonization.** Only the US gets intra-party measurement. Japan's LDP factions, Italy's DC *correnti*, and the Labour/Conservative wings are left as single parties. This is differential measurement error. | Moderate | Noted. Shown to be numerically irrelevant (§4.3). |
| 5 | **Exclusion restriction.** Legal origin is the classic instrument for *financial and regulatory* development (La Porta et al.), which affects volatility directly. Colonizers selected *where* to settle (Acemoglu, Johnson & Robinson). Ruggedness affects trade and income directly (Nunn & Puga's own paper). Controlling for "transport infrastructure" does not close these channels. | Severe | Diagnostics, Conley et al. (2012) bounds, alternative instrument sets (§4.4). |
| 6 | **What the instrument identifies.** Legal origin moves fractionalization through the electoral system (British origin → first-past-the-post → fewer parties, by Duverger's law). It therefore identifies the effect of the *majoritarian bundle*: fewer parties, but also district accountability and geographic targeting (Persson & Tabellini). That is not fractionalization alone. | Severe | Interpretive. Cannot be fixed with these instruments. |
| 7 | **Sample selection on democracy is post-treatment.** Democratic survival itself responds to macro crises. | Moderate | Report both V-Dem > 0.7 and Polity2 > 6 samples. |
| 8 | **Small N.** About 56–80 democracies with 1–2 instruments. Weak-instrument bias toward OLS and poor size of the usual t-tests. | Moderate | Report LIML, Anderson-Rubin sets, leave-one-out. |

## 2. Design choices made during implementation

These are the choices I made myself. Any of them can be changed in one place in the scripts.

1. **Identification:** between-country cross-section 2SLS, using HC1 robust SEs. *(chosen with you)*
2. **US IENP:** k-means on DW-NOMINATE (dim 1, dim 2), House only, one fit per Congress.
   - k is chosen by the **gap statistic** (k = 1…8). Silhouette cannot return k = 1, so it always forces factions.
   - Robustness variants: silhouette, fixed k ∈ {3, 4, 5}, a within-party Gaussian-mixture fit with BIC, and caucus rosters. *(rosters chosen with you)*
3. **Caucus blocs:** members in several caucuses are assigned to the most distinctive one.
   - Republicans: HFC > Liberty > Tea Party > RSC > Main Street.
   - Democrats: Progressive > Blue Dog > New Dem > Populist.
   - Everyone else is "unaffiliated" within their party.
4. **Instrument source:** La Porta legal-origin dummies taken from the Nunn–Puga file. QoG's
   `ht_colonial` was *rejected* because it codes the US, UK, Canada and Australia as "never colonized".
5. **Window and filtering:**
   - Years 1961–2016: WDI growth starts in 1961, Golder ENPP ends in 2016.
   - Only democratic country-years are used (V-Dem polyarchy > 0.7 primary, Polity2 > 6 alternative).
   - A country needs ≥ 10 such years to enter, and ≥ 8 for the fiscal outcome (IMF data start 1980).
6. **Outcomes:**
   - Volatility is the standard deviation over the country's democratic years. It is not detrended and not computed on a rolling window.
   - Fiscal balance is IMF WEO general-government net lending (% GDP), not IFS.
7. **Controls:**
   - Baseline: log Maddison GDP per capita in the first democratic year, plus mean polyarchy.
   - Extended: adds distance to coast (the transport channel) and continent dummies.
   - Human capital was not added: it costs observations at this N.
8. **MARPOR layer:** Dalton-style polarization on `rile`, weighted by seat share among parties with
   manifesto data. Specifics:
   - Elections where those parties hold less than 70% of seats are dropped.
   - Each election's value is carried forward until the next election.
   - A country needs ≥ 5 democratic years with data.
   - Dataset version MPDS2026a.
9. **Not implemented:** CLEA. It was replaced by Golder ENPP, which matches MARPOR's own seat
   counts at r = 0.93 across countries.

## 3. The US Internal Effective Number of Parties

![US IENP by method](output/figures/us_ienp_methods.png)

| Construction (House, 1961–2016) | Mean | Min | Max |
|---|---|---|---|
| Nominal parties | 1.94 | 1.78 | 2.02 |
| k-means, gap statistic (primary) | 2.16 | 1.00 | 4.74 |
| k-means, silhouette | 2.82 | 1.94 | 4.72 |
| k-means, k = 3 / 4 / 5 | 2.81 / 3.70 / 4.57 | — | ≤ k |
| Gaussian mixture within party, BIC | 2.73 | 1.89 | 4.28 |
| Caucus rosters (1995–2016 only) | 5.09 | 2.19 | 7.31 |

Across the 104th–114th Congresses, the variants are weakly or **negatively** correlated with
each other. For example, caucus-based vs gap-statistic IENP is r = −0.61
(`output/tables/us_ienp_correlations_104_114.csv`).

The caucus series rises mainly because caucuses were *founded and grew*: the RSC went from 63
members (108th Congress) to 172 (114th). That measures how organized factions are, which is not the same as how fragmented
the legislature is.

**Conclusion:** the design's claim that the US moves from a static 2.0 to a comparable 3.2–4.5 is
not robust. It holds only if the researcher picks k = 4 or 5.

## 4. Cross-national 2SLS

Sample: 56 democracies in the V-Dem > 0.7 sample and 80 in the Polity2 > 6 sample.
Fractionalization means 1.55–8.98 effective parties.

### 4.1 First stage (V-Dem sample, outcome = growth SD)

| | Coef. | SE | p |
|---|---|---|---|
| British legal origin | **−1.19** | 0.41 | 0.004 |
| Ruggedness | −0.19 | 0.21 | 0.35 |
| Robust first-stage F (joint) | **9.3** | | |

Legal origin works in the direction Duverger's law predicts: about one fewer effective party.
Ruggedness is irrelevant: alone its F is 0.42.

### 4.2 Main estimates

| Outcome | Sample | N | OLS | 2SLS (SE) | p | LIML | F | Over-id p | Anderson-Rubin 95% set |
|---|---|---|---|---|---|---|---|---|---|
| SD of GDP growth | V-Dem | 56 | −0.06 | **0.72** (0.43) | 0.10 | 0.78 | 9.3 | 0.48 | [−0.04, ∞) |
| SD of fiscal balance | V-Dem | 54 | −0.15 | −0.66 (0.52) | 0.20 | −0.84 | 8.6 | 0.19 | (−∞, 0.84] |
| Mean GDP growth | V-Dem | 56 | 0.05 | 0.05 (0.30) | 0.88 | 0.05 | 9.3 | 0.97 | [−1.88, 1.40] |
| SD of GDP growth | Polity | 80 | −0.15 | 0.12 (0.48) | 0.80 | 0.46 | 14.3 | **0.025** | [0.46, 1.08]* |
| SD of fiscal balance | Polity | 76 | −0.19 | **−1.29** (0.60) | 0.03 | −1.29 | 12.6 | 0.99 | [−5.14, −0.12] |
| Mean GDP growth | Polity | 80 | 0.00 | −0.44 (0.37) | 0.23 | −0.44 | 14.3 | 0.81 | [−2.29, 0.32] |

\* In this row the over-identification test rejects (p = 0.025), so the two instruments disagree.
The Anderson-Rubin test checks the coefficient value and instrument validity *jointly*. Its narrow
set here reflects the instruments being invalid, not precision.

How to read the table:
- **OLS** is close to zero everywhere.
- **2SLS on growth volatility** is positive but imprecise in the V-Dem sample and near zero in the Polity sample.
- **2SLS on fiscal volatility** is *negative*: more parties go with smoother budgets. It is significant only in the Polity sample. This is the opposite of the gridlock mechanism the design proposes.

### 4.3 Robustness (growth volatility)

![Robustness growth](output/figures/robustness_growth_sd.png)

The full tables for both outcomes are `output/tables/robustness_{growth_sd,fiscal_sd}.csv`.

- **US measure:** the coefficient ranges from 0.71 to 0.88 across all eight US constructions, and is 0.74 with the US dropped. The IENP harmonization does not matter for the causal estimate.
- **Instruments:**
  - Legal origin only (just-identified): 0.60 (p = 0.17), Anderson-Rubin set [−0.14, 2.68].
  - All five legal-origin families plus ruggedness: 0.76 (p = 0.07, F = 15.7).
- **Controls:** none gives 0.45 (p = 0.20); extended gives 0.62 (p = 0.18).
- **Functional form and outliers:** log(fractionalization) gives 2.20 (p = 0.10). Dropping Brazil, Belgium and Ecuador gives 1.05 (p = 0.10).
- **Leave-one-out:** the coefficient stays between 0.53 and 0.96, and no single deletion produces p < 0.05. Fiscal volatility stays between −0.88 and −0.26.
- **No specification** of growth volatility clears p < 0.05 with conventional or weak-IV-robust inference.

### 4.4 Exclusion-restriction diagnostics

Do the instruments predict other channels to volatility? Regressions on the instruments alone,
V-Dem sample:

| Dependent | British legal origin (p) | Ruggedness (p) |
|---|---|---|
| % European descent | **−38.7 (0.001)** | −5.0 (0.26) |
| Mean V-Dem polyarchy | **−0.035 (0.03)** | 0.002 (0.71) |
| Distance to coast | 0.09 (0.39) | **−0.07 (0.03)** |
| Rule of law (2000) | 0.16 (0.51) | 0.16 (0.11) |
| log initial GDP pc | −0.04 (0.83) | 0.05 (0.49) |

The instruments are not "as good as random" with respect to settler composition, democratic depth
and geography.

There is also a warning in the reduced form. Ruggedness lowers growth volatility (−0.30,
p = 0.06) while barely moving fractionalization. That pattern points to a direct channel, which
the over-identification test (p = 0.48) is too weak to detect at this N.

**Conley, Hansen & Rossi (2012) bounds.** Allow British legal origin a direct effect on growth SD
of up to ±δ:

| Max \|δ\| (pp of growth SD) | 95% union CI for 2SLS coefficient |
|---|---|
| 0 | [−0.13, 1.57] |
| 0.25 | [−0.25, 1.84] |
| 0.5 | [−0.38, 2.12] |
| 1.0 | [−0.71, 2.71] |

### 4.5 Manifesto Project: a symmetric ideological measure

Polarization is the seat-weighted dispersion of party platforms on MARPOR's left-right `rile`
scale, scaled 0–1. It is computed identically for all countries, so the US needs no special
treatment.

- Coverage: 40 countries in the V-Dem sample, 47 in the Polity sample.
- Distribution: median 0.13. Range from 0.04 (Malta) to 0.26 (Israel).
- US: 0.14, the 57th percentile.

**Correlations (V-Dem sample).**
- ENPP and polarization are distinct concepts: r = 0.40.
- Golder ENPP vs MARPOR seat-based ENPP: r = 0.93, which validates the main fractionalization variable.

**Estimates.** All 2SLS rows use the legal-origin and ruggedness instruments; the full table is
`output/tables/marpor_polarization.csv`.

| Model | Outcome | Sample | N | Coef (SE) | p | First-stage F | Anderson-Rubin 95% set |
|---|---|---|---|---|---|---|---|
| 2SLS frac, MARPOR subsample | growth SD | V-Dem | 40 | 1.02 (0.45) | 0.02 | 11.7 | [−0.05, 4.18] |
| — legal origin only | growth SD | V-Dem | 40 | 0.89 (0.44) | 0.04 | 11.5 | [−0.01, 2.51] |
| — + continents, coast | growth SD | V-Dem | 40 | 1.24 (0.89) | 0.16 | **3.3** | unbounded |
| — controlling polarization | growth SD | V-Dem | 40 | 0.82 (0.31) | 0.009 | 21.7 | [−0.11, 1.81] |
| 2SLS frac, MARPOR subsample | growth SD | Polity | 45 | 0.74 (0.31) | 0.02 | 29.6 | [−0.08, 1.05] |
| — + continents, coast | growth SD | Polity | 45 | 0.58 (0.58) | 0.32 | 7.7 | (−∞, 0.98] |
| 2SLS frac, MARPOR subsample | fiscal SD | V-Dem | 39 | −0.84 (0.60) | 0.17 | 15.7 | [−5.04, 0.38] |
| OLS polarization | growth SD | Polity | 47 | **−15.7** (5.2) | 0.003 | — | — |
| — + continents, coast | growth SD | Polity | 45 | **−17.3** (6.2) | 0.006 | — | — |
| OLS polarization, + continents, coast | fiscal SD | Polity | 44 | 8.2 (4.1) | 0.046 | — | — |
| 2SLS polarization | growth SD | Polity | 45 | −62.6 (43.3) | 0.15 | **3.1** | unbounded |

**Fractionalization, MARPOR subsample.** In the ~40 well-covered democracies, the
growth-volatility coefficient is larger and conventionally significant. Two things undercut it:
- **Weak-instrument-robust sets include zero**, even with legal origin as the only instrument.
- **Adding continent dummies collapses the first stage** (F 3–8) and the estimate. British legal
  origin in this subsample is essentially the Anglosphere: UK, Ireland, US, Canada, Australia,
  New Zealand, Cyprus, Israel and South Africa. The instrument mostly separates
  "Anglosphere vs. continental Europe and Latin America," and region absorbs that.

**Polarization.** Ideologically polarized party systems go with *smoother* growth (a 0.05 rise in
polarization, about 1 SD, is associated with roughly 0.8 pp lower growth SD) and somewhat *more*
volatile budgets.
- Both associations survive continent controls.
- The instruments do not predict polarization (F ≈ 2–4), so neither can be read causally.
- Nine specifications per outcome and sample were run, so treat single p ≈ 0.05 results with caution.
- This is the most interesting lead in the data: **ideological distance, not the number of
  parties**, is what correlates with macro outcomes. It points to a different research question
  than the one the design poses.

## 5. What would be needed for a credible test

- **Within-country variation from electoral reforms.** New Zealand 1996 (first-past-the-post → MMP), Italy 1993 and 2005, Japan 1994: event study or synthetic control. This removes the need for time-invariant instruments.
- **For the US internal pathway, primary-rule changes as natural experiments.** Top-two primaries in Washington 2008 and California 2010, and open vs closed primaries across state legislatures. Use these with a fragmentation measure validated *ex ante*, for example against roll-call defections on leadership votes, rather than a clustering k chosen after the fact.
- **Apply intra-party measurement to every country or to none.** For example, MARPOR-based dispersion or legislative-defection rates for all parliaments.

## Files

- `output/tables/main_{vdem,polity}.csv`: OLS, 2SLS, LIML, reduced form, diagnostics
- `output/tables/first_stage_{vdem,polity}.csv`
- `output/tables/robustness_{growth_sd,fiscal_sd}.csv`, `leave_one_out_*.csv`, `conley_bounds_growth_sd.csv`
- `output/tables/exclusion_diagnostics.csv`
- `output/tables/us_ienp_summary.csv`, `us_ienp_correlations_104_114.csv`
- `output/tables/marpor_polarization.csv`, `marpor_correlations_vdem.csv`
