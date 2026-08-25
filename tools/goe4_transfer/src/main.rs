//! Column-transfer search for a four-row-live Garden of Eden orphan.
//!
//! Formulation (see scripts/goe4_transfer.py for the long version): preimage
//! columns are (h+2)-bit vectors, h = 4 + 2*dead_rows. NFA states are pairs
//! (a, b) of preimage columns, indexed s = a * ncols + b; on letter sigma
//! (an image column with live cells only in the middle four rows) there is a
//! transition (a, b) -> (b, c) iff img(a, b, c) = sigma. All states are
//! initial and final, so a window word has a preimage patch iff the NFA
//! accepts it, and an orphan of height h exists iff the NFA is NOT universal.
//!
//! Universality is decided by a BACKWARD antichain fixpoint over "bad"
//! subsets (sets of states from which some word reaches the empty subset in
//! the determinized automaton). Bad sets are downward closed, so the family
//! is represented by its maximal elements:
//!
//!   seeds:   Dead_sigma = { s : no sigma-successor }        (succ = empty)
//!   step:    Smax(sigma, b) = { s : succ_sigma(s) subseteq b }
//!
//! iterated to fixpoint. The full state set becomes bad iff an orphan word
//! exists; the word is reconstructed from the (sigma, parent) provenance
//! chain. If the fixpoint converges without covering the full set, the final
//! antichain is an inductive certificate that no orphan of this shape exists.
//!
//! Exit codes: 0 = universal (no orphan of this shape), 2 = orphan found
//! (window printed; cross-check with scripts/preimage_sat.py).

use std::time::Instant;

fn life_next(a3: u32, b3: u32, c3: u32) -> u32 {
    let centre = (b3 >> 1) & 1;
    let s = a3.count_ones() + b3.count_ones() + c3.count_ones() - centre;
    u32::from(s == 3 || (s == 2 && centre == 1))
}

fn img_col(a: u32, b: u32, c: u32, height: u32) -> u32 {
    let mut out = 0;
    for i in 0..height {
        let a3 = (a >> i) & 7;
        let b3 = (b >> i) & 7;
        let c3 = (c >> i) & 7;
        out |= life_next(a3, b3, c3) << i;
    }
    out
}

struct Args {
    dead_rows: u32,
    report_every: u64,
    mode: String,
}

fn parse_args() -> Args {
    let mut args = Args { dead_rows: 0, report_every: 10, mode: "core".to_string() };
    let mut it = std::env::args().skip(1);
    while let Some(flag) = it.next() {
        let value = it.next().unwrap_or_else(|| panic!("missing value for {flag}"));
        match flag.as_str() {
            "--dead-rows" => args.dead_rows = value.parse().unwrap(),
            "--report-every" => args.report_every = value.parse().unwrap(),
            "--mode" => args.mode = value, // core | backward
            other => panic!("unknown flag {other}"),
        }
    }
    args
}

/// Bitset over NFA states (s = a * ncols + b). Because states (b2, *) are the
/// slice [b2*ncols, (b2+1)*ncols), a state's successor set on sigma is the
/// c-mask C[sigma][s] placed inside row b2 of the bitset.
#[derive(Clone, PartialEq)]
struct StateSet {
    words: Vec<u64>,
}

impl StateSet {
    fn empty(nwords: usize) -> Self {
        StateSet { words: vec![0; nwords] }
    }
    fn is_subset(&self, other: &StateSet) -> bool {
        self.words.iter().zip(&other.words).all(|(&s, &o)| s & !o == 0)
    }
    fn set(&mut self, s: usize) {
        self.words[s / 64] |= 1 << (s % 64);
    }
    fn count(&self) -> u32 {
        self.words.iter().map(|w| w.count_ones()).sum()
    }
}

