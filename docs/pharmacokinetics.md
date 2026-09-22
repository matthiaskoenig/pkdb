# Pharmacokinetic calculations

PK-DB uses [`pkpdutils`](https://matthiaskoenig.github.io/pkpdutils/) for non-compartmental analysis of concentration timecourses. The backend declares `pkpdutils>=1.2,<2`, with the tested release recorded in `backend/uv.lock`. `pkdb-analysis` is no longer a dependency.

## Methods and output mapping

The adapter uses `Timecourse` and `nca_single`. It explicitly selects linear trapezoidal integration and terminal regression over all eligible points after the concentration maximum, preserving PK-DB's existing method choices rather than adopting the library's different defaults. Calculations retain source relationships, units, and the selected mean, median, or individual value statistic. Non-finite or unavailable parameters are omitted.

| pkpdutils parameter | PK-DB measurement type |
| --- | --- |
| `auc_last` | `auc_end` |
| `auc_inf_obs` | `auc_inf` |
| `cmax` | `cmax` |
| `tmax` | `tmax` |
| `lambda_z` | `kel` |
| `thalf` | `thalf` |
| `cl` or extravascular `cl_f` | `clearance` |
| `vz` or extravascular `vz_f` | `vd` |
| `vss` | `vd_ss` |

Dose-dependent calculations require a usable scalar single dose of the same substance, supported dose dimensions, and a known route. Missing or unsupported dose metadata still permits dose-independent parameters. Extravascular clearance and volume are apparent CL/F and Vz/F; they do not establish absolute bioavailability. Intravenous administration uses bolus or infusion calculations according to the supplied timing metadata, converting dose times into the timecourse's units.

## Differences from the previous library

`pkpdutils` applies route-aware handling at the dose time, including an oral zero concentration or IV back-extrapolation when applicable. Consequently, exposure and dose-dependent values can differ from the previous library when the first observation occurs after dosing. Its steady-state volume `vss` is an IV parameter derived from clearance and mean residence time; it is not the previous implementation's dose divided by the fitted terminal intercept. Unknown routes do not justify either an IV or extravascular dose-dependent estimate.

These changes apply when studies are newly prepared or replaced. Changing the dependency does not recalculate existing stored measurements automatically. Historical migration reports and frozen fixtures retain the previous evidence; they are not rewritten as proof of numerical equivalence.
