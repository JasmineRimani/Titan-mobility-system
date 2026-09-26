"""The numbers of the IAC-26 paper, checked against the code.

    python -m unittest discover -s tests -v

A. Lukianov and J. Rimani, "Preliminary Design and Performance Assessment of
Screw-propelled Vehicle", 77th International Astronautical Congress,
Antalya, 2026, IAC-26,A3,IP,204,x115954.

Each test names the table, figure or section of the paper it checks, and the
tolerances are the rounding the paper uses. A failure therefore means the
code no longer reproduces a published number. Either the change that caused
it is a mistake, or the paper numbers are superseded by a deliberate model
change, in which case update the expected value here and say why in the
commit message. Standard library only.
"""

import contextlib
import dataclasses
import io
import os
import re
import sys
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import make_paper_tables  # noqa: E402
import run_example  # noqa: E402
import validate  # noqa: E402
from sizing.environment import TITAN  # noqa: E402
from sizing.mers import MassModel  # noqa: E402
from sizing.screw import ScrewGeometry  # noqa: E402
from sizing.sizing_loop import Mission, size  # noqa: E402
from sizing.terrain import CASES, LIQUEFIED_SOFT, TITAN_LUNAR_PROXY  # noqa: E402


def quietly(fn, *args, **kwargs):
    """Run fn with its printout captured; return (result, text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fn(*args, **kwargs)
    return out, buf.getvalue()


def baseline(**mass_model):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return size(Mission(), ScrewGeometry(), TITAN_LUNAR_PROXY, TITAN,
                    MassModel(**mass_model))


def number(pattern, text):
    m = re.search(pattern, text)
    if m is None:
        raise AssertionError(f"pattern not found in output: {pattern}")
    return [float(g) for g in m.groups()]


class Table7BaselineGeometry(unittest.TestCase):
    def test_geometry(self):
        g = ScrewGeometry()
        self.assertEqual(g.n_screws, 2)
        self.assertEqual((g.drum_diameter, g.blade_height, g.length, g.pitch),
                         (0.55, 0.08, 1.10, 0.45))
        self.assertAlmostEqual(g.outer_diameter, 0.71, places=6)
        self.assertAlmostEqual(g.helix_angle_deg, 12.8, delta=0.05)
        self.assertAlmostEqual(g.screw_efficiency, 0.24, delta=0.005)

    def test_mission(self):
        m = Mission()
        self.assertEqual((m.payload_mass, m.target_speed, m.design_slope,
                          m.design_slip, m.drive_duty, m.drive_session_h),
                         (12.0, 0.028, 20.0, 0.30, 0.15, 4.0))
        self.assertEqual(m.delivered_mass_cap, 213.0)


class Tables8and9Baseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = baseline()
        cls.p = cls.res.performance

    def test_converges_in_six_iterations(self):
        self.assertTrue(self.res.converged)
        self.assertEqual(self.res.iterations, 6)

    def test_table8_masses(self):
        expected = {
            "payload": 12.0, "mobility_running_gear": 75.0,
            "mobility_actuators": 4.6, "eps_source": 25.3, "eps_battery": 1.5,
            "eps_pmad": 4.0, "structure": 16.5, "thermal": 12.8,
            "data_handling": 5.1, "navigation": 2.4, "comms": 7.7,
            "harness": 3.6, "margin": 26.6,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(self.res.masses[key], value, delta=0.05, msg=key)
        self.assertAlmostEqual(self.res.total_mass, 197.1, delta=0.05)
        dry = self.res.total_mass - self.res.masses["margin"]
        self.assertAlmostEqual(dry, 170.5, delta=0.05)

    def test_table8_power(self):
        self.assertAlmostEqual(self.res.powers["drive_electrical"], 44.8, delta=0.05)
        self.assertAlmostEqual(self.res.powers["source_sized"], 61.7, delta=0.05)
        self.assertAlmostEqual(self.res.powers["housekeeping"], 55.0, delta=0.05)

    def test_table9_performance(self):
        p = self.p
        self.assertAlmostEqual(p["sinkage_m"] * 1000.0, 1.9, delta=0.06)
        self.assertAlmostEqual(p["contact_pressure_kPa"], 1.63, delta=0.005)
        self.assertAlmostEqual(p["thrust_required_N"], 126.0, delta=0.5)
        self.assertAlmostEqual(p["thrust_available_N"], 307.0, delta=0.5)
        self.assertAlmostEqual(p["drawbar_margin"], 2.45, delta=0.005)
        self.assertAlmostEqual(p["equilibrium_slip"], 0.018, delta=0.0005)
        self.assertAlmostEqual(p["screw_torque_Nm"], 18.9, delta=0.05)
        self.assertAlmostEqual(p["screw_speed_rpm"], 5.3, delta=0.05)
        self.assertAlmostEqual(p["motor_torque_Nm"], 0.07, delta=0.005)
        self.assertEqual(round(p["gear_ratio"]), 938)
        self.assertAlmostEqual(p["mobility_mass_fraction"], 0.40, delta=0.005)
        self.assertAlmostEqual(p["obstacle_capability_m"], 0.36, delta=0.006)
        self.assertAlmostEqual(p["overturning_margin"], 55.0, delta=0.5)
        self.assertAlmostEqual(p["screw_vol"], 0.52, delta=0.005)
        self.assertAlmostEqual(p["screw_vol_req"], 0.47, delta=0.005)
        self.assertAlmostEqual(p["flotation_margin"], 1.12, delta=0.005)

    def test_section_4_4_and_5_numbers(self):
        p = self.p
        self.assertAlmostEqual(p["radius_to_sinkage"], 182.0, delta=0.5)
        self.assertAlmostEqual(p["resistance_used_N"], 26.7, delta=0.05)
        self.assertAlmostEqual(p["resistance_bekker_N"], 0.2, delta=0.05)
        self.assertAlmostEqual(p["aero_drag_N"], 5.7, delta=0.05)
        self.assertAlmostEqual(p["drive_energy_Wh_per_km"], 445.0, delta=0.5)
        self.assertAlmostEqual(p["traverse_m_per_earth_day"], 360.0, delta=5.0)

    def test_every_screen_of_table6_passes(self):
        for name, ok in self.res.checks.items():
            self.assertTrue(ok, name)


class Figure1Sensitivity(unittest.TestCase):
    """Section 5.1: the drum shell areal density dominates."""

    def test_drum_areal_density_range(self):
        self.assertAlmostEqual(baseline(drum_areal_density=12.6).total_mass, 201.0, delta=0.5)
        self.assertAlmostEqual(baseline(drum_areal_density=53.1).total_mass, 485.0, delta=0.5)

    def test_blade_areal_density_range(self):
        self.assertAlmostEqual(baseline(blade_areal_density=14.6).total_mass, 176.4, delta=0.1)


class Figure2ClosureLimit(unittest.TestCase):
    def test_closure_limit(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rho = run_example.closure_limit(Mission(), ScrewGeometry(),
                                            TITAN_LUNAR_PROXY, TITAN)
        self.assertAlmostEqual(rho, 14.3, delta=0.05)


class Figure3TerrainCases(unittest.TestCase):
    def test_thrust_ratio_on_every_terrain(self):
        expected = {
            "dry_sand": 3.40, "clayey_soil": 3.23, "sandy_loam": 2.91,
            "titan_lunar_proxy": 2.45, "lunar_average": 2.21, "mss_b": 1.02,
            "snow_msa": 0.94, "mss_a": 0.92, "msa_sand_wes": 0.50,
            "liquefied_soft": 0.22,
        }
        for name, ratio in expected.items():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = size(Mission(), ScrewGeometry(), CASES[name], TITAN, MassModel())
            self.assertAlmostEqual(r.performance["drawbar_margin"], ratio,
                                   delta=0.005, msg=name)


class Figure4TractionCalibration(unittest.TestCase):
    """Section 5.3: kappa calibrated on the Marsh Screw Amphibian."""

    def run_kappa(self, kappa):
        g = dataclasses.replace(ScrewGeometry(), traction_efficiency=kappa)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = size(Mission(), g, TITAN_LUNAR_PROXY, TITAN, MassModel())
        slope, _ = run_example.max_slope_deg(
            r.performance["thrust_available_N"], r.total_mass * TITAN.gravity,
            r.performance["resistance_used_N"] + r.performance["aero_drag_N"])
        return r, slope

    def test_slope_calibration(self):
        r, slope = self.run_kappa(0.65)
        self.assertAlmostEqual(r.performance["drawbar_margin"], 1.59, delta=0.005)
        self.assertAlmostEqual(r.performance["equilibrium_slip"], 0.036, delta=0.0005)
        self.assertAlmostEqual(slope, 39.0, delta=0.5)

    def test_towing_calibration(self):
        r, slope = self.run_kappa(0.35)
        self.assertAlmostEqual(r.performance["drawbar_margin"], 0.86, delta=0.005)
        self.assertLess(r.performance["equilibrium_slip"], 0.0)   # traction limited
        self.assertAlmostEqual(slope, 16.0, delta=0.5)

    def test_mass_does_not_move_with_kappa(self):
        self.assertAlmostEqual(self.run_kappa(0.35)[0].total_mass,
                               self.run_kappa(1.0)[0].total_mass, places=6)


class Figure5FeasibilityBox(unittest.TestCase):
    """Section 5.5: under 213 kg only the 0.55 m drum passes, up to 20 kg."""

    @staticmethod
    def feasible(d, payload):
        g0 = ScrewGeometry()
        k = d / g0.drum_diameter
        g = dataclasses.replace(g0, drum_diameter=d, blade_height=g0.blade_height * k,
                                length=g0.length * k, pitch=g0.pitch * k)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return size(Mission(payload_mass=payload), g, TITAN_LUNAR_PROXY,
                        TITAN, MassModel()).feasible

    def test_feasible_region(self):
        self.assertTrue(self.feasible(0.55, 20))
        self.assertFalse(self.feasible(0.55, 25))
        for pl in (5, 20, 40):
            self.assertFalse(self.feasible(0.45, pl))
            self.assertFalse(self.feasible(0.65, pl))


class Sections52and54Gravity(unittest.TestCase):
    @staticmethod
    def rows(terrain):
        _, text = quietly(run_example.gravity_study, ScrewGeometry(), terrain,
                          m_fixed=baseline().total_mass)
        out = {}
        for body in ("Earth", "Moon", "Titan"):
            out[body] = number(body + r"\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+"
                                      r"([\d.]+)\s+([\d.]+)\s+([\d.]+)", text)
        return out

    def test_lunar_proxy(self):
        r = self.rows(TITAN_LUNAR_PROXY)
        for body, z, p, mu in (("Earth", 7.4, 6.1, 0.93), ("Moon", 2.2, 1.8, 1.12),
                               ("Titan", 1.9, 1.6, 1.15)):
            self.assertAlmostEqual(r[body][0], z, delta=0.06, msg=body)
            self.assertAlmostEqual(r[body][1], p, delta=0.05, msg=body)
            self.assertAlmostEqual(r[body][2], mu, delta=0.005, msg=body)

    def test_wet_clay_slope_does_not_move(self):
        r = self.rows(LIQUEFIED_SOFT)
        for body in ("Earth", "Moon", "Titan"):
            self.assertAlmostEqual(r[body][3], 2.0, delta=0.5, msg=body)


class Tables3and4Database(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = make_paper_tables.load()

    def test_table3_inventory(self):
        self.assertEqual(len(self.rows), 24)
        count = {}
        for r in self.rows:
            count[r["architecture"]] = count.get(r["architecture"], 0) + 1
        self.assertEqual(count, {"screw": 14, "screw_wheel": 1, "wheel": 6,
                                 "track": 2, "tensegrity": 1})

    def test_table4_completeness(self):
        def n(test):
            return sum(1 for r in self.rows if test(r))
        has = lambda r, k: make_paper_tables.num(r[k]) is not None  # noqa: E731
        geometry = ("drum_diameter_m", "blade_height_m", "length_m", "pitch_m")
        self.assertEqual(n(lambda r: has(r, "mass_kg") or has(r, "gross_mass_kg")), 21)
        self.assertEqual(n(lambda r: has(r, "mobility_mass_kg")), 7)
        self.assertEqual(n(lambda r: has(r, "payload_mass_kg")), 9)
        self.assertEqual(n(lambda r: has(r, "power_W")), 13)
        self.assertEqual(n(lambda r: has(r, "speed_mps")), 9)
        self.assertEqual(n(lambda r: all(has(r, k) for k in geometry)), 3)
        self.assertEqual(n(lambda r: has(r, "mu_drawbar")), 1)

    def test_section_4_4_mobility_fraction_ranges(self):
        f = make_paper_tables.fractions(self.rows, "mobility_mass_kg")
        screw = [v for _, v in f["screw"]]
        wheel = [v for _, v in f["wheel"]]
        self.assertAlmostEqual(min(screw), 16.4, delta=0.05)
        self.assertAlmostEqual(max(screw), 49.3, delta=0.05)
        self.assertAlmostEqual(min(wheel), 15.0, delta=0.05)
        self.assertAlmostEqual(max(wheel), 47.0, delta=0.05)


class Tables10and11MarshScrewAmphibian(unittest.TestCase):
    def test_table10_screw_terrain_block(self):
        _, text = quietly(validate.level_a)
        self.assertEqual(number(r"empty\s+\d+kg\s+([\d.]+)k\s+([\d.]+)k\s+\+(\d+)%", text),
                         [4.15, 3.59, 16.0])
        self.assertEqual(number(r"loaded\s+\d+kg\s+([\d.]+)k\s+([\d.]+)k\s+\+(\d+)%", text),
                         [5.74, 4.96, 16.0])
        z_patel, z_wong = number(r"z =\s+([\d.]+) mm.*\n.*z =\s+([\d.]+) mm", text)
        self.assertAlmostEqual(z_patel, 37.0, delta=0.5)
        self.assertAlmostEqual(z_wong, 11.0, delta=0.5)
        self.assertAlmostEqual(number(r"mu = ([\d.]+)", text)[0], 0.68, delta=0.005)
        self.assertEqual(number(r"from towing\s+([\d.]+)", text), [0.36])
        self.assertEqual(number(r"from slope tests\s+([\d.]+) to ([\d.]+)", text),
                         [0.61, 0.70])

    def test_table11_closure_loop(self):
        _, text = quietly(validate.level_c)
        self.assertIn("converged: True in 10 iterations", text)
        rows = {
            r"total mass, kg\s+([\d.]+)\s+([\d.]+)": (1170.0, 1794.0),
            r"empty mass, kg\s+([\d.]+)\s+([\d.]+)": (674.0, 1297.0),
        }
        for pattern, (loop, msa) in rows.items():
            got = number(pattern, text)
            self.assertAlmostEqual(got[0], loop, delta=0.5, msg=pattern)
            self.assertAlmostEqual(got[1], msa, delta=0.5, msg=pattern)
        for pattern, value in ((r"running gear, kg\s+([\d.]+)", 205.0),
                               (r"hull and frame, kg\s+([\d.]+)", 351.0),
                               (r"flotation margin\s+([\d.]+)", 1.93),
                               (r"drawbar margin, kappa 1\s+([\d.]+)", 1.83),
                               (r"drawbar margin, kappa 0.65\s+([\d.]+)", 1.19),
                               (r"drawbar margin, kappa 0.35\s+([\d.]+)", 0.64)):
            got = number(pattern, text)[0]
            tol = 0.5 if value > 10 else 0.005
            self.assertAlmostEqual(got, value, delta=tol, msg=pattern)


if __name__ == "__main__":
    unittest.main()
