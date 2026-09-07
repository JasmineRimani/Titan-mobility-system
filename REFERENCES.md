# Reading list

Grouped by which block of the method each source supports.
`sources.yaml` is the machine-readable index and says exactly which number in
the code comes from which paper. This file is the human reading order.

Entries marked **in the shared set** are the PDFs distributed with this
package. Entries marked **to obtain** are not, and are worth chasing.

---

## Read first, in this order

1. **Villacrés, Barczyk, Lipsett, "Literature review on Archimedean screw
   propulsion for off-road vehicles", J. Terramechanics 108 (2023) 47-57.**
   *in the shared set* (`villacres2023`)
   The state of the art in one place: Cole's 1961 analytical model, the
   Bekker/Nagaoka adaptation and its validity limit, every reported drawbar
   and slip figure, and the central conclusion that no experimentally
   validated cross-terrain dynamic model exists. Mine its reference list.

2. **Genta and Genta, "Preliminary assessment of a small robotic rover for
   Titan exploration", Acta Astronautica 68 (2011) 556-566.**
   *in the shared set* (`genta2011`)
   The mission-level backbone: Titan gravity and temperature, RTG options,
   40 kg rover with a 6 kg mobility subsystem, 100 m/h, 20 degree grade,
   100 mm obstacle, and the explicit admission that Titan soil parameters are
   unknown and lunar values are being substituted.

3. **Patel, "An investigation into optimal mobility system for planetary
   rovers", PhD thesis, Surrey Space Centre, 2005.**
   *in the shared set* (`patel2005`)
   The richest single source for mass fractions and terramechanics together:
   chassis fraction K from 0.3 to 0.5, the full ExoMars TN4 subsystem mass
   budget, the Bekker equation set, soil parameter tables for Mars, the Moon
   and terrestrial soils, ground pressure limits, and design rules.

4. **Thoesen et al., "Granular scaling laws for helically driven dynamics",
   Physical Review E 102, 032902 (2020), and the gravity-variant version,
   "Helically-driven granular mobility and gravity-variant scaling
   relations" (2022).**
   *to obtain*
   The bridge from Earth test data to Titan gravity, and the only screw model
   in the literature with a reported accuracy in the single digits (3 to 9
   percent on a lunar analogue soil). Read before writing any methodology
   section.
   https://link.aps.org/pdf/10.1103/PhysRevE.102.032902 and
   https://pmc.ncbi.nlm.nih.gov/articles/PMC9063715

---

## Screw propulsion

- **Richter et al., "ARCSnake", IEEE T-RO 38(2), 2022, 797-809.**
  *in the shared set* (`richter2022`)
  Reference screw geometry, 128 mm drum and 150 mm outer diameter, 22 degree
  lead angle, 2 starts, and the clearest statement of the hard-ground failure
  mode.
- **Chen et al., "Characterization and evaluation of screw-based locomotion
  across aquatic, granular and transitional media", arXiv:2511.11958 (2025).**
  *in the shared set* (`chen2025`)
  A clean parametric test matrix, the aspect ratio and tip speed metrics used
  in `screw.py`, and the lateral-displacement and saturated-sand stall failure
  modes.
- **Green, McBryan, Mick, Nelson, Marvi, "Regolith excavation performance of a
  screw-propelled vehicle", Advanced Intelligent Systems, 2021 (CASPER).**
  *in the shared set* (`green2021`)
  A 3.4 kg four-screw vehicle under 30 W, with cost of transport and
  excavation transport rate defined as metrics. Screw geometry is not
  reported, which is why CASPER cannot be used for end-to-end validation.
- **Sagara, Fujiwara, Iizuka, Aerospace 12 (2025) 699.**
  *in the shared set* (`sagara2025`)
  Complete Bekker / Wong-Reece / Janosi-Hanamoto equation set as used for
  sizing, full screw-wheel geometry, silica sand properties, and quantified
  sideslip on a 20 degree slope.
- **US Army Waterways Experiment Station, Marsh Screw Amphibian
  trafficability reports, TR 3-641 and companions.**
  *to obtain* (`wes_tr3641`)
  The only source with documented test conditions and a measured drawbar
  coefficient, 0.64 of vehicle weight in very soft ground. The single highest
  value item on the reading list for filling the database.
  https://apps.dtic.mil/sti/pdfs/AD0646274.pdf and
  https://apps.dtic.mil/sti/pdfs/AD0694057.pdf
- **Osinski and Szykiedans, "Small remotely operated screw-propelled
  vehicle", Springer, 2015.** *to obtain* (`osinski2015`)
  The smallest entry in the database with a documented mobility mass split.
