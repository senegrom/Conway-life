# Community workflow and publication

## Where work is tracked

### LifeWiki

Use for pattern definitions and provenance, program tutorials, current record/status pages, proof and forum links, and downloadable RLE/macrocell files. Check each page's revision history; old pages can be stale.

### ConwayLife forums

Use for announcing a candidate result, confirming whether a target is still open, obtaining independent simulation/checking, sharing search partials and proof logs, and coordinating wiki updates. Community guidance for spaceship discoveries is to post to the forum first rather than immediately creating a LifeWiki article.

### Catagolue

Use for apgsearch census results, object identities/apgcodes, peer-reviewed hauls and distributed random-search coordination.

### Formal trackers

- Ville Salo's open-problem page is the strongest compact formal list found.
- Primary papers are canonical.
- TheoremDB can provide dated secondary audits and bounded work records, but should not outrank a paper or author statement.

## Result release checklist

### New pattern

- [ ] exact RLE/macrocell;
- [ ] rule and topology;
- [ ] displacement/period/population/bounding box;
- [ ] independent evolution in two engines;
- [ ] comparison against current status page;
- [ ] forum post;
- [ ] Catagolue submission if applicable;
- [ ] archived artefact hash.

### Search bound or nonexistence result

- [ ] formal search-space definition;
- [ ] completeness argument;
- [ ] source commit and build flags;
- [ ] full command;
- [ ] checkpoint/restart semantics;
- [ ] machine-readable proof or exhaustive-state digest;
- [ ] independent checker;
- [ ] negative-result write-up.

### Performance result

- [ ] common workload bytes;
- [ ] topology and generation count;
- [ ] engine commit;
- [ ] hardware/driver/compiler;
- [ ] correctness digest;
- [ ] raw repetitions;
- [ ] initialization and update split;
- [ ] memory/VRAM;
- [ ] no incompatible CUPS/HashLife comparison.

## Publication routes

### Informal but essential

1. repository release;
2. ConwayLife forum thread;
3. independent verification;
4. Catagolue or LifeWiki update.

This is often the fastest route to community recognition and prevents duplication.

### Software papers

**Journal of Open Source Software** is a good fit when the benchmark/search library is feature-complete, meaningfully reusable, OSI licensed, documented, tested and maintained. JOSS papers describe the software; they should not be used as the sole venue for a major new scientific result.

**Journal of Open Research Software** is an alternative for a software metapaper or a longer research-software practice article.

### Cellular-automata venues

**Journal of Cellular Automata** explicitly covers theoretical CA and CA as computational models. It is suitable for theorem work, new search algorithms, systematic pattern science and simulator methods.

**AUTOMATA / ACRI** are recurring specialist conferences for CA and discrete complex systems. Check the next call rather than relying on completed 2026 dates.

**Complex Systems** is broad but highly relevant. It is suitable for accessible algorithmic, mathematical or empirical Life work and states that it charges no publication fees.

### Theory and computer science

For universality, decidability, symbolic dynamics and complexity:

- arXiv first (`cs.FL`, `cs.DM`, `math.DS`, sometimes `nlin.CG`);
- Theoretical Computer Science;
- an appropriate theory conference/journal selected to match the proof.

### HPC and systems

A dense GPU or parallel HashLife improvement may fit an HPC venue only when the contribution generalises beyond Life: new temporal-blocking theory, scalable memoization, multi-GPU algorithms, portable Boolean-kernel synthesis, or a rigorous cross-architecture evaluation.

## Authorship and priority

- Commit hypotheses and experiment designs before long runs.
- Tag releases used for claims.
- Keep contributor roles in each result.
- Do not put a person's name on a result without agreement.
- Preserve solver logs and raw data so priority and correctness do not depend on prose.
