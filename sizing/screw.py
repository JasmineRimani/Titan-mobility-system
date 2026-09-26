"""Reduced-order screw-terrain model (Level 1).

"Paper Eq. (n)" below refers to the equations of Lukianov and Rimani,
IAC-26,A3,IP,204,x115954 (77th IAC, Antalya, 2026); see CITATION.cff.

Pieces, each replaceable and each with a source:

1. Sinkage and compaction resistance
   Classical Bekker pressure-sinkage on the cylindrical drum contact patch.
   Equations from patel2005 / ellery2005 / sagara2025.

2. Available thrust
   Mohr-Coulomb shear ceiling with Janosi-Hanamoto slip mobilisation,
   optionally capped by a measured drawbar coefficient where one exists
   (wes_tr3641, villacres2023).

3. Torque and power
   Power-screw (screw jack) relation. Screws convert torque to axial thrust
   with an efficiency set by the lead angle and the soil-on-metal friction,
   which is why they are slow and power hungry.

4. Geometry metrics from chen2025
   aspect ratio psi = tan(alpha) / (N * BH),  tip speed = omega * R * sin(alpha)

VALIDITY. villacres2023 is explicit that the Bekker-derived scroll models
hold only while sinkage stays below the flight height, that is while the
screw is running on top of the soil rather than swimming in it. Soft mud and
snow, exactly where screws beat everything else, are outside that range.
The code flags this rather than extrapolating quietly.

NOT MODELLED, and to be stated as limitations: lateral drift and side slip
(observed in chen2025 and sagara2025), the switch to wheel-like rolling on
hard ground (richter2022), hydrodynamic drag and thrust in liquid, dynamic
sinkage, multi-pass effects, and the interaction between multiple screws.
Static buoyancy IS screened, conservatively, by displaced_volume and
flotation_vol below; nothing else about a liquid crossing is.
"""

import math
import warnings
from dataclasses import dataclass

from .terrain import TerrainDataMissing


@dataclass
class ScrewGeometry:
    # Baseline geometry (September 2026). Re-baselined from 0.60 / 0.10 /
    # 1.20 / 0.45 when the mass screen moved to the lander-only 213 kg
    # benchmark: this is the smallest geometry in the trade space that
    # passes every screen, including drum-only flotation, on the Titan
    # lunar-proxy soil. See outputs/trade_space.csv and docs/MODEL_NOTES.md section 10.
    n_screws: int = 2
    drum_diameter: float = 0.55      # m, D_drum
    blade_height: float = 0.08       # m, BH
    length: float = 1.10             # m, L
    pitch: float = 0.45              # m, p, axial advance per revolution
    n_starts: int = 1
    soil_metal_friction: float = 0.6  # ASSUMED, calibrate against a test
    # Fraction of the Mohr-Coulomb ceiling a rotating screw actually
    # converts into drawbar pull. 1.0 reproduces the uncorrected model.
    # validate.py calibrates it on the Marsh Screw Amphibian sand tests
    # (wes_tr3641): about 0.35 from the towing tests, about 0.65 from the
    # slope tests. Keep 1.0 for the uncorrected result and report both.
    traction_efficiency: float = 1.0

    @property
    def outer_diameter(self) -> float:
        return self.drum_diameter + 2.0 * self.blade_height

    @property
    def mean_diameter(self) -> float:
        return 0.5 * (self.drum_diameter + self.outer_diameter)

    @property
    def helix_angle(self) -> float:
        """Lead angle at the mean diameter, rad. Paper Eq. (2)."""
        return math.atan2(self.pitch, math.pi * self.mean_diameter)

    @property
    def helix_angle_deg(self) -> float:
        return math.degrees(self.helix_angle)

    @property
    def screw_efficiency(self) -> float:
        """Power-screw efficiency, eta = tan(lam) / tan(lam + rho). Paper Eq. (3)."""
        lam = self.helix_angle
        rho = math.atan(self.soil_metal_friction)
        return math.tan(lam) / math.tan(lam + rho)

    @property
    def aspect_ratio(self) -> float:
        """chen2025 Eq. 3. Low psi is a crowded blade layout."""
        return math.tan(self.helix_angle) / (self.n_starts * self.blade_height)

    def tip_speed(self, omega: float) -> float:
        """chen2025 Eq. 4, m/s."""
        return omega * (self.outer_diameter / 2.0) * math.sin(self.helix_angle)


# Reference geometries from the literature, for anchoring a scaling study.
ARCSNAKE = ScrewGeometry(n_screws=1, drum_diameter=0.128, blade_height=0.011,
                         length=0.30, pitch=math.pi * 0.139 * math.tan(math.radians(22.0)),
                         n_starts=2)
SAGARA_SCREW_WHEEL = ScrewGeometry(n_screws=4, drum_diameter=0.115,
                                   blade_height=0.0125, length=0.080,
                                   pitch=0.040, n_starts=1)

