# Model notes

The working notes behind the method: what each model does, where each number
comes from, what is still a placeholder, and what changed on the way to the
paper. They are the detailed companion to the IAC-26 paper and to the
top-level README. Section numbers are kept from the original README so that
references in the code still resolve. Every number here is printed by
`run_example.py` or `validate.py`; `docs/PAPER_MAP.md` says where each part of
the paper lives in the code.

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
| Delivered mass benchmark | 213 kg growth-predicted lander mass, used as the screen; 344 kg predicted total including a 131 kg aeroshell, for reference | tandem_tm2022 |
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
screens against the 213 kg lander-only figure, reports 344 kg alongside it,
and says where both came from. What none of these papers
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
where the terrain case has one. Three such measurements exist: 0.24 of test
weight on sand and 0.107 on wet clay for the full-scale MSA (wes_tr3641,
p. 21 and p. 42-43) and 0.54 in snow for the 1/5 scale model
(villacres2023). An earlier version of this package carried 0.64 for the
MSA; that figure is not in the report and was removed (see section 10).

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
2, mobility fraction between 0.15 and 0.60, obstacle capability against
the 100 mm requirement using h_max about 0.5 D, and static flotation in
liquid methane. The obstacle one is an analogy from wheels, and whether a
screw drum climbs like a wheel of the same diameter is not established
anywhere in `sources.yaml`.

**Flotation.** The volume displaced by the drums is compared against
`m_total / rho_liquid`, with rho_liquid = 423 kg/m3 for liquid methane
(genta2011). Gravity cancels out of Archimedes, so the requirement is a
mass, not a weight, and the number is the same as it would be on Earth for
the same liquid. Only the drum cylinders are counted, not the blades and
not any hull above them, which makes the screen a conservative floor on
buoyancy: passing means the vehicle floats on drums alone, failing means
the question is open rather than settled. Freeboard, trim, stability in
waves and the drag of driving a screw through liquid are all outside it,
and all of them matter before anyone calls this vehicle amphibious. The
baseline clears the screen with about 12 percent margin, 0.52 m3 displaced
against 0.47 m3 required.

**Validity, stated plainly.** villacres2023 is explicit that Bekker-derived
scroll models hold only while sinkage stays below the flight height, that is
while the screw runs on top of the soil rather than swimming in it. Soft mud
and snow, exactly where screws beat everything else, are outside that range.
The code checks this on every run and says so in the output rather than
extrapolating quietly.

**Not modelled.** Lateral drift and side slip, which chen2025 and sagara2025
both measure and which is a known screw weakness. The switch to wheel-like
rolling on hard ground, which richter2022 calls screw slippage. Everything
about a liquid crossing beyond the static flotation screen above, in
particular hydrodynamic drag, thrust in liquid and stability. Dynamic sinkage,
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
fitted, checked or defended. The former `fit_mers.py` paper utility reported
which rows were missing which half; that script is no longer included.

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
| drum areal density | 12.6 to 53.1 kg/m2 | 144 % |
| blade areal density | 14.6 to 29.1 kg/m2 | 10 % |
| drive duty cycle | 0.05 to 0.40 | 6 % |
| power source | MMRTG to SNAP-19, 2.44 to 3.14 W/kg | 5 % |
| **drive module mass** | **0.5 to 2.0 kg** | **2.5 %** |
| soil-on-metal friction | 0.4 to 0.8 | 2.5 % |
| drivetrain efficiency | 0.47 to 0.78 | 1.6 % |
| design slip | 0.10 to 0.40 | 1.6 % |
| rolling resistance c_rr | 0.10 to 0.25 | 1.4 % |

On a screw vehicle the running gear carries the mobility mass and the
actuators do not. Across its evidence range the drum areal density moves
the answer more than fifty times further than the whole 0.5 to 2 kg module
bracket. This is Fig. 1 of the paper. So the thing to go
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
lander-only mass benchmark               213 kg   [tandem_tm2022]
closure limit, this geometry            14.3 kg/m2
micro-rover wheel evidence range        12.6 to 53.1 kg/m2   [patel2005]
```

Six of the seven real wheels are above that limit; only the Crab wheel, at
12.6, is below it, next to the ARCSnake screw module at 12.7 (Fig. 2 of the
paper). The wheels are 10 to 14 cm parts hollowed from aluminium billet and
a 0.55 m drum is a thin rolled shell on ribs, so this is an upper bound rather than a contradiction.
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
the 0.15 taken from the rimani_week4_mobility terrain table for the Titan
proxy case.

**A quantified flotation comparison.** genta2011 reports 8.3 mm of sinkage
and 6.98 kPa maximum ground pressure for its 40 kg wheeled Titan rover on the
same lunar-proxy soil. The converged screw design here sits near 1.6 kPa at
about five times the mass. That is the flotation argument for screws measured
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

`data/vehicles.csv` holds 25 rows: 24 vehicles and concepts, which are
the database of the paper, and one synthetic row labelled as such. Four columns do most of the work:

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
screw    0.164  0.236  0.408  0.493       median 0.322
wheeled  0.150  0.308  0.470              median 0.308
```

