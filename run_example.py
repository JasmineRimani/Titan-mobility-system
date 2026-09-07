"""Baseline Titan case, cross-checks against the literature, and a trade space.

    python run_example.py

Writes outputs/baseline_breakdown.csv, outputs/trade_space.csv and, if
matplotlib is installed, outputs/trade_space.png.
"""

import csv
import math
import os

from sizing.environment import EARTH, MOON, TITAN
from sizing.mers import MassModel
from sizing.screw import (ScrewGeometry, sinkage, compaction_resistance,
                          contact_width, drawbar_available)
from sizing.sizing_loop import Mission, size
from sizing.terrain import CASES, LIQUEFIED_SOFT, TITAN_LUNAR_PROXY

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")


def load_benchmarks():
    with open(os.path.join(HERE, "data", "benchmarks.csv"), newline="") as f:
        return list(csv.DictReader(f))


def database_mobility_fractions():
    """Observed mobility mass fraction per architecture, from data/vehicles.csv."""
    out = {}
    with open(os.path.join(HERE, "data", "vehicles.csv"), newline="") as f:
        for r in csv.DictReader(f):
            tot = r["gross_mass_kg"] or r["mass_kg"]
            if r["mobility_mass_kg"] and tot:
                out.setdefault(r["architecture"], []).append(
                    (r["system_id"], float(r["mobility_mass_kg"]) / float(tot)))
    return out


def print_result(res, title):
    print("=" * 66)
    print(title)
    print("=" * 66)
    print(f"converged: {res.converged} in {res.iterations} iterations\n")
    print("MASS [kg]")
    for k in ("payload", "mobility_running_gear", "mobility_actuators",
              "eps_source", "eps_battery", "eps_pmad", "structure", "thermal",
              "data_handling", "navigation", "comms", "harness", "margin", "total"):
        print(f"  {k:26s} {res.masses[k]:8.1f}")
    print("\nPOWER [W]")
    for k, v in res.powers.items():
        print(f"  {k:26s} {v:8.1f}")
    print("\nPERFORMANCE")
    for k, v in res.performance.items():
        print(f"  {k:26s} {v:8.3f}")
    print("\nFEASIBILITY")
    for k, v in res.checks.items():
        print(f"  {k:26s} {'PASS' if v else 'FAIL'}")
    print(f"\noverall: {'FEASIBLE' if res.feasible else 'NOT FEASIBLE'}")
    if res.warnings:
        print("\nMODEL NOTES")
        for w in res.warnings:
            print(f"  - {w}")
    print()


def cross_check(res):
    """Compare the converged design against numbers taken from the literature."""
    print("=" * 66)
    print("CROSS-CHECK AGAINST THE LITERATURE")
    print("=" * 66)

    frac = res.performance["mobility_mass_fraction"]
    db = database_mobility_fractions()
    screw = sorted(v for _, v in db.get("screw", []))
    wheel = sorted(v for _, v in db.get("wheel", []))
    print(f"mobility mass fraction, this design      {frac:.3f}")
    print(f"  screw vehicles in data/vehicles.csv    "
          f"{min(screw):.3f} to {max(screw):.3f}  ({len(screw)} entries)")
    print(f"  wheeled rovers in data/vehicles.csv    "
          f"{min(wheel):.3f} to {max(wheel):.3f}  ({len(wheel)} entries)")
    print("  chassis fraction K for real rovers     0.300 to 0.500  [patel2005]")
    print("  NOTE: the screw and wheeled ranges overlap. The database as it")
    print("  stands does NOT support a claim that screw mobility is inherently")
    print("  a larger mass fraction than wheeled mobility.\n")

    p = res.performance["contact_pressure_kPa"]
    print(f"contact pressure, this design            {p:.2f} kPa")
    print("  lunar recommended design value         1.40 kPa   [wakabayashi2009]")
    print("  lunar allowable                        8.00 kPa   [wakabayashi2009]")
    print("  terrestrial reference                 20.00 kPa   [wakabayashi2009]\n")

    print(f"cost of transport, this design           {res.performance['cost_of_transport']:.2f}")
    print("  CASPER, 3.4 kg screw rover on Earth      5.30      [green2021, calculated]\n")

    print(f"drive electrical power, this design      {res.powers['drive_electrical']:.1f} W")
    print("  Genta 40 kg Titan rover, level ground    2.4 W     [genta2011]")
    print("  Genta 40 kg Titan rover, 20 deg slope   34.0 W     [genta2011]")
    print("  Ju et al. small screw rover              5 to 6 W  [villacres2023]\n")

    print("expected model error, for reference")
    print("  helical granular scaling laws on BP1     3 to 9 percent   [villacres2023]")
    print("  granular scaling laws generally          9 to 36 percent  [villacres2023]")
    print("  DEM against hardware                   4.5 to 25 percent  [villacres2023]")
    print("  This package is cruder than all three. Quote ranges, not points.\n")


