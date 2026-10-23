"""Adversarial analytic tests; findings are intentionally unresolved, not fixes."""
from __future__ import annotations

import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "simulator"))
from scripts.audit_stage4_energy_inventory import (  # noqa: E402
    audit_default_six_hours, chemical_inventory_joules,
    rc_capacitance_farads, parameter_jump_joules,
)
from candidate_sim import model_energy_consistent as phys  # noqa: E402


class Stage4EnergyInventoryAdversarial(unittest.TestCase):
    def test_pack_geometry_is_168s2p(self):
        self.assertEqual(phys.N_GROUPS, 168)
        self.assertEqual(phys.BRANCHES, 2)
        self.assertEqual(phys.N_MODULES, 28)
        self.assertEqual(phys.GROUPS_PER_MODULE, 6)
        self.assertEqual(phys.N_GROUPS * phys.BRANCHES, 336)

    def test_aging_decreases_assumed_chemical_inventory_with_soc_held_fixed(self):
        x = audit_default_six_hours()
        self.assertLess(x["aging_capacity_inventory_delta_J"], 0.0)
        # Independently cross-checked algebraically: about -4.1715 kJ.
        self.assertAlmostEqual(
            x["aging_capacity_inventory_delta_J"], -4171.5131092992, delta=0.01
        )
        self.assertEqual(x["approval"], "NONE; Stage 4 official experiments remain unauthorized")

    def test_zero_aging_rate_has_zero_capacity_inventory_jump(self):
        p = replace(phys.ModelConfig(), aging_rate_per_s=0.0)
        e0 = chemical_inventory_joules(0.6, p.aging_index, p)
        e1 = chemical_inventory_joules(0.6, p.aging_index, p)
        self.assertEqual(e0, e1)
        self.assertEqual(
            parameter_jump_joules(0.15, p.aging_index, p.aging_index, p),
            0.0,
        )

    def test_rc_capacitance_changes_when_r1_ages(self):
        p = phys.ModelConfig()
        a0 = p.aging_index
        a1 = a0 + p.aging_rate_per_s * 21600
        c0 = rc_capacitance_farads(a0, p)
        c1 = rc_capacitance_farads(a1, p)
        self.assertGreater(c0, c1)
        self.assertAlmostEqual(c0, 287907.86948176584, delta=1e-5)
        self.assertAlmostEqual(c1, 287891.15963787434, delta=1e-5)
        dE = parameter_jump_joules(0.15, a0, a1, p)
        self.assertAlmostEqual(dE, -63.16320990986307, delta=1e-6)

    def test_unphysical_inputs_are_rejected(self):
        p = phys.ModelConfig()
        for z in (-0.1, 1.01, float("nan")):
            with self.subTest(z=z), self.assertRaises(ValueError):
                chemical_inventory_joules(z, 0.2, p)
        for v in (float("nan"), float("inf")):
            with self.subTest(v=v), self.assertRaises(ValueError):
                parameter_jump_joules(v, 0.2, 0.3, p)


if __name__ == "__main__":
    unittest.main()
