"""Publication figures for the paper.

    python make_figures.py              writes into figures/
    python make_figures.py OUTDIR       writes into OUTDIR as well

Writes fig1..fig5 as PDF (for the paper) and PNG (for checking). The file
numbers follow the figure numbers of the IAC-26 paper:
  fig1_sensitivity            Fig. 1, one-at-a-time sensitivity of the mass
  fig2_closure_limit          Fig. 2, converged mass against drum areal density
  fig3_drawbar_margin         Fig. 3, thrust ratio on every terrain case
  fig4_traction_calibration   Fig. 4, thrust ratio against kappa
  fig5_feasibility_box        Fig. 5, feasibility box
Every figure is generated from the model, so it cannot drift from the code.

Layout rules, kept deliberately strict so the figures stay clean at column
width in a two-column paper:
  - no text inside the plot area: no annotations, no value labels, no
    in-figure titles. Reference lines and marked points are identified in a
    legend placed outside the axes; bar values go on a secondary tick axis
    outside the plot; the title and the explanation live in the caption.
  - every figure is resized until its tight bounding box, legend and tick
    labels included, is exactly the printed width (one column or the full
    text width of the IAC template), so it is placed at 100 % scale and
    the 7 to 8 pt text stays 7 to 8 pt on paper.
  - one hue for magnitude, a second hue only where the split is real
    (sourced against assumed, calibrated against uncorrected).
  - pass and fail carried by colour AND marker, hatch or tick text, never
    colour alone.
"""

import dataclasses as dc
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from sizing.environment import TITAN
from sizing.mers import AREAL_DENSITY_EVIDENCE, MassModel
from sizing.screw import ScrewGeometry
from sizing.sizing_loop import Mission, size
from sizing.terrain import CASES, TITAN_LUNAR_PROXY

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")

# --- palette -------------------------------------------------------------
INK = "#1a1a1a"
MUTED = "#6f6e69"
GRID = "#e4e3dc"
AXIS = "#9c9b93"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
RED = "#c8342f"
BLUES5 = ["#9cc3f2", "#5f9fe8", "#2a78d6", "#1c5cab", "#0e3c78"]

