# Contributing

## Claim discipline

Every contribution must distinguish theorem, exhaustive computational result, heuristic evidence, author-reported benchmark, independently reproduced benchmark and dynamic community record. Do not write “open” without a source and last-checked date.

## Research-result pull requests

Include a linked issue, exact claim, source/commit and command, raw artefacts, independent verification route, limitations, updated CSV registry and changelog entry.

## Code

- Keep standard-library Python compatible with supported versions.
- Add tests for parsers and checkers.
- Fail loudly on unsupported rules or topology.
- Never silently normalise coordinate conventions.
- Include type hints and useful errors.

## Large files

Do not commit multi-gigabyte search states directly. Use a release asset or archive and commit the content hash, byte size, provenance, retrieval instructions and licence.

## Community conduct

Credit prior discoverers and tool authors. Ask before assigning authorship. Publish failed searches when their bounds are useful.