def gravity_study(geom, terrain, m_fixed=200.0):
    """Same vehicle, three gravities.

    Flotation improves as gravity falls, because contact pressure falls.
    Gradeability is subtler: the frictional part of the traction ceiling
    scales with weight and cancels out of the slope balance, but the
    cohesive part does not, so in a cohesive soil low gravity also improves
    the maximum slope. Both effects are visible in the table below.
    """
    print("=" * 66)
    print(f"GRAVITY STUDY, same {m_fixed:.0f} kg vehicle, terrain = {terrain.name}")
    print("=" * 66)
    print(f"{'body':8s} {'g':>6s} {'W':>9s} {'z':>8s} {'z/D':>7s} "
          f"{'p_c':>8s} {'mu_avail':>9s} {'slope_max':>10s}")
    print(f"{'':8s} {'m/s2':>6s} {'N':>9s} {'mm':>8s} {'-':>7s} {'kPa':>8s} "
          f"{'-':>9s} {'deg':>10s}")
    for env in (EARTH, MOON, TITAN):
        w = m_fixed * env.gravity
        load = w / geom.n_screws
        z = sinkage(load, geom, terrain)
        b = contact_width(z, geom.outer_diameter)
        pc = load / (b * geom.length) / 1000.0

        have = geom.n_screws * drawbar_available(load, 0.30, geom, terrain)
        rc = geom.n_screws * compaction_resistance(z, geom, terrain)
        mu_avail = have / w
        lo, hi = 0.0, 85.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if have >= w * math.sin(math.radians(mid)) + rc:
                lo = mid
            else:
                hi = mid
        slope = 0.5 * (lo + hi)
        cap = " (capped)" if slope > 84.0 else ""
        print(f"{env.name:8s} {env.gravity:6.2f} {w:9.1f} {z*1000:8.2f} "
              f"{z/geom.outer_diameter:7.3f} {pc:8.2f} {mu_avail:9.3f} "
              f"{slope:10.1f}{cap}")
    print("\nRead this table carefully, it contains a real result.")
    print("Contact pressure and sinkage scale with gravity, so flotation on")
    print("Titan is close to free. Gradeability is the interesting part. In a")
    print("purely frictional soil the weight cancels between the required and")
    print("the available force, so the maximum slope is gravity independent,")
    print("which is the classic remark. Here it does not fully cancel, because")
    print("the Mohr-Coulomb ceiling has a cohesion term c*A that does NOT")
    print("scale with weight. At low gravity that term is a larger share of")
    print("the total, so mu_avail rises and the maximum slope improves.")
    print("Whether that survives on Titan depends entirely on the cohesion of")
    print("the real surface material, which nobody has measured.")
    if terrain.mu_db_max is None:
        print("This terrain has no measured drawbar cap, so mu_avail comes")
        print("from the Mohr-Coulomb ceiling alone and the slope search can")
        print("saturate. The liquefied_soft case below carries the measured")
        print("cap of 0.64 from the Marsh Screw Amphibian trials.")
    print()


