# Pre-analysis plan, Part IV: budget punctuation and the party-organization first stage

Committed **before** any outcome regression for designs G and H was run. It extends Parts II–III.

**Why.** Part III left two specific gaps.
1. Veto-player measures did not lower *average* annual fiscal change within countries.
   Punctuated-equilibrium theory (Jones et al. 2009) predicts that institutional friction
   suppresses *moderate* changes and amplifies rare *large* ones. A null on the mean could hide
   both effects.
2. Anti-defection laws did not move party cohesion, so the cohesion → steadier-budgets association
   (C1b) still has no first stage. Theory (Hazan & Rahat 2010; Carey 2007) points to how parties
   select their candidates.

## Design G: veto players and budget punctuation

**Data.**
- IMF GFS COFOG spending shares via QoG (`gfs_*`): 10 functions, 1972–2021.
- IMF general-government expenditure, % GDP: Public Finances in Modern History `exp`, with Fiscal
  Monitor `G_X_G01_GDP_PT` filling gaps.
- WDI real GDP growth.

**Constructed outcomes (country-year).**
- **Composition distance** (Tsebelis & Chang 2004): Euclidean distance between the year-t and
  year-(t−1) vectors of function shares (pp). Requires both years present and shares summing to
  95–105.
- **Real function growth:** g_f,t = Δlog share_f + Δlog(expenditure/GDP) + log(1 + growth/100).
  - Functions with a share below 0.5% in either year are excluded.
  - |g_f,t| > 2 is treated as a data break and dropped.
- **Central tendency:** median over functions of |g_f,t|.
- **Tail:** share of a country-year's functions with |g_f,t| > 0.25. The threshold is fixed here.
- **L-kurtosis** (Hosking τ4) of all g_f,t within a country-decade with ≥ 30 function-years. This is
  the standard punctuation statistic; higher means more punctuated.

**Veto measures.**
- Henisz POLCON III (primary).
- ParlGov number of cabinet parties (secondary).
- V-Dem party incohesion, an informal veto player (secondary).

**Sample.** V-Dem polyarchy > 0.5. Years through 2016 when POLCON is used.

**Specifications.** Two-way fixed effects (country and year); for G4, country and decade.
SEs clustered by country.

| Test | Outcome | Prediction (POLCON) |
|---|---|---|
| **G1** | Composition distance | − |
| **G2** | Median \|g\| | − |
| **G3** | Large-change share | + |
| **G4** | L-kurtosis, country-decade | + |

**Secondary tests.**
- G1–G4 with cabinet parties and with incohesion.
- Aggregate tail: indicator for |Δ fiscal balance| > 3 pp, with POLCON (prediction +).

## Design H: party organization → cohesion (V-Party)

**Data.** V-Party v2 (`vdeminstitute/vdemdata`, `vparty`). The unit is party × election year.

**Variables (codebook directions).**
- `v2panom`: higher = more *inclusive* selectorate (0 leader … 4 all voters).
- `v2padisa`: higher = *more cohesive*, i.e. less visible elite disagreement or departures.
- `v2paind`: higher = more personalized.
- `v2pagovsup`: 0/1 = senior or junior governing partner.

**H-validation (fixed rule, as in Part II).** `v2padisa` counts as validated if both hold:
- for US Democrats and Republicans, its correlation with party-level House defection rates
  (Congress following the election) is ≤ −0.5;
- seat-weighted country cohesion correlates with V-Dem `v2pscohesv` at ≥ 0.5.

**Specifications.** SEs clustered by party.
- **H1 (primary):** `v2padisa` at election e on `v2panom` of the same party at e−1. Party fixed
  effects + country × election-year fixed effects. Prediction −: more inclusive selection means
  less cohesion.
- **H1b (secondary):** the same, contemporaneous.
- **H2 (secondary, two-sided):** `v2paind` at e−1 → `v2padisa`, same fixed effects.

**H3 (primary): governing-party cohesion and fiscal change.**
- For each country-year, take the seat-weighted mean `v2padisa` of the parties governing after the
  most recent election (`v2pagovsup` ∈ {0, 1}).
- Outcome |Δ fiscal|. Country + year FE, SEs clustered by country.
- Sample: polyarchy > 0.5, 1980–2019.
- Prediction (veto players, C1b): **+**, i.e. more cohesive governing parties mean larger fiscal
  changes.
- **H3-IV (exploratory):** the same, with governing parties' seat-weighted `v2panom` as the
  instrument. Reported only if H1's first stage has F > 10.

## Primary family (Holm, two-sided α = 0.05)

G1, G2, G3, G4 (POLCON), H1, H3: six tests.
