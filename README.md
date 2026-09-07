# Preliminary sizing of a screw-propelled planetary rover

A small, readable Phase-0/A sizing method for screw-propelled rovers, with
Titan as the reference case and terrestrial screw and tracked vehicles as the
validation evidence. Pure Python, standard library only, matplotlib optional
for one figure.

Every number in the package is either traced to a source in `sources.yaml`
or labelled `PLACEHOLDER` / `ASSUMED`. Nothing sits in between. The papers
themselves are distributed alongside this folder; `sources.yaml` is the index
that says which number came from which one.

```bash
python run_example.py     # baseline, literature cross-checks, gravity study, trade space
python validate.py        # mobility fraction priors, mobility-block reconstruction
python fit_mers.py        # actuator mass relations from catalogue data
```

---

## 1. The idea in one page

A screw-propelled rover cannot be sized by scaling a terrestrial vehicle,
because the vehicles that exist were built for a different gravity, a
different mission and a different mass definition. It also cannot be sized by
terramechanics alone, because pressure-sinkage and shear models tell you what
a vehicle of a given mass does on a given soil, but they do not tell you what
the motor weighs.

So the method is a loop:

```
guess total mass
  -> allocate subsystem masses, power and volume
  -> set screw geometry (N, D_drum, BH, L, p, lead angle, starts)
  -> screw-terrain block: sinkage, thrust, torque, mobility power
  -> size actuators from torque, size the power system from the duty cycle
  -> recompute total mass
  -> repeat to convergence
```

and a rule that protects it:

> **The database gives priors and validation cases. Physics closes the design.**

An Earth-derived mobility mass fraction may seed the loop. It may not survive
into the answer. By convergence, mobility mass is the sum of drums, helices,
motors, gearboxes, bearings, mounts and drive electronics. Comparing the
converged fraction back against the database range is then a sanity check,
not an assumption. `validate.py` prints both.

---

## 2. The Titan reference mission

This is the part that has to exist before anything can be designed, and it is
now filled in from the papers rather than guessed.

| Quantity | Value | Source |
|---|---|---|
| Surface gravity | 1.352 m/s2 | genta2011 |
| Surface pressure | 1.5 bar | zimmerman_postHuygens |
| Surface temperature | 90 K | zimmerman_postHuygens |
| Atmospheric density | 5.6 kg/m3, calculated from p and T, about 5 x Earth | matthies2017 |
| Near-surface wind | about 1 m/s, described as low | matthies2017 |
| Liquid methane density | 423 kg/m3 at boiling point | genta2011 |
| Surface soil parameters | none measured. Lunar regolith used as a proxy | genta2011 |
| Delivered mass, reference cap | 344 kg predicted total for a Titan surface vehicle | tandem_tm2022 |
| Delivered science payload, comparison | 100 kg inside a 5028 kg launch and 2600 kg injected, about 30 percent margin | zimmerman_postHuygens |
| Science payload | 12 kg predicted, 10 kg current best estimate | tandem_tm2022 |
| Target speed | 0.028 m/s, that is 100 m/h | genta2011 |
| Max grade | 20 degrees, that is 36 percent | genta2011 |
| Obstacle | 100 mm with no wheel lift-off | genta2011 |
| Power source | SNAP-19, 42.7 We for 13.6 kg, or MMRTG, about 110 We for under 45 kg | genta2011 |
| Battery | 100 Wh/kg Li-ion, assumed kept warm | matthies2017 |
| Surface system peak power, comparison | 60 W | zimmerman_postHuygens |
| Comms, if direct to Earth | 22 W RF and 65 W DC, 1 kbps, 8 h/day, about 3.6 Mbyte/day | zimmerman_postHuygens |
| Round trip light time | over 2.5 h, so no teleoperation | genta2011 |
| Landing error ellipse | 200 to 500 km by 50 to 100 km, unguided Huygens-like EDL | matthies2017 |

**On "how much mass can we actually land."** The defensible answer from these
sources is the 100 to 350 kg class for a Titan surface vehicle. The package
uses 344 kg as the cap and says where it came from. What none of these papers
gives is an EDL mass chain for a screw rover specifically, so treat the cap as
a requirement inherited from a comparator, not as a derived number.

**On wind.** Near-surface winds on Titan are weak, about 1 m/s. A paper that
says Titan has "strong wind" without an altitude and a resulting load is
wrong. The wind that matters in these studies is the descent wind that drives
the landing ellipse, not a wind load on a surface vehicle.