with the synthetic row excluded. The screw entries are ARCSnake, the Osinski
vehicle, the Auger Driven Ice Surveyor and CSUB.

The two ranges overlap. With this data you cannot claim that screw mobility
inherently costs a larger mass fraction than wheeled mobility. A wheeled Titan
rover concept sits at 0.150 (genta2011) and the ExoMars locomotion subsystem
sits at 0.470 (patel2005), so the spread within wheeled designs is as large as
the difference between architectures. Adding entries with a documented
mobility mass split is the highest-value database task there is.

**Working rule.** Every data point found while coding or reading goes into the
CSV, with its `source_id`, not only into a report or a code comment.


---

## 6. Validation, at four levels

**Level 0, priors.** `validate.py` reads the database and prints the
mobility mass fraction of every vehicle that has one, by architecture: screw
0.16 to 0.49, wheeled 0.15 to 0.47. The ranges overlap, so the database
cannot be used to say that screws cost more mass than wheels. These numbers
seed the loop and bound the answer, never replace it.

**Level A, the screw-terrain block against the Marsh Screw Amphibian.** The
block runs at the MSA geometry and test weights and is compared with the WES
report (DTIC AD0450621): ground pressure within 16 percent, static sinkage 4
to 13 times smaller than the rut a rotating screw cuts in sand, and a
Mohr-Coulomb ceiling 1.5 to 3 times the measured drawbar pull. The last gap
is the screw traction efficiency kappa, about 0.35 from the towing test and
0.61 to 0.70 from the slope tests (section 10). This is Table 10 of the
paper.

**Level C, the closure loop against the Marsh Screw Amphibian.** The whole
loop designs a new vehicle to the MSA requirements (496 kg payload,
0.72 m/s, an 18 degree sand slope) with the MSA rotor and an engine-driven
mass model whose coefficients are all assumed. It converges at 1170 kg
loaded against the 1794 kg vehicle that was built, because a rover
structural fraction does not describe a welded aluminium hull with a cab.
The drum-only flotation screen passes with margin 1.9, as it must for a
vehicle that ran at 8 mph on water, and the traction screen says the
vehicle climbs the 18 degree slope at kappa = 0.65 and not at kappa = 0.35,
which is the evidence that the towing figure was power limited and that the
slope-derived kappa is the one to carry. This is Table 11 of the paper.

**Level B, mobility-block reconstruction at known vehicle mass.** The
mobility mass and drive power of a database vehicle are hidden and predicted
from its recorded mass, geometry, terrain and speed. This deliberately does
not run the full closure loop on a terrestrial vehicle, because closing the
loop needs a power-system model and a radioisotope source is the wrong model
for a diesel amphibian. No real entry has both a documented mobility mass
and its screw geometry, so this path still runs only on the synthetic row.
That is the honest state of the field: the geometry of the historical screw
vehicles is in the original test reports, not in the review literature.
`validate.py` prints the missing fields ranked by frequency, and that list
is the database work plan.

Earth validation validates the model structure and the workflow and shows
where the model is optimistic. It does not validate Titan performance.

---

## 7. Two results worth checking first

**Flotation on Titan is close to free; the running gear carries the mass
and the slope carries the risk.** The baseline sinks about 2 mm and sits at
about 1.6 kPa contact pressure, against a lunar recommended design value of
1.4 kPa and an allowable of 8 kPa (wakabayashi2009). The running gear, 38
percent of the total, dominates the mass budget, and traction on the 20
degree design slope is where the terrain uncertainty bites (section 10).

**Gravity does not simply cancel.** The classic remark is that gravity cancels
in the maximum slope expression, so low gravity buys flotation but not
gradeability. That holds for a purely frictional soil. It does not hold once
cohesion is in the traction ceiling, because the cohesive term c*A does not
scale with weight, so at low gravity it is a larger share of the total and the
maximum slope improves. `run_example.py` runs the same vehicle at Earth, Moon
and Titan gravity on two soils and shows both behaviours. On the lunar-proxy
soil the available traction coefficient rises from 0.93 under Earth gravity
to 1.15 under Titan gravity; on the wet-clay case, where a measured drawbar
cap applies, it does not move and the slope stays at about 2 degrees.
Whether the cohesion effect survives on the real Titan surface depends
entirely on a cohesion nobody has measured, which is the point.

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

