# Primary-source observations relevant to the simulator

**Porsche Technical Feature** (February 25, 2021; Australian model information):
https://newsroom.porsche.com/en_AU/2021/products/technical-feature-the-porsche-taycan-23670.html

- Taycan 4S standard **Performance Battery**: nominal energy **79.2 kWh**, **28 modules**, **336 pouch cells**; published pack voltage range **520–720 V**.
- Taycan 4S with this standard battery: front PMSM max **150 kW / 300 Nm**, rear PMSM max **270 kW / 340 Nm**, with other axle/version-dependent limits in the source.
- Battery module thermal coupling and conditioning include active cooling/heating and dependence on operating strategy.
- Inverters are axle-specific and the article gives a family-level **up to 98.5%** efficiency figure, not a Taycan-specific full operating efficiency map.

**Porsche AfterSales bulletin 2518.2** (December 2, 2025):
https://static.nhtsa.gov/odi/tsbs/2026/MC-11027127-0001.pdf

- Applies across Taycan model years/types as specified in its vehicle list, with separate diagrams for 28- and 33-module packs.
- Discusses post-repair dielectric-strength testing (DST) and insulation-resistance testing (IR), which are distinct.
- Its acceptance rules for repeated terminal-level IR testing include a **second-test result below 200 MΩ** as failure, in the narrow specified workshop-test context. This must **not** be treated as a calibration of the real-time BMS isolation signal.
- The bulletin explicitly requires trained HV personnel, protective equipment and official procedures. The research application is **not** a safety clearance tool.

**Scientific status:** Primary-source engineering specifications and procedural thresholds; not time-series measurements or quantitative validation of the model. Variations by vehicle options, market and production year remain relevant.