---

## 3. The three models, and how good they are

**Sinkage and motion resistance.** Classical Bekker pressure-sinkage solved
numerically on the cylindrical drum contact patch, then Bekker compaction
resistance. Equation forms from patel2005, ellery2005 and sagara2025. This is
the one piece whose parameters exist in the published literature for real
soils.

**Available thrust.** Mohr-Coulomb ceiling on the contact patch, mobilised by
a Janosi-Hanamoto slip term, then capped by a measured drawbar coefficient
where the terrain case has one. Two such measurements exist: 0.64 of vehicle
weight in very soft ground (wes_tr3641) and 0.54 in snow for the 1/5 scale
model (villacres2023).

**Motion resistance.** Two routes, and they overlap. Bekker compaction
resistance is mechanistic. The rolling resistance coefficient c_rr from
rimani_week4_mobility is an empirical lump that already contains compaction.
Adding both double counts, so the code takes the larger, reports both, and
says which one won. On the Titan proxy terrain c_rr wins by two orders of
magnitude, which is worth knowing before quoting a compaction number.

**Motor sizing.** Following rimani_week4_mobility Step 4, the loop reports the
gear ratio implied by the speed requirement and the motor torque a datasheet
would have to supply, tau_motor about 2 tau_screw / (G eta_g). That is the
datasheet match the course teaches, and it replaces the mass regression that
used to sit here.

**Torque and power.** The power-screw relation. The helix acts as a screw jack
against the soil:

```
F_axial = 2*pi*eta*T / p        eta = tan(lead) / tan(lead + atan(mu))
```

For realistic lead angles this gives efficiencies around 0.2 to 0.4, which is
why screws are slow and power hungry and why the power system tends to drive
the design.

**Feasibility checks now applied.** Mass within the delivered cap, radius to
sinkage at least 6 (rimani_week4_mobility, replacing the looser z below 0.3 D
rule), thrust available against thrust required, overturning margin at least
2, mobility fraction between 0.15 and 0.60, and obstacle capability against
the 100 mm requirement using h_max about 0.5 D. The last one is an analogy
from wheels, and whether a screw drum climbs like a wheel of the same diameter
is not established anywhere in `sources.yaml`.

**Validity, stated plainly.** villacres2023 is explicit that Bekker-derived
scroll models hold only while sinkage stays below the flight height, that is
while the screw runs on top of the soil rather than swimming in it. Soft mud
and snow, exactly where screws beat everything else, are outside that range.
The code checks this on every run and says so in the output rather than
extrapolating quietly.

**Not modelled.** Lateral drift and side slip, which chen2025 and sagara2025
both measure and which is a known screw weakness. The switch to wheel-like
rolling on hard ground, which richter2022 calls screw slippage. Buoyancy and
hydrodynamic drag, so a liquid crossing is out of scope. Dynamic sinkage,
multi-pass effects, bulldozing resistance, and the interaction between
multiple screws. State these as limitations in any paper.

**Geometry, and why there is no single right lead angle.** The literature
disagrees by medium: 22 degrees for maximum drawbar and minimum slip
(richter2022, attributed to Cole 1961), 35 degrees from a Taguchi optimisation
in granular material, 30 degrees for a submerged screw (both via
villacres2023). chen2025 finds blade height dominant in granular media and
pitch dominant in water. `screw.py` carries all three as
`RECOMMENDED_HELIX_ANGLE_DEG` rather than picking one.

---

## 4. The actuator question, and what actually matters

An earlier version of this package carried an invented power law
`m = a * T^b` for motors and gearboxes, fitted to synthetic rows in
`data/actuators.csv`. Both are gone. Not one source in `sources.yaml` gives a
rated torque and a mass for the same actuator, so that regression could not be
fitted, checked or defended. `fit_mers.py` now prints exactly which rows are
missing which half.

The method taught in rimani_week4_mobility does not need it. It sizes the
drive by torque and speed, matches a datasheet, and takes the module mass from
a bracket:

> Small terrestrial prototypes: about 0.5 to 2 kg per wheel module;
> flight-like designs are typically higher due to sealing, redundancy, and
> thermal and radiation constraints.

