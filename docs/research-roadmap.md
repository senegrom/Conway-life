# Research roadmap

## Stage 0 — establish the evidence ledger

- import this repository;
- enable issue tracking;
- pin the source registry;
- label every problem by status evidence;
- add a dated status-check issue before compute begins.

Exit criterion: all claims in the README point to a source row.

## Stage 1 — correctness kernel and workload corpus

- use the pure-Python reference engine for small tests;
- pin RLE/macrocell inputs;
- define canonical coordinate and topology conventions;
- create output digests;
- validate adapters against block, blinker, glider and random torus cases.

Exit criterion: every engine adapter agrees on small cases.

## Stage 2 — reproduce public performance claims

Priority order:

1. Golly 5.0 HashLife versus QuickLife.
2. lifelib HashLife versus tile-based.
3. `gol_engines` asynchronous versus synchronous and versus Golly/lifelib on 0E0P.
4. Binary Banter CUDA/OpenCL on the RTX GPU.
5. CAT `PACK`; tensor-core CAT as an adjacent radius study.
6. apgsearch end-to-end soup throughput.

Exit criterion: raw result JSON, output hashes and a generated summary table.

## Stage 3 — first benchmark release

- publish all raw runs;
- publish crossover plots;
- document failures and non-reproduced claims;
- add reproducible containers or build scripts;
- submit upstream issues for discovered correctness/performance problems.

Exit criterion: tagged release with DOI-ready archive.

## Stage 4 — SAT/SMT preimage programme

### 4A. Four-row Garden of Eden

1. formalise the infinite horizontal strip and finite witness conditions;
2. reproduce known height-5 examples and height-4 orphan nonexistence statements where code/certificates exist;
3. implement a transfer/SAT encoding;
4. search bounded widths;
5. emit a candidate or proof trace;
6. independently replay.

### 4B. Padding constant

1. formalise the exact `pad_i` implication;
2. reproduce the thickness-4 theorem examples and known lower bounds;
3. search for a counterexample at thickness 3;
4. classify minimal obstructions;
5. seek a compositional proof if no counterexample appears.

Exit criterion: a verified candidate, a rigorous bounded negative result, or a structural lemma.

## Stage 5 — specialised community search

Select one current target after a forum/status audit:

- unknown spaceship speed with ikpx2;
- width/period minimality with LSSS/LLSSS;
- smaller unsynthesizable still life;
- CatForce conduit/oscillator search.

Exit criterion: independently verified pattern or complete negative search.

## Research governance

- Every major run has a GitHub issue.
- Every issue states a falsifiable question.
- Every result includes an artefact hash.
- Dynamic records are rechecked before launch and before publication.
- Failed searches are retained with exact bounds.
- Claims are phrased at the strength of the evidence.
