# TUM dataset ZIP — byte-level intake (2026-10-23)

**Status:** External source archive available and verified at the file-integrity level only. No calibration, fitting, quantitative signal validation or test-set performance evaluation performed.

- Local supplied file: `m1774217_001.zip`, 427,200,572 bytes.
- Container ZIP SHA-256: `b95969e312a371c95e6d3f9796f2c18c17225f4a84874888c2798187756f16e4`.
- Inside: 92 `realdriving_data_publication/realdriving_*.csv` recordings and a `checksum.sha512` manifest.
- **92/92 SHA-512 checks passed** against the manifest included in the archive, verifying decompressed contents (which also checks their ZIP CRCs as read by Python's `zipfile`).
- All 92 recordings carry the same 29-column header.
- Sample headers: `time`, `hv_soc`, `hv_current`, `hv_voltage`, `dcdc_aux`, `hv_heater_current`, `hv_compressor_power`, `lv_power`, `vehicle_speed`, `motor_speed`, `gearbox_speed`, `motor_torque`, `temp_battery_avg`, `temp_stator`, `temp_inverter`, `temp_gearbox`.
- Per-CSV uncompressed bytes range 1,084,938–11,120,301.
- Source identification in existing project intake: Rosenberger and Lienkamp, TUM, *CAN Data of a Porsche Taycan during Real-world Driving Scenarios*, DOI `10.14459/2025mp1774217.001`.

**Transfer caveat:** The original TUM recording is reported as a 2022 RWD 93.4 kWh Performance Battery Plus vehicle; the Project Taycan reference is a 2022 4S AWD with 79.2 kWh battery. This is external driving evidence, **not** direct empirical validation of the target pack, front motor, or all fault hypotheses.

**Next gate:** Unit, sign, clock, missingness, sample-period and numerical-range checks for every CSV; document mappings between TUM variable names and allowed OBD channels without post hoc repair; freeze permitted training/held-out usage rules prior to any comparison. Do not publish the 427 MB source corpus into a public repo; only integrity metadata and reproducible scripts.