cross-checked against a drivetrain mass fraction of 10 to 25 percent of rover
mass. The bracket is corroborated independently: the ExoMars centre wheel
motor and gear assembly is 1.25 kg (patel2005 Table 37), which sits inside it.
So `mers.py` now uses a module mass of 1.5 kg per driven screw, a choice
inside a sourced range, and reports the gear ratio and motor torque next to
it. `MassModel(actuator_model="power_law")` exists for the day someone
collects catalogue data, and refuses to run until the coefficients are
supplied.

**And then the sensitivity study says the whole question barely matters.**
Sweeping each uncertain input across its plausible range, with everything else
at the baseline:

| Input | Range | Span in total mass |
|---|---|---|
| drum areal density | 6 to 24 kg/m2 | 71 % |
| blade areal density | 9 to 36 kg/m2 | 28 % |
| drive duty cycle | 0.05 to 0.40 | 7 % |
| power source | MMRTG to SNAP-19 | 5 % |
| soil-on-metal friction | 0.4 to 0.8 | 3 % |
| **drive module mass** | **0.5 to 2.0 kg** | **2 %** |
| design slip | 0.10 to 0.40 | 2 % |
| drivetrain efficiency | 0.47 to 0.78 | 2 % |
| rolling resistance c_rr | 0.10 to 0.25 | 1 % |

On a screw vehicle the running gear carries the mobility mass and the
actuators do not. Doubling the drum areal density moves the answer thirty
times further than the whole 0.5 to 2 kg module bracket. So the thing to go
and measure is the mass per square metre of a drum and a helix, not a motor
regression. `run_example.py` prints this table on every run, so it stays
honest as the model changes.

## 4a. What a second pass through the papers turned up

The first pass took numbers from summaries. A verification pass read the
papers themselves, confirmed every value already in the code, and found
several more that were being left on the table.

**A sourced areal density for the drum, the dominant uncertainty.**
patel2005 Table 68 gives mass, diameter and width for the wheels of five
normalised micro-rover chassis. Dividing mass by the curved shell area gives
the areal density this package needs:

```
Crab 12.6   ELMS 18.3 (body text) / 31.8 (Table 68)   Marsokhod 24.5
Sojourner 35.0   Shrimp 35.0   Nanokhod 53.1          kg/m2
```

and patel2005 Table 14 gives grouser mass as a linear function of height,
58.224 kg per metre of height for 20 grousers of 0.1 m width, which is
29.1 kg per square metre of blade face. Both are now in
`data/running_gear.csv` with the derivation and the caveats written out. The
blade default has moved from an invented 18 to the sourced 29.1.

**The drum shell is a requirement, not an input.** Because the running gear
dominates the budget, `run_example.py` now solves for the areal density at
which the converged mass reaches the delivered cap:

```
delivered mass cap                       344 kg   [tandem_tm2022]
closure limit, this geometry            24.8 kg/m2
micro-rover wheel evidence range        12.6 to 53.1 kg/m2   [patel2005]
```

Four of the seven real wheels are above that limit. They are 10 to 14 cm
wheels hollowed from aluminium billet and a 0.6 to 0.8 m drum is a thin
rolled shell on ribs, so this is an upper bound rather than a contradiction.
It is still the first number to go and check, and it is now stated as a
structural requirement instead of buried in a default.

**A real screw drum, recovered from a table that text extraction had lost.**
richter2022 Table I is an image, so the first pass could not read it. Reading
the page directly gives the ARCSnake body module at 1.0 kg for a 128 mm by
196 mm screw segment, which is 12.7 kg per square metre of drum surface, with
the motor, sun gear, power electronics, IMU, single board computer and network
switch all inside that 1.0 kg. The bare shell is lighter. That is a screw and
not a wheel, and it is the closest thing to a measurement in the whole set, so
it is now what justifies the 12.0 kg/m2 default rather than a scaling
argument. The same table gives the system mass of 6.1 kg, 310 W per module and
1240 W for the four-module system, all now in the database.

**Genta's own mobility mass budget, which settles the module question.**
genta2011 Section 3.5: 400 g per traction motor, 1.5 kg per corner including
a 20 percent allowance, 6 kg of mobility on a 40 kg Titan rover. That is a
Titan design, not a terrestrial wheel module, and it agrees exactly with the
1.5 kg per driven screw this package assumes. Both rows are now in
`data/actuators.csv`. Note the architecture: the motor sits in the wheel hub
with no reduction gear at all, turning at 2.97 rpm. This package assumes a
5000 rpm motor and reports a 938:1 gear ratio. Direct drive is a real
alternative and it is worth a line in the paper.

