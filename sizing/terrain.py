"""Terrain cases.

A terrain case is a parameter set with a source, not a label. Cases whose
Bekker parameters are unavailable cannot be used for sinkage, and the code
says so instead of substituting a guess.

Bekker parameter units follow Wong: k_c in N/m^(n+1), k_phi in N/m^(n+2).

Rolling resistance coefficients c_rr are taken from the table in
rimani_week4_mobility:

    hard flat road (Earth)   0.01 to 0.02
    sandy soil (Earth)       0.05 to 0.10
    loose lunar regolith     0.10 to 0.20
    very loose Mars soil     0.15 to 0.25

Note that patel2005 adopts 0.05 for Mars, treating it as an unpaved road,
which is below that table's Mars range. The two disagree. The value used
here is stated per case so the choice is visible.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Terrain:
    name: str
    k_c: Optional[float]        # N/m^(n+1)
    k_phi: Optional[float]      # N/m^(n+2)
    n: Optional[float]
    cohesion: float             # Pa
    phi: float                  # deg
    shear_K: float              # m
    density: Optional[float]    # kg/m^3
    mu_db_max: Optional[float]  # measured max drawbar pull / weight
    source: str
    evidence: str
    c_rr: float = 0.10          # rolling resistance coefficient
    c_rr_source: str = "ASSUMED"

    @property
    def has_bekker(self) -> bool:
        return None not in (self.k_c, self.k_phi, self.n)


# --- terrestrial soils, Patel thesis Table 9, citing Wong (2001) -----------
# NOTE: Wong's own printed dry-sand set is often quoted as n = 1.1,
# k_c = 0.99 kN/m^(n+1), k_phi = 1528 kN/m^(n+2). Patel's table gives n = 1
# and k_phi = 1.52e5. The two differ by an order of magnitude in k_phi.
# The Patel values are used here because that is the source in hand.
# Check against Wong's book before quoting either in a paper.
DRY_SAND = Terrain(
    "dry_sand", 990.0, 1.52e5, 1.0, 1040.0, 28.0, 0.025, 1520.0, None,
    "patel2005 Table 9 (Wong 2001)", "direct",
    c_rr=0.075, c_rr_source="rimani_week4_mobility, sandy soil 0.05 to 0.10",
)
SANDY_LOAM = Terrain(
    "sandy_loam", 5270.0, 1.51e6, 1.0, 1720.0, 29.0, 0.025, 1520.0, None,
    "patel2005 Table 9 (Wong 2001)", "direct",
    c_rr=0.075, c_rr_source="rimani_week4_mobility, sandy soil 0.05 to 0.10",
)
CLAYEY_SOIL = Terrain(
    "clayey_soil", 13190.0, 6.92e6, 1.0, 4140.0, 13.0, 0.025, 1520.0, None,
    "patel2005 Table 9 (Wong 2001)", "direct",
    c_rr=0.05, c_rr_source="rimani_week4_mobility, low end of sandy soil",
)

# --- lunar, Patel thesis Table 6 (Carrier et al. 1991) ---------------------
LUNAR_AVERAGE = Terrain(
    "lunar_average", 1350.0, 8.2e5, 1.0, 520.0, 42.0, 0.018, 1500.0, None,
    "patel2005 Table 6 (Carrier 1991); shear_K from ellery2005", "direct",
    c_rr=0.15, c_rr_source="rimani_week4_mobility, loose lunar regolith 0.10 to 0.20",
)

# --- Titan, and the honest state of it ------------------------------------
# There is no measured Bekker parameter set for Titan. genta2011 sizes its
# Titan rover with lunar regolith parameters and says so explicitly. This
# case reproduces that choice, with the caveat attached, so that any result
# computed on it is visibly a proxy result.
TITAN_LUNAR_PROXY = Terrain(
    "titan_lunar_proxy", 1400.0, 8.2e5, 1.0, 520.0, 42.0, 0.018, 1500.0, None,
    "genta2011 (lunar regolith used as a Titan substitute)",
    "PROXY, not a Titan measurement. Largest single uncertainty in any Titan "
    "mobility sizing.",
    c_rr=0.10, c_rr_source="genta2011, f = 0.1 for a Titan rover on the lunar proxy soil, being the computed rolling resistance times a safety factor of 3",
)

# --- Mars simulants, Patel thesis Table 4 (DLR, Richter and Hamacher 1999) -
MSS_A = Terrain(
    "mss_a", 2370.0, 60300.0, 0.63, 188.0, 24.8, 0.025, 1137.0, None,
    "patel2005 Table 4 (DLR MSS-A)", "direct",
    c_rr=0.20, c_rr_source="rimani_week4_mobility, very loose Mars soil 0.15 to 0.25",
)
MSS_B = Terrain(
    "mss_b", 18773.0, 763600.0, 1.1, 441.0, 17.8, 0.025, 1137.0, None,
    "patel2005 Table 4 (DLR MSS-B)", "direct",
    c_rr=0.20, c_rr_source="rimani_week4_mobility, very loose Mars soil 0.15 to 0.25",
)

# --- test sand used in a screw-wheel slope experiment ----------------------
# Bekker parameters are NOT reported, so sinkage cannot be computed on this
# case. It is still usable for shear, slip and the sideslip comparison.
# The paper prints cohesion as 761.8 N/m^3, which is dimensionally wrong for
# a cohesion; 762 Pa is used here and flagged.
SILICA_SAND_N5 = Terrain(
    "silica_sand_no5", None, None, None, 762.0, 22.3, 0.013, 1300.0, None,
    "sagara2025 Table 4", "cohesion unit inconsistent in source; Bekker "
    "parameters unavailable",
    c_rr=0.075, c_rr_source="rimani_week4_mobility, sandy soil 0.05 to 0.10",
)

# --- screw-specific drawbar evidence --------------------------------------
# These cases exist to carry the only measured screw drawbar coefficients in
# the literature we have. Their Bekker parameters are assumed (or borrowed
# from Wong's dry sand), because the trafficability reports give cone index,
# not pressure-sinkage constants.
#
# CORRECTION (September 2026). An earlier version carried mu_db_max = 0.64
# attributed to wes_tr3641 "in very soft ground". That figure could not be
# found in the report (DTIC AD0450621). The report gives, for the loaded
# vehicle (3954 lb):
#   - sand, CI about 75 to 95:   "tow loads up to about 24% of its test
#     weight", measured at full throttle and about 0.5 mph (p. 20-21);
#     the loaded vehicle climbed an 18 deg sand slope and failed at 21 deg
#     (Table 1C, p. 20), which bounds the usable traction coefficient
#     between 0.24 and about tan(18 deg) + c_rr = 0.32 + 0.08 = 0.40.
#   - fine-grained soil (fat clay CH, free water), RCI 20 to 30: maximum
#     towing force 425 lb at about 28 percent slip, then falling
#     (Table 2B, p. 42-43), which is 425 / 3954 = 0.107 of test weight.
# The 0.64 was most probably a misreading of test number 64D. Both values
# below are the report's, with page references, and both are far lower
# than the Mohr-Coulomb ceiling for the same soils. That gap is the
# screw traction efficiency that validate.py calibrates.
SNOW_MSA = Terrain(
    "snow_msa", 500.0, 4.0e5, 1.0, 500.0, 22.0, 0.03, 400.0, 0.54,
    "villacres2023 (MSA 1/5 scale, drawbar 54 percent of body weight in snow)",
    "mu_db_max direct; Bekker parameters ASSUMED",
    c_rr=0.15, c_rr_source="ASSUMED, no snow row in the c_rr table",
)
# Sand on which the full-scale MSA was tested. Bekker set is Wong's dry sand
# as tabulated by patel2005 (see the k_phi caveat above). The drawbar cap is
# the measured towing figure; the slope tests imply a somewhat higher value.
MSA_SAND_WES = Terrain(
    "msa_sand_wes", 990.0, 1.52e5, 1.0, 1040.0, 28.0, 0.025, 1520.0, 0.24,
    "wes_tr3641 (MSA loaded on sand: towing force about 24 percent of test "
    "weight, p. 21; climbed 18 deg, not 21 deg, Table 1C p. 20). Bekker set "
    "patel2005 Table 9 dry sand",
    "mu_db_max direct (towing); Bekker parameters from a generic dry sand, "
    "NOT the WES test sand",
    c_rr=0.075, c_rr_source="rimani_week4_mobility, sandy soil 0.05 to 0.10",
)
# Fine-grained soil with free water, the regime where the MSA beat the M29C
# Weasel. Bekker parameters ASSUMED; the report gives rating cone index only.
LIQUEFIED_SOFT = Terrain(
    "liquefied_soft", 100.0, 4.0e4, 0.8, 200.0, 10.0, 0.05, 1200.0, 0.107,
    "wes_tr3641 (MSA loaded on fat clay with free water, RCI 20 to 30: "
    "425 lb maximum towing force at about 28 percent slip, Table 2B "
    "p. 42-43, over a 3954 lb test weight)",
    "mu_db_max calculated from the report's towing force and test weight; "
    "Bekker parameters ASSUMED",
    c_rr=0.05, c_rr_source="ASSUMED; the report stresses that free water and "
    "low soil-rotor friction are what let the MSA move on this ground, and "
    "it reached 5 mph on it, so a low value is used",
)

CASES = {t.name: t for t in (
    DRY_SAND, SANDY_LOAM, CLAYEY_SOIL, LUNAR_AVERAGE, TITAN_LUNAR_PROXY,
    MSS_A, MSS_B, SILICA_SAND_N5, SNOW_MSA, MSA_SAND_WES, LIQUEFIED_SOFT,
)}


class TerrainDataMissing(Exception):
    """Raised when a terrain case lacks the parameters a model needs."""
