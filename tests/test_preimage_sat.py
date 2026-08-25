from __future__ import annotations

import random
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import pysat  # noqa: F401

    HAVE_PYSAT = True
except ImportError:  # pragma: no cover - CI is stdlib-only
    HAVE_PYSAT = False

import preimage_sat as ps


class LifeRuleTests(unittest.TestCase):
    def test_life_out_matches_rule(self):
        # centre index 4 in NEIGH order; exhaustive check against B3/S23.
        for bits in range(512):
            neigh = tuple((bits >> k) & 1 for k in range(9))
            s = sum(neigh) - neigh[4]
            expected = 1 if s == 3 or (s == 2 and neigh[4]) else 0
            self.assertEqual(ps.life_out(neigh), expected)

    def test_blocked_partition(self):
        self.assertEqual(len(ps._BLOCKED[0]), 140)  # alive-producing blocked for v=0
        self.assertEqual(len(ps._BLOCKED[1]), 372)


@unittest.skipUnless(HAVE_PYSAT, "python-sat not installed")
class PreimageSatTests(unittest.TestCase):
    def test_exhaustive_2x2(self):
        mismatches, orphans = ps.exhaustive_validate(2, 2)
        self.assertEqual(mismatches, 0)
        self.assertEqual(orphans, 0)

    def test_random_images_have_preimages(self):
        rng = random.Random(42)
        for _ in range(50):
            ph, pw = rng.randint(4, 7), rng.randint(4, 7)
            patch = [[rng.randint(0, 1) for _ in range(pw)] for _ in range(ph)]
            window = ps.step_patch(patch)
            has, found = ps.check_window(window)
            self.assertTrue(has)
            self.assertTrue(ps.verify_patch(window, found))

    def test_returned_patch_verifies(self):
        window = ps.parse_window("0110\n1001\n0110")
        has, patch = ps.check_window(window)
        if has:
            self.assertTrue(ps.verify_patch(window, patch))


if __name__ == "__main__":
    unittest.main()
