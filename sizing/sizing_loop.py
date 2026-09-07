"""The sizing loop.

    guess m_total
      -> allocate subsystem masses, power and volume
      -> set screw geometry
      -> screw-terrain block: sinkage, thrust, torque, mobility power
      -> size actuators from torque, power system from the duty cycle
      -> recompute m_total
      -> repeat to convergence

The loop is the contribution. The database supplies its coefficients and the
cases it is validated against.
"""

import math
from dataclasses import dataclass, field

from .environment import Environment, TITAN
from .mers import (MassModel, DRIVETRAIN_FRACTION_RANGE, drive_module_mass,
                   eps_mass, required_motor_torque, running_gear_mass)
from .screw import (ScrewGeometry, bulldozing_flag, check_validity,
                    compaction_resistance, contact_width, cost_of_transport,
                    drawbar_available, kinematics, obstacle_capability,
                    radius_to_sinkage, rolling_resistance, sinkage,
                    torque_and_power, traction_limited_slope)
from .terrain import Terrain, TITAN_LUNAR_PROXY


@dataclass
class Mission:
    """The Titan reference mission, written down before anything is designed.

    Sources for the defaults:
      payload_mass 12 kg           tandem_tm2022, predicted science payload
      target_speed 0.028 m/s       genta2011, 100 m/h max speed
      design_slope 20 deg          genta2011, max grade 36 percent
      max_obstacle 0.10 m          genta2011, 100 mm obstacle, no wheel lift-off
      delivered_mass_cap 344 kg    tandem_tm2022, predicted total mass.
                                   zimmerman_postHuygens delivers 100 kg of
                                   science payload inside a 5028 kg launch
                                   with about 30 percent margin, so the
                                   100 to 350 kg class is the defensible
                                   range for a Titan surface vehicle.
      design_slip 0.30             villacres2023 reports screw slip reaching
                                   40 percent, so 30 percent is inside the
                                   observed range but is still a CHOICE
      payload_power, avionics_power, thermal_power, drive_duty,
      drive_session_h, cg_height, drag_coefficient   ASSUMED, no source
    """
    payload_mass: float = 12.0
    payload_power: float = 15.0
    avionics_power: float = 20.0      # matthies2017 avionics allocation
    thermal_power: float = 20.0       # zimmerman_postHuygens sonde jacket, 20 We
    target_speed: float = 0.028
    design_slope: float = 20.0
    acceleration: float = 0.01
    design_slip: float = 0.30
    drive_duty: float = 0.15
    drive_session_h: float = 4.0
    min_radius_to_sinkage: float = 6.0   # r/z >= 6 to 10, rimani_week4_mobility
    motor_nominal_rpm: float = 5000.0    # CHOICE, for reporting the gear ratio
    max_obstacle: float = 0.10
    delivered_mass_cap: float = 344.0
    cg_height: float = 0.6
    drag_coefficient: float = 1.2


@dataclass
class Result:
    converged: bool
    iterations: int
    total_mass: float
    masses: dict = field(default_factory=dict)
    powers: dict = field(default_factory=dict)
    performance: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return self.converged and all(self.checks.values())