## 10. Development record, 25 September 2026

**Mass screen moved to the lander-only benchmark.** The paper adopts the
213 kg growth-predicted lander mass from tandem_tm2022, not the 344 kg
total that includes a 131 kg aeroshell. `Mission.delivered_mass_cap` is now
213 and `Mission.system_mass_cap` carries 344 for reference; both appear
on the trade-space figures. The previous baseline geometry (0.60 / 0.10 /
1.20 / 0.45) closed at 235 kg and failed the new screen, so the default
`ScrewGeometry` was re-based to 0.55 / 0.08 / 1.10 / 0.45, the smallest
geometry in the sweep that passes every screen including drum-only
flotation. It closes at 197 kg. The numbers in sections 2 to 7 of these
notes have been updated to this baseline; `python run_example.py` prints the
current ones.

**The Marsh Screw Amphibian is now a real validation case.** The WES
report (DTIC AD0450621) gives the rotor geometry, test weights, ground
pressures, ruts, towing forces and slope results, all now in
`data/vehicles.csv`, `data/benchmarks.csv` and `sources.yaml` with page
references. `validate.py` Level A compares the screw-terrain block with
them: contact pressure within 16 percent, static sinkage a factor of 4 to
13 below the first-pass rut on sand, and a Mohr-Coulomb traction ceiling
1.5 to 3 times the measured drawbar pull.

**Screw traction efficiency.** That last gap is now a parameter,
`ScrewGeometry.traction_efficiency` (kappa), multiplying the Mohr-Coulomb
ceiling. Calibrated on the MSA it is about 0.35 from the towing test and
0.61 to 0.70 from the slope tests. `run_example.py` carries 1.0, 0.65 and
0.35 into the Titan case: the 20 degree drawbar margin goes 2.45, 1.59,
0.86. Fig. 4 of the paper shows the sweep. Mass does not move, because thrust is
sized from the requirement.

**A database error corrected.** The drawbar coefficient of 0.64 attributed
to wes_tr3641 could not be found in the report and was most likely a
misreading of test number 64D. It has been replaced everywhere by the
report's own 0.24 (sand) and 0.107 (wet clay). The MSA masses were also
replaced by the report's 2860 lb empty and 3954 lb loaded. The report
numbers came through a text extraction of the DTIC scan; check pages 4,
5, 18, 20, 21 and 42 to 43 against the PDF before relying on them further.

**Equilibrium slip.** `sizing/screw.py` now solves the slip at which
available thrust equals required thrust; the loop reports it as
`equilibrium_slip` (or -1 when traction limited). Power is still sized at
the conservative design slip, and the paper says so.

**Two mission-level numbers.** The loop reports drive energy per kilometre
and the traverse per Earth day at the assumed duty cycle (445 Wh/km and
about 360 m/day for the baseline).

**Level C validation.** `validate.py` now also designs a
new vehicle to the Marsh Screw Amphibian requirements through the whole
closure loop, with the MSA rotor and an engine-driven mass model whose
coefficients are all assumed: 1170 kg converged against 1794 kg built,
flotation margin 1.9 for a vehicle that floated, and the 18 deg slope
climbed at kappa = 0.65 but not at 0.35.

**Slope convention.** The gravity study and the traction calibration now
use the loop's own force balance, F_av >= W sin(theta) + R, for the
largest slope held, instead of two different conventions. The wet-clay
case's assumed c_rr was lowered from 0.25 to 0.05, because the report
says free water and low friction are what let the MSA move on it.

**Figures for the paper (evening update).** `make_figures.py` was rewritten so
that no text sits inside a plot area: reference lines and markers are named in
a legend below the axes, bar values are on a secondary axis, and titles are
left to the captions. Each figure is resized until its tight bounding box is
exactly one column (3.08 in) or the full text width (6.28 in) of the IAC
template, so it is placed at 100 % scale. `python make_figures.py OUTDIR`
also copies the figures into OUTDIR (the paper folder). The feasibility sweep
now scales blade height, length and lead in the baseline proportions, so it
passes through the baseline design; under 213 kg the 0.55 m drum passes up to
20 kg of payload. The figure files are numbered as in the paper
(`fig1_sensitivity` is Fig. 1, and so on).

The paper-production scripts were subsequently removed. The figure files
remain in `figures/`; current CI checks their underlying numerical results
and the optional trade-space plot from `run_example.py`.
