//! Column-transfer search for a four-row-live Garden of Eden orphan.
//!
//! Formulation (long version in scripts/goe4_transfer.py): preimage columns
//! are (h+2)-bit vectors, h = 4 + 2*dead_rows. NFA states are pairs (a, b)
//! of preimage columns, s = a * ncols + b; on letter sigma (one of the 16
//! image columns whose live cells sit in the middle four rows) there is a
//! transition (a, b) -> (b, c) iff img(a, b, c) = sigma. All states are
//! initial and final, so a window word has a preimage patch iff the NFA
//! accepts it, and an orphan of height h exists iff the NFA is NOT universal.
//! A shortest escaping word is a minimal-width orphan; cross-check any find
//! with scripts/preimage_sat.py.
//!
//! Modes:
//!   --mode core    sigma-total core greatest fixpoint (cheap sufficient
//!                  check for universality; known to be empty at d=0,1)
//!   --mode search  the real decision procedure:
//!                  1. bisimulation quotient of the NFA (partition refinement)
//!                  2. simulation preorder on the quotient
//!                  3. forward subset BFS with simulation-reduced subsets and
//!                     simulation-based antichain domination (Doyen-Raskin /
//!                     Abdulla et al. style)
//!
//! Exit codes: 0 universal, 2 orphan found, 3 stopped at a cap.

use std::collections::{HashMap, VecDeque};
use std::time::Instant;

fn life_next(a3: u32, b3: u32, c3: u32) -> u32 {
    let centre = (b3 >> 1) & 1;
    let s = a3.count_ones() + b3.count_ones() + c3.count_ones() - centre;
    u32::from(s == 3 || (s == 2 && centre == 1))
}

fn img_col(a: u32, b: u32, c: u32, height: u32) -> u32 {
    let mut out = 0;
    for i in 0..height {
        out |= life_next((a >> i) & 7, (b >> i) & 7, (c >> i) & 7) << i;
    }
    out
}

struct Args {
    dead_rows: u32,
    mode: String,
    max_depth: u32,
    report_every: u64,
}

fn parse_args() -> Args {
    let mut args = Args {
        dead_rows: 0,
        mode: "search".to_string(),
        max_depth: u32::MAX,
        report_every: 10,
    };
    let mut it = std::env::args().skip(1);
    while let Some(flag) = it.next() {
        let value = it.next().unwrap_or_else(|| panic!("missing value for {flag}"));
        match flag.as_str() {
            "--dead-rows" => args.dead_rows = value.parse().unwrap(),
            "--mode" => args.mode = value,
            "--max-depth" => args.max_depth = value.parse().unwrap(),
            "--report-every" => args.report_every = value.parse().unwrap(),
            other => panic!("unknown flag {other}"),
        }
    }
    args
}

const N_SIGMA: usize = 16;

/// Pair-state NFA: succ[sigma][s] = Vec<state> (successors (b2, c)).
/// Built once, then quotiented.
struct Nfa {
    n: usize,
    succ: Vec<Vec<Vec<u32>>>, // [sigma][state] -> successor states
}

fn build_pair_nfa(dead_rows: u32) -> Nfa {
    let height = 4 + 2 * dead_rows;
    let ncols: usize = 1 << (height + 2);
    let n = ncols * ncols;
    let live_mask: u32 = 0b1111 << dead_rows;
    let mut succ: Vec<Vec<Vec<u32>>> = vec![vec![Vec::new(); n]; N_SIGMA];
    for a in 0..ncols {
        for b in 0..ncols {
            let s = a * ncols + b;
            for c in 0..ncols {
                let sigma = img_col(a as u32, b as u32, c as u32, height);
                if sigma & !live_mask != 0 {
                    continue;
                }
                succ[(sigma >> dead_rows) as usize][s].push((b * ncols + c) as u32);
            }
        }
    }
    Nfa { n, succ }
}

/// Bisimulation quotient by signature refinement. Returns (class per state,
/// class count).
fn bisim_classes(nfa: &Nfa, report: bool) -> (Vec<u32>, usize) {
    let mut class: Vec<u32> = vec![0; nfa.n];
    let mut n_classes = 1usize;
    loop {
        let mut sig_map: HashMap<Vec<u64>, u32> = HashMap::new();
        let mut next_class: Vec<u32> = vec![0; nfa.n];
        for s in 0..nfa.n {
            // Signature: current class + per-sigma sorted successor class sets.
            let mut sig: Vec<u64> = vec![class[s] as u64];
            for sigma in 0..N_SIGMA {
                let mut cs: Vec<u32> = nfa.succ[sigma][s].iter().map(|&t| class[t as usize]).collect();
                cs.sort_unstable();
                cs.dedup();
                sig.push(u64::MAX); // separator
                sig.extend(cs.iter().map(|&c| c as u64));
            }
            let next_id = sig_map.len() as u32;
            let id = *sig_map.entry(sig).or_insert(next_id);
            next_class[s] = id;
        }
        let new_count = sig_map.len();
        if report {
            println!("bisim refinement: {new_count} classes");
        }
        // Each round refines the previous partition (the signature includes the
        // old class), so an unchanged class count means the partition is stable.
        let stable = new_count == n_classes;
        class = next_class;
        n_classes = new_count;
        if stable {
            return (class, n_classes);
        }
    }
}

