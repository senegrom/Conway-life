# Determine the optimal padding constant

## Problem

Resolve Ville Salo's Q28820954: determine the minimal zero-padding thickness in the Life image-extension implication.

## Plan

1. Formalise the quantifiers and cylinder-set statement.
2. Reproduce the known thickness-4 theorem and lower-bound examples.
3. Search for a pattern witnessing failure at thickness 3.
4. Minimise any witness by area, population and boundary complexity.
5. If no witness appears, extract finite-state structure that might prove thickness 3 sufficient.

## Verification

SAT model or proof log, independent local predecessor checker, exact pattern and padding convention, and a formal bridge from finite search to the global statement.

## Source

https://villesalo.com/openproblems.html
