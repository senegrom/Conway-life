# Open-problem register

**Last checked:** 2026-08-23

## Status policy

“Open” is a dated evidence claim, not an eternal truth. Before starting a major search:

1. re-open the primary source;
2. search the ConwayLife forum and LifeWiki revision history;
3. search recent papers and citations;
4. contact the problem author for formal questions where practical;
5. record the status check in `docs/research-log.md`.

## Tier 1: precise formal questions

### LIFE-F001 — optimal zero-padding thickness

For a finite rectangular pattern \(P\), determine the minimal padding thickness \(i\) in the Salo–Törmä image-extension statement.

- Source ID: Q28820954.
- Status evidence: author-current.
- Likely method: SAT/SMT, transfer matrices, symbolic dynamics, certificate extraction.
- Useful partial result: prove or disprove sufficiency at a fixed smaller thickness.
- Verification: exhaustive local checker plus SAT proof log.

### LIFE-F002 — finite-support predecessor decidability

Is it decidable whether a finite-support Life configuration has a finite-support predecessor?

- Source ID: Q52773486.
- Important distinction: finite-instance one-step predecessor existence is computationally hard, but this exact global finite-support question remains separately listed.
- Likely method: tiling reductions or a positive bounded-completion theorem.

### LIFE-F003 — smallest periodic target with no periodic predecessor

What is the smallest fundamental domain of a spatially periodic configuration with a predecessor but no spatially periodic predecessor?

- Source ID: Q37342605.
- Current construction in the 2025 paper: \(6210\times37800\).
- Likely method: minimise the gadget system, symmetry quotienting, SAT search.
- Verification: one SAT certificate of a predecessor plus UNSAT certificates over all relevant periodic predecessor domains.

### LIFE-F004 — generic nilpotence

Is Conway Life generically nilpotent?

- Source ID: Q99848042.
- Theory-heavy dynamical-systems question.
- Computational experiments may suggest structure but will not settle it alone.

### LIFE-F005 — sensitivity to initial conditions

Is Conway Life sensitive to initial conditions in the topological-dynamics sense?

- Source ID: Q15988843.
- Requires a precise topological definition and proof, not empirical “chaos.”

### LIFE-F006 — temporal-periodic density

For each \(p\), are finite-support points dense in the subshift of temporally \(p\)-periodic configurations?

- Source ID: Q97141311(p).
- Includes still-life finitization at \(p=1\).

### LIFE-F007 — strong irreducibility of temporal-periodic subshifts

For each \(p\), is the temporally \(p\)-periodic subshift strongly irreducible?

- Source ID: Q36263295(p).
- Transfer/SFT methods may produce bounded counterexamples or gluing bounds.

### LIFE-F008 — still-life finitization

Are finite-support fixed points dense among all fixed points?

- Status evidence: paper-open.
- Computational direction: determine the largest patch sizes for which every locally extendable finite patch has a finite still-life completion, or find structured obstruction families.

### LIFE-F009 — strong block-map universality

Life is semiweakly universal as a one-step block map. Is it strongly universal?

- Status evidence: explicit Question 2 in the 2025 paper; secondary review in July 2026.
- Strong means simulated assignments correspond bijectively to allowed Life predecessors, with no extraneous predecessors.
- A bounded route tests necessary periodic-fibre counts for small macrotile areas.

### LIFE-F010 — higher powers

Can the one-step backward-computation results be extended to fixed higher powers of Life?

- Status evidence: explicit Question 3 in the 2025 paper.
- Likely method: multi-time-layer SAT gadgets and compositional forcing.

### LIFE-F011 — universal backward chains

Are there Life configurations such that every predecessor chain performs universal computation backwards?

- Status evidence: explicit Question 4 in the 2025 paper.
- Extremely ambitious.

## Tier 2: precise community questions

### LIFE-C001 — four-row live-cell Garden of Eden

Does a Garden of Eden exist whose live cells are restricted to four consecutive rows?

- Status evidence: LifeWiki current page.
- Distinguish this from the proved nonexistence of height-4 **orphans** under the specified-cell definition.
- Strong starter target.

### LIFE-C002 — unknown spaceship speeds

Examples listed by the 2026 ikpx2 tutorial include:

- \((2,1)c/7\);
- orthogonal \(c/8\);
- orthogonal \(3c/8\);
- diagonal \(c/9\).

- Status evidence: community-dynamic.
- Recheck the Spaceship Discussion thread and status page before each run.
- Tools: ikpx2 for oblique/SAT-style extension; LSSS/LLSSS for slice searches.

### LIFE-C003 — smallest unsynthesizable still life

Reduce the 154-cell known example, or raise the population lower bound above 22.

- Status evidence: current LifeWiki synthesis page.
- Any candidate must include the self-forcing proof/certificate, not only failed synthesis searches.

### LIFE-C004 — glider destruction and invulnerability

Questions include two-glider destruction minima, glider-proof targets and invulnerable finite targets.

- Status evidence: needs-recheck; source list is labelled September 2023.
- A first task is a 2026 status audit.

### LIFE-C005 — spaceship census/minimality gaps

Use the Spaceship Search Status Page to select a cell in the width/period/symmetry table that lacks either a construction or proof of minimality.

- Status evidence: community-dynamic.
- Negative exhaustive searches can be valuable when the search space is rigorously complete.

## Tier 3: systems questions

### LIFE-S001 — cross-engine benchmark

Build the first maintained workload-stratified benchmark across HashLife, StreamLife, sparse tile and dense GPU engines.

- This is an infrastructure gap, not a theorem.
- Publishability: JOSS when feature-complete; CA/HPC paper if it yields new algorithmic conclusions.

### LIFE-S002 — adaptive hybrid simulator

Can an engine automatically route regions/time windows among dense GPU, sparse tiles and HashLife based on measured reuse and entropy?

- Research hypothesis, not a community-certified open problem.
- A negative crossover map is still useful.

## Recently solved traps

- Generalised grandfather problem: solved in 2022.
- One interpretation of unique father: solved in 2022.
- Finite-support orphan coNP-completeness: solved in 2025.
- Periodic predecessor existence: proved undecidable in 2025.
- Omniperiodicity: solved; do not treat old period-gap tables as current open problems.

## Primary sources

- https://villesalo.com/openproblems.html
- https://doi.org/10.1016/j.tcs.2025.115237
- https://arxiv.org/abs/2308.10198
- https://arxiv.org/abs/1912.00692
- https://doi.org/10.4230/LIPIcs.ICALP.2022.131
- https://conwaylife.com/wiki/Garden_of_Eden
- https://conwaylife.com/wiki/LifeWiki:Spaceship_Search_Status_Page
- https://conwaylife.com/wiki/Tutorials/ikpx2
- https://conwaylife.com/wiki/Glider_synthesis
