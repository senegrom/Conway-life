//! Benchmark adapter for binary-banter/fast-game-of-life (BB-OPENCL / BB-trivial).
//!
//! Fills a deterministic pseudo-random region (SplitMix64, one draw per cell in
//! row-major order over the fill region), runs the requested engine, and emits
//! one JSON line with timing, population and canonical raster digests.
//!
//! The canonical digest is SHA-256 over an ASCII raster of the FULL universe:
//! for each row, one '0'/'1' character per cell followed by '\n'.
//!
//! Boundary semantics: bounded plane, dead outside. The OpenCL engine rounds
//! the requested universe up (width to a multiple of 32, height to the padded
//! core size); the reported universe dimensions are the effective ones, and
//! digests always cover the effective universe. Pass a width/height that the
//! engine maps to itself (width % 32 == 0, height in {738, 1473, 2208, 4416, ...})
//! when exact cross-engine comparison is required.

use sha2::{Digest, Sha256};
use std::time::Instant;

const SPLITMIX_GAMMA: u64 = 0x9E37_79B9_7F4A_7C15;

struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    fn next(&mut self) -> u64 {
        self.state = self.state.wrapping_add(SPLITMIX_GAMMA);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

fn fill_cells(fill_w: usize, fill_h: usize, density_ppm: u64, seed: u64) -> Vec<(usize, usize)> {
    assert!(density_ppm < 1_000_000, "density-ppm must be < 1000000");
    let threshold = ((density_ppm as u128) << 64) / 1_000_000;
    let threshold = threshold as u64;
    let mut rng = SplitMix64::new(seed);
    let mut cells = Vec::new();
    for y in 0..fill_h {
        for x in 0..fill_w {
            if rng.next() < threshold {
                cells.push((x, y));
            }
        }
    }
    cells
}

fn raster_digest(universe_w: usize, universe_h: usize, alive: impl Fn(usize, usize) -> bool) -> (String, u64) {
    let mut hasher = Sha256::new();
    let mut row = vec![0u8; universe_w + 1];
    row[universe_w] = b'\n';
    let mut population = 0u64;
    for y in 0..universe_h {
        for x in 0..universe_w {
            if alive(x, y) {
                row[x] = b'1';
                population += 1;
            } else {
                row[x] = b'0';
            }
        }
        hasher.update(&row);
    }
    (hex(&hasher.finalize()), population)
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

struct Args {
    width: usize,
    height: usize,
    fill_width: Option<usize>,
    fill_height: Option<usize>,
    density_ppm: u64,
    seed: u64,
    gens: u32,
    engine: String,
    pattern_file: Option<String>,
    dump_raster: Option<String>,
}

fn parse_args() -> Args {
    let mut args = Args {
        width: 0,
        height: 0,
        fill_width: None,
        fill_height: None,
        density_ppm: 0,
        seed: 0,
        gens: 0,
        engine: "opencl".to_string(),
        pattern_file: None,
        dump_raster: None,
    };
    let mut it = std::env::args().skip(1);
    while let Some(flag) = it.next() {
        let value = it.next().unwrap_or_else(|| panic!("missing value for {flag}"));
        match flag.as_str() {
            "--width" => args.width = value.parse().unwrap(),
            "--height" => args.height = value.parse().unwrap(),
            "--fill-width" => args.fill_width = Some(value.parse().unwrap()),
            "--fill-height" => args.fill_height = Some(value.parse().unwrap()),
            "--density-ppm" => args.density_ppm = value.parse().unwrap(),
            "--seed" => args.seed = value.parse().unwrap(),
            "--gens" => args.gens = value.parse().unwrap(),
            "--engine" => args.engine = value,
            "--pattern-file" => args.pattern_file = Some(value),
            "--dump-raster" => args.dump_raster = Some(value),
            other => panic!("unknown flag {other}"),
        }
    }
    assert!(args.width > 0 && args.height > 0, "--width and --height are required");
    args
}

fn read_pattern(path: &str) -> (Vec<(usize, usize)>, usize, usize) {
    let text = std::fs::read_to_string(path).unwrap();
    let mut cells = Vec::new();
    let mut width = 0;
    let mut height = 0;
    for (y, line) in text.lines().enumerate() {
        let line = line.trim_end();
        if line.is_empty() {
            continue;
        }
        height = y + 1;
        width = width.max(line.len());
        for (x, ch) in line.chars().enumerate() {
            match ch {
                '1' | 'o' | 'O' | '*' => cells.push((x, y)),
                '0' | '.' | 'b' => {}
                other => panic!("unexpected raster character {other:?}"),
            }
        }
    }
    (cells, width, height)
}

fn dump_raster(path: &str, universe_w: usize, universe_h: usize, alive: &dyn Fn(usize, usize) -> bool) {
    let mut out = Vec::with_capacity((universe_w + 1) * universe_h);
    for y in 0..universe_h {
        for x in 0..universe_w {
            out.push(if alive(x, y) { b'1' } else { b'0' });
        }
        out.push(b'\n');
    }
    std::fs::write(path, out).unwrap();
}

fn main() {
    let args = parse_args();
    let (cells, fill_w, fill_h) = match &args.pattern_file {
        Some(path) => read_pattern(path),
        None => {
            let fill_w = args.fill_width.unwrap_or(args.width);
            let fill_h = args.fill_height.unwrap_or(args.height);
            (fill_cells(fill_w, fill_h, args.density_ppm, args.seed), fill_w, fill_h)
        }
    };
    assert!(fill_w <= args.width && fill_h <= args.height);

    match args.engine.as_str() {
        "opencl" => run_opencl(&args, fill_w, fill_h, &cells),
        "trivial" => run_trivial(&args, fill_w, fill_h, &cells),
        other => panic!("unknown engine {other}; use opencl or trivial"),
    }
}

fn emit(
    args: &Args,
    fill_w: usize,
    fill_h: usize,
    universe_w: usize,
    universe_h: usize,
    input_digest: &str,
    input_population: u64,
    output_digest: &str,
    output_population: u64,
    init_seconds: f64,
    update_seconds: f64,
    readback_seconds: f64,
) {
    println!(
        "{{\"engine\":\"{}\",\"requested_width\":{},\"requested_height\":{},\"universe_width\":{},\"universe_height\":{},\"fill_width\":{},\"fill_height\":{},\"density_ppm\":{},\"seed\":{},\"generations\":{},\"input_raster_sha256\":\"{}\",\"input_population\":{},\"output_raster_sha256\":\"{}\",\"output_population\":{},\"init_seconds\":{:.6},\"update_seconds\":{:.6},\"readback_seconds\":{:.6}}}",
        args.engine,
        args.width,
        args.height,
        universe_w,
        universe_h,
        fill_w,
        fill_h,
        args.density_ppm,
        args.seed,
        args.gens,
        input_digest,
        input_population,
        output_digest,
        output_population,
        init_seconds,
        update_seconds,
        readback_seconds,
    );
}

fn run_opencl(args: &Args, fill_w: usize, fill_h: usize, cells: &[(usize, usize)]) {
    use fast_game_of_life::opencl::Game;

    let init_start = Instant::now();
    let mut game = Game::new(args.width, args.height);
    let (columns, padded_height) = game.buffer_dims();
    let (padding_x, padding_y) = Game::paddings();
    let universe_w = (columns - 2 * padding_x) * 32;
    // The kernel writes back simulation_rows() rows per work group; rows in the
    // padded core beyond that coverage are permanently dead, i.e. outside the
    // universe. The simulated universe height is therefore a multiple of
    // simulation_rows().
    let sim_rows = Game::simulation_rows();
    let universe_h = (padded_height - 2 * padding_y) / sim_rows * sim_rows;

    // Pack the fill into a full padded buffer image and upload in one transfer.
    let mut words = vec![0u32; columns * padded_height];
    for &(x, y) in cells {
        let column = x / 32 + padding_x;
        let index = (y + padding_y) + column * padded_height;
        words[index] |= 0x8000_0000 >> (x % 32);
    }
    game.write_buffer_words(&words);
    let init_seconds = init_start.elapsed().as_secs_f64();

    let input_set: std::collections::HashSet<(usize, usize)> = cells.iter().copied().collect();
    let (input_digest, input_population) =
        raster_digest(universe_w, universe_h, |x, y| input_set.contains(&(x, y)));

    let update_start = Instant::now();
    game.step(args.gens);
    let update_seconds = update_start.elapsed().as_secs_f64();

    let readback_start = Instant::now();
    let words = game.read_buffer_words();
    let readback_seconds = readback_start.elapsed().as_secs_f64();

    let alive = |x: usize, y: usize| {
        let column = x / 32 + padding_x;
        let index = (y + padding_y) + column * padded_height;
        words[index] & (0x8000_0000 >> (x % 32)) != 0
    };
    let (output_digest, output_population) = raster_digest(universe_w, universe_h, &alive);
    if let Some(path) = &args.dump_raster {
        dump_raster(path, universe_w, universe_h, &alive);
    }

    emit(
        args, fill_w, fill_h, universe_w, universe_h,
        &input_digest, input_population, &output_digest, output_population,
        init_seconds, update_seconds, readback_seconds,
    );
}

fn run_trivial(args: &Args, fill_w: usize, fill_h: usize, cells: &[(usize, usize)]) {
    use fast_game_of_life::trivial::Game;

    let init_start = Instant::now();
    let mut game = Game::new(args.width, args.height);
    for &(x, y) in cells {
        game.set(x, y);
    }
    let init_seconds = init_start.elapsed().as_secs_f64();

    let input_set: std::collections::HashSet<(usize, usize)> = cells.iter().copied().collect();
    let (input_digest, input_population) =
        raster_digest(args.width, args.height, |x, y| input_set.contains(&(x, y)));

    let update_start = Instant::now();
    game.step(args.gens);
    let update_seconds = update_start.elapsed().as_secs_f64();

    let readback_start = Instant::now();
    let alive = |x: usize, y: usize| game.get(x, y);
    let (output_digest, output_population) = raster_digest(args.width, args.height, &alive);
    let readback_seconds = readback_start.elapsed().as_secs_f64();
    if let Some(path) = &args.dump_raster {
        dump_raster(path, args.width, args.height, &alive);
    }

    emit(
        args, fill_w, fill_h, args.width, args.height,
        &input_digest, input_population, &output_digest, output_population,
        init_seconds, update_seconds, readback_seconds,
    );
}