def main():
    os.makedirs(OUT, exist_ok=True)
    mission, geom = Mission(), ScrewGeometry()
    terrain = TITAN_LUNAR_PROXY

    res = size(mission, geom, terrain, TITAN, MassModel())
    print_result(res, f"Baseline: {TITAN.name}, terrain = {terrain.name}")
    cross_check(res)
    gravity_study(geom, terrain, m_fixed=res.total_mass)
    gravity_study(geom, LIQUEFIED_SOFT, m_fixed=res.total_mass)

    with open(os.path.join(OUT, "baseline_breakdown.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "item", "value"])
        for group, d in (("mass_kg", res.masses), ("power_W", res.powers),
                         ("performance", res.performance)):
            for k, v in d.items():
                w.writerow([group, k, round(v, 4)])
        for k, v in res.checks.items():
            w.writerow(["check", k, v])
        for i, note in enumerate(res.warnings):
            w.writerow(["note", i, note])

    print("=" * 66)
    print("TERRAIN SENSITIVITY, same geometry and mission")
    print("=" * 66)
    print(f"{'terrain':20s} {'m_total':>9s} {'z/D':>7s} {'p_c kPa':>9s} "
          f"{'P_drive':>9s} {'margin':>8s} {'feasible':>9s}")
    for name, t in CASES.items():
        if not t.has_bekker:
            print(f"{name:20s} {'-':>9s} {'-':>7s} {'-':>9s} {'-':>9s} {'-':>8s} "
                  f"{'no Bekker data':>9s}")
            continue
        r = size(mission, geom, t, TITAN, MassModel())
        print(f"{name:20s} {r.total_mass:9.1f} {r.performance['sinkage_ratio']:7.3f} "
              f"{r.performance['contact_pressure_kPa']:9.2f} "
              f"{r.powers['drive_electrical']:9.1f} "
              f"{r.performance['drawbar_margin']:8.2f} {str(r.feasible):>9s}")
    print()

    payloads = [5, 10, 12, 15, 20, 25, 30, 40]
    diameters = [0.40, 0.50, 0.60, 0.70, 0.80]
    rows = []
    for d in diameters:
        for pl in payloads:
            m = Mission(payload_mass=pl)
            g = ScrewGeometry(drum_diameter=d, length=2.0 * d, pitch=0.75 * d)
            r = size(m, g, terrain, TITAN, MassModel())
            rows.append({
                "drum_diameter_m": d, "payload_kg": pl,
                "total_mass_kg": round(r.total_mass, 2),
                "mobility_fraction": round(r.performance["mobility_mass_fraction"], 3),
                "sinkage_ratio": round(r.performance["sinkage_ratio"], 4),
                "contact_pressure_kPa": round(r.performance["contact_pressure_kPa"], 3),
                "drive_power_W": round(r.powers["drive_electrical"], 1),
                "drawbar_margin": round(r.performance["drawbar_margin"], 2),
                "cost_of_transport": round(r.performance["cost_of_transport"], 2),
                "feasible": r.feasible,
            })
    with open(os.path.join(OUT, "trade_space.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} trade-space points to outputs/trade_space.csv")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6.8, 4.4))
        for d in diameters:
            sub = [r for r in rows if r["drum_diameter_m"] == d]
            ax.plot([r["payload_kg"] for r in sub], [r["total_mass_kg"] for r in sub],
                    marker="o", ms=4, label=f"D_drum = {d:.2f} m")
            bad = [r for r in sub if not r["feasible"]]
            ax.plot([r["payload_kg"] for r in bad], [r["total_mass_kg"] for r in bad],
                    linestyle="none", marker="x", ms=9, color="0.2")
        cap = Mission().delivered_mass_cap
        ax.axhline(cap, color="0.4", linestyle="--", lw=1)
        ax.annotate(f"delivered mass cap {cap:.0f} kg [tandem_tm2022]",
                    (payloads[0], cap), textcoords="offset points",
                    xytext=(2, 4), fontsize=8, color="0.35")
        ax.set_xlabel("science payload mass [kg]")
        ax.set_ylabel("converged total mass [kg]")
        ax.set_title("Titan screw rover, lunar-proxy terrain\n"
                     "crosses mark infeasible points", fontsize=10)
        ax.legend(fontsize=8, frameon=False)
        ax.grid(alpha=0.25, lw=0.6)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "trade_space.png"), dpi=160)
        print("wrote outputs/trade_space.png")
    except ImportError:
        print("matplotlib not installed, skipping the plot")


if __name__ == "__main__":
    main()
