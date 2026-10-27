# E66 branch qualification

B2 and Stage4B remain unapproved. The present exploratory result is not a replacement of the original acceptance criteria.

Two monotone piecewise linear branches fitted to the previously exposed 25C GITT rested anchors passed leave-one-interior-anchor-out interpolation: discharge RMSE 15.281mV, max31.744mV; charge RMSE16.452mV, max35.952mV. Endpoints were not extrapolated. Four domain/interpolation guards passed. This is within-session interpolation, not independent dynamic validation.

Development 1C MCCC initialization was reproduced from source hash 1b4484914764b7f819cab2e43639a770c2ee890488aa3e7142034f7bf3c2ad37: precharge mean BMS cell voltage3.151667V, whereas the supported charge branch begins at3.244410V. Charge-only inversion is therefore rejected. No clipping, artificial SOC or silent extrapolation was used.

The full stage cannot currently be approved: long-charge electrochemical transfer remains failed; a history-state transition has not been calibrated and independently tested; thermal prediction and full feature transfer remain unsupported. A partial interpolation pass cannot close these claims. Final blind data and historical episodes remain closed.

Environment recovered: PyBaMM26.4.2, mat-io1.0.1. Initial attempt with mat-io0.4.0 reproduced the known `_Class` decoder failure; recovery followed the existing 2026-10-24 decoder amendment. Source code and prior freeze JSONs were retrieved from commit be93c924fc02dfd246302eabd6340d339a763b08. No original freeze was overwritten.

Next substantive task: construct and test a constrained history-state transition initialized on the discharge-rest branch, rather than applying the charge branch instantaneously. This requires distinguishing transient and quasi-equilibrium contributions using development pulse/rest data before independently evaluating sustained charging. Even successful electrical qualification would not by itself resolve missing thermal and vehicle-level observations.
