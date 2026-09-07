"""Mass estimation relationships and subsystem fractions.

Terramechanics sizes a vehicle from a given mass. It does not tell you what
the motor weighs. That mapping is what closes the loop, and it has to come
from data.

WHAT IS SOURCED HERE
  Non-mobility subsystem fractions come from the ExoMars TN4 mass budget
  reproduced in patel2005 Table 37 (96.567 kg nominal, 111.696 kg predicted):
     structure 9.7 %, thermal 7.5 %, data handling 3.0 %, navigation 1.4 %,
     communications 4.5 %, harness 2.1 %  -> 28.2 % of total
     power 17.4 % and locomotion 54.4 % are computed here instead of assumed.
  Average margin in that budget is 15.6 %.
  Drivetrain efficiency chain 0.59 gearbox x 0.80 motor x 0.90 wheel is also
  from patel2005 (about 0.40 overall).
  Power sources are from genta2011: SNAP-19 42.7 We for 13.6 kg (3.14 W/kg),
  MMRTG about 110 We for under 45 kg (about 2.44 W/kg).
  Battery specific energy 100 Wh/kg is from matthies2017 (Li-ion, kept warm).

WHAT IS STILL A PLACEHOLDER
  The actuator relations m = a * T^b. No published regression exists in any
  of the sources indexed in sources.yaml; they give discrete points only
  (for example Maxon RE-25 at 130 g and RE-20 at about 60 g, patel2005). So
  these coefficients are invented and must be replaced:
      fill data/actuators.csv from a motor and gearbox catalogue,
      run fit_mers.py, paste the result back here.
  Drum and blade areal densities are also placeholders. green2021 gives a
  3.4 kg four-screw vehicle but no screw geometry, so it cannot be inverted
  into an areal density.

CROSS-CHECK AVAILABLE
  patel2005 gives the chassis to total mass fraction K in the range 0.30 to
  0.50 for real rovers (LRV 0.308, Sojourner 0.4, MER 0.5, ExoMars 0.32 to
  0.40). The user's own screw database suggests 0.25 to 0.50 for screw
  vehicles. A converged mobility fraction outside roughly 0.2 to 0.6 should
  be treated as a red flag, not a result.
"""

import math
from dataclasses import dataclass


@dataclass
class MassModel:
    # actuators, m = a * T^b, T in N m, m in kg.  PLACEHOLDER, see module note
    motor_a: float = 0.055
    motor_b: float = 0.85
    gearbox_a: float = 0.040
    gearbox_b: float = 0.90

    # running gear.  PLACEHOLDER
    drum_areal_density: float = 12.0     # kg/m^2 of drum shell
    blade_areal_density: float = 18.0    # kg/m^2 of developed blade
    bearing_fraction: float = 0.10       # of drum plus blade mass
    drive_electronics: float = 0.8       # kg per screw

    # non-mobility subsystem fractions of dry mass.  patel2005 Table 37
    structure_fraction: float = 0.097
    thermal_fraction: float = 0.075
    data_handling_fraction: float = 0.030
    navigation_fraction: float = 0.014
    comms_fraction: float = 0.045
    harness_fraction: float = 0.021
    margin_fraction: float = 0.156       # patel2005 Table 37, average margin

    # power subsystem
    source_specific_power: float = 2.44  # W/kg, MMRTG class, genta2011
    battery_specific_energy: float = 100.0   # Wh/kg, matthies2017
    pmad_fraction: float = 0.15          # of source plus battery.  ASSUMED

    # drivetrain efficiencies, patel2005
    gearbox_efficiency: float = 0.59
    motor_efficiency: float = 0.80

    @property
    def non_mobility_fraction(self) -> float:
        return (self.structure_fraction + self.thermal_fraction
                + self.data_handling_fraction + self.navigation_fraction
                + self.comms_fraction + self.harness_fraction)


# Power source options, genta2011.  (electrical W, mass kg)
POWER_SOURCES = {
    "snap19": (42.7, 13.6),      # 525 Wt, used as the baseline in genta2011
    "mmrtg": (110.0, 45.0),      # about 2 kWt
    "arps_titan_rover": (110.0, None),   # arps_titan_rover, mass not sourced
    "rps_zimmerman": (100.0, None),      # 1250 Wt, mass not sourced
}


def specific_power(source_key: str) -> float:
    p, m = POWER_SOURCES[source_key]
    if m is None:
        raise ValueError(f"mass of power source '{source_key}' is not in any "
                         f"indexed source; cannot compute W/kg")
    return p / m


def actuator_mass(torque: float, mm: MassModel) -> float:
    """Motor plus gearbox mass for one screw drive, kg. PLACEHOLDER fit."""
    t = max(torque, 1e-3)
    return mm.motor_a * t ** mm.motor_b + mm.gearbox_a * t ** mm.gearbox_b


def running_gear_mass(geom, mm: MassModel) -> float:
    """Drums, helices and bearings for all screws, kg. PLACEHOLDER densities."""
    shell = math.pi * geom.drum_diameter * geom.length * mm.drum_areal_density
    turns = geom.length / geom.pitch
    annulus = math.pi * (geom.outer_diameter ** 2 - geom.drum_diameter ** 2) / 4.0
    blade = turns * annulus * geom.n_starts * mm.blade_areal_density
    per_screw = (shell + blade) * (1.0 + mm.bearing_fraction)
    return geom.n_screws * per_screw


def eps_mass(p_house: float, p_drive_elec: float, drive_duty: float,
             drive_session_h: float, mm: MassModel):
    """(source mass, battery mass, pmad mass) in kg.

    The source is sized for the time-averaged load, the battery covers the
    difference during one driving session. genta2011 makes the same point in
    words: level-ground driving needs 2.4 W and is easy, a 20 degree slope
    needs about 34 W and "should be dealt only with fully charged batteries".
    """
    p_source = p_house + drive_duty * p_drive_elec
    m_source = p_source / mm.source_specific_power

    deficit = max(0.0, p_house + p_drive_elec - p_source)
    m_batt = (deficit * drive_session_h) / mm.battery_specific_energy
    return m_source, m_batt, mm.pmad_fraction * (m_source + m_batt)
