"""Actuator mass model: check what data exists, and fit only if it can.

    python fit_mers.py

WHY THIS SCRIPT LOOKS THE WAY IT DOES

The package used to ship an invented power law m = a * T^b for motors and
gearboxes, fitted to synthetic rows. Both are gone. Not one source indexed in
sources.yaml gives a rated torque AND a mass for the same actuator, so that
regression cannot be fitted, checked or defended from the literature.

The method taught in rimani_week4_mobility does not need it. It sizes the
drive by torque and speed, matches a datasheet, and takes the module mass
from a bracket of 0.5 to 2 kg per driven wheel module, cross-checked against
a 10 to 25 percent drivetrain mass fraction. That is what sizing/mers.py now
does by default.

This script therefore does three things:
  1. reports what data/actuators.csv actually contains, and what each row is
     missing,
  2. fits m = a * T^b if and only if there are at least three complete rows,
  3. otherwise reports the module model that is being used instead, and what
     it would take to replace it.

To collect the missing half: each row names a real part. Open the
manufacturer datasheet, read the rated torque or the mass, and fill the gap.
Fifteen complete rows spanning two decades of torque are enough for a fit
worth quoting.
"""

import csv
import math
import os

from sizing.mers import MODULE_MASS_RANGE_KG, DRIVETRAIN_FRACTION_RANGE, MassModel

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "data", "actuators.csv")
MIN_POINTS = 3


def fit_power_law(x, y):
    """Least squares on log10(y) = log10(a) + b log10(x). Returns a, b, r2."""
    lx = [math.log10(v) for v in x]
    ly = [math.log10(v) for v in y]
    n = len(lx)
    mx, my = sum(lx) / n, sum(ly) / n
    sxx = sum((v - mx) ** 2 for v in lx)
    sxy = sum((lx[i] - mx) * (ly[i] - my) for i in range(n))
    b = sxy / sxx
    loga = my - b * mx
    pred = [loga + b * v for v in lx]
    ss_res = sum((ly[i] - pred[i]) ** 2 for i in range(n))
    ss_tot = sum((v - my) ** 2 for v in ly)
    return 10.0 ** loga, b, (1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"))


def main():
    with open(PATH, newline="") as fh:
        rows = list(csv.DictReader(fh))

    complete, partial = [], []
    for r in rows:
        try:
            r["_T"] = float(r["rated_torque_Nm"])
            r["_m"] = float(r["mass_kg"])
            complete.append(r)
        except (TypeError, ValueError):
            partial.append(r)

    print("=" * 70)
    print("WHAT data/actuators.csv CONTAINS")
    print("=" * 70)
    print(f"{len(rows)} rows, {len(complete)} with both a torque and a mass.\n")
    for r in partial:
        has = ("mass only" if r["mass_kg"] else
               ("torque only" if r["rated_torque_Nm"] else "neither"))
        print(f"  {r['model'][:38]:38s} {has:12s} [{r['source_id']}]")
    if partial:
        print("\nEvery row above names a real part. The missing half is in the")
        print("manufacturer datasheet, not in any of the papers.\n")

    print("=" * 70)
    if len(complete) >= MIN_POINTS:
        print("FIT")
        print("=" * 70)
        for kind in sorted({r["part_type"] for r in complete}):
            sub = [r for r in complete if r["part_type"] == kind]
            if len(sub) < MIN_POINTS:
                print(f"{kind}: only {len(sub)} complete rows, need {MIN_POINTS}")
                continue
            t = [r["_T"] for r in sub]
            m = [r["_m"] for r in sub]
            a, b, r2 = fit_power_law(t, m)
            err = [abs(a * ti ** b - mi) / mi for ti, mi in zip(t, m)]
            print(f"{kind}:  m = {a:.5f} * T^{b:.4f}")
            print(f"    n = {len(sub)}, R2 = {r2:.4f}, "
                  f"mean |err| = {100*sum(err)/len(err):.1f} %")
            print(f"    valid for T in [{min(t):.2f}, {max(t):.2f}] N m")
            print(f"    -> MassModel(actuator_model='power_law', "
                  f"{kind}_a={a:.5f}, {kind}_b={b:.4f})")
            if b < 0.7 or b > 1.1:
                print(f"    WARNING: exponent {b:.2f} is outside the range a")
                print(f"    torque-scaling argument would predict. For a machine")
                print(f"    of constant air-gap shear stress, torque and mass both")
                print(f"    scale with rotor volume, so b near 1. Bigger machines")
                print(f"    cool better and reach higher shear stress, pulling b")
                print(f"    down towards 0.8. Outside 0.7 to 1.1, suspect the data.")
    else:
        mm = MassModel()
        lo, hi = MODULE_MASS_RANGE_KG
        dlo, dhi = DRIVETRAIN_FRACTION_RANGE
        print("NO FIT POSSIBLE, AND NONE IS NEEDED YET")
        print("=" * 70)
        print(f"Only {len(complete)} complete rows, {MIN_POINTS} would be the bare")
        print("minimum and it would still be a two-parameter fit through three")
        print("points. The package is not using a regression.\n")
        print("What it uses instead, from sizing/mers.py:")
        print(f"  drive module mass      {mm.module_mass:.2f} kg per driven screw")
        print(f"  sourced bracket        {lo:.1f} to {hi:.1f} kg per wheel module")
        print(f"                         [rimani_week4_mobility]")
        print(f"  corroboration          1.25 kg for the ExoMars centre wheel")
        print(f"                         motor and gear [patel2005 Table 37]")
        print(f"  cross-check            drivetrain {dlo*100:.0f} to {dhi*100:.0f} "
              f"percent of rover mass")
        print(f"                         [rimani_week4_mobility]")
        print(f"  motor torque margin    {mm.motor_torque_margin:.1f} x")
        print(f"                         [rimani_week4_mobility Step 4]\n")
        print("run_example.py reports the required screw torque, the gear ratio")
        print("and the motor torque, which is what a datasheet match needs.")
        print("Before replacing this with a regression, run the sensitivity")
        print("study in run_example.py: the drive module is a small part of a")
        print("screw vehicle's mobility mass, and the drum and blade areal")
        print("densities are worth far more attention.")
    print()


if __name__ == "__main__":
    main()
