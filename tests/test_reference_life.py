from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reference_life as life


class ReferenceLifeTests(unittest.TestCase):
    def setUp(self):
        self.patterns = ROOT / "benchmarks/patterns"

    def test_block_is_stable(self):
        block = life.read_rle(self.patterns / "block.rle").live
        self.assertEqual(life.advance(block, 10), block)

    def test_blinker_period_two(self):
        blinker = life.read_rle(self.patterns / "blinker.rle").live
        self.assertNotEqual(life.advance(blinker, 1), blinker)
        self.assertEqual(life.advance(blinker, 2), blinker)

    def test_glider_translation(self):
        glider = life.read_rle(self.patterns / "glider.rle").live
        shifted = frozenset((x + 1, y + 1) for x, y in glider)
        self.assertEqual(life.advance(glider, 4), shifted)

    def test_rle_round_trip_up_to_translation(self):
        glider = life.read_rle(self.patterns / "glider.rle").live
        decoded = life.parse_rle_text(life.to_rle(glider)).live
        min_x = min(x for x, _ in glider)
        min_y = min(y for _, y in glider)
        normalised = frozenset((x - min_x, y - min_y) for x, y in glider)
        self.assertEqual(decoded, normalised)

    def test_digest_is_order_independent(self):
        cells = [(2, 1), (0, 0), (1, 1)]
        self.assertEqual(life.coordinate_sha256(cells), life.coordinate_sha256(reversed(cells)))

    def test_rejects_other_rules(self):
        with self.assertRaises(ValueError):
            life.parse_rle_text("x = 1, y = 1, rule = B36/S23\no!\n")


if __name__ == "__main__":
    unittest.main()