# Printed widths in the IAC template: A4, 0.98 in margins, 10 pt column gap.
COL_W = 3.08      # in, one column
FULL_W = 6.28     # in, full text width

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["TeX Gyre Termes", "Nimbus Roman", "Liberation Serif",
                   "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK,
    "axes.linewidth": 0.7,
    "xtick.color": INK, "ytick.color": INK,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 3, "ytick.major.size": 3,
    "text.color": INK,
    "grid.color": GRID, "grid.linewidth": 0.6,
    "legend.fontsize": 7.5,
    "legend.frameon": False,
    "legend.handlelength": 2.0,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

MISSION, GEOM, TERRAIN = Mission(), ScrewGeometry(), TITAN_LUNAR_PROXY
CAP = MISSION.delivered_mass_cap
SYS_CAP = MISSION.system_mass_cap
EXTRA_OUT = []


def tidy(ax, grid_axis="y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis)
    ax.set_axisbelow(True)


def bare(ax):
    for side in ("top", "left", "bottom", "right"):
        ax.spines[side].set_visible(False)


def render(name, builder, width, height):
    """Build the figure at the width whose tight bounding box equals width."""
    w = width
    for _ in range(6):
        fig = builder(w, height)
        fig.canvas.draw()
        got = fig.get_tightbbox(fig.canvas.get_renderer()).width
        if abs(got - width) < 0.01:
            break
        plt.close(fig)
        w += width - got
    os.makedirs(OUT, exist_ok=True)
    for ext in ("pdf", "png"):
        path = os.path.join(OUT, f"{name}.{ext}")
        fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.0)
        for d in EXTRA_OUT:
            os.makedirs(d, exist_ok=True)
            shutil.copy(path, d)
    plt.close(fig)
    print(f"  wrote figures/{name}.pdf and .png, {width:.2f} in wide")


def run(ms=None, gm=None, tr=None, mm=None):
    return size(ms or MISSION, gm or GEOM, tr or TERRAIN, TITAN, mm or MassModel())


def scaled_geometry(d):
    """Baseline proportions scaled to drum diameter d, so the sweep passes
    exactly through the baseline design at d = GEOM.drum_diameter."""
    k = d / GEOM.drum_diameter
    return dc.replace(GEOM, drum_diameter=d, blade_height=GEOM.blade_height * k,
                      length=GEOM.length * k, pitch=GEOM.pitch * k)


def reference_handles():
    return [Line2D([], [], color=MUTED, ls="--", lw=1.0,
                   label=f"lander-only benchmark, {CAP:.0f} kg"),
            Line2D([], [], color=MUTED, ls=":", lw=1.1,
                   label=f"lander plus aeroshell, {SYS_CAP:.0f} kg")]


# =========================================================================
def fig2_closure_limit():
    """Converged total mass against drum shell areal density."""
    def total(rho):
        return run(mm=dc.replace(MassModel(), drum_areal_density=rho)).total_mass

    rhos = [5 + 0.5 * i for i in range(111)]
    masses = [total(r) for r in rhos]
    lo, hi = 1.0, 200.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if total(mid) <= CAP else (lo, mid)
    limit = 0.5 * (lo + hi)
    wheels = [v for k, v in AREAL_DENSITY_EVIDENCE.items() if k != "arcsnake_screw_module"]
    screw = AREAL_DENSITY_EVIDENCE["arcsnake_screw_module"]
    wheel_m = [total(v) for v in wheels]
    screw_m = total(screw)

    def build(w, h):
        fig, ax = plt.subplots(figsize=(w, h))
        ax.plot(rhos, masses, color=BLUE, lw=1.6, zorder=3)
        ax.axhline(CAP, color=MUTED, ls="--", lw=1.0, zorder=2)
        ax.axhline(SYS_CAP, color=MUTED, ls=":", lw=1.1, zorder=2)
        ax.axvline(limit, color=RED, ls="-.", lw=1.0, zorder=2)
        ax.plot(wheels, wheel_m, ls="none", marker="o", ms=4.4, mfc="white",
                mec=INK, mew=0.9, zorder=5)
        ax.plot([screw], [screw_m], ls="none", marker="D", ms=4.4, mfc=ORANGE,
                mec="white", mew=0.6, zorder=6)
        ax.set_xlim(5, 60)
        ax.set_ylim(120, 560)
        ax.set_xlabel(r"drum shell areal density, $\sigma_d$  [kg m$^{-2}$]")
        ax.set_ylabel("converged total mass  [kg]")
        tidy(ax, "both")
        handles = [
            Line2D([], [], color=BLUE, lw=1.6, label="baseline geometry"),
            Line2D([], [], color=RED, ls="-.", lw=1.0,
                   label=f"closure limit, {limit:.1f} kg m$^{{-2}}$"),
            *reference_handles(),
            Line2D([], [], ls="none", marker="o", ms=4.4, mfc="white", mec=INK,
                   mew=0.9, label="micro-rover wheels"),
            Line2D([], [], ls="none", marker="D", ms=4.4, mfc=ORANGE, mec="white",
                   label="ARCSnake screw module"),
        ]
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                   ncol=2, columnspacing=0.8, handletextpad=0.4, handlelength=1.8)
        return fig

    render("fig2_closure_limit", build, COL_W, 2.3)
    return limit


