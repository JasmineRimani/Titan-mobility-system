# Where each part of the paper lives in the code

The paper:

> A. Lukianov and J. Rimani, "Preliminary Design and Performance Assessment of
> Screw-propelled Vehicle", 77th International Astronautical Congress (IAC),
> Antalya, Turkiye, 5-9 October 2026, IAC-26,A3,IP,204,x115954.

Every number in the paper is printed by one of the scripts below, and
`tests/test_paper_numbers.py` checks the headline ones on every run. If a
number in the paper cannot be found in the output, that is a bug.

```bash
python run_example.py       # Tables 8 and 9, Sections 5.1 to 5.5, Figs. 1 to 4 in numbers
python validate.py          # Tables 10 and 11 (Section 4.5), database fractions
python make_paper_tables.py # Tables 3 and 4, database census and fractions (LaTeX in outputs/)
python make_figures.py      # Figs. 1 to 5, PDF and PNG in figures/
```

---

## Figures

| Paper | File | Script | Numbers printed by |
|---|---|---|---|
| Fig. 1, one-at-a-time sensitivity of the converged mass | `figures/fig1_sensitivity` | `make_figures.py` | `run_example.py`, block SENSITIVITY |
| Fig. 2, converged mass against drum shell areal density | `figures/fig2_closure_limit` | `make_figures.py` | `run_example.py`, block DRUM SHELL AS A REQUIREMENT |
| Fig. 3, available over required thrust on every terrain case | `figures/fig3_drawbar_margin` | `make_figures.py` | `run_example.py`, block TERRAIN SENSITIVITY, column `margin` |
| Fig. 4, thrust ratio against the screw traction efficiency kappa | `figures/fig4_traction_calibration` | `make_figures.py` | `run_example.py`, block TRACTION CALIBRATION |
| Fig. 5, feasibility box | `figures/fig5_feasibility_box` | `make_figures.py` | `make_figures.py` itself |

`python make_figures.py OUTDIR` also copies the five figures into `OUTDIR`,
for example the folder of a LaTeX manuscript. Each figure is sized to the
column width (3.08 in) or the text width (6.28 in) of the IAC template, so it
is placed at 100 % scale.

## Tables

| Paper | What it is | Where it comes from |
|---|---|---|
| Table 1 | Nominal environmental inputs | `sizing/environment.py`, `TITAN` |
| Table 2 | Adopted terrain inputs | `sizing/terrain.py`, `TITAN_LUNAR_PROXY` |
| Table 3 | Inventory of the vehicle database by architecture | `make_paper_tables.py`, printed; data in `data/vehicles.csv` |
| Table 4 | Completeness of the database | `make_paper_tables.py`, printed |
| Table 5 | Coefficients of the sizing model | `sizing/mers.py` (`MassModel`), `sizing/screw.py` (`ScrewGeometry.soil_metal_friction`, `traction_efficiency`) |
| Table 6 | Preliminary design screens | `sizing/sizing_loop.py` (`Mission`, checks at the end of `size`) |
| Table 7 | Baseline geometry and operating assumptions | defaults of `ScrewGeometry` and `Mission` |
| Table 8 | Converged baseline mass and power budget | `run_example.py`, blocks MASS and POWER; also `outputs/baseline_breakdown.csv` |
| Table 9 | Baseline performance and screening outcome | `run_example.py`, blocks PERFORMANCE and FEASIBILITY |
| Table 10 | Screw-terrain block against the Marsh Screw Amphibian | `validate.py`, LEVEL A |
| Table 11 | Closure loop applied to the MSA requirements | `validate.py`, LEVEL C |

Numbers quoted in the text of Section 5:

| Section | Numbers | Printed by |
|---|---|---|
| 4.2 | 24 records, field completeness | `make_paper_tables.py` |
| 4.4 | six iterations, 445 Wh/km, about 360 m per Earth day | `run_example.py` baseline |
| 4.4 | mobility mass fraction 0.40 against screw 0.16 to 0.49 and wheeled 0.15 to 0.47 | `run_example.py` CROSS-CHECK, `validate.py` LEVEL 0 |
| 5.1 | 201 to 485 kg over the drum areal density range | `run_example.py` SENSITIVITY |
| 5.1 | closure limit 14.3 kg/m2 | `run_example.py` DRUM SHELL |
| 5.2 | 7.4, 2.2 and 1.9 mm, 6.1, 1.8 and 1.6 kPa under Earth, lunar and Titan gravity; 7.0 kPa for the Genta rover | `run_example.py` GRAVITY STUDY and CROSS-CHECK |
| 5.3 | margins 1.59 and 0.86, equilibrium slip 3.6 %, 39 and 16 deg | `run_example.py` TRACTION CALIBRATION |
| 5.4 | available traction coefficient 0.93, 1.12 and 1.15; about 2 deg on wet clay | `run_example.py` GRAVITY STUDY, both terrains |
| 5.5 | feasible region of the feasibility box | `make_figures.py`, Fig. 5 |

