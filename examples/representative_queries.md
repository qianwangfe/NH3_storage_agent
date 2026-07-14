# Representative queries

## 1. Material-family state diversity

```text
Using the NH3 Storage dataset, compare the raw counts of solid, mixed/transition, and liquid records across material families. Highlight borohydrides and return the figure and supporting CSV files.
```

Expected route: `nh3_storage -> state_complexity`

## 2. LiBH4 state sequence

```text
Trace the reported state sequence of LiBH4·xNH3 from x = 1 to 3. List the composition, reported state, conditions, evidence type, confidence, and DOI. Determine whether the literature supports a solid–liquid-like–solid sequence.
```

Expected route: `nh3_storage -> state_sequence_lookup`

## 3. Conductivity versus loading

```text
Using DigBat, plot ionic conductivity against NH3/BH4 ratio for LiBH4 near 305 ± 3 K and Mg(BH4)2 near 323 ± 3 K. Use one representative value per formula and DOI, aggregate multiple DOI in log10 conductivity space, and export the plotting data.
```

Expected route: `digbat -> conductivity_loading`

## 4. Hydrogen release versus loading

```text
Using DigHyd, compare reported H2 release across ammoniated borohydrides with NH3/BH4 > 0. Retain the host borohydride, loading, temperature, conditions, and DOI. Do not connect non-comparable studies.
```

Expected route: `dighyd -> h2_release_loading`

## 5. Evidence-to-hypothesis map

Run queries 1–4 in the same session, then ask:

```text
Based on the previous state, conductivity, and H2-release evidence, compare NH3 stoichiometry alone, cation effects, and coordination-shell reconstruction. Separate direct evidence, indirect evidence, and hypotheses, and generate an evidence-to-hypothesis map.
```

Expected route: `session evidence -> mechanism_synthesis`

## 6. Computational validation

```text
Design a USPEX, molecular-dynamics, and metadynamics workflow to test whether coordination-shell switching explains LiBH4·NH3, LiBH4·2NH3, and LiBH4·3NH3. Specify collective variables, descriptors, expected observations, uncertainty checks, and falsification criteria.
```

Expected route: `session evidence -> computational_design`