# =========================================================================
def fig1_sensitivity():
    """Span of converged total mass when each uncertain input is swept alone."""
    base = run().total_mass
    mmr = lambda **kw: run(mm=dc.replace(MassModel(), **kw)).total_mass
    msr = lambda **kw: run(ms=dc.replace(MISSION, **kw)).total_mass
    gmr = lambda **kw: run(gm=dc.replace(GEOM, **kw)).total_mass
    trr = lambda **kw: run(tr=dc.replace(TERRAIN, **kw)).total_mass
    rows = [
        ("drum areal density, 12.6 to 53.1 kg m$^{-2}$",
         mmr(drum_areal_density=12.6), mmr(drum_areal_density=53.1), True),
        ("blade areal density, 14.6 to 29.1 kg m$^{-2}$",
         mmr(blade_areal_density=14.6), mmr(blade_areal_density=29.1), True),
        ("drive duty cycle, 0.05 to 0.40", msr(drive_duty=0.05), msr(drive_duty=0.40), False),
        ("power source, 2.44 to 3.14 W kg$^{-1}$",
         mmr(source_specific_power=2.44), mmr(source_specific_power=3.14), True),
        ("soil-metal friction, 0.4 to 0.8",
         gmr(soil_metal_friction=0.4), gmr(soil_metal_friction=0.8), False),
        ("drive module mass, 0.5 to 2.0 kg", mmr(module_mass=0.5), mmr(module_mass=2.0), True),
        ("design slip, 0.10 to 0.40", msr(design_slip=0.10), msr(design_slip=0.40), True),
        ("drivetrain efficiency, 0.47 to 0.78",
         mmr(drivetrain_efficiency_model="patel"),
         mmr(drivetrain_efficiency_model="course"), True),
        ("rolling resistance $c_{rr}$, 0.10 to 0.25", trr(c_rr=0.10), trr(c_rr=0.25), True),
    ]
    rows.sort(key=lambda r: abs(r[2] - r[1]))      # largest at the top

    def build(w, h):
        fig, ax = plt.subplots(figsize=(w, h))
        for i, (_, a, b, sourced) in enumerate(rows):
            ax.barh(i, abs(b - a), left=min(a, b), height=0.56,
                    color=BLUE if sourced else ORANGE, zorder=3)
        ax.axvline(base, color=INK, ls="--", lw=0.9, zorder=4)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([r[0] for r in rows])
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_xlim(150, 500)
        ax.set_xlabel("converged total mass  [kg]")
        tidy(ax, "x")
        ax2 = ax.twinx()                    # span values outside the plot area
        ax2.set_ylim(ax.get_ylim())
        ax2.set_yticks(range(len(rows)))
        ax2.set_yticklabels([f"{abs(b - a):.0f} kg ({100 * abs(b - a) / base:.0f}%)"
                             for _, a, b, _ in rows])
        ax2.tick_params(axis="y", length=0, pad=4)
        bare(ax2)
        handles = [Patch(color=BLUE, label="range taken from a source"),
                   Patch(color=ORANGE, label="range assumed"),
                   Line2D([], [], color=INK, ls="--", lw=0.9,
                          label=f"baseline design, {base:.0f} kg")]
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                   ncol=3, columnspacing=2.0)
        return fig

    render("fig1_sensitivity", build, FULL_W, 2.35)


# =========================================================================
def fig5_feasibility_box():
    """Converged total mass against payload for five drum diameters."""
    payloads = [5, 10, 12, 15, 20, 25, 30, 40]
    diameters = [0.45, 0.55, 0.65, 0.75, 0.85]
    series = []
    for d in diameters:
        pts = []
        for pl in payloads:
            r = run(ms=dc.replace(MISSION, payload_mass=pl), gm=scaled_geometry(d))
            pts.append((pl, r.total_mass, r.feasible))
        series.append(pts)

    def build(w, h):
        fig, ax = plt.subplots(figsize=(w, h))
        for k, pts in enumerate(series):
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=BLUES5[k], lw=1.4, zorder=3)
            ok = [p for p in pts if p[2]]
            bad = [p for p in pts if not p[2]]
            ax.plot([p[0] for p in ok], [p[1] for p in ok], ls="none", marker="o", ms=4.0,
                    mfc=BLUES5[k], mec="white", mew=0.6, zorder=5)
            ax.plot([p[0] for p in bad], [p[1] for p in bad], ls="none", marker="x", ms=4.0,
                    mec=RED, mew=1.0, zorder=5)
        ax.axhline(CAP, color=MUTED, ls="--", lw=1.0, zorder=2)
        ax.axhline(SYS_CAP, color=MUTED, ls=":", lw=1.1, zorder=2)
        ax.set_xlim(3, 42)
        ax.set_ylim(120, 440)
        ax.set_xlabel("science payload mass  [kg]")
        ax.set_ylabel("converged total mass  [kg]")
        tidy(ax, "both")
        handles = [Line2D([], [], color=BLUES5[k], lw=1.4, label=f"$D_d$ = {d:.2f} m")
                   for k, d in enumerate(diameters)]
        handles += [Line2D([], [], ls="none", marker="o", ms=4.0, mfc=MUTED, mec="white",
                           label="passes every screen"),
                    Line2D([], [], ls="none", marker="x", ms=4.0, mec=RED, mew=1.0,
                           label="fails a screen"),
                    *reference_handles()]
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                   ncol=2, columnspacing=0.8, handletextpad=0.4, handlelength=1.8)
        return fig

    render("fig5_feasibility_box", build, COL_W, 2.3)


# =========================================================================
PRETTY = {"dry_sand": "dry sand", "sandy_loam": "sandy loam",
          "clayey_soil": "clayey soil", "lunar_average": "lunar average",
          "titan_lunar_proxy": "Titan lunar proxy", "mss_a": "MSS-A, Mars",
          "mss_b": "MSS-B, Mars", "snow_msa": "snow, MSA 1/5*",
          "msa_sand_wes": "sand, MSA*", "liquefied_soft": "wet clay, MSA*"}


