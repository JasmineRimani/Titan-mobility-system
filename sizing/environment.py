"""Environments.

Every value carries the source_id it comes from (see sources.yaml).
Values tagged ASSUMED are not in any source and must be replaced.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Environment:
    name: str
    gravity: float            # m/s^2
    atm_density: float        # kg/m^3
    atm_pressure: float       # Pa
    temperature: float        # K
    design_wind: float        # m/s, near-surface design wind speed
    liquid_density: float     # kg/m^3 of the surface liquid, 0 if none
    sources: dict = field(default_factory=dict)


EARTH = Environment(
    name="Earth", gravity=9.81, atm_density=1.225, atm_pressure=101325.0,
    temperature=288.0, design_wind=0.0, liquid_density=1000.0,
    sources={"all": "standard sea level"},
)

MOON = Environment(
    name="Moon", gravity=1.62, atm_density=0.0, atm_pressure=0.0,
    temperature=250.0, design_wind=0.0, liquid_density=0.0,
    sources={"gravity": "patel2005 (lunar soil table uses g = 1.63 m/s^2)"},
)

# Titan.
#   gravity, temperature, methane density  -> genta2011
#   surface pressure, temperature 90 K     -> zimmerman_postHuygens
#   near-surface wind about 1 m/s          -> matthies2017
#   atmospheric density: matthies2017 says "almost 5 times Earth sea level".
#     5.6 kg/m^3 below is CALCULATED from p = 1.5 bar, T = 90 K, pure N2
#     (rho = p*M/(R*T)), which agrees with that statement. Replace with a
#     Titan-GRAM value for the actual latitude, season and altitude.
TITAN = Environment(
    name="Titan", gravity=1.352, atm_density=5.6, atm_pressure=1.5e5,
    temperature=90.0, design_wind=1.0, liquid_density=423.0,
    sources={
        "gravity": "genta2011",
        "temperature": "zimmerman_postHuygens (90 K); genta2011 (about -180 C)",
        "atm_pressure": "zimmerman_postHuygens (1.5 bar)",
        "atm_density": "CALCULATED from p, T, N2; consistent with matthies2017",
        "design_wind": "matthies2017 (near surface about 1 m/s, described as low)",
        "liquid_density": "genta2011 (liquid methane at boiling point)",
    },
)

ENVIRONMENTS = {e.name.lower(): e for e in (EARTH, MOON, TITAN)}
