"""Baseline Titan case, cross-checks against the literature, and a trade space.

    python run_example.py

Writes outputs/baseline_breakdown.csv, outputs/trade_space.csv and, if
matplotlib is installed, outputs/trade_space.png.
"""

import copy
import csv
import dataclasses
import math
import os
import numpy

from sizing.environment import EARTH, MOON, TITAN
from sizing.mers import (AREAL_DENSITY_EVIDENCE, AREAL_DENSITY_RANGE,
                        MassModel, MODULE_MASS_RANGE_KG)
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
    print("  Genta 40 kg WHEELED Titan rover        6.98 kPa   [genta2011]")
    print("  lunar recommended design value         1.40 kPa   [wakabayashi2009]")
    print("  lunar allowable                        8.00 kPa   [wakabayashi2009]")
    print("  terrestrial reference                 20.00 kPa   [wakabayashi2009]")
    print("  A wheeled Titan rover at 40 kg sits at 6.98 kPa. This design is")
    print("  heavier and still sits well below it. That is the flotation")
    print("  argument for screws, quantified against a real Titan concept")
    print("  rather than asserted.\n")

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



def sensitivity(mission, geom, terrain, env, base):
    """Which uncertain input actually moves the answer.

    Each parameter is swept across its plausible range with everything else
    held at the baseline, and the resulting span in converged total mass is
    reported. Rank the list before deciding what to go and measure. There is
    no point fitting a motor mass regression to three decimal places if the
    drum areal density moves the answer ten times as far.
    """
    print("=" * 66)
    print("SENSITIVITY: WHICH UNCERTAIN INPUT MOVES THE ANSWER")
    print("=" * 66)

    def run(mm=None, ms=None, gm=None, tr=None):
        r = size(ms or mission, gm or geom, tr or terrain, env, mm or MassModel())
        return r.total_mass

    cases = []

    def mass_model(**kw):
        return dataclasses.replace(MassModel(), **kw)

    lo, hi = MODULE_MASS_RANGE_KG
    cases.append(("drive module mass, kg", lo, hi,
                  run(mm=mass_model(module_mass=lo)),
                  run(mm=mass_model(module_mass=hi)),
                  "sourced bracket [rimani_week4_mobility]"))

    alo, ahi = AREAL_DENSITY_RANGE
    cases.append(("drum areal density, kg/m2", alo, ahi,
                  run(mm=mass_model(drum_areal_density=alo)),
                  run(mm=mass_model(drum_areal_density=ahi)),
                  "micro-rover wheels [patel2005], see data/running_gear.csv"))

    cases.append(("blade areal density, kg/m2", 14.6, 29.1,
                  run(mm=mass_model(blade_areal_density=14.6)),
                  run(mm=mass_model(blade_areal_density=29.1)),
                  "one face against both faces of the grouser data [patel2005]"))

    cases.append(("drivetrain efficiency", 0.472, 0.78,
                  run(mm=mass_model(drivetrain_efficiency_model="patel")),
                  run(mm=mass_model(drivetrain_efficiency_model="course")),
                  "patel2005 against rimani_week4_mobility"))

    cases.append(("power source, W/kg", 2.44, 3.14,
                  run(mm=mass_model(source_specific_power=2.44)),
                  run(mm=mass_model(source_specific_power=3.14)),
                  "MMRTG against SNAP-19 [genta2011]"))

    cases.append(("soil-on-metal friction", 0.4, 0.8,
                  run(gm=dataclasses.replace(geom, soil_metal_friction=0.4)),
                  run(gm=dataclasses.replace(geom, soil_metal_friction=0.8)),
                  "ASSUMED, sets the screw efficiency"))

    cases.append(("design slip", 0.10, 0.40,
                  run(ms=dataclasses.replace(mission, design_slip=0.10)),
                  run(ms=dataclasses.replace(mission, design_slip=0.40)),
                  "course teaches 10-20 pc, screws reach 40 pc [villacres2023]"))

    cases.append(("rolling resistance c_rr", 0.10, 0.25,
                  run(tr=dataclasses.replace(terrain, c_rr=0.10)),
                  run(tr=dataclasses.replace(terrain, c_rr=0.25)),
                  "loose regolith to very loose [rimani_week4_mobility]"))

    cases.append(("drive duty cycle", 0.05, 0.40,
                  run(ms=dataclasses.replace(mission, drive_duty=0.05)),
                  run(ms=dataclasses.replace(mission, drive_duty=0.40)),
                  "ASSUMED, a mission choice"))

    cases.sort(key=lambda c: -abs(c[4] - c[3]))
    print(f"baseline total mass {base:.1f} kg\n")
    print(f"{'parameter':28s} {'low':>8s} {'high':>8s} {'m_lo':>8s} {'m_hi':>8s} "
          f"{'span':>8s} {'span pc':>8s}")
    for name, lo_v, hi_v, m_lo, m_hi, note in cases:
        span = abs(m_hi - m_lo)
        print(f"{name:28s} {lo_v:8.3f} {hi_v:8.3f} {m_lo:8.1f} {m_hi:8.1f} "
              f"{span:8.1f} {100*span/base:7.1f}%")
    print()
    for name, _, _, _, _, note in cases:
        print(f"  {name:28s} {note}")
    print()
    top = cases[0][0]
    print(f"Ranked by effect, the input worth measuring first is: {top}.")
    print("Spend the effort there, not on the parameter that is easiest to")
    print("look up.\n")



