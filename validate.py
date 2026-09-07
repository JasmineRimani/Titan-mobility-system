"""Validation against real vehicles, at two levels.

    python validate.py

LEVEL 0, priors from the database.
    Mobility mass fraction for every entry that has one, with median and
    range, split by architecture. This is what the database is legitimately
    for: seeding the loop and bounding the answer. It is not evidence about
    Titan.

LEVEL B, mobility-block reconstruction at the vehicle's known mass.
    For every entry with enough data, the mobility mass and drive power are
    hidden, the mobility block runs from the vehicle's recorded mass,
    geometry, terrain and speed, and the prediction is compared:

        eps = |predicted - actual| / actual

    This deliberately does NOT run the full mass-closure loop. Closing the
    loop needs a power-system model, and a radioisotope source is the wrong
    model for a terrestrial vehicle with a diesel engine. Validate the
    mobility block here; validate the closure separately once a planetary
    vehicle with a full mass budget is in the database.

    Entries without enough data are listed with the fields that are missing.
    That list is the work plan for the database.

Earth validation validates the model structure and the workflow. It does not
validate Titan performance. Say so in the paper.
"""

import csv
import os
import statistics

from sizing.environment import EARTH
from sizing.mers import (MassModel, drive_module_mass, running_gear_mass)
from sizing.screw import (ScrewGeometry, check_validity, compaction_resistance,
                          contact_width, kinematics, sinkage, torque_and_power)
from sizing.terrain import CASES

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "data", "vehicles.csv")

GEOMETRY = ["drum_diameter_m", "blade_height_m", "length_m", "pitch_m"]
TRUTH = ["mobility_mass_kg", "power_W"]
MISSION = ["payload_mass_kg", "speed_mps", "mass_definition", "terrain_case"]
REQUIRED = GEOMETRY + TRUTH + MISSION


def f(row, key):
    try:
        return float(row[key])
    except (TypeError, ValueError, KeyError):
        return None


def total_mass(row):
    return f(row, "gross_mass_kg") or f(row, "mass_kg")


def level0(rows):
    print("=" * 74)
    print("LEVEL 0 : MOBILITY MASS FRACTION PRIORS FROM THE DATABASE")
    print("=" * 74)
    by_arch = {}
    for r in rows:
        m, t = f(r, "mobility_mass_kg"), total_mass(r)
        if m and t:
            by_arch.setdefault(r["architecture"], []).append((r["system_id"], m / t, r["source_id"]))

    for arch, items in sorted(by_arch.items()):
        vals = sorted(v for _, v, _ in items)
        med = statistics.median(vals)
        print(f"\n{arch}  (n = {len(vals)})")
        for sid, v, src in sorted(items, key=lambda x: x[1]):
            print(f"    {sid:14s} {v:6.3f}   [{src}]")
        print(f"    {'median':14s} {med:6.3f}   range {min(vals):.3f} to {max(vals):.3f}")

    screw = [v for _, v, _ in by_arch.get("screw", [])]
    wheel = [v for _, v, _ in by_arch.get("wheel", [])]
    print("\nHow to use these numbers:")
    print("  - as a starting guess for the loop, m_mobility_0 = f * m_total_0")
    print("  - as a plausibility bound on the converged answer")
    print("  - NOT as the answer itself")
    if screw and wheel:
        print(f"\n  screw range   {min(screw):.3f} to {max(screw):.3f}")
        print(f"  wheeled range {min(wheel):.3f} to {max(wheel):.3f}")
        if min(screw) < max(wheel) and min(wheel) < max(screw):
            print("  The two ranges OVERLAP. With this data you cannot claim that")
            print("  screw mobility costs a larger mass fraction than wheels.")
    print(f"\n  n is small ({sum(len(v) for v in by_arch.values())} entries with a mobility mass).")
    print("  Adding entries with a documented mobility mass split is the single")
    print("  highest-value database task.\n")


