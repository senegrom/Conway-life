# Windows / WSL2 environment

This project is designed around a Windows machine with an NVIDIA RTX GPU.

## Native Windows

Use for Golly 5.0 GUI and visual inspection, native CUDA builds where a project supports them cleanly, and NVIDIA monitoring tools.

## WSL2 Ubuntu

Use for lifelib, `gol_engines`, LSSS, LLSSS, ikpx2, compiler-heavy SAT/SMT experiments and repository scripts.

Large LSSS searches can use substantial disk space. Keep the working tree and search data inside the WSL2 Linux filesystem rather than `/mnt/c` when performance matters.

## Suggested directory layout

```text
~/life-research/
  src/          # cloned external engines
  conway-life-open-research/
  datasets/
  scratch/
  results/
```

Do not commit external engine source trees into this repository. Record their remote URL and commit hash.

## Reproducibility capture

For every benchmark, capture:

```bash
uname -a
lscpu
free -h
nvidia-smi
git rev-parse HEAD
<compiler> --version
```

Also record Windows build, WSL kernel, NVIDIA driver, CUDA toolkit, GPU power limit, CPU power mode, total RAM and storage type.

## Build isolation

Prefer a documented shell script, Nix/Guix, a Docker/Podman image when GPU support is reproducible, or a lockfile plus exact compiler version. A container does not make hardware results portable by itself; driver and GPU details remain part of the result.