def closure_limit(mission, geom, terrain, env):
    """Heaviest drum shell the design can carry and still close.

    The running gear dominates the mass budget, so the areal density of the
    drum is not just an input, it is a structural requirement. Solve for the
    value at which converged total mass reaches the delivered mass cap, and
    state it as a requirement on the drum design.
    """
    import dataclasses as dc

    def total(rho):
        return size(mission, geom, terrain, env,
                    dc.replace(MassModel(), drum_areal_density=rho)).total_mass

    cap = mission.delivered_mass_cap
    lo, hi = 1.0, 200.0
    if total(lo) > cap:
        return None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if total(mid) <= cap:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def running_gear_requirement(mission, geom, terrain, env, mm):
    print("=" * 66)
    print("DRUM SHELL AS A REQUIREMENT, NOT AN INPUT")
    print("=" * 66)
    limit = closure_limit(mission, geom, terrain, env)
    alo, ahi = AREAL_DENSITY_RANGE
    print(f"delivered mass cap                    {mission.delivered_mass_cap:6.0f} kg"
          f"   [tandem_tm2022]")
    print(f"assumed drum areal density            {mm.drum_areal_density:6.1f} kg/m2  CHOICE")
    if limit is None:
        print("The design does not close at any drum areal density.")
        return
    print(f"closure limit, this geometry          {limit:6.1f} kg/m2")
    print(f"micro-rover wheel evidence range      {alo:6.1f} to {ahi:.1f} kg/m2"
          f"   [patel2005]")
    print()
    for name, v in sorted(AREAL_DENSITY_EVIDENCE.items(), key=lambda kv: kv[1]):
        flag = "closes" if v <= limit else "DOES NOT CLOSE"
        print(f"    {name:16s} {v:5.1f} kg/m2   {flag}")
    print()
    if limit < ahi:
        print("Read that as a requirement on the structure: the drum shell must")
        print("come in under {:.0f} kg per square metre, and several real".format(limit))
        print("micro-rover wheels do not. Those are 10 to 14 cm wheels hollowed")
        print("from aluminium billet, and a 0.6 to 0.8 m drum is a thin rolled")
        print("shell on ribs, so the comparison is an upper bound rather than a")
        print("contradiction. It is still the number to go and check first.")
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
    running_gear_requirement(mission, geom, terrain, TITAN, MassModel())
    sensitivity(mission, geom, terrain, TITAN, res.total_mass)

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


    payloads = numpy.arange(5,50,5) ##[5, 10, 12, 15, 20, 25, 30, 40]
    diameters = numpy.arange(0.1,1,0.2) ##[0.40, 0.50, 0.60, 0.70, 0.80]
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
                "feasible": r.feasible, "floats_in_methane":r.checks["floats_in_methane"],
		"screw_vol, m3": round(r.performance["screw_vol"],3),"screw_vol_req, m3": round(r.performance["screw_vol_req"],3),
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