def fig3_drawbar_margin():
    """Uncorrected drawbar margin of the baseline on every terrain case."""
    res = sorted(((n, run(tr=t).performance["drawbar_margin"])
                  for n, t in CASES.items() if t.has_bekker), key=lambda x: x[1])

    def build(w, h):
        fig, ax = plt.subplots(figsize=(w, h))
        for i, (_, m) in enumerate(res):
            fails = m < 1.0
            ax.barh(i, m, height=0.58, color=RED if fails else BLUE,
                    hatch="////" if fails else None, edgecolor="white", lw=0, zorder=3)
        ax.axvline(1.0, color=INK, ls="--", lw=0.9, zorder=4)
        ax.set_yticks(range(len(res)))
        ax.set_yticklabels([PRETTY.get(n, n) for n, _ in res])
        ax.set_ylim(-0.6, len(res) - 0.4)
        ax.set_xlim(0, 3.5)
        ax.set_xlabel(r"$F_{av}/F_{req}$, 20$^\circ$ slope, $\kappa$ = 1")
        tidy(ax, "x")
        ax2 = ax.twinx()                    # values outside the plot area
        ax2.set_ylim(ax.get_ylim())
        ax2.set_yticks(range(len(res)))
        ax2.set_yticklabels([f"{m:.2f}" for _, m in res])
        for lab, (_, m) in zip(ax2.get_yticklabels(), res):
            lab.set_color(RED if m < 1.0 else INK)
        ax2.tick_params(axis="y", length=0, pad=3)
        bare(ax2)
        handles = [Patch(color=BLUE, label="met"),
                   Patch(facecolor=RED, hatch="////", edgecolor="white", label="not met"),
                   Line2D([], [], color=INK, ls="--", lw=0.9, label="margin = 1")]
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                   ncol=3, columnspacing=1.2, handletextpad=0.5, handlelength=1.6)
        return fig

    render("fig3_drawbar_margin", build, COL_W, 2.35)


# =========================================================================
def fig4_traction_calibration():
    """Titan drawbar margin against the screw traction efficiency kappa."""
    def margin(k):
        return run(gm=dc.replace(GEOM, traction_efficiency=k)).performance["drawbar_margin"]

    kappas = [0.2 + 0.02 * i for i in range(41)]
    margins = [margin(k) for k in kappas]
    points = [(1.00, "o", BLUE, "uncorrected"),
              (0.65, "s", ORANGE, "MSA slope tests"),
              (0.35, "^", ORANGE, "MSA towing test")]
    pm = {k: margin(k) for k, *_ in points}

    def build(w, h):
        fig, ax = plt.subplots(figsize=(w, h))
        ax.axvspan(0.35, 0.65, color=ORANGE, alpha=0.13, lw=0, zorder=1)
        ax.plot(kappas, margins, color=BLUE, lw=1.6, zorder=3)
        ax.axhline(1.0, color=INK, ls="--", lw=0.9, zorder=2)
        for k, mk, c, _ in points:
            ax.plot([k], [pm[k]], ls="none", marker=mk, ms=5.0, mfc=c, mec="white",
                    mew=0.7, zorder=5)
        ax.set_xlim(0.2, 1.02)
        ax.set_ylim(0, 3)
        ax.set_xlabel(r"screw traction efficiency, $\kappa$")
        ax.set_ylabel(r"$F_{av}/F_{req}$, 20$^\circ$ slope")
        tidy(ax, "both")
        handles = [Line2D([], [], color=BLUE, lw=1.6, label="baseline design"),
                   Patch(color=ORANGE, alpha=0.25, label=r"$\kappa$ calibrated on the MSA"),
                   Line2D([], [], color=INK, ls="--", lw=0.9, label="margin = 1")]
        handles += [Line2D([], [], ls="none", marker=mk, ms=5.0, mfc=c, mec="white",
                           label=f"{lab}, {pm[k]:.2f}")
                    for k, mk, c, lab in points]
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                   ncol=2, columnspacing=0.8, handletextpad=0.5, handlelength=1.8)
        return fig

    render("fig4_traction_calibration", build, COL_W, 2.2)


if __name__ == "__main__":
    EXTRA_OUT.extend(sys.argv[1:])
    print("rendering figures")
    fig1_sensitivity()
    fig2_closure_limit()
    fig3_drawbar_margin()
    fig4_traction_calibration()
    fig5_feasibility_box()
    print("done")