# Recommended lead angles disagree by medium. Do not pick one constant.
#   22 deg  richter2022, attributed to Cole 1961, max drawbar / min slip
#   35 deg  villacres2023 reporting Seo et al. Taguchi optimum in granular
#   30 deg  villacres2023 reporting Karaseva, most efficient submerged
RECOMMENDED_HELIX_ANGLE_DEG = {"granular": 35.0, "general": 22.0, "submerged": 30.0}


def contact_width(z: float, D: float) -> float:
    """Chord width of a cylinder of diameter D sunk to depth z. Paper Eq. (4)."""
    if z <= 0.0:
        return 1e-6
    if z >= D / 2.0:
        return D
    return 2.0 * math.sqrt(z * (D - z))


def sinkage(load_per_screw: float, geom: ScrewGeometry, terrain) -> float:
    """Static sinkage z [m] from Bekker pressure-sinkage. Paper Eq. (5).

        W / (b(z) * L) = (k_c / b(z) + k_phi) * z^n
    """
    if not terrain.has_bekker:
        raise TerrainDataMissing(
            f"terrain '{terrain.name}' has no Bekker parameters "
            f"({terrain.evidence}). Sinkage cannot be computed. Supply k_c, "
            f"k_phi and n, or choose another terrain case."
        )
    D, L = geom.outer_diameter, geom.length

    def residual(z):
        b = contact_width(z, D)
        return load_per_screw / (b * L) - (terrain.k_c / b + terrain.k_phi) * z ** terrain.n

    lo, hi = 1e-6, 0.95 * D
    if residual(hi) > 0.0:
        return hi                      # fully sunk, the design does not close
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if residual(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def check_validity(z: float, geom: ScrewGeometry, quiet: bool = False) -> bool:
    """True while the Bekker-derived scroll model is inside its stated range.

    villacres2023: the adapted model holds only while sinkage stays below the
    flight height. Beyond that the screw is swimming, not running on top.
    """
    ok = z <= geom.blade_height
    if not ok and not quiet:
        warnings.warn(
            f"sinkage {z*1000:.1f} mm exceeds blade height "
            f"{geom.blade_height*1000:.1f} mm. The Bekker-derived screw model "
            f"is outside its validity range (villacres2023). Treat the result "
            f"as an extrapolation.", RuntimeWarning)
    return ok


def compaction_resistance(z: float, geom: ScrewGeometry, terrain) -> float:
    """Bekker compaction resistance per screw, N. Paper Eq. (6)."""
    b = contact_width(z, geom.outer_diameter)
    return b * (terrain.k_c / b + terrain.k_phi) * z ** (terrain.n + 1.0) / (terrain.n + 1.0)


def bulldozing_flag(z: float, geom: ScrewGeometry) -> bool:
    """patel2005 / ellery2005: bulldozing matters once z/D exceeds 0.06."""
    return z / geom.outer_diameter > 0.06


def drawbar_available(load_per_screw: float, slip: float, geom: ScrewGeometry,
                      terrain) -> float:
    """Available axial thrust per screw, N. Paper Eq. (10), per screw.

    Mohr-Coulomb ceiling on the contact patch, mobilised by a
    Janosi-Hanamoto slip term, then capped by a measured drawbar coefficient
    when the terrain case has one. With traction_efficiency = 1 and no
    measured cap it reduces to paper Eq. (9).
    """
    ceiling = coulomb_ceiling(load_per_screw, geom, terrain) * geom.traction_efficiency
    if terrain.mu_db_max is not None:
        ceiling = min(ceiling, terrain.mu_db_max * load_per_screw)
    return ceiling * slip_mobilisation(slip, geom, terrain)


def coulomb_ceiling(load_per_screw: float, geom: ScrewGeometry, terrain) -> float:
    """Uncorrected Mohr-Coulomb shear limit on the equivalent contact patch, N.

    The bracketed term of paper Eq. (9).

    A_c c + W_s tan(phi), with A_c = b(z) L at the static sinkage. This is
    what a rigid running gear could mobilise at most; a rotating screw in
    dry sand reaches a fraction of it (see traction_efficiency).
    """
    z = sinkage(load_per_screw, geom, terrain)
    b = contact_width(z, geom.outer_diameter)
    area = b * geom.length
    return area * terrain.cohesion + load_per_screw * math.tan(math.radians(terrain.phi))


def slip_mobilisation(slip: float, geom: ScrewGeometry, terrain) -> float:
    """Janosi-Hanamoto mobilisation factor in [0, 1] for shear travel j = s L.

    The last factor of paper Eqs. (9) and (10).
    """
    travel = max(slip, 1e-6) * geom.length
    return 1.0 - (terrain.shear_K / travel) * (1.0 - math.exp(-travel / terrain.shear_K))


def equilibrium_slip(load_per_screw: float, required_per_screw: float,
                     geom: ScrewGeometry, terrain) -> float:
    """Slip at which available thrust equals required thrust, or None.

    Solves F_av(s) = F_req for s in (0, 1) by bisection on the monotonic
    Janosi-Hanamoto mobilisation. Returns None when even full slip cannot
    supply the required thrust, which is the traction-limited case. This is
    the operating point the vehicle would settle at; the design slip used
    for power sizing is a separate, deliberately conservative, choice.
    """
    if drawbar_available(load_per_screw, 1.0, geom, terrain) < required_per_screw:
        return None
    lo, hi = 1e-6, 1.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if drawbar_available(load_per_screw, mid, geom, terrain) < required_per_screw:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def kinematics(geom: ScrewGeometry, speed: float, slip: float):
    """(omega [rad/s], ideal speed [m/s]) for a target ground speed. Paper Eq. (11).

    v_ideal = p * omega / (2 pi),  s = 1 - v / v_ideal
    """
    ideal = speed / max(1.0 - slip, 1e-3)
    return 2.0 * math.pi * ideal / geom.pitch, ideal


def torque_and_power(thrust_per_screw: float, geom: ScrewGeometry, omega: float):
    """Screw torque [N m] and mechanical power per screw [W].

    Paper Eq. (12). The electrical power, n_s T omega / eta_dt, is formed in
    sizing_loop.size.
    """
    torque = thrust_per_screw * geom.pitch / (2.0 * math.pi * geom.screw_efficiency)
    return torque, torque * omega


def cost_of_transport(power: float, weight: float, speed: float) -> float:
    """green2021 Eq. 1, dimensionless. COT = P / (W v)."""
    return power / max(weight * speed, 1e-9)


def rolling_resistance(weight: float, terrain) -> float:
    """R_r = c_rr * W.  rimani_week4_mobility.

    Kept separate from Bekker compaction resistance. The two overlap
    conceptually: c_rr is an empirical lump that already contains compaction
    on soft ground. Using both double counts. sizing_loop uses whichever the
    caller selects and says which.
    """
    return terrain.c_rr * weight


def traction_limited_slope(mu: float) -> float:
    """theta = arctan(mu), in degrees.  rimani_week4_mobility.

    m g sin(theta) <= mu m g cos(theta), so mass and gravity cancel and the
    traction-limited slope depends only on the available friction
    coefficient. This is the closed form behind the gravity discussion.
    """
    return math.degrees(math.atan(mu))


def radius_to_sinkage(z: float, geom: ScrewGeometry) -> float:
    """r / z.  rimani_week4_mobility gives a design rule of r/z >= 6 to 10."""
    return (geom.outer_diameter / 2.0) / max(z, 1e-9)


def obstacle_capability(geom: ScrewGeometry, alpha: float = 0.5) -> float:
    """h_max ~ alpha * d, alpha = 0.3 to 0.7.  rimani_week4_mobility.

    Stated for wheels. Whether a screw drum climbs like a wheel of the same
    diameter is not established anywhere in sources.yaml, so treat this as
    an analogy that needs testing, not a result.
    """
    return alpha * geom.outer_diameter


def displaced_volume(geom: ScrewGeometry) -> float:
    """Volume displaced by the screw drums when fully submerged, m^3.

    V_drums of paper Eq. (17).

        V = n_screws * (pi / 4) * D_drum^2 * L

    Drum cylinders only. The helical blades displace a little more, and any
    hull carried above the drums displaces a great deal more, so this is a
    deliberately conservative floor on buoyancy rather than an estimate of
    it. Treat a design that passes on drum volume alone as safe, and one
    that fails as undecided rather than sunk.

    NOT VALIDATED. No Titan amphibian exists to check this against, and the
    terrestrial screw amphibians in the database (MSA, ZIL-2906) float on
    sealed drums whose internal volume is not recorded here.
    """
    return geom.n_screws * math.pi * geom.drum_diameter ** 2 / 4.0 * geom.length


def flotation_vol(env, mass: float) -> float:
    """Displaced volume needed to float a vehicle of the given mass, m^3.

    V_req of paper Eq. (17).

    Archimedes: rho_liquid * V * g = m * g, so V = m / rho_liquid. Gravity
    cancels, so the requirement is the same on Titan as it would be on Earth
    for the same liquid. Takes a MASS in kg, not a weight in newtons.

    Returns infinity on a body with no surface liquid, so a flotation
    requirement is never satisfied by accident on a dry world.

    Static flotation only. Freeboard, trim, stability in waves and the
    hydrodynamic drag of a screw driving itself through liquid are all
    outside this, and all of them matter before anyone claims the vehicle
    is amphibious.
    """
    if env.liquid_density <= 0.0:
        return float("inf")
    return mass / env.liquid_density
