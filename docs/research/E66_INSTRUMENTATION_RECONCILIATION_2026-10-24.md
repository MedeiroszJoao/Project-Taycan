# LG E66: primary instrumentation reconciliation

**Scope:** source-document audit, 2026-10-24, at repository baseline `e48f336`. No new MAT numeric payload was opened, no existing six-FIT simulation/decoding was repeated, and neither the two validation nor four blind module files were inspected. This note supplements the [six-FIT audit](../audits/STAGE4B_REAL_E66_MODULE_FIT_NUMERICAL_2026-10-24.md), preserving its source discrepancy.

## Primary evidence and provenance

Uwalaka, Yao, Duque and Kollmeyer (2024), *Fast Charging and Characterization Dataset for Porsche Taycan LG E66 Battery Cell and Module*, [Borealis V1](https://borealisdata.ca/dataset.xhtml?persistentId=doi%3A10.5683%2FSP3%2F7JP3NM), DOI `10.5683/SP3/7JP3NM`, published 2024-10-10, CC BY 4.0. The local uploaded outer ZIP has SHA-256 `d569bb98ec52ed6b0e151e3269154063dcc4b8a13ab05b30ac7bb3fa94cfd20b`. The authors' original PDF pages 1 and 3 were rendered and visually inspected, in addition to text extraction. Raw source documents remain outside the repository; this is an attributed analysis.

| Primary member | Bytes | SHA-256 |
|---|---:|---|
| `3-Taycan Module Instrumentation.pdf` | 236837 | `c7a21d62ba0330b2a741b53a327d809696605ce71cceda8acc886631716da146` |
| `0-Readme - Cell.txt` | 9192 | `2b700b53b45d531b5077fc08c2b22fdede20ed2e3fa5f83ea442335cec5a31f1` |
| `2-Readme - Module.txt` | 7416 | `bbeb81ea8033e0379c24e81f6708bbfbc0f8e0ee8eefd0102c9348fae39c359c` |

Machine-readable evidence: [`PRIMARY_EVIDENCE.json`](../../results/stage4b_instrumentation/PRIMARY_EVIDENCE.json). Source date/version is the dataset's published version, not an inferred vehicle production year.

## Topology conclusion

**VALIDAÇÃO EXTERNA — documentary support for the measured apparatus, not model accuracy.** Page 1, Figure 1 calls the photographed object a “6s2p Taycan module”; page 3 explicitly gives “Configuration: 6s2p” under module specifications. These are two explicit statements from the experiment authors and do not depend on inferring wiring from the numerical voltage ratio. The existing six-FIT ratio and current-scale results are consistent corroboration.

The Borealis landing-page description still says “6p2s”. Preserve both statements in provenance. The defensible interpretation for this specific laboratory module is **six series groups, two cells in parallel per group** based on the instrumentation document; a reversed abbreviation in the abstract is a likely transcription error, **HIPÓTESE NÃO VERIFICADA** until the authors issue a correction. The PDF includes apparatus photographs and thermal-position diagrams, not a complete electrical wiring schematic or an OEM pack/variant identification certificate. It supports freezing a *documented laboratory module mapping* with this discrepancy recorded. It does not independently identify the source vehicle as the target 2022 4S 79.2 kWh, certify every module's internals or validate the complete 168s2p pack.

The cell README describes a nominal **65 Ah** E66 cell; the module charge protocol defines 1C as **132 A**, i.e. a **132 Ah protocol reference**. These are distinct source conventions (65 versus approximately 66 Ah per parallel branch), not measured usable capacity estimates. Do not replace either with a fitted capacity or force their equality. In particular, multiplying nominal voltage, 132 Ah and target module count is dimensional bookkeeping, not observed pack energy.

## Current and time contracts

**DEMONSTRADO COMPUTACIONALMENTE / document inspection:** the module README specifies `RecordingTime` in seconds, AVL and Orion BMS currents in amperes, module/cell voltages in volts, accumulated charging/discharging counters in Ah and temperatures in °C. It describes current stages for MCCC charging: 1C starts at 132 A and subsequently steps through 66, 33, 16.5, 10 and 5 A. The quoted currents are protocol magnitudes.

**INCONCLUSIVO from documents alone:** neither README nor the instrumentation PDF explicitly defines which current-column sign represents charge. The six-FIT opposite correlations establish relative inversion, not absolute convention, gain, offset or time alignment. Before deriving energy or PyBaMM input, anchor polarity to the **already permitted FIT** MCCC charge segments and increasing charge counter, then compare `-I_AVL` against a positive-discharge convention and inspect the BMS counterpart. Check timestamps/lag and counter resets; publish any offset/gain/lag estimation as development calibration. Do not use blind outcomes to choose this mapping. A single `CellVoltage` with `CellID` indicates multiplexed identity; it must not be silently treated as six synchronous cell readings.

The README quotes AVL accuracy ±0.1%, but does not specify enough metrological detail here to turn that into a per-sample confidence interval: range dependence, full-scale-versus-reading interpretation, channel calibration, synchronization and correlation remain open. The chamber accuracy is ±1°C; chiller temperature accuracy ±0.25°C. These do not establish thermocouple measurement uncertainty or factory BMS accuracy.

## Thermal mapping and implications for F15–F17

**VALIDAÇÃO EXTERNA — sensor-placement evidence only:** page 1 lists nine additional thermocouples placed on cell 4, three beneath the module, three on the cooling plate and **two** positions corresponding to the stock module temperature sensors. The module README names the stock-position measurements `T1` and `T2`. The nine A1–E3 surface points sample one cell's face; they are not nine independent cells or nine factory channels. The figure-number reference in introductory text is imperfect (the top-placement diagram is Figure 7), so use the diagram labels and named sensor positions rather than assuming all captions cross-reference correctly.

The laboratory cooling boundary is a 30°C chamber, initially 30°C coolant, 50/50 water–glycol at **1.75 L/min total**, split between two external parallel cooling plates. It is not an OEM vehicle coolant-flow measurement. Actual recorded inlet temperature, not merely the nominal chiller setpoint, is the relevant numerical boundary when comparing a thermal model.

**HIPÓTESE NÃO VERIFICADA:** the synthetic requirement of three temperatures per each of 28 modules is not supported by this apparatus document. Two stock positions plus laboratory instrumentation cannot be substituted for the historical three-per-module contract. F15–F17 portability remains conditional on a new declared mapping or explicit missingness; the existing strict masks must not be suppressed to manufacture availability. A within-cell laboratory temperature gradient and a module/pack thermal spread measure different spatial quantities.

## Gates and limited disposition

| Question | Disposition |
|---|---|
| Is 6s2p documented independently of observed voltage? | **PASS**, explicitly in original apparatus PDF pages 1 and 3 |
| Has the conflicting web abstract been corrected by its authors? | **INCONCLUSIVO**, discrepancy retained |
| Is this target 2022 4S 79.2 kWh pack identity established? | **INCONCLUSIVO** |
| Are units documented? | **PASS**, with field/multiplexing caveats |
| Are absolute current polarity, calibration and synchronization certified by source text? | **INCONCLUSIVO**, resolve empirically on FIT only |
| Are three factory temperature sensors per module supported? | **FAIL** as a claim from this source; it documents two positions |
| Were validation/blind numeric payloads consumed by this audit? | **NO**, zero |

The immediate technical action is to use this documented 6s2p laboratory mapping in a prospective cell-to-module comparison, while resolving current polarity and acquisition alignment on the six existing FIT files. No numerical topology reanalysis or unbounded search for another wiring certificate is necessary for that limited research mapping.
