# Pre-analysis plan, Part III: veto players and identified shocks to party discipline

Committed **before** any outcome regression for designs D–F was run. It extends
`pre_analysis_plan.md` (Part II).

**Motivation.**
- The only Part II result that survived Holm correction (C1b: less cohesive parties go with lower
  fiscal volatility) is a cross-sectional correlation.
- Part II's reform design had only four events.
- Part III therefore (D) adds within-country shocks to party discipline, (E) tests veto-player
  predictions directly, and (F) pools a systematic electoral-reform catalogue.

**Theoretical frame: veto players (Tsebelis 2002).** More actors whose agreement is needed means a
larger winset of the status quo and smaller policy changes. Predictions:
- formal veto points (Henisz POLCON), coalition partners, and their ideological range all **lower**
  year-to-year fiscal change;
- loosening party discipline turns individual legislators into partial veto players, which also
  **lowers** fiscal change;
- polarization raises volatility **only when it translates into alternation between single-party
  governments** (Azzimonti & Talbert 2014), not under coalition government.

## Common elements

**Outcomes (annual).**
- **|Δ fiscal|**: absolute change in general-government net lending, % GDP (IMF). Primary for D and E.
- **|Δ growth|**: absolute change in real GDP growth (WDI via QoG).
- Secondary: 5-year trailing SD of each.

**Inference.** Wherever treatment varies within few countries (D, F), the primary p-value is
**randomization inference (RI)**: each event's timing (and direction) is reassigned to randomly drawn
eligible control countries, 2,000 draws. Cluster-robust SEs are reported but not used for inference
there. In the many-country panel (E), country-clustered SEs are the primary inference.

## Design D: anti-defection laws as shocks to party discipline

**Events.** `data/reference/anti_defection_events.csv`: 14 dated changes in 7 countries.
- Tightening (+1): IND 1985, IND 2003, ISR 1991, BRA 2007, NZL 2001, NZL 2018, ZAF 2009, PNG 2001,
  UKR 2006, UKR 2014.
- Loosening (−1): NZL 2005, ZAF 2003, PNG 2010, UKR 2010.
- Dates come from the legal record; sources are listed in the file.
- Post = years ≥ `first_post_year`. The event year itself is dropped when `first_post_year` is
  later than the event year.

**Window.** τ ∈ [−6, +6] around `first_post_year`, years 1975–2023.

**Controls (per event).** Countries with V-Dem polyarchy > 0.5 in every window year that has data,
no event of their own in the window, and not among the treated countries.

**Estimation.**
- **First stage:** incohesion (−V-Dem `v2pscohesv`).
- **Instrument:** direction × post, a single signed instrument.
- **Stacked 2SLS** with stack × country and stack × year fixed effects.

**Hypotheses.**
- **D1 (primary):** 2SLS effect of incohesion on |Δ fiscal|. C1b predicts a negative sign.
- **D2 (secondary):** the same for |Δ growth|.
- **D-fs:** the first stage must be negative (tightening lowers incohesion). An RI p > 0.10 on the
  first stage marks D as uninformative.

## Design E: veto-player panel

**Data.**
- ParlGov `view_cabinet`. For year t, the cabinet is the last non-caretaker cabinet that started on
  or before 1 January of t.
- Cabinet measures:
  - number of cabinet parties;
  - ideological range: max − min ParlGov `left_right` among cabinet parties, 0 if single-party;
  - single-party indicator;
  - PM-party ideological swing: |`left_right` of PM party in t − that in t−1|.
- Henisz POLCON III (`h_polcon3`, via QoG) for the broad panel.
- MARPOR polarization (country-year, from Part I).

**Specifications.** Two-way fixed effects (country, year); SEs clustered by country.
- **E1:** |Δ fiscal| ~ number of cabinet parties (prediction −).
- **E2:** |Δ fiscal| ~ cabinet ideological range (−).
- **E3:** |Δ fiscal| ~ POLCON III, all countries, years 1980–2016, V-Dem polyarchy > 0.5 (−).
- **E4:** |Δ growth| ~ polarization × single-party + main effects (interaction +).
- **E5 (secondary):** |Δ fiscal| ~ PM-party swing × single-party + main effects (interaction +).

**Sample.** ParlGov countries, years 1980–2022 for fiscal and 1961–2022 for growth.

## Design F: systematic electoral-reform catalogue

**Events.** Changes in Bormann & Golder (DES) electoral-system family `gol_est` (1 majoritarian,
2 proportional, 3 mixed) between consecutive years within a country, subject to all of:
- previous coding in the immediately preceding year (no regime break);
- 1966 ≤ year ≤ 2015;
- V-Dem polyarchy > 0.5 in the year before (broad sample); > 0.7 for the clean sample.

**A priori direction (Duverger).**
- **+1** (toward proportionality): 1→3, 1→2, 3→2.
- **−1** (toward majoritarian): 2→3, 2→1, 3→1.

**Window and controls.**
- τ ∈ [−8, +10]; the τ = 0 election year is dropped.
- Controls per event: polyarchy > 0.5 at τ = −1, no `gol_est` change in the window, not treated.

**Estimation.** Stacked 2SLS of each outcome on ENPP, with ENPP instrumented by the single a priori
instrument direction × post. Stack × country and stack × year fixed effects.

**Hypotheses.**
- **F1 (primary):** effect on |Δ growth|.
- **F2 (primary):** effect on |Δ fiscal|.
- Secondary: 5-year SDs; the clean sample; per-event instruments estimated by LIML.

## Primary family for Part III (Holm, two-sided α = 0.05)

D1, E1, E2, E3, E4, F1, F2: seven tests.
