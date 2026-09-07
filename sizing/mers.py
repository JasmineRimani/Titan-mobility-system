"""Mass estimation relationships and subsystem fractions.

Terramechanics sizes a vehicle from a given mass. It does not tell you what
the drive module weighs. That mapping is what closes the loop.

HOW THE DRIVE MODULE IS SIZED HERE, AND WHY

  An earlier version of this file carried an invented power law
  m = a * T^b for motors and gearboxes. It has been removed. No source in
  sources.yaml contains a torque-and-mass pair for a single actuator, so
  that regression could not be fitted, checked, or defended.

  The method taught in rimani_week4_mobility does not use a mass regression
  at all. It sizes the drive by torque and speed, picks a motor and gear
  ratio against a datasheet, and takes the module mass from a bracket:

      "Small terrestrial prototypes: ~0.5-2 kg per wheel module;
       flight-like designs are typically higher due to sealing,
       redundancy, and thermal/radiation constraints."

  and cross-checks the result against

      "Drivetrain mass fraction ~ 10-25% of total rover mass" (wheeled rover)

  That bracket is corroborated by patel2005 Table 37, where the ExoMars
  centre wheel motor and gear assembly is 2.5 kg for two units, so 1.25 kg
  each, which sits inside the 0.5 to 2 kg range.

  So the default model here is a MODULE MASS, not a regression. One number
  per driven screw, from a sourced bracket, with the required motor torque
  and gear ratio reported alongside it so the student can do the datasheet
  match that the course actually teaches.

  If catalogue data is later collected, set actuator_model="power_law" and
  supply coefficients fitted with fit_mers.py. The code refuses to use that
  path uncalibrated.

OTHER SOURCED VALUES
  Non-mobility subsystem fractions: ExoMars TN4 budget, patel2005 Table 37.
  Average margin in that budget 15.6 percent.
  Drivetrain efficiency: patel2005 gives 0.59 gearbox x 0.80 motor, about
  0.47 overall. rimani_week4_mobility gives 0.7 to 0.85 overall. Both are
  offered; they differ by nearly a factor of two and the choice is visible.
  Power sources, genta2011: SNAP-19 42.7 We for 13.6 kg, MMRTG about 110 We
  for under 45 kg. Battery 100 Wh/kg, matthies2017.
"""

from dataclasses import dataclass


class UncalibratedModel(Exception):
    """Raised when a model is asked for a number it has no data to produce."""


# --- running gear areal density evidence ---------------------------------
# Derived in data/running_gear.csv from patel2005 Table 68, which gives mass,
# diameter and width for the wheels of five normalised micro-rover chassis.
# Areal density is mass / (pi * D * width), the curved shell only, which is
# the same convention running_gear_mass() uses for a screw drum.
#
#   Crab       12.6      Marsokhod  24.5      ELMS  31.8 (18.3 in the body text)
#   Sojourner  35.0      Shrimp     35.0      Nanokhod 53.1      kg/m^2
#
# THE SCALING CAVEAT, which matters more than the numbers. Those are 10 to
# 14 cm wheels hollowed out of aluminium billet. A 0.6 to 0.8 m screw drum is
# not built that way; it is a thin rolled shell on ribs, and shell mass per
# square metre falls as the part grows because the wall thickness is set by
# handling and buckling, not by scaling the diameter. So the micro-rover
# numbers are an upper bound for a large drum, not a value to copy across.
#
# THE ONE REAL SCREW DRUM IN THE SET. richter2022 Table I gives the ARCSnake
# body module at 1.0 kg for a 128 mm diameter and 196 mm long screw segment,
# which is 12.7 kg/m^2 of drum surface. That module contains the screw shell
# AND its motor, sun gear, power electronics, IMU, single board computer and
# network switch, so the bare shell is lighter still. It is a screw, not a
# wheel, and it is the closest thing to a measurement this package has.
#
# The default of 12.0 kg/m^2 therefore sits just under a real screw module
# with its electronics included, and just under the lightest micro-rover
# wheel. It is still a CHOICE and it is still the single most load-bearing
# assumption in this package. run_example.py reports the areal density at
# which the design stops closing under the delivered mass cap, so the
# assumption is visible as a structural requirement rather than buried.
AREAL_DENSITY_EVIDENCE = {
    "arcsnake_screw_module": 12.7, "crab": 12.6, "marsokhod": 24.5, "elms_body_text": 18.3,
    "elms_table68": 31.8, "sojourner": 35.0, "shrimp": 35.0,
    "nanokhod": 53.1,
}
AREAL_DENSITY_RANGE = (12.6, 53.1)   # kg/m^2, micro-rover wheels, patel2005

# Blade face areal density, 29.1 kg/m^2, CALCULATED from patel2005 Table 14:
# grouser mass rises linearly with height at 58.224 kg per metre of height for
# 20 grousers of 0.1 m width, so 58.224 / (20 * 0.1) = 29.1 kg per m^2 of
# blade face. That table states a 2 mm grouser thickness but its own mass
# column implies about 10.8 mm at aluminium density; the mass column is the
# quantity used here. See data/running_gear.csv.
BLADE_AREAL_DENSITY_SOURCED = 29.1

# rimani_week4_mobility, per driven wheel module
MODULE_MASS_RANGE_KG = (0.5, 2.0)
# rimani_week4_mobility, wheeled rover
DRIVETRAIN_FRACTION_RANGE = (0.10, 0.25)