def size(mission: Mission,
         geom: ScrewGeometry,
         terrain: Terrain = TITAN_LUNAR_PROXY,
         env: Environment = TITAN,
         mm: MassModel = None,
         m_guess: float = 200.0,
         tol: float = 1e-3,
         max_iter: int = 300,
         divergence_cap: float = 50.0) -> Result:
    """Run the fixed-point loop.

    divergence_cap: if total mass grows past this multiple of the initial
    guess the design does not close, because mobility mass feeds resistance
    which feeds mobility mass. That is a real result, not a bug.
    """
    mm = mm or MassModel()
    frac_sum = mm.non_mobility_fraction
    if frac_sum >= 1.0:
        raise ValueError("non-mobility fractions sum to 1 or more")

    m_total = m_guess
    converged = False
    notes = []

    for it in range(1, max_iter + 1):
        weight = m_total * env.gravity
        load_per_screw = weight / geom.n_screws

        z = sinkage(load_per_screw, geom, terrain)
        # Two ways to get motion resistance, and they overlap. Bekker
        # compaction is mechanistic; c_rr is an empirical lump that already
        # contains compaction. Adding them double counts, so take the larger
        # and report both.
        r_bekker = geom.n_screws * compaction_resistance(z, geom, terrain)
        r_crr = rolling_resistance(weight, terrain)
        r_comp = max(r_bekker, r_crr)

        frontal_area = geom.n_screws * geom.outer_diameter * 1.2   # ASSUMED
        f_aero = 0.5 * env.atm_density * mission.drag_coefficient \
            * frontal_area * env.design_wind ** 2

        f_required = (m_total * mission.acceleration
                      + weight * math.sin(math.radians(mission.design_slope))
                      + r_comp + f_aero)
        f_available = geom.n_screws * drawbar_available(
            load_per_screw, mission.design_slip, geom, terrain)

        omega, _ = kinematics(geom, mission.target_speed, mission.design_slip)
        torque, p_mech = torque_and_power(f_required / geom.n_screws, geom, omega)
        p_drive_elec = geom.n_screws * p_mech / mm.drivetrain_efficiency

        # rimani_week4_mobility Step 4: gear ratio from the speed requirement,
        # then the motor torque the datasheet has to supply.
        omega_motor = mission.motor_nominal_rpm * 2.0 * math.pi / 60.0
        gear_ratio = omega_motor / max(omega, 1e-9)
        motor_torque = required_motor_torque(torque, gear_ratio, mm)

        m_running = running_gear_mass(geom, mm)
        m_actuators = geom.n_screws * (drive_module_mass(torque, mm)
                                       + mm.drive_electronics)
        m_mobility = m_running + m_actuators

        p_house = mission.payload_power + mission.avionics_power + mission.thermal_power
        m_src, m_bat, m_pmad = eps_mass(p_house, p_drive_elec, mission.drive_duty,
                                        mission.drive_session_h, mm)
        m_eps = m_src + m_bat + m_pmad

        m_dry = (mission.payload_mass + m_mobility + m_eps) / (1.0 - frac_sum)
        m_new = m_dry * (1.0 + mm.margin_fraction)

        if abs(m_new - m_total) / m_total < tol:
            m_total, converged = m_new, True
            break
        if m_new > divergence_cap * m_guess or not math.isfinite(m_new):
            m_total = min(m_new, divergence_cap * m_guess)
            notes.append("loop diverged: mobility mass feeds resistance which "
                         "feeds mobility mass. The design does not close.")
            break
        m_total = 0.5 * (m_total + m_new)

    if not check_validity(z, geom, quiet=True):
        notes.append(f"sinkage {z*1000:.1f} mm exceeds blade height "
                     f"{geom.blade_height*1000:.1f} mm, so the Bekker-derived "
                     f"screw model is outside its stated validity range "
                     f"(villacres2023).")
    if bulldozing_flag(z, geom):
        notes.append("z/D exceeds 0.06, so bulldozing resistance is no longer "
                     "negligible (patel2005, ellery2005) and is NOT modelled here.")
    lo, hi = DRIVETRAIN_FRACTION_RANGE
    drive_frac = m_actuators / m_total
    if not (lo <= drive_frac <= hi):
        notes.append(f"drive module mass is {drive_frac*100:.1f} percent of "
                     f"total, outside the {lo*100:.0f} to {hi*100:.0f} percent "
                     f"drivetrain fraction that rimani_week4_mobility quotes "
                     f"for wheeled rovers. For a screw vehicle the running "
                     f"gear, not the actuators, carries the mass, so this is "
                     f"expected rather than wrong. Check it deliberately.")
    if r_crr > r_bekker:
        notes.append(f"motion resistance is set by the empirical c_rr "
                     f"({r_crr:.1f} N) rather than Bekker compaction "
                     f"({r_bekker:.1f} N). c_rr for this terrain is "
                     f"{terrain.c_rr:.3f} [{terrain.c_rr_source}].")
    if terrain.evidence.startswith("PROXY"):
        notes.append(f"terrain '{terrain.name}' is a proxy, not a measurement: "
                     f"{terrain.evidence}")

    masses = {
        "payload": mission.payload_mass,
        "mobility_running_gear": m_running,
        "mobility_actuators": m_actuators,
        "mobility_total": m_mobility,
        "eps_source": m_src, "eps_battery": m_bat, "eps_pmad": m_pmad,
        "eps_total": m_eps,
        "structure": mm.structure_fraction * m_dry,
        "thermal": mm.thermal_fraction * m_dry,
        "data_handling": mm.data_handling_fraction * m_dry,
        "navigation": mm.navigation_fraction * m_dry,
        "comms": mm.comms_fraction * m_dry,
        "harness": mm.harness_fraction * m_dry,
        "dry": m_dry, "margin": m_total - m_dry, "total": m_total,
    }
    powers = {
        "payload": mission.payload_power,
        "avionics": mission.avionics_power,
        "thermal": mission.thermal_power,
        "housekeeping": p_house,
        "drive_mechanical": geom.n_screws * p_mech,
        "drive_electrical": p_drive_elec,
        "source_sized": p_house + mission.drive_duty * p_drive_elec,
    }
    track_width = geom.n_screws * geom.outer_diameter
    overturn = (m_total * env.gravity * track_width / 2.0) / max(f_aero * mission.cg_height, 1e-9)

    performance = {
        "sinkage_m": z,
        "sinkage_ratio": z / geom.outer_diameter,
        "contact_pressure_kPa": load_per_screw / (
            contact_width(z, geom.outer_diameter) * geom.length) / 1000.0,
        "resistance_used_N": r_comp,
        "resistance_bekker_N": r_bekker,
        "resistance_crr_N": r_crr,
        "aero_drag_N": f_aero,
        "thrust_required_N": f_required,
        "thrust_available_N": f_available,
        "drawbar_margin": f_available / f_required if f_required > 0 else float("inf"),
        "screw_torque_Nm": torque,
        "gear_ratio": gear_ratio,
        "motor_torque_Nm": motor_torque,
        "radius_to_sinkage": radius_to_sinkage(z, geom),
        "obstacle_capability_m": obstacle_capability(geom),
        "traction_limited_slope_deg": traction_limited_slope(
            f_available / max(weight, 1e-9)),
        "screw_speed_rpm": omega * 60.0 / (2.0 * math.pi),
        "tip_speed_mps": geom.tip_speed(omega),
        "screw_efficiency": geom.screw_efficiency,
        "helix_angle_deg": geom.helix_angle_deg,
        "aspect_ratio_chen": geom.aspect_ratio,
        "cost_of_transport": cost_of_transport(p_drive_elec, m_total * env.gravity,
                                               mission.target_speed),
        "mobility_mass_fraction": m_mobility / m_total,
        "overturning_margin": overturn,
    }
    checks = {
        "mass_within_delivered_cap": m_total <= mission.delivered_mass_cap,
        "radius_to_sinkage_ok": radius_to_sinkage(z, geom) >= mission.min_radius_to_sinkage,
        "thrust_available": f_available >= f_required,
        "overturning_margin_ge_2": overturn >= 2.0,
        "mobility_fraction_plausible": 0.15 <= m_mobility / m_total <= 0.60,
        "obstacle_requirement_met": obstacle_capability(geom) >= mission.max_obstacle,
    }
    return Result(converged, it, m_total, masses, powers, performance, checks, notes)