## Equations

"Paper Eq. (n)" in the docstrings and comments of `sizing/` refers to these.

| Paper | Quantity | Python |
|---|---|---|
| Eq. (1) | mobility and payload mass fractions | `size()` result `mobility_mass_fraction`; `validate.py` LEVEL 0; `make_paper_tables.fractions` |
| Eq. (2) | outer and mean diameter, lead angle | `ScrewGeometry.outer_diameter`, `.mean_diameter`, `.helix_angle` |
| Eq. (3) | power-screw efficiency | `ScrewGeometry.screw_efficiency` |
| Eq. (4) | equivalent-cylinder contact width | `screw.contact_width` |
| Eq. (5) | equilibrium sinkage | `screw.sinkage` |
| Eq. (6) | Bekker compaction resistance | `screw.compaction_resistance`; `R_r = c_rr W` in `screw.rolling_resistance`; the larger of the two is taken in `sizing_loop.size` |
| Eq. (7) | aerodynamic drag | `sizing_loop.size` |
| Eq. (8) | required propulsive force | `sizing_loop.size` |
| Eq. (9) | available thrust, uncorrected | `screw.coulomb_ceiling` times `screw.slip_mobilisation` |
| Eq. (10) | available thrust with kappa and a measured drawbar cap | `screw.drawbar_available`; equilibrium slip in `screw.equilibrium_slip` |
| Eq. (11) | ideal advance speed and screw angular velocity | `screw.kinematics` |
| Eq. (12) | screw torque and electrical drive power | `screw.torque_and_power`, `sizing_loop.size` |
| Eq. (13) | reduction ratio and motor torque | `sizing_loop.size`, `mers.required_motor_torque` |
| Eq. (14) | running-gear mass | `mers.running_gear_mass` |
| Eq. (15) | power source and battery mass | `mers.eps_mass` |
| Eq. (16) | dry and total mass, closure | `sizing_loop.size` |
| Eq. (17) | drum displacement and volume to float | `screw.displaced_volume`, `screw.flotation_vol` |

## References

The paper's reference list against the `source_id` used in the code and the
data. Sources marked "context" are cited in the paper for background and do
not supply a number to the code.

| Paper | Reference | source_id |
|---|---|---|
| [1] | Stevens, The first steam screw propeller boats, 1893 | context |
| [2] | Villacres, Barczyk, Lipsett, J. Terramechanics 108, 2023 | `villacres2023` |
| [3] | US Army WES, Technical Report 3-641, 1964 (Marsh Screw Amphibian) | `wes_tr3641` |
| [4] | Osinski and Szykiedans, Springer, 2015 | `osinski2015` |
| [5] | Knight, Rush, Stinson, J. Terramechanics 2(4), 1965 | context |
| [6] | Neumeyer and Jones, J. Terramechanics 2(4), 1965 | context |
| [7] | Thoesen, Ramirez, Marvi, ICRA 2018 | context |
| [8] | Thoesen et al., Physical Review E 102, 2020 | context, accuracy figures taken through `villacres2023` |
| [9] | Chen et al., arXiv:2511.11958, 2025 | `chen2025` |
| [10] | Sagara, Fujiwara, Iizuka, Aerospace 12, 2025 | `sagara2025` |
| [11] | Green et al., Advanced Intelligent Systems, 2021 (CASPER) | `green2021` |
| [12] | Richter et al., IEEE T-RO 38(2), 2022 (ARCSnake) | `richter2022` |
| [13] | Genta and Genta, Acta Astronautica 68, 2011 | `genta2011` |
| [14] | Matthies, NIAC Titan Aerial Daughtercraft, 2017 | `matthies2017` |
| [15] | Deitrich et al., NASA TM-20220014544, 2022 (TANDEM) | `tandem_tm2022` |
| [16] | Atkinson et al., Icarus 210, 2010 (Huygens penetrometry) | context |
| [17] | Nixon et al., Planetary and Space Science 155, 2018 | context |
| [18] | Lorenz, JBIS 61, 2008 (Titan Bumblebee) | context |
| [19] | Rodriguez et al., Experimental Astronomy 54, 2022 (POSEIDON) | context |
| [20] | Li and Bingham, NASA terramechanics white paper, 2022 | cited in the paper (Table 2) for k_c, k_phi, n and K of the lunar-proxy soil; the code records the same k_c, k_phi and n under `genta2011` |
| [21] | Patel, PhD thesis, University of Surrey, 2005 | `patel2005` |
| [22] | Wakabayashi, Sato, Nishida, J. Terramechanics 46, 2009 | `wakabayashi2009` |

Sources in `sources.yaml` that are not in the paper's reference list, but do
supply values to the code: `zimmerman_postHuygens`, `ellery2005`,
`mateosanguino2017`, `arps_titan_rover`, `copperstone_helix`,
`rimani_week4_mobility` (course notes, not public), and the `user_db_*`
entries transcribed from the authors' working spreadsheet. `sources.yaml`
says what each one supplies.
