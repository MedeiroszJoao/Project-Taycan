# Stage4B E66 real-module experiment groups & topology-falsification gate

Date: 2026-10-24. **Frozen before numerical payload inspection.** Official source Borealis DOI `10.5683/SP3/7JP3NM`; module `837535`, size 5,501,501 bytes, MD5 `619eb01774c04696e399d106639a342c`, SHA-256 independently `a5628a9d56d2e097158620346c3f69b5ff5c6269bb2770f643e91f397abcac7e`, 12 MATLAB level-5 files CRC verified [run 40075085474](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40075085474).

The author dataset description says “twelve E66 cells (6p2s)” but the experimental module README explicitly equates **2C to 264 A**, meaning 1C=132 A and apparent module reference capacity **132 Ah**. For an approximately 66Ah E66 single cell, an arrangement of **2 parallel ×6 series** yields 132Ah while 6 parallel ×2 series yields ~396Ah. Naming may be in a reversed convention; neither interpretation is approved before reading official electrical instrument wiring/voltage evidence. Expected module voltage differs by factor ~3 (2s vs 6s). Do not arbitrarily change target Taycan 4S topology; this is an external recovered module only.

## Independent experimental partition — prior to numeric data inspection

**DEVELOPMENT-FIT / metadata plus data may be read now:** 
- `20240209_0.7C_CP_Loss.mat`;
- `20240209_1C_CP_Loss.mat`;
- `20240323_1.2C_CP_Loss.mat`;
- `20240314_1C_Test (MCCC).mat`;
- `20240315_0.5C_Test (MCCC) Part1.mat`;
- `20240315_0.5C_Test (MCCC) Part2.mat`.

**VALIDATION — metadata/schema only initially, numeric results later with preregistered pipeline:**
- `20240207_1.5C_CP_Loss.mat`;
- `20240313_1.5C_Test (MCCC).mat`.

**BLIND EXTERNAL E66 HOLDOUT — DO NOT INSPECT NUMERIC PAYLOAD:**
- `20240318_2C_Test (MCCC) Part 1.mat`;
- `20240318_2C_Test (MCCC) Part 2.mat`;
- `20240322_TopUp&DC_for_FC.mat`;
- `20240323_Fast_Charge.mat`.

These four files represent **two related experiments** (2C split parts and fast-charge preparation/test), not four independent vehicle/cell trials. File names/ZIP CRCs and static structural metadata are public and already observed; the blind rule applies to numeric measurements. Single module, strong within-unit correlation.

## First numeric schema/architecture checks on development files only

Use official `meas` struct variable schema and `RecordingTime,AVL_Current,AVL_Voltage,BMS_Current,BMS_Voltage,CellVoltage,CellID` fields when available. Verify measured module voltage domain and source current protocol vs claimed “6p2s”; flag V≈20–25V compatible with 6 serial groups versus V≈7–9V compatible with two serial groups (these are coarse diagnostic sanity bands, NOT certification or hard fit targets). Verify signal units/indices, min/max/nonfinite and timebase, do not train yet. No numerical access to the four blind files; in validation two files, only `scipy.io.whosmat` top-level metadata permissible at this stage.

No automatic PyBaMM parameter transfer from Chen2020 LG M50. First achieve credible cell voltage/current/temperature signal mapping and stop at data adequacy. The preserved historical 1152 Stage4 tests are absolutely separate and untouched.