fn main() {
    let args = parse_args();
    let height = 4 + 2 * args.dead_rows;
    let pre_bits = height + 2;
    let ncols: usize = 1 << pre_bits;
    let nstates = ncols * ncols;
    let nwords = nstates / 64;
    let cblocks = ncols.div_ceil(64);
    let n_sigma = 16usize;
    let live_mask: u32 = 0b1111 << args.dead_rows;

    println!(
        "height {height} (dead rows {}), preimage columns {ncols}, states {nstates}",
        args.dead_rows
    );

    // c_table[sigma][s * cblocks ..][..cblocks]: mask over c with img(a,b,c)=sigma,
    // for state s = (a, b).
    let t0 = Instant::now();
    let mut c_table: Vec<Vec<u64>> = vec![vec![0u64; nstates * cblocks]; n_sigma];
    for a in 0..ncols {
        for b in 0..ncols {
            let s = a * ncols + b;
            for c in 0..ncols {
                let sigma = img_col(a as u32, b as u32, c as u32, height);
                if sigma & !live_mask != 0 {
                    continue;
                }
                let idx = (sigma >> args.dead_rows) as usize;
                c_table[idx][s * cblocks + c / 64] |= 1u64 << (c % 64);
            }
        }
    }
    println!("transition tables built in {:.1}s", t0.elapsed().as_secs_f64());

    if args.mode == "core" {
        // Greatest fixpoint of the sigma-total core: D := all states;
        // repeatedly remove states lacking, for some sigma, a successor
        // inside D. All states are initial and final, so a nonempty core
        // proves universality: any word can be traced greedily inside D.
        // (An empty core is NOT proof that an orphan exists — fall back to
        // --mode backward in that case.)
        let mut core = StateSet { words: vec![u64::MAX; nwords] };
        let mut iteration = 0u32;
        loop {
            iteration += 1;
            let mut removed = 0u64;
            let snapshot = core.clone();
            for s in 0..nstates {
                if snapshot.words[s / 64] & (1 << (s % 64)) == 0 {
                    continue;
                }
                let b2 = s % ncols;
                let row = &snapshot.words[b2 * ncols / 64..(b2 * ncols / 64) + cblocks];
                let mut total = true;
                for sigma in 0..n_sigma {
                    let cm = &c_table[sigma][s * cblocks..s * cblocks + cblocks];
                    if !cm.iter().zip(row).any(|(&c, &r)| c & r != 0) {
                        total = false;
                        break;
                    }
                }
                if !total {
                    core.words[s / 64] &= !(1 << (s % 64));
                    removed += 1;
                }
            }
            let remaining = core.count();
            println!("core iteration {iteration}: removed {removed}, remaining {remaining}");
            if removed == 0 {
                if remaining > 0 {
                    println!(
                        "UNIVERSAL at height {height}: nonempty sigma-total core of {remaining} \
                         states (of {nstates}). Every four-row pattern with {} specified dead \
                         rows above and below has a preimage patch, at any width; no orphan of \
                         this shape exists.",
                        args.dead_rows
                    );
                    std::process::exit(0);
                }
                println!(
                    "CORE EMPTY at height {height}: inconclusive — a greedy single-run strategy \
                     does not exist; rerun with --mode backward for the exact answer."
                );
                std::process::exit(1);
            }
        }
    }

    // succ_sigma(s) is empty iff the c-mask is all zero; Smax(sigma, b) tests
    // c-mask subseteq row_b2(b) where row_b2 is the contiguous slice of b's
    // bitset covering states (b2, *).
    let smax = |sigma: usize, bad: &StateSet| -> StateSet {
        let table = &c_table[sigma];
        let mut out = StateSet::empty(nwords);
        for s in 0..nstates {
            let b2 = s % ncols;
            let cm = &table[s * cblocks..s * cblocks + cblocks];
            let row = &bad.words[b2 * ncols / 64..(b2 * ncols / 64) + cblocks];
            if cm.iter().zip(row).all(|(&c, &r)| c & !r == 0) {
                out.set(s);
            }
        }
        out
    };

    // Antichain of maximal bad sets, with provenance for word reconstruction.
    struct Elem {
        set: StateSet,
        sigma: u8,
        parent: usize, // usize::MAX for seeds
        alive: bool,
    }
    let mut elems: Vec<Elem> = Vec::new();

    let insert = |elems: &mut Vec<Elem>, cand: StateSet, sigma: u8, parent: usize| -> bool {
        if cand.count() == 0 {
            return false;
        }
        for e in elems.iter() {
            if e.alive && cand.is_subset(&e.set) {
                return false; // dominated by an existing maximal bad set
            }
        }
        for e in elems.iter_mut() {
            if e.alive && e.set.is_subset(&cand) {
                e.alive = false;
            }
        }
        elems.push(Elem { set: cand, sigma, parent, alive: true });
        true
    };

    // Seeds: Dead_sigma = Smax(sigma, empty).
    let empty = StateSet::empty(nwords);
    for sigma in 0..n_sigma {
        let dead = smax(sigma, &empty);
        if dead.count() > 0 {
            println!("seed Dead_{sigma:02}: {} states", dead.count());
        }
        insert(&mut elems, dead, sigma as u8, usize::MAX);
    }
    if elems.is_empty() {
        println!(
            "UNIVERSAL at height {height} (trivially): every state has a successor \
             on every letter; the empty subset is unreachable."
        );
        return;
    }

    let full_count = nstates as u32;
    let mut frontier: Vec<usize> = (0..elems.len()).collect();
    let mut round = 0u32;
    let mut last_report = Instant::now();

    loop {
        round += 1;
        let mut new_frontier: Vec<usize> = Vec::new();
        for &parent_idx in &frontier {
            if !elems[parent_idx].alive {
                continue;
            }
            for sigma in 0..n_sigma {
                let cand = smax(sigma, &elems[parent_idx].set);
                let cnt = cand.count();
                if cnt == full_count {
                    // Full state set is bad: an orphan word exists.
                    let mut word = vec![sigma as u8];
                    let mut cur = parent_idx;
                    loop {
                        word.push(elems[cur].sigma);
                        if elems[cur].parent == usize::MAX {
                            break;
                        }
                        cur = elems[cur].parent;
                    }
                    report_orphan(&word, height, args.dead_rows);
                    std::process::exit(2);
                }
                if insert(&mut elems, cand, sigma as u8, parent_idx) {
                    new_frontier.push(elems.len() - 1);
                }
            }
            if last_report.elapsed().as_secs() >= args.report_every {
                let live = elems.iter().filter(|e| e.alive).count();
                let biggest = elems.iter().filter(|e| e.alive).map(|e| e.set.count()).max().unwrap_or(0);
                println!(
                    "round {round}: antichain {live} (of {} created), largest bad set {biggest}/{nstates}",
                    elems.len()
                );
                last_report = Instant::now();
            }
        }
        if new_frontier.is_empty() {
            break;
        }
        frontier = new_frontier;
    }

    let live = elems.iter().filter(|e| e.alive).count();
    let biggest = elems.iter().filter(|e| e.alive).map(|e| e.set.count()).max().unwrap_or(0);
    println!(
        "UNIVERSAL at height {height}: fixpoint reached without covering the full \
         state set. No orphan with live cells in the middle four rows and {} specified \
         dead rows above and below exists, at any width. \
         (maximal bad antichain {live}, largest bad set {biggest} of {nstates} states, {round} rounds)",
        args.dead_rows
    );
}

fn report_orphan(word: &[u8], height: u32, dead_rows: u32) {
    // Provenance chain: word[0] is applied first from the full set; seeds are
    // last. The window word reads in the same order.
    println!(
        "ORPHAN CANDIDATE: height {height} (dead rows {dead_rows}), width {}",
        word.len()
    );
    for row in 0..height {
        let line: String = word
            .iter()
            .map(|&s| {
                let col = (s as u32) << dead_rows;
                if (col >> row) & 1 == 1 { '1' } else { '0' }
            })
            .collect();
        println!("{line}");
    }
    println!("Cross-check this window with scripts/preimage_sat.py before celebrating.");
}
