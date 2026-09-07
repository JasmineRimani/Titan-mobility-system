"""Fit actuator mass estimation relationships from catalogue data.

    python fit_mers.py

Reads data/actuators.csv and fits  m = a * T^b  on log-log axes, separately
for motors and gearboxes. Prints the coefficients to paste into
sizing/mers.py, together with the fit quality and the range of validity.

data/actuators.csv already holds the real hardware points that appear in the
indexed papers (Maxon RE-25 at 130 g, RE-20 at about 60 g, the Sojourner
RE-16 stall torque, the MER drive actuator output torque, the ARCSnake screw
drive torque). None of them has BOTH a rated torque and a mass, which is why
no fit is possible from the literature alone. Add catalogue rows (Maxon,
Kollmorgen, Nanotec, Harmonic Drive), delete the synthetic ones, and this
script gives you the coefficients to paste into sizing/mers.py.

A few hundred real pairs take an afternoon to collect and they close the
sparsest part of the mobility mass budget.
"""

import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "data", "actuators.csv")


def fit_power_law(x, y):
    """Least squares on log10(y) = log10(a) + b*log10(x). Returns a, b, r2."""
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
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return 10.0 ** loga, b, r2


def main():
    rows, skipped = [], []
    with open(PATH, newline="") as f:
        for r in csv.DictReader(f):
            try:
                r["rated_torque_Nm"] = float(r["rated_torque_Nm"])
                r["mass_kg"] = float(r["mass_kg"])
            except (TypeError, ValueError):
                skipped.append(r)
                continue
            rows.append(r)

    if skipped:
        print(f"{len(skipped)} rows skipped for missing torque or mass:")
        for r in skipped:
            have = "mass" if r["mass_kg"] else ("torque" if r["rated_torque_Nm"] else "neither")
            print(f"  {r['manufacturer']:10s} {r['model'][:28]:28s} has {have:8s} "
                  f"[{r['source_id']}]")
        print("These are the real hardware points in the literature. Each needs")
        print("its missing half from the manufacturer catalogue.\n")

    synthetic = [r for r in rows if "SYNTHETIC" in r["source_id"].upper()]
    if synthetic:
        print("!" * 62)
        print(f"WARNING: {len(synthetic)} of {len(rows)} rows are synthetic demo data.")
        print("Do not quote these coefficients. Replace with catalogue data.")
        print("!" * 62)
        print()

    for kind in ("motor", "gearbox"):
        sub = [r for r in rows if r["part_type"] == kind]
        if len(sub) < 3:
            print(f"{kind}: need at least 3 points, have {len(sub)}")
            continue
        t = [r["rated_torque_Nm"] for r in sub]
        m = [r["mass_kg"] for r in sub]
        a, b, r2 = fit_power_law(t, m)
        err = [abs(a * ti ** b - mi) / mi for ti, mi in zip(t, m)]
        print(f"{kind}:  m = {a:.5f} * T^{b:.4f}    "
              f"(n={len(sub)}, R2={r2:.4f}, mean |err|={100*sum(err)/len(err):.1f} %)")
        print(f"          valid for T in [{min(t):.2f}, {max(t):.2f}] N m")
        print(f"          -> in sizing/mers.py set  {kind}_a = {a:.5f}, {kind}_b = {b:.4f}")
        print()


if __name__ == "__main__":
    main()
