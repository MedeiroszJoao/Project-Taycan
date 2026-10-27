# E66 GITT history audit — 2026-10-27

Status: POSTHOC DIAGNOSTIC, NOT B2 APPROVAL.

Reproduced directly from the authorized 25C GITT payload; SHA256 checked against previous receipt. Extracted 28 quiet intervals >=600s and 13 paired anchors with SOC proxy difference <1e-4. The SOC proxy uses initial SOC=1 and capacity=61.259778569358865Ah. None of the four final blind module payloads was opened.

25 duplicate timestamps have identical current, voltage and temperature; zero conflicts. First-versus-last duplicate handling changes integrated charge by exactly zero.

Selected later-minus-earlier paired voltages:

| SOC proxy | Gap mV | Temperature difference C | Earlier/later final-ten-minute change mV |
|---|---:|---:|---:|
|0.065651|127.742|0.02342|0.752 / -0.313|
|0.114827|97.593|-0.28459|0.507 / -0.307|
|0.311529|32.400|-0.38990|0.200 / -0.200|
|0.508237|9.300|-0.02184|0.200 / -0.100|
|0.901645|1.400|-0.47856|0 / -0.200|

The low-SOC voltage separation survives duplicate-handling checks and is much larger than voltage change in the final ten minutes. The largest pair is nearly isothermal. These facts strengthen history dependence as a modeling concern; they do not uniquely identify equilibrium hysteresis. Slow relaxation, charge-counting biases and path-dependent internal states remain unresolved. A single OCV function cannot be assumed sufficient merely because two-hour rests were used.

Next: evaluate charge/discharge-specific quasi-OCV branches with explicit initialization and constrained SOC mapping, preserving existing failure records and performing development regression checks before any independent evaluation. Branch fitting to these same anchors is calibration, not validation. B2 and broad 4B remain unapproved.

Reproduction: `python scripts/audit_e66_gitt_history.py`. Requires NumPy, SciPy and the E66 archive at the documented project_sources path. Script contains source hash, finite-value, monotonic-clock and conflict checks. This run completed successfully; no full project test-suite claim.
