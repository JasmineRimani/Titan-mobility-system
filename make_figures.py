"""Publication figures for the paper.

    python make_figures.py

Writes figures/fig1..fig4 as PDF (for the paper) and PNG (for checking).
Every figure is generated from the model, so they cannot drift from the code.

Design notes: single hue for magnitude, a second hue only where the split is
real (sourced against assumed), pass and fail carried by colour AND marker
shape AND a text label, never colour alone. Palette validated for colour
vision deficiency on a white print surface.
"""

import math
import os
import dataclasses as dc

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from sizing.environment import TITAN
from sizing.mers import AREAL_DENSITY_EVIDENCE, MassModel
from sizing.screw import ScrewGeometry
from sizing.sizing_loop import Mission, size
from sizing.terrain import CASES, TITAN_LUNAR_PROXY

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")

# --- palette -------------------------------------------------------------
INK        = "#0b0b0b"
INK2       = "#52514e"
MUTED      = "#898781"
GRID       = "#e1e0d9"
AXIS       = "#c3c2b7"
SERIES     = "#2a78d6"   # blue, slot 1
SERIES2    = "#eb6834"   # orange, slot 2
FAIL       = "#d03b3b"   # critical
ORDINAL5   = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Nimbus Roman"],
    "font.size": 8,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK,
    "axes.linewidth": 0.8,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "grid.color": GRID, "grid.linewidth": 0.6,
    "legend.fontsize": 7.5, "legend.frameon": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

MISSION, GEOM, TERRAIN = Mission(), ScrewGeometry(), TITAN_LUNAR_PROXY
CAP = MISSION.delivered_mass_cap


def tidy(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", alpha=0.9)
    ax.set_axisbelow(True)


def total_for_rho(rho):
    return size(MISSION, GEOM, TERRAIN, TITAN,
                dc.replace(MassModel(), drum_areal_density=rho)).total_mass


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), dpi=300,
                    bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"  wrote figures/{name}.pdf and .png")


# =========================================================================
def fig1_closure_limit():
    rhos = [5 + 0.5 * i for i in range(111)]
    masses = [total_for_rho(r) for r in rhos]

    lo, hi = 1.0, 200.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if total_for_rho(mid) <= CAP:
            lo = mid
        else:
            hi = mid
    limit = 0.5 * (lo + hi)

    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    ax.plot(rhos, masses, color=SERIES, lw=2, zorder=3)
    ax.axhline(CAP, color=MUTED, ls="--", lw=1, zorder=2)
    ax.axvline(limit, color=FAIL, ls=":", lw=1.2, zorder=2)

    ax.text(59, CAP + 8, f"delivered mass cap {CAP:.0f} kg", ha="right",
            va="bottom", fontsize=7, color=INK2)
    ax.text(limit - 1.2, 630, f"closure limit\n{limit:.1f} kg m$^{{-2}}$",
            ha="right", va="top", fontsize=7, color=FAIL)

    for name, rho in sorted(AREAL_DENSITY_EVIDENCE.items(), key=lambda kv: kv[1]):
        m = total_for_rho(rho)
        ok = m <= CAP
        ax.plot(rho, m, marker="o" if ok else "X", ms=5.5,
                mfc=SERIES if ok else FAIL, mec="white", mew=0.8, zorder=5,
                linestyle="none")

    labels = [("Crab,\nARCSnake", 12.7, "left", 7, -2),
              ("ELMS", 18.3, "left", 7, -3),
              ("Marsokhod", 24.5, "left", 7, -3),
              ("ELMS (Table 68)", 31.8, "right", -7, 3),
              ("Sojourner, Shrimp", 35.0, "left", 7, -4),
              ("Nanokhod", 53.1, "right", -7, 3)]
    for txt, rho, ha, dx, dy in labels:
        ax.annotate(txt, (rho, total_for_rho(rho)),
                    textcoords="offset points", xytext=(dx, dy),
                    ha=ha, fontsize=6.5, color=INK2)

    ax.set_xlim(5, 60)
    ax.set_ylim(140, 660)
    ax.set_xlabel("drum shell areal density  [kg m$^{-2}$]")
    ax.set_ylabel("converged total mass  [kg]")
    ax.set_title("The drum shell is a requirement, not an input", loc="left",
                 color=INK, pad=8)
    handles = [Line2D([], [], marker="o", ls="none", mfc=SERIES, mec="white",
                      ms=5.5, label="design closes"),
               Line2D([], [], marker="X", ls="none", mfc=FAIL, mec="white",
                      ms=5.5, label="does not close")]
    ax.legend(handles=handles, loc="lower right", handletextpad=0.4)
    tidy(ax)
    save(fig, "fig1_closure_limit")
    return limit