/// Quotient NFA: successor class sets per class.
fn quotient(nfa: &Nfa, class: &[u32], n_classes: usize) -> Nfa {
    let mut succ: Vec<Vec<Vec<u32>>> = vec![vec![Vec::new(); n_classes]; N_SIGMA];
    let mut done: Vec<bool> = vec![false; n_classes];
    for s in 0..nfa.n {
        let q = class[s] as usize;
        if done[q] {
            continue;
        }
        done[q] = true;
        for sigma in 0..N_SIGMA {
            let mut cs: Vec<u32> = nfa.succ[sigma][s].iter().map(|&t| class[t as usize]).collect();
            cs.sort_unstable();
            cs.dedup();
            succ[sigma][q] = cs;
        }
    }
    Nfa { n: n_classes, succ }
}

/// Bitset helpers over `n` states.
fn words(n: usize) -> usize {
    n.div_ceil(64)
}
fn bit_get(v: &[u64], i: usize) -> bool {
    v[i / 64] & (1 << (i % 64)) != 0
}
fn bit_clear(v: &mut [u64], i: usize) {
    v[i / 64] &= !(1 << (i % 64));
}

/// Simulation preorder on an NFA (all states final): sim[t] = bitset of s
/// with s simulated by t ... stored as rows: sim_row(s) = bitset of t that
/// simulate s (s <= t). Greatest fixpoint.
fn simulation(nfa: &Nfa, report: bool) -> Vec<Vec<u64>> {
    let n = nfa.n;
    let w = words(n);
    // sim[s] = { t : s <= t }, initially all.
    let mut full = vec![u64::MAX; w];
    if n % 64 != 0 {
        full[w - 1] = (1u64 << (n % 64)) - 1;
    }
    let mut sim: Vec<Vec<u64>> = vec![full.clone(); n];
    let t0 = Instant::now();
    loop {
        let mut changed = false;
        for s in 0..n {
            for t in 0..n {
                if s == t || !bit_get(&sim[s], t) {
                    continue;
                }
                // s <= t requires: forall sigma, forall s' in succ(s,sigma):
                // exists t' in succ(t,sigma) with s' <= t'.
                'check: for sigma in 0..N_SIGMA {
                    for &sp in &nfa.succ[sigma][s] {
                        let mut ok = false;
                        for &tp in &nfa.succ[sigma][t] {
                            if bit_get(&sim[sp as usize], tp as usize) {
                                ok = true;
                                break;
                            }
                        }
                        if !ok {
                            bit_clear(&mut sim[s], t);
                            changed = true;
                            break 'check;
                        }
                    }
                }
            }
        }
        if !changed {
            break;
        }
    }
    if report {
        let pairs: u64 = sim.iter().map(|r| r.iter().map(|w| w.count_ones() as u64).sum::<u64>()).sum();
        println!(
            "simulation preorder computed in {:.1}s: {pairs} pairs (incl. {n} reflexive)",
            t0.elapsed().as_secs_f64()
        );
    }
    sim
}

/// Reduce a state set to its simulation-maximal elements (one per mutual pair).
fn sim_reduce(set: &mut Vec<u32>, sim: &[Vec<u64>]) {
    let snapshot = set.clone();
    set.retain(|&s| {
        !snapshot.iter().any(|&t| {
            t != s
                && bit_get(&sim[s as usize], t as usize)
                && !(bit_get(&sim[t as usize], s as usize) && t > s)
        })
    });
}

/// S dominated-by T (prune T) iff forall s in S exists t in T: s <= t.
/// Any word emptying T then also empties S, so exploring T is redundant.
fn dominates(seen: &[u32], cand: &[u32], sim: &[Vec<u64>]) -> bool {
    seen.iter().all(|&s| cand.iter().any(|&t| bit_get(&sim[s as usize], t as usize)))
}