**A Titan-specific rolling resistance coefficient.** genta2011 uses f = 0.10,
being the computed value multiplied by a safety factor of 3. That replaces
the 0.15 taken from the course terrain table for the Titan proxy case.

**A quantified flotation comparison.** genta2011 reports 8.3 mm of sinkage
and 6.98 kPa maximum ground pressure for its 40 kg wheeled Titan rover on the
same lunar-proxy soil. The converged screw design here sits near 1.7 kPa at
several times the mass. That is the flotation argument for screws measured
against a real Titan concept rather than asserted, and `run_example.py` prints
the comparison.

**Two more screw failure modes worth stating.** villacres2023 records that the
MSA became immobilised in mud at 10 to 15 percent moisture content, with the
material sticking to the scrolls, on ground firm enough to carry its weight.
chen2025 records outright stall in saturated sand, where rolling beat screwing
by a factor of 27. Neither is modelled here, and both belong in the
limitations paragraph.

**Verification note.** Every value attributed to genta2011,
zimmerman_postHuygens, matthies2017, green2021 and sagara2025 was checked
against the paper text on this pass. All held.

## 4b. What is still a placeholder

| Placeholder | Where | How to remove it |
|---|---|---|
| drum and blade areal densities | `mers.py` | The dominant uncertainty, by a wide margin. green2021 gives a 3.4 kg four-screw vehicle but no screw geometry, so it cannot be inverted. Weigh a drum, or find one vehicle with both a mobility mass and drum dimensions. |
| soil-on-metal friction coefficient | `screw.py` | Calibrate against one measured torque and thrust pair. |
| Bekker parameters for the screw-specific terrain cases | `terrain.py` | `snow_msa` and `liquefied_soft` carry measured drawbar coefficients but assumed pressure-sinkage constants, because the trafficability reports give cone index, not Bekker constants. |
| Titan soil parameters | `terrain.py` | Nothing to replace them with yet. genta2011 substitutes lunar regolith and says so. The code labels the case `titan_lunar_proxy` and warns on every run that uses it. |
| c_rr for snow and liquefied ground | `terrain.py` | Not in the course table, assumed here. |
| duty cycle, payload power, drag coefficient, frontal area, CG height, motor nominal speed | `sizing_loop.py` | Mission choices, not physics. Set them deliberately and record why. |

**Two disagreements between sources, both left visible.** patel2005 gives a
drivetrain efficiency chain of about 0.47 overall, rimani_week4_mobility gives
0.7 to 0.85; `MassModel.drivetrain_efficiency_model` selects between them.
patel2005 adopts c_rr = 0.05 for Mars, the course table gives 0.15 to 0.25 for
very loose Mars soil; the value used is stated per terrain case.

**One discrepancy to resolve.** patel2005 Table 9, citing Wong, gives dry sand
as n = 1, k_c = 990, k_phi = 1.52e5. Wong's own printed set is usually quoted
as n = 1.1, k_c = 990, k_phi = 1.528e6, an order of magnitude stiffer in
k_phi. The Patel values are used here because that is the source in hand. The
choice changes sinkage substantially. Check the original table before quoting
either.

---

## 5. The database

`data/vehicles.csv` now holds 25 entries. Four columns do most of the work:

- **mass_definition**: `m_dry`, `m_wet`, `m_operational`, `m_cbe`, `m_gross`.
- **power_type**: `P_peak`, `P_continuous`, `P_average`, `P_installed`,
  `P_measured`, `P_bol`. Battery energy divided by endurance is an average
  draw, not a motor rating. 
- **evidence**: what kind of number each value is, per row, in words.
- **role_in_methodology**: mobility mass benchmark, screw traction validation,
  system-level Earth analogue, tracked validation baseline, Titan system
  comparator, rover subsystem fraction reference, qualitative architecture
  reference, physics and scaling reference, excluded from fit.

Plus **source_id**, which points into `sources.yaml`.

`data/benchmarks.csv` holds the scalar results worth checking a design
against: drawbar coefficients, cost of transport, bearing capacities, slip
values, reported model errors. `run_example.py` prints the comparison.

**A finding that came out of populating it.** The mobility mass fractions
that can actually be computed from documented data are:

```
screw    0.236  0.408  0.493       median 0.408
wheeled  0.150  0.308  0.470       median 0.308
```