- **Nagaoka, Kubota et al., "Development of lunar exploration rover using
  screw propulsion units".** *to obtain*
  The closest existing planetary application, and the origin of the
  Bekker-derived scroll model that villacres2023 reviews.

## Terramechanics and rover sizing

- **Ellery, "Environment-robot interaction: the basis for mobility in
  planetary micro-rovers", RAS 51 (2005) 29-39.**
  *in the shared set* (`ellery2005`)
  Science payload 5 to 15 percent of rover mass, the same Bekker formulation
  as Patel with lunar values, obstacle climbing by architecture.
- **Wakabayashi, Sato, Nishida, "Design and mobility evaluation of tracked
  lunar vehicle", J. Terramechanics 46 (2009) 105-114.**
  *in the shared set* (`wakabayashi2009`)
  The tracked validation baseline. Lunar bearing capacity 8 kPa allowable and
  1.4 kPa recommended, optimum crawler contact pressure about 1.96 kPa, slip
  0.1 to 0.2 on a 20 degree slope against about 0.6 for a rigid wheel.
- **Mateo Sanguino, "50 years of rovers for planetary exploration", RAS 94
  (2017) 172-185.** *in the shared set* (`mateosanguino2017`)
  Mass, size, wheel count and speed for about 100 vehicles. Use its Table 1,
  not the histograms, for rover priors: the histogram sample mixes terrestrial
  and planetary robots.
- **Wong, Theory of Ground Vehicles, 5th ed.** *to obtain*
  The reference behind Patel's soil tables. Needed to settle the dry sand
  k_phi discrepancy documented in `terrain.py`.
- **NASA, Terramechanics for LTV modelling and simulation (white paper).**
  *to obtain*
  Which terramechanics models are validated, at what fidelity, for what
  purpose. Useful for justifying the fidelity hierarchy.
  https://ntrs.nasa.gov/api/citations/20220010732/downloads/Terramechanics_white_paper.pdf

## Titan mission context

- **Zimmerman, Lunine, Lorenz, "A post-Huygens Titan surface science mission
  design", IEEE Aerospace.** *in the shared set* (`zimmerman_postHuygens`)
  The delivered mass chain, 5028 kg launch to 100 kg of science payload with
  about 30 percent margin, plus surface pressure, temperature and the comms
  budget.
- **Matthies, "Titan Aerial Daughtercraft", NIAC Phase 1 final report, NTRS
  20170001998.** *in the shared set* (`matthies2017`)
  Near-surface wind about 1 m/s, atmospheric density about 5 times Earth,
  100 Wh/kg battery, 20 percent structure fraction, and the landing error
  ellipse.
- **Committee on Planetary and Lunar Exploration, "Scientific rationale for
  mobility in planetary environments", NRC, NTRS 20000025059.**
  *in the shared set* (`nrc_mobility`)
  Science justification for surface mobility. Material for the introduction
  and the requirements section.
- **Schilling and Jungius, "Mobile robots for planetary exploration", Control
  Engineering Practice 4(4), 1996.** *in the shared set* (`schilling1996`)
  Historical and design-constraint context.
- **A rideshare tensegrity rover concept to explore Titan's lands and
  oceans, NASA TM-20220014544.** *to obtain* (`tandem_tm2022`)
  Source of the 344 kg delivered-mass reference and the 12 kg science
  payload. Mission-scale comparator only.
- **Advanced radioisotope power system enabled Titan rover concept with
  inflatable wheels, NTRS 20100001596.** *to obtain* (`arps_titan_rover`)
  Four 1.5 m inflatable wheels, about 110 We at beginning of life.
- **Titan-GRAM, NASA MFS-32297-1.** *to obtain*
  Engineering estimates of Titan density, temperature, pressure and winds.
  Replace the calculated atmospheric density in `environment.py` with a
  Titan-GRAM value for the actual latitude, season and altitude.
  https://software.nasa.gov/software/MFS-32297-1
- **Huygens SSP penetrometry**, "Penetrometry of granular and moist planetary
  surface materials: application to the Huygens landing site on Titan",
  Icarus (2010), and "Titan surface mechanical properties from the SSP ACC-I
  record". *to obtain*
  The only in-situ mechanical measurement of a Titan surface. Everything else
  is inference, including the lunar proxy this package currently uses.
  https://www.sciencedirect.com/science/article/abs/pii/S0019103510002915

## Only if a surrogate is added

- Forrester, Sóbester, Keane, *Engineering Design via Surrogate Modelling*,
  Wiley, 2008.
- Rasmussen and Williams, *Gaussian Processes for Machine Learning*, MIT
  Press, 2006. Free online.