fn main() {
    let args = parse_args();
    let height = 4 + 2 * args.dead_rows;
    let t0 = Instant::now();
    let nfa = build_pair_nfa(args.dead_rows);
    println!(
        "height {height} (dead rows {}), pair states {}, built in {:.1}s",
        args.dead_rows,
        nfa.n,
        t0.elapsed().as_secs_f64()
    );

    if args.mode == "core" {
        run_core(&nfa, height, args.dead_rows);
        return;
    }

    // --mode search
    let (class, n_classes) = bisim_classes(&nfa, true);
    println!("bisimulation quotient: {} -> {} classes", nfa.n, n_classes);
    let q = quotient(&nfa, &class, n_classes);
    let sim = simulation(&q, true);

    // Start subset: all classes, sim-reduced.
    let mut start: Vec<u32> = (0..q.n as u32).collect();
    sim_reduce(&mut start, &sim);
    start.sort_unstable();
    println!("start subset after simulation reduction: {} of {} classes", start.len(), q.n);

    struct Node {
        set: Vec<u32>,
        parent: usize,
        sigma: u8,
        depth: u32,
    }
    let mut nodes: Vec<Node> = vec![Node { set: start, parent: usize::MAX, sigma: 0, depth: 0 }];
    let mut antichain: Vec<usize> = vec![0];
    let mut queue: VecDeque<usize> = VecDeque::new();
    queue.push_back(0);
    let mut explored = 0u64;
    let mut last_report = Instant::now();
    let mut capped = false;

    while let Some(id) = queue.pop_front() {
        let depth = nodes[id].depth;
        if depth >= args.max_depth {
            capped = true;
            continue;
        }
        explored += 1;
        if last_report.elapsed().as_secs() >= args.report_every {
            println!(
                "depth {depth}, explored {explored}, antichain {}, queue {}",
                antichain.len(),
                queue.len()
            );
            last_report = Instant::now();
        }
        for sigma in 0..N_SIGMA {
            let mut nxt: Vec<u32> = Vec::new();
            for &s in &nodes[id].set {
                for &t in &q.succ[sigma][s as usize] {
                    if !nxt.contains(&t) {
                        nxt.push(t);
                    }
                }
            }
            if nxt.is_empty() {
                // Orphan word found.
                let mut word = vec![sigma as u8];
                let mut cur = id;
                while cur != 0 {
                    word.push(nodes[cur].sigma);
                    cur = nodes[cur].parent;
                }
                word.reverse();
                report_orphan(&word, height, args.dead_rows);
                std::process::exit(2);
            }
            sim_reduce(&mut nxt, &sim);
            nxt.sort_unstable();
            if antichain.iter().any(|&aid| dominates(&nodes[aid].set, &nxt, &sim)) {
                continue;
            }
            antichain.retain(|&aid| !dominates(&nxt, &nodes[aid].set, &sim));
            let new_id = nodes.len();
            nodes.push(Node { set: nxt, parent: id, sigma: sigma as u8, depth: depth + 1 });
            antichain.push(new_id);
            queue.push_back(new_id);
        }
    }

    if capped {
        println!(
            "STOPPED at depth cap {}: no orphan of height {height} (dead rows {}) with width <= {} exists; wider is undecided.",
            args.max_depth, args.dead_rows, args.max_depth
        );
        std::process::exit(3);
    }
    println!(
        "UNIVERSAL at height {height}: subset exploration exhausted without reaching the \
         empty set. No orphan with live cells in the middle four rows and {} specified dead \
         rows above and below exists, at any width. (antichain {}, explored {explored})",
        args.dead_rows,
        antichain.len()
    );
}

fn run_core(nfa: &Nfa, height: u32, dead_rows: u32) {
    let n = nfa.n;
    let mut alive = vec![true; n];
    let mut iteration = 0;
    loop {
        iteration += 1;
        let mut removed = 0u64;
        let snapshot = alive.clone();
        for s in 0..n {
            if !snapshot[s] {
                continue;
            }
            let total = (0..N_SIGMA)
                .all(|sigma| nfa.succ[sigma][s].iter().any(|&t| snapshot[t as usize]));
            if !total {
                alive[s] = false;
                removed += 1;
            }
        }
        let remaining = alive.iter().filter(|&&a| a).count();
        println!("core iteration {iteration}: removed {removed}, remaining {remaining}");
        if removed == 0 {
            if remaining > 0 {
                println!(
                    "UNIVERSAL at height {height}: nonempty sigma-total core of {remaining} states."
                );
                std::process::exit(0);
            }
            println!(
                "CORE EMPTY at height {height} (dead rows {dead_rows}): inconclusive; use --mode search."
            );
            std::process::exit(1);
        }
    }
}

fn report_orphan(word: &[u8], height: u32, dead_rows: u32) {
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