# =========================================================================
def fig2_sensitivity():
    base = size(MISSION, GEOM, TERRAIN, TITAN, MassModel()).total_mass

    def mm(**kw):
        return size(MISSION, GEOM, TERRAIN, TITAN,
                    dc.replace(MassModel(), **kw)).total_mass

    def ms(**kw):
        return size(dc.replace(MISSION, **kw), GEOM, TERRAIN, TITAN, MassModel()).total_mass

    def gm(**kw):
        return size(MISSION, dc.replace(GEOM, **kw), TERRAIN, TITAN, MassModel()).total_mass

    def tr(**kw):
        return size(MISSION, GEOM, dc.replace(TERRAIN, **kw), TITAN, MassModel()).total_mass

    rows = [
        ("drum areal density\n12.6 to 53.1 kg m$^{-2}$",
         mm(drum_areal_density=12.6), mm(drum_areal_density=53.1), True),
        ("blade areal density\n14.6 to 29.1 kg m$^{-2}$",
         mm(blade_areal_density=14.6), mm(blade_areal_density=29.1), True),
        ("drive duty cycle\n0.05 to 0.40", ms(drive_duty=0.05), ms(drive_duty=0.40), False),
        ("power source\n2.44 to 3.14 W kg$^{-1}$",
         mm(source_specific_power=2.44), mm(source_specific_power=3.14), True),
        ("soil-on-metal friction\n0.4 to 0.8",
         gm(soil_metal_friction=0.4), gm(soil_metal_friction=0.8), False),
        ("drive module mass\n0.5 to 2.0 kg", mm(module_mass=0.5), mm(module_mass=2.0), True),
        ("design slip\n0.10 to 0.40", ms(design_slip=0.10), ms(design_slip=0.40), True),
        ("drivetrain efficiency\n0.47 to 0.78",
         mm(drivetrain_efficiency_model="patel"),
         mm(drivetrain_efficiency_model="course"), True),
        ("rolling resistance\n0.10 to 0.25", tr(c_rr=0.10), tr(c_rr=0.25), True),
    ]
    rows.sort(key=lambda r: abs(r[2] - r[1]))

    fig, ax = plt.subplots(figsize=(6.9, 3.3))
    for i, (label, a, b, sourced) in enumerate(rows):
        left, right = min(a, b), max(a, b)
        ax.barh(i, right - left, left=left, height=0.55,
                color=SERIES if sourced else SERIES2, zorder=3)
        span = right - left
        ax.text(right + 6, i, f"{span:.0f} kg  ({100*span/base:.0f}%)",
                va="center", fontsize=7, color=INK2)

    ax.axvline(base, color=MUTED, ls="--", lw=1, zorder=2)
    ax.text(base - 8, len(rows) - 0.45, f"baseline {base:.0f} kg", ha="right",
            va="bottom", fontsize=7, color=INK2)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=7)
    ax.set_xlabel("converged total mass  [kg]")
    ax.set_xlim(150, 700)
    ax.set_ylim(-0.7, len(rows) + 0.15)
    ax.set_title("What actually moves the answer, each input swept alone",
                 loc="left", color=INK, pad=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=SERIES, label="range from a source"),
               plt.Rectangle((0, 0), 1, 1, color=SERIES2, label="range assumed")]
    ax.legend(handles=handles, loc="lower right", handlelength=1.2)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", alpha=0.9)
    ax.set_axisbelow(True)
    save(fig, "fig2_sensitivity")