The two ranges overlap. With this data you cannot claim that screw mobility
inherently costs a larger mass fraction than wheeled mobility. A wheeled Titan
rover concept sits at 0.150 (genta2011) and the ExoMars locomotion subsystem
sits at 0.470 (patel2005), so the spread within wheeled designs is as large as
the difference between architectures. Adding entries with a documented
mobility mass split is the highest-value database task there is.

**Working rule.** Every data point found while coding or reading goes into the
CSV, with its `source_id`, not only into a report or a code comment.

---

## 6. Validation, at two levels

**Level 0, priors.** Mobility mass fraction per architecture, with median and
range. Used to seed the loop and to bound the answer, never as the answer.

**Level B, mobility-block reconstruction.** The mobility mass and drive power
are hidden, the mobility block runs from the vehicle's recorded mass,
geometry, terrain and speed, and the prediction is compared. This deliberately
does not run the full mass-closure loop on a terrestrial vehicle, because
closing the loop needs a power-system model and a radioisotope source is the
wrong model for a diesel amphibian.

Right now exactly one row runs, and it is a synthetic demo row labelled as
such. Every real entry is missing screw geometry. That is the honest state of
the field: the geometry of the historical screw vehicles is in the original
test reports, not in the review literature. `validate.py` prints the missing
fields ranked by frequency, and the Marsh Screw Amphibian reports are the
highest-value target because they are the only source with documented test
conditions and a measured drawbar coefficient.

Earth validation validates the model structure and the workflow. It does not
validate Titan performance.

---

## 7. Two results worth checking first

**Flotation on Titan is close to free, and the design is driven by screw
efficiency and power system mass.** The baseline sinks about 2 mm and sits at
about 1.5 kPa contact pressure, against a lunar recommended design value of
1.4 kPa and an allowable of 8 kPa (wakabayashi2009). The power subsystem and
the running gear dominate the mass budget instead.

**Gravity does not simply cancel.** The classic remark is that gravity cancels
in the maximum slope expression, so low gravity buys flotation but not
gradeability. That holds for a purely frictional soil. It does not hold once
cohesion is in the traction ceiling, because the cohesive term c*A does not
scale with weight, so at low gravity it is a larger share of the total and the
maximum slope improves. `run_example.py` runs the same vehicle at Earth, Moon
and Titan gravity on two soils and shows both behaviours. On the cohesive
soft case the maximum slope roughly doubles from Earth to Titan. Whether that
survives on the real Titan surface depends entirely on a cohesion nobody has
measured, which is the point.

---

## 8. Where higher fidelity belongs

Not inside the loop.

| Level | Role | Method |
|---|---|---|
| 0 | Priors, feasibility, sensitivity | Database ratios, dimensional analysis, Earth test data |
| 1 | Inside the sizing loop | This package, plus the helical granular scaling laws |
| 2 | Calibration and correction of Level 1, selected cases only | DEM for granular terrain, CFD for wind and liquid |

For scale, villacres2023 reports what the better methods actually achieve:
helical granular scaling laws 3 to 9 percent on a lunar analogue soil,
granular scaling laws generally 9 to 36 percent, DEM against hardware 4.5 to
25 percent. This package is cruder than all three. Quote ranges, not points.

If a surrogate is added later, build it as a correction to the reduced-order
model rather than a replacement:

```
mu = mu_reduced + delta_mu_surrogate(W/A, lead, p/D, BH/D, s, g, terrain)
```

The helical granular scaling laws are the piece that makes gravity transfer
defensible at Level 1, and they are the thing to read before writing any
methodology section.

---

## 9. Files

```
sources.yaml            every source behind every number, by source_id
sizing/environment.py   Earth, Moon and Titan, each value with its source
sizing/terrain.py       terrain cases as parameter sets, with evidence flags
sizing/screw.py         reduced-order screw-terrain model and validity guards
sizing/mers.py          mass relations and subsystem fractions
sizing/sizing_loop.py   the fixed-point loop and the feasibility checks
run_example.py          baseline, cross-checks, gravity study, trade space
validate.py             Level 0 priors and Level B reconstruction
fit_mers.py             actuator mass relations from catalogue data
data/vehicles.csv       25 vehicles, with mass definitions and evidence
data/benchmarks.csv     scalar results from the literature to check against
data/actuators.csv      catalogue data for the actuator fit
REFERENCES.md           reading list, grouped by which block it supports
```