def level_b(rows):
    print("=" * 74)
    print("LEVEL B : MOBILITY-BLOCK RECONSTRUCTION AT KNOWN VEHICLE MASS")
    print("=" * 74)

    usable, incomplete = [], []
    for r in rows:
        missing = [k for k in REQUIRED if not (r.get(k) or "").strip()]
        if not total_mass(r):
            missing.append("gross_mass_kg or mass_kg")
        if r["terrain_case"] and r["terrain_case"] not in CASES:
            missing.append("terrain_case (unknown case)")
        (incomplete if missing else usable).append((r, missing))

    if not usable:
        print("\nNo entry carries enough data for a reconstruction yet.")
        print("That is the honest state of the database, not a bug.\n")

    mm = MassModel()
    for r, _ in usable:
        terrain = CASES[r["terrain_case"]]
        if not terrain.has_bekker:
            print(f"\n{r['system_id']}: terrain '{terrain.name}' has no Bekker "
                  f"parameters, so sinkage cannot be computed. Skipped.")
            continue

        geom = ScrewGeometry(
            n_screws=int(float(r["n_screws"])),
            drum_diameter=f(r, "drum_diameter_m"), blade_height=f(r, "blade_height_m"),
            length=f(r, "length_m"), pitch=f(r, "pitch_m"),
            n_starts=int(float(r["n_starts"] or 1)))

        m = total_mass(r)
        v = f(r, "speed_mps")
        slip = 0.30                       # CHOICE, inside the observed range
        w = m * EARTH.gravity
        load = w / geom.n_screws

        z = sinkage(load, geom, terrain)
        r_comp = geom.n_screws * compaction_resistance(z, geom, terrain)
        f_req = max(r_comp, terrain.c_rr * w)   # larger of Bekker compaction
                                                # and the empirical c_rr lump
        omega, _ = kinematics(geom, v, slip)
        torque, p_mech = torque_and_power(f_req / geom.n_screws, geom, omega)
        p_elec = geom.n_screws * p_mech / mm.drivetrain_efficiency

        m_pred = running_gear_mass(geom, mm) + geom.n_screws * (
            drive_module_mass(torque, mm) + mm.drive_electronics)
        m_act = f(r, "mobility_mass_kg")
        p_act = f(r, "power_W")

        print(f"\n{r['system_id']}  {r['name']}   [{r['source_id']}]")
        print(f"  vehicle mass {m:.1f} kg, {geom.n_screws} screws, "
              f"D_outer {geom.outer_diameter:.3f} m, L {geom.length:.3f} m, "
              f"p {geom.pitch:.3f} m, lead {geom.helix_angle_deg:.1f} deg")
        print(f"  sinkage {z*1000:.1f} mm ({z/geom.outer_diameter:.3f} D), "
              f"contact pressure "
              f"{load/(contact_width(z, geom.outer_diameter)*geom.length)/1000.0:.2f} kPa")
        print(f"  mobility mass  predicted {m_pred:9.2f} kg   actual {m_act:9.2f} kg"
              f"   eps = {abs(m_pred-m_act)/m_act*100:7.1f} %")
        print(f"  drive power    predicted {p_elec:9.1f} W    actual {p_act:9.1f} W "
              f"   eps = {abs(p_elec-p_act)/p_act*100:7.1f} %")
        print(f"  careful: the recorded power is {r['power_type']}, which is not"
              f" the same quantity as a continuous drive power. Compare like"
              f" with like before drawing a conclusion.")
        if abs(m_pred - m_act) / m_act > 0.3:
            print("  -> mass error above 30 percent. The drum and blade areal")
            print("     densities in mers.py are placeholders and they carry")
            print("     most of the mobility mass. Calibrate them on this")
            print("     vehicle before trusting any converged design.")
        if not check_validity(z, geom, quiet=True):
            print("  -> sinkage exceeds the blade height, so the model is")
            print("     outside its validity range [villacres2023].")

    print("\n" + "=" * 74)
    print("ENTRIES NOT YET USABLE, AND WHY")
    print("=" * 74)
    counts = {}
    for r, missing in incomplete:
        for k in missing:
            counts[k] = counts.get(k, 0) + 1
        print(f"{r['system_id']:14s} {r['name'][:32]:32s} {', '.join(missing)}")
    print("\nMost frequently missing fields, in priority order:")
    for k, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {c:3d} x  {k}")
    print("\nFilling these, each with a source, is the database work plan.")
    print("The Marsh Screw Amphibian reports are the highest-value target:")
    print("they are the only source with documented test conditions and a")
    print("measured drawbar coefficient.\n")


def main():
    with open(PATH, newline="") as fh:
        rows = list(csv.DictReader(fh))
    level0(rows)
    level_b(rows)


if __name__ == "__main__":
    main()