# =========================================================================
def fig3_feasibility_box():
    payloads = [5, 10, 12, 15, 20, 25, 30, 40]
    diameters = [0.40, 0.50, 0.60, 0.70, 0.80]

    fig, ax = plt.subplots(figsize=(3.45, 2.9))
    for k, d in enumerate(diameters):
        xs, ys, bad_x, bad_y = [], [], [], []
        for pl in payloads:
            g = ScrewGeometry(drum_diameter=d, length=2.0 * d, pitch=0.75 * d)
            r = size(dc.replace(MISSION, payload_mass=pl), g, TERRAIN, TITAN,
                     MassModel())
            xs.append(pl); ys.append(r.total_mass)
            if not r.feasible:
                bad_x.append(pl); bad_y.append(r.total_mass)
        ax.plot(xs, ys, color=ORDINAL5[k], lw=1.8, marker="o", ms=3.2,
                mec="white", mew=0.6, label=f"{d:.2f}", zorder=3)
        ax.plot(bad_x, bad_y, ls="none", marker="X", ms=6, mfc=FAIL,
                mec="white", mew=0.8, zorder=5)

    ax.axhline(CAP, color=MUTED, ls="--", lw=1, zorder=2)
    ax.set_ylim(130, 400)
    ax.text(5, CAP + 4, f"delivered mass cap {CAP:.0f} kg", ha="left",
            va="bottom", fontsize=7, color=INK2)
    ax.text(5, 390, "crosses mark infeasible points", ha="left", va="top",
            fontsize=7, color=FAIL)
    ax.set_xlabel("science payload mass  [kg]")
    ax.set_ylabel("converged total mass  [kg]")
    ax.set_title("Feasibility box for a Titan screw rover", loc="left",
                 color=INK, pad=8)
    leg = ax.legend(title="drum diameter  [m]", loc="upper center",
                    bbox_to_anchor=(0.5, -0.20), ncol=5, handlelength=1.2,
                    columnspacing=1.0, handletextpad=0.4)
    leg.get_title().set_fontsize(7)
    leg.get_title().set_color(INK2)
    tidy(ax)
    save(fig, "fig3_feasibility_box")


# =========================================================================
def fig4_drawbar_margin():
    cases = [(n, t) for n, t in CASES.items() if t.has_bekker]
    res = []
    for n, t in cases:
        r = size(MISSION, GEOM, t, TITAN, MassModel())
        measured = t.mu_db_max is not None
        res.append((n, r.performance["drawbar_margin"], measured))
    res.sort(key=lambda x: x[1], reverse=True)   # worst at the top

    fig, ax = plt.subplots(figsize=(3.45, 3.0))
    for i, (name, margin, measured) in enumerate(res):
        fails = margin < 1.0
        ax.barh(i, margin, height=0.6, color=FAIL if fails else SERIES, zorder=3)
        ax.text(margin + 0.05, i, f"{margin:.2f}" + ("  FAIL" if fails else ""),
                va="center", fontsize=7, color=FAIL if fails else INK2)
    ax.axvline(1.0, color=MUTED, ls="--", lw=1, zorder=4)
    ax.text(1.05, len(res) - 0.45, "margin = 1", fontsize=7, color=INK2,
            va="bottom")

    pretty = {"dry_sand": "dry sand", "sandy_loam": "sandy loam",
              "clayey_soil": "clayey soil", "lunar_average": "lunar average",
              "titan_lunar_proxy": "Titan lunar proxy", "mss_a": "MSS-A",
              "mss_b": "MSS-B", "snow_msa": "snow (MSA)",
              "liquefied_soft": "liquefied soft ground"}
    labels = [pretty.get(n, n) + ("  *" if m else "") for n, _, m in res]
    ax.set_yticks(range(len(res)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("thrust available / thrust required")
    ax.set_xlim(0, 4.1)
    ax.set_ylim(-0.7, len(res) + 0.15)
    ax.set_title("Traction, not flotation, is the design driver", loc="left",
                 color=INK, pad=8)
    ax.annotate("*  the only cases with a measured drawbar coefficient",
                (0, -0.19), xycoords="axes fraction", fontsize=6.5, color=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", alpha=0.9)
    ax.set_axisbelow(True)
    save(fig, "fig4_drawbar_margin")


if __name__ == "__main__":
    print("rendering figures")
    fig1_closure_limit()
    fig2_sensitivity()
    fig3_feasibility_box()
    fig4_drawbar_margin()
    print("done")
