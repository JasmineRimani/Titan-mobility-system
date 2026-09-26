"""Validation against real vehicles, at two levels.

    python validate.py

LEVEL 0, priors from the database.
    Mobility mass fraction for every entry that has one, with median and
    range, split by architecture. This is what the database is legitimately
    for: seeding the loop and bounding the answer. It is not evidence about
    Titan.

LEVEL A, screw-terrain block against the Marsh Screw Amphibian tests.
    The only full-scale screw vehicle for which geometry, test weight, soil
    and measured performance are all in one document (wes_tr3641, DTIC
    AD0450621). The block is run at the vehicle's test weight on the sand
    case and compared with the report's ground pressure, first-pass rut,
    towing force and slope-climbing results. The gap between the
    Mohr-Coulomb ceiling and the measured drawbar pull is expressed as a
    screw traction efficiency, which is then carried into the Titan
    sensitivity study. This is the calibration the paper needs before it
    quotes a traction margin on Titan.

LEVEL C, closure-loop design of a new vehicle to the MSA requirements.
    The whole sizing loop is run as if the Marsh Screw Amphibian had to be
    designed from its requirements (Earth, sand, 496 kg payload, 0.72 m/s,
    18 deg slope) with its rotor geometry, and the converged vehicle is
    compared with the one that was built. The power system is an engine,
    not an RTG, so a terrestrial mass model with clearly ASSUMED
    coefficients is used. This checks that the loop closes, that the
    flotation screen agrees with a vehicle that is known to have floated,
    and shows which coefficients the closed mass is sensitive to.

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
import dataclasses
import math
import os
import statistics

from sizing.environment import EARTH
from sizing.mers import (MassModel, drive_module_mass, running_gear_mass)
from sizing.sizing_loop import Mission, size
from sizing.screw import (ScrewGeometry, check_validity, compaction_resistance,
                          contact_width, coulomb_ceiling, kinematics,
                          rolling_resistance, sinkage, slip_mobilisation,
                          torque_and_power)
from sizing.terrain import CASES, Terrain

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


# --- Level A -------------------------------------------------------------
# The Marsh Screw Amphibian as tested by WES in 1963-64. Every number here
# is read from wes_tr3641 and duplicated in data/vehicles.csv and
# data/benchmarks.csv, page references there.
IN = 0.0254
LB = 0.45359237
MSA_GEOM = ScrewGeometry(n_screws=2, drum_diameter=26 * IN, blade_height=2.5 * IN,
                         length=129.5 * IN, pitch=48 * IN, n_starts=1)
MSA_MASS_EMPTY, MSA_MASS_LOADED = 2860 * LB, 3954 * LB
MSA_MEASURED = {
    "ground_pressure_kPa_at_3in": {"empty": 0.52 * 6.894757, "loaded": 0.72 * 6.894757},
    "rut_first_pass_m_unloaded_sand": 5.6 * IN,
    "towing_over_weight_sand_loaded": 0.24,
    "slope_climbed_deg": 18.0, "slope_failed_deg": 21.0,
    "towing_over_weight_clay_loaded": 425.0 / 3954.0, "slip_at_peak_clay": 0.28,
}
# Wong's own dry-sand set (n = 1.1, k_phi 1.528e6) against the Patel table
# (n = 1, k_phi 1.52e5): docs/MODEL_NOTES.md (section 4b) flags the discrepancy, this block shows
# what each does to the MSA sinkage.
SAND_WONG = Terrain("dry_sand_wong", 990.0, 1.528e6, 1.1, 1040.0, 28.0, 0.025,
                    1520.0, None, "Wong 2001 as usually quoted", "check the book",
                    c_rr=0.075, c_rr_source="rimani_week4_mobility")


def level_a():
    sand = CASES["msa_sand_wes"]
    g = MSA_GEOM
    print("=" * 74)
    print("LEVEL A : SCREW-TERRAIN BLOCK AGAINST THE MARSH SCREW AMPHIBIAN")
    print("=" * 74)
    print(f"geometry [wes_tr3641 p. 4-5]: {g.n_screws} rotors, drum {g.drum_diameter:.3f} m, "
          f"over helix {g.outer_diameter:.3f} m, contact length {g.length:.3f} m, "
          f"lead {g.pitch:.3f} m, lead angle {g.helix_angle_deg:.1f} deg at the mean "
          f"diameter (report: about 32 deg to the vertical)")
    print(f"power-screw efficiency at mu_sm = {g.soil_metal_friction}: {g.screw_efficiency:.3f}")
    print()

    # (a) contact pressure at the report's 3 in penetration, both weights
    print("(a) ground pressure at 3 in penetration, equivalent-cylinder contact model")
    print(f"    {'case':8s} {'weight':>8s} {'model':>8s} {'report':>8s} {'error':>7s}")
    for case, m in (("empty", MSA_MASS_EMPTY), ("loaded", MSA_MASS_LOADED)):
        w = m * EARTH.gravity / g.n_screws
        b = contact_width(3 * IN, g.outer_diameter)
        model = w / (b * g.length) / 1000.0
        meas = MSA_MEASURED["ground_pressure_kPa_at_3in"][case]
        print(f"    {case:8s} {m:7.0f}kg {model:7.2f}k {meas:7.2f}k {(model-meas)/meas*100:+6.0f}%")
    print("    The report's figure is itself a computed ground pressure, so this")
    print("    checks the contact-area convention of Eq. (4), not the soil.")
    print()

    # (b) static sinkage against the first-pass rut, two Bekker sets
    print("(b) static sinkage, unloaded on sand, against the 5.6 in first-pass rut")
    w = MSA_MASS_EMPTY * EARTH.gravity / g.n_screws
    for name, t in (("patel2005 table (k_phi 1.52e5, n 1)", sand),
                    ("Wong as usually quoted (k_phi 1.528e6, n 1.1)", SAND_WONG)):
        z = sinkage(w, g, t)
        print(f"    {name:46s} z = {z*1000:6.1f} mm   z/BH = {z/g.blade_height:5.2f}"
              f"   rut/z = {MSA_MEASURED['rut_first_pass_m_unloaded_sand']/z:5.1f}")
    print(f"    measured rut after one pass                     {MSA_MEASURED['rut_first_pass_m_unloaded_sand']*1000:6.1f} mm"
          f"   (2.2 blade heights)")
    print("    The static Bekker sinkage is a fraction of the rut a rotating screw")
    print("    cuts in sand. The report describes digging and bulldozing on sand;")
    print("    neither is in the model, so on sand the model UNDERPREDICTS sinkage")
    print("    by a factor of 4 (Patel set) to 20 (Wong set). On the clay with free")
    print("    water the 50-pass rut was 2.6 in, close to the blade height.")
    print()

    # (c) traction: Mohr-Coulomb ceiling against the measured drawbar pull
    print("(c) traction, loaded on sand: Mohr-Coulomb ceiling against measurement")
    w = MSA_MASS_LOADED * EARTH.gravity / g.n_screws
    ceiling = coulomb_ceiling(w, g, sand)
    mu_ceiling = ceiling / w
    mob = slip_mobilisation(0.28, g, sand)
    mu_tow = MSA_MEASURED["towing_over_weight_sand_loaded"]
    # slope tests bound the usable coefficient from the other side:
    # climbed 18 deg, failed 21 deg, with rolling resistance c_rr on top
    mu_slope_lo = math.tan(math.radians(18.0)) + sand.c_rr
    mu_slope_hi = math.tan(math.radians(21.0)) + sand.c_rr
    print(f"    Mohr-Coulomb ceiling, c A + W tan(phi)      mu = {mu_ceiling:.3f}")
    print(f"    Janosi-Hanamoto mobilisation at s = 0.28       {mob:.3f}  (K = {sand.shear_K} m, L = {g.length:.2f} m)")
    print(f"    measured towing force / test weight  [p. 21]   mu = {mu_tow:.3f}")
    print(f"    implied by 18 deg climbed  (tan 18 + c_rr)     mu >= {mu_slope_lo:.3f}")
    print(f"    implied by 21 deg failed   (tan 21 + c_rr)     mu <  {mu_slope_hi:.3f}")
    k_tow = mu_tow / (mu_ceiling * mob)
    k_lo = mu_slope_lo / (mu_ceiling * mob)
    k_hi = mu_slope_hi / (mu_ceiling * mob)
    print(f"    screw traction efficiency kappa = measured / (ceiling x mobilisation):")
    print(f"        from towing        {k_tow:.2f}")
    print(f"        from slope tests   {k_lo:.2f} to {k_hi:.2f}")
    print("    The towing figure was taken at full throttle and 0.5 mph, so it may")
    print("    be power limited as well as traction limited; the slope bracket is")
    print("    the cleaner traction number. Carry kappa = 0.35 (towing) and")
    print("    kappa = 0.65 (slope) into the Titan sensitivity as the calibrated")
    print("    range. kappa = 1 is the uncorrected model and is optimistic on sand.")
    print()

    # (d) fine-grained soil: the cohesion the measured pull would need
    print("(d) fine-grained soil with free water, RCI 20 to 30, loaded")
    mu_clay = MSA_MEASURED["towing_over_weight_clay_loaded"]
    print(f"    measured peak towing / weight at s = 0.28      mu = {mu_clay:.3f}")
    print("    The liquefied_soft case carries this as mu_db_max. Its Bekker and")
    print("    shear parameters are ASSUMED, so no ceiling is computed here; the")
    print("    report itself concludes that cone index does not characterise a")
    print("    screw on this ground and that soil wetness and soil-rotor friction do.")
    print()

    # (e) power: what the model says the MSA needs to move on sand
    print("(e) drive power on sand at the reported 1.6 mph, loaded, s = 0.28")
    W = MSA_MASS_LOADED * EARTH.gravity
    f_req = rolling_resistance(W, sand)
    omega, _ = kinematics(g, 0.72, 0.28)
    torque, p_mech = torque_and_power(f_req / g.n_screws, g, omega)
    print(f"    motion resistance c_rr W                      {f_req:8.0f} N")
    print(f"    rotor speed                                   {omega*60/(2*math.pi):8.1f} rpm")
    print(f"    rotor torque, power-screw analogy             {torque:8.0f} N m")
    print(f"    mechanical drive power, both rotors           {g.n_screws*p_mech/1000:8.1f} kW")
    print(f"    installed engine power                        {86.5:8.1f} kW  [p. 4]")
    print("    Not a like-for-like comparison: installed power is not drive power,")
    print("    and the report describes labored progress on sand. The model's")
    print("    level-ground number is a lower bound; digging, bulldozing and the")
    print("    hull drag it neglects are where the rest of the 116 hp went.")
    print()
    return {"kappa_towing": k_tow, "kappa_slope": (k_lo, k_hi)}


def level_c():
    """Design a new vehicle to the MSA requirements and compare it with the MSA."""
    # dry_sand carries the same Bekker and shear parameters as msa_sand_wes
    # but no measured drawbar cap, so the traction efficiency kappa is what
    # sets the available thrust and the calibration can be seen working.
    sand = CASES["dry_sand"]
    print("=" * 74)
    print("LEVEL C : CLOSURE-LOOP DESIGN OF A NEW VEHICLE TO THE MSA REQUIREMENTS")
    print("=" * 74)
    payload = MSA_MASS_LOADED - MSA_MASS_EMPTY
    # Requirements read from the report: carry the loaded-minus-empty mass,
    # average 1.6 mph on sand, climb the 18 deg slope it climbed. Slip 0.28
    # is where its towing force peaked on clay. No mass cap: the design
    # is free to close where it closes, and the result is compared after.
    mission = Mission(payload_mass=payload, payload_power=0.0, avionics_power=0.0,
                      thermal_power=0.0, target_speed=0.72, design_slope=18.0,
                      design_slip=0.28, drive_duty=1.0, drive_session_h=0.0,
                      max_obstacle=0.0, delivered_mass_cap=1e9,
                      system_mass_cap=1e9, cg_height=1.0,
                      motor_nominal_rpm=3600.0)
    # Terrestrial, engine-driven mass model. Every coefficient ASSUMED and
    # visible here; none is a measurement of the MSA.
    #   engine specific power 0.40 kW/kg: 86.5 kW Chrysler slant-six at
    #     roughly 215 kg dry, order of magnitude only
    #   drive module 25 kg per rotor: chain drive, sprockets, bearings
    #   hull and frame 0.30 of dry mass, no thermal, no avionics
    #   drum areal density 12 kg/m2 as in the Titan case, aluminium rotor
    mm = MassModel(module_mass=25.0, drive_electronics=0.0,
                   structure_fraction=0.30, thermal_fraction=0.0,
                   data_handling_fraction=0.0, navigation_fraction=0.0,
                   comms_fraction=0.0, harness_fraction=0.02,
                   margin_fraction=0.0, source_specific_power=400.0,
                   battery_specific_energy=1.0, pmad_fraction=0.0,
                   drivetrain_efficiency_model="course")
    geom = MSA_GEOM
    r = size(mission, geom, sand, EARTH, mm, m_guess=1500.0)
    print(f"requirements: payload {payload:.0f} kg, {mission.target_speed:.2f} m/s, "
          f"{mission.design_slope:.0f} deg slope on sand, slip {mission.design_slip}")
    print(f"geometry fixed at the MSA rotor; mass model terrestrial, all ASSUMED")
    print(f"converged: {r.converged} in {r.iterations} iterations\n")
    rows = [
        ("total mass, kg", r.total_mass, MSA_MASS_LOADED, "loaded test weight, p. 4"),
        ("empty mass, kg", r.total_mass - payload, MSA_MASS_EMPTY, "empty weight, p. 4"),
        ("running gear, kg", r.masses["mobility_running_gear"], None, "not reported"),
        ("drive modules, kg", r.masses["mobility_actuators"], None, "not reported"),
        ("engine, kg", r.masses["eps_source"], None, "not reported"),
        ("hull and frame, kg", r.masses["structure"], None, "not reported"),
        ("drive power, mech kW", r.powers["drive_mechanical"] / 1000, 86.5, "installed, not drive, p. 4"),
        ("contact pressure, kPa", r.performance["contact_pressure_kPa"], 4.96, "loop at static sinkage; report at 3 in"),
        ("static sinkage, mm", r.performance["sinkage_m"] * 1000, 142.0, "first-pass rut, unloaded"),
        ("drum displacement, m3", r.performance["screw_vol"], None, ""),
        ("volume to float, m3", r.performance["screw_vol_req"], None, ""),
        ("flotation margin", r.performance["flotation_margin"], None, "MSA floated: 8 mph on water"),
        ("drawbar margin, kappa 1", r.performance["drawbar_margin"], None, "uncorrected"),
    ]
    print(f"    {'quantity':26s} {'loop':>10s} {'MSA':>10s}   note")
    for name, v, ref, note in rows:
        ref_s = "-" if ref is None else f"{ref:10.2f}"
        print(f"    {name:26s} {v:10.2f} {ref_s:>10s}   {note}")
    for kappa in (0.65, 0.35):
        g = dataclasses.replace(geom, traction_efficiency=kappa)
        rk = size(mission, g, sand, EARTH, mm, m_guess=1500.0)
        print(f"    {'drawbar margin, kappa ' + format(kappa, '.2f'):26s} {rk.performance['drawbar_margin']:10.2f} "
              f"{'-':>10s}   18 deg slope; the MSA climbed it")
    print()
    print("Read: with the rotor geometry fixed, the loop closes an engine-driven")
    print("vehicle in the right mass class, about one third lighter than the")
    print("loaded MSA and about half its empty mass, and the drum-only")
    print("flotation screen passes with margin, as it must")
    print("for a vehicle that ran at 8 mph on water. The empty mass is not a")
    print("prediction: hull fraction, engine specific power and drum areal")
    print("density are all assumed and each moves it by tens of percent; a")
    print("welded aluminium hull with a driver's cab is heavier than a rover")
    print("chassis fraction allows for. The traction rows are the useful part:")
    print("at kappa = 0.65 the loop says the vehicle climbs the 18 deg slope it")
    print("did climb, and at kappa = 0.35 it says it cannot, which is the")
    print("evidence that the towing figure was power limited and that the slope")
    print("bracket is the calibration to carry. The mechanical drive power is")
    print("a level-ground-plus-slope number and cannot be compared with the")
    print("installed engine power.")
    print()
    return r


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
    level_a()
    level_c()
    level_b(rows)


if __name__ == "__main__":
    main()