@dataclass
class MassModel:
    # --- drive module ------------------------------------------------------
    # "module"    : fixed mass per driven screw, from the sourced bracket
    # "power_law" : m = a * T^b, refuses to run until calibrated
    actuator_model: str = "module"
    module_mass: float = 1.5          # kg per driven screw. Upper half of the
                                      # 0.5-2 kg bracket, because a Titan
                                      # module is sealed, redundant and cold.
                                      # CHOICE inside a sourced range.
    motor_torque_margin: float = 2.0  # rimani_week4_mobility Step 4,
                                      # tau_motor ~ 2 * tau_wheel / (G * eta_g)
    motor_a: float = None             # only for actuator_model="power_law"
    motor_b: float = None
    gearbox_a: float = None
    gearbox_b: float = None

    # --- running gear.  THE DOMINANT UNCERTAINTY --------------------------
    # See data/running_gear.csv and AREAL_DENSITY_EVIDENCE below.
    drum_areal_density: float = 12.0     # kg/m^2 of drum shell.  CHOICE
    blade_areal_density: float = 29.1    # kg/m^2 of blade face.  patel2005
    bearing_fraction: float = 0.10       # of drum plus blade mass
    drive_electronics: float = 0.8       # kg per screw

    # --- non-mobility subsystem fractions of dry mass, patel2005 Table 37 --
    structure_fraction: float = 0.097
    thermal_fraction: float = 0.075
    data_handling_fraction: float = 0.030
    navigation_fraction: float = 0.014
    comms_fraction: float = 0.045
    harness_fraction: float = 0.021
    margin_fraction: float = 0.156

    # --- power subsystem ---------------------------------------------------
    source_specific_power: float = 2.44      # W/kg, MMRTG class, genta2011
    battery_specific_energy: float = 100.0   # Wh/kg, matthies2017
    pmad_fraction: float = 0.15              # ASSUMED

    # --- drivetrain --------------------------------------------------------
    # "patel"  : 0.59 * 0.80 = 0.472  [patel2005]
    # "course" : 0.78, midpoint of 0.7 to 0.85  [rimani_week4_mobility]
    drivetrain_efficiency_model: str = "patel"

    @property
    def drivetrain_efficiency(self) -> float:
        if self.drivetrain_efficiency_model == "patel":
            return 0.59 * 0.80
        if self.drivetrain_efficiency_model == "course":
            return 0.78
        raise ValueError(f"unknown drivetrain model "
                         f"'{self.drivetrain_efficiency_model}'")

    @property
    def non_mobility_fraction(self) -> float:
        return (self.structure_fraction + self.thermal_fraction
                + self.data_handling_fraction + self.navigation_fraction
                + self.comms_fraction + self.harness_fraction)


# Power source options, genta2011.  (electrical W, mass kg)
POWER_SOURCES = {
    "snap19": (42.7, 13.6),
    "mmrtg": (110.0, 45.0),
    "arps_titan_rover": (110.0, None),
    "rps_zimmerman": (100.0, None),
}


def specific_power(source_key: str) -> float:
    p, m = POWER_SOURCES[source_key]
    if m is None:
        raise UncalibratedModel(
            f"the mass of power source '{source_key}' is not in any indexed "
            f"source, so W/kg cannot be computed")
    return p / m


def drive_module_mass(torque: float, mm: MassModel) -> float:
    """Mass of one screw drive module (motor, gearbox, bearings, mounts), kg.

    torque is the screw output torque in N m. It is unused by the default
    module model and is kept in the signature so a calibrated power law can
    be dropped in without touching the caller.
    """
    if mm.actuator_model == "module":
        return mm.module_mass
    if mm.actuator_model == "power_law":
        if None in (mm.motor_a, mm.motor_b, mm.gearbox_a, mm.gearbox_b):
            raise UncalibratedModel(
                "actuator_model='power_law' needs motor_a, motor_b, "
                "gearbox_a and gearbox_b. No source in sources.yaml gives a "
                "torque-and-mass pair for one actuator, so these cannot be "
                "filled from the literature. Collect catalogue rows in "
                "data/actuators.csv, run fit_mers.py, and paste the "
                "coefficients into MassModel. Until then use "
                "actuator_model='module'.")
        t = max(torque, 1e-3)
        return mm.motor_a * t ** mm.motor_b + mm.gearbox_a * t ** mm.gearbox_b
    raise ValueError(f"unknown actuator_model '{mm.actuator_model}'")


def required_motor_torque(screw_torque: float, gear_ratio: float,
                          mm: MassModel) -> float:
    """rimani_week4_mobility Step 4.  tau_motor ~ margin * tau / (G * eta_g)."""
    return mm.motor_torque_margin * screw_torque / (gear_ratio * 0.59)


def running_gear_mass(geom, mm: MassModel) -> float:
    """Drums, helices and bearings for all screws, kg. PLACEHOLDER densities."""
    import math
    shell = math.pi * geom.drum_diameter * geom.length * mm.drum_areal_density
    turns = geom.length / geom.pitch
    annulus = math.pi * (geom.outer_diameter ** 2 - geom.drum_diameter ** 2) / 4.0
    blade = turns * annulus * geom.n_starts * mm.blade_areal_density
    per_screw = (shell + blade) * (1.0 + mm.bearing_fraction)
    return geom.n_screws * per_screw


def eps_mass(p_house: float, p_drive_elec: float, drive_duty: float,
             drive_session_h: float, mm: MassModel):
    """(source mass, battery mass, pmad mass) in kg."""
    p_source = p_house + drive_duty * p_drive_elec
    m_source = p_source / mm.source_specific_power
    deficit = max(0.0, p_house + p_drive_elec - p_source)
    m_batt = (deficit * drive_session_h) / mm.battery_specific_energy
    return m_source, m_batt, mm.pmad_fraction * (m_source + m_batt)
