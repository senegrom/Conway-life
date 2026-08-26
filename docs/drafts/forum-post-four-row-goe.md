# DRAFT — ConwayLife forum post (do not post without review)

Target board: the existing "orphan pattern / garden of eden" thread
(conwaylife.com/forums/viewtopic.php?f=2&t=797) or a new thread in
"General Discussion". Purpose: status audit + tool/bounds announcement +
invitation for prior art. Post as the repository owner.

---

**Title suggestion:** Four-row Garden of Eden: tooling, small width bounds,
and a structural note on the height-4 orphan theorem

I've been working on the open question of whether a Garden of Eden exists
whose live cells are confined to four consecutive rows (as distinct from
Andrew J. Wade's 2023 result that no height-4 orphan exists when all
specified cells count). Before going further I'd like to check for prior
art: **has anyone recorded bounded searches specific to this live-cell
variant?** I could not find any in the wiki or in the searchable record,
but I may well have missed forum work.

What I have so far, all reproducible from
https://github.com/senegrom/Conway-life (MIT/CC-BY):

**Formulation.** A witness would be an orphan of height 4+2d: middle four
rows free, d specified dead rows above and below. Equivalently, for each
height, a word rejected by the transfer NFA whose states are pairs of
(h+2)-bit preimage columns (all states initial and final, 16-letter
alphabet of image columns). An orphan for ANY d resolves the question
positively, by compactness.

**Bounded results** (2QBF, forall-pattern/exists-preimage form with
lex-leader symmetry breaking, CAQE; every claim cross-checked against an
exhaustively validated SAT preimage checker, and small cases against brute
force):

| dead rows d | window height | no orphan up to width |
|---|---|---|
| 0 | 4 | any width (Wade 2023); QBF re-verified w <= 5 |
| 1 | 6 | 5 (w=6 open, >2h solver time) |
| 2 | 8 | 4 |

These widths are small — the pattern spaces involved are tiny — so I
treat this as the start of a systematic record rather than a claim of
novelty. Eker's 5x83 Garden of Eden suggests the interesting regime is
far wider than current QBF reach.

**A structural note that may be of independent interest.** The height-4
extension property behind Wade's theorem is "deep" in the following
precise sense: define a witness family of size k as a set F of nonempty
state sets of size <= k of the transfer NFA, closed under every letter
(each W in F has some W' in F inside its successor set). A nonempty
closed family proves universality (= no orphan of that shape at any
width). Computation shows the greatest such family is EMPTY for k = 1
(349 of 4096 pair-states survive one elimination round, none survive two)
and k = 2 (8.4M pairs collapse 443,155 -> 296 -> 0). So no column-by-column
strategy tracking at most two candidate preimage runs can witness the
theorem — at least three-way lookahead is necessary. This also explains
why antichain/simulation methods make no progress on this automaton (the
simulation preorder is completely trivial). Exact determinization of the
d=0 subset automaton exceeds 16M reachable subsets with the BFS frontier
only at word length 7 (discovery ratio ~11 per explored subset), so the
per-height unbounded-width question appears out of reach for explicit
automata methods altogether.

Questions for the forum:

1. Any prior bounded searches on the four-row live-cell variant?
2. Is the witness-complexity observation known in some other guise?
3. Does anyone have compute or a better idea for the per-height
   unbounded-width question at d >= 1? The transfer automaton for d = 1
   has 65,536 states and all the standard reductions fail.

Tools: preimage SAT checker (pysat), transfer-automaton searches (Rust),
QDIMACS generator with Quine-McCluskey Life encoding, CAQE built natively
on Windows. Happy to share instances or details.

---

# Posting checklist (for the user)

- [ ] Read the existing thread t=797 first; adjust "prior art" phrasing to
      whatever is already there.
- [ ] Verify the width table against benchmarks/results and the research
      log at posting time (d=1 w=5 and the determinization outcome may
      have landed since this draft).
- [ ] Confirm repo URL and licence line.
- [ ] No session links; no Claude attribution is customary on the forum,
      but disclose tooling assistance if you prefer.
