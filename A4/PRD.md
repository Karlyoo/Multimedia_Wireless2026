# A4 Baseline Reproduction Specification

Date: 2026-11-21 (Asia/Taipei)
Status: Scope approved by the user on 2026-11-21; implemented and verified. See study_note.md and results/validation.json. No claim of exact curve agreement or instructor scope approval.

## Objective

Reconstruct the empirical spatial channel correlation in Figure 7 and Equation (11) of G. Tian et al., “Deep-Learning-Based High-Precision Localization With Massive MIMO,” IEEE TMLCN, vol. 2, pp. 19–33, 2024, DOI: 10.1109/TMLCN.2023.3334712, using ns-3.

This is a channel-statistic baseline for the final localization project. It is not a reproduction of the paper's neural-network positioning accuracy. Instructor acceptance of this distinction has not been established.

## Existing Evidence

- `../A3/src/channel-spatial-probe.cc` implements an uplink channel probe with configurable samples and RNG run.
- `../A3/results/los/correlation.csv` and `../A3/results/nlos/correlation.csv` contain short-path readiness data, not paper comparisons.
- `../A3/environment.md` records previous build and numerical verification. Recheck runtime availability before relying on those historical checks.
- Existing repository baseline: `b180274fc538519c114521ad8f7451e14549e537`. The worktree was clean before creating this specification.

## Proposed Experiment

| Parameter | Planned value |
|---|---|
| Simulator | ns-3.48; record actual source revision and build |
| Channel | ThreeGppChannelModel, InH-OfficeMixed |
| Direction | One single-element UE transmitter to one BS receiver |
| BS array | 4 by 25 elements, half-wavelength spacing |
| Carrier | 3.7 GHz |
| Frequency samples | 100 tones, 180 kHz spacing; document grid interpretation |
| Geometry | BS (0,0,2.5) m; UE starts (2,2,1.73) m, moving in +x |
| Motion | 0.1 m/s; snapshot interval 10 ms; spatial spacing 1 mm |
| Path | 4.2 m; 42 simulated seconds; 4,201 snapshots |
| Primary condition | LOS |
| Sensitivity condition | NLOS, kept distinct from the primary reconstruction |
| RNG | Seed 20261109; runs 1 through 10 per condition; channel stream start 1 |
| Traffic / MAC | Not applicable to direct channel extraction; no packet workload |
| Initial signal model | Ideal normalized small-scale channel, no receiver noise or RF impairments |

The geometry, statistical model, duration and RNG choices are project assumptions, not claimed original paper settings. Ten runs per condition are a proposed budget, not a guarantee of statistical convergence. Begin with one full-path pilot to assess memory, runtime and channel-update validity before launching the batch.

## Analysis and Reference Data

1. Obtain a readable original Figure 7; verify axes and Equation (11) before final plotting.
2. If numerical reference data are unavailable, digitize the original curve. Preserve image provenance, axis calibration and the extraction method; label digitization uncertainty. Never fabricate reference points.
3. Compute normalized complex pair correlations, average complex values within each run and lag, then take magnitude.
4. Report each run's curve. Summarize magnitudes across independent channel runs, explicitly defining the aggregation and variability band. Do not pool complex correlations across runs as an undocumented substitute.
5. Plot the reference and simulated result using the same axis definitions and ranges verified from the original figure. Show NLOS separately or clearly label it as sensitivity analysis.
6. If reference extraction cannot be completed, report the missing overlay as an open requirement; do not mark A4 complete.

## Deliverables

- `study_note.md`: selected result, equation, flowchart, parameters, RNG policy, exact commands, numerical results, provenance, differences and limitations.
- `src/`: simulation, batch runner, analysis and validation code; compile once per batch where practical.
- `reference/`: attributed reference figure/data and digitization record when available.
- `results/`: per-run CSVs, configurations, execution records, aggregate tables and comparison figures.
- Updated A4 submission links in the repository README.

The written submission is in English. The original experiment scope excluded slides; the user subsequently authorized the 15-minute deck described below.

## Acceptance Checks

- Full-path pilot executes successfully; all planned completed runs are recorded, and failures are explicit.
- Finite channel values, expected dimensions, correlation magnitude bounded by one, and unit zero-lag correlation.
- Same seed/run reproduces numerical outputs; changing run changes results.
- Channel varies along a continuous moving link rather than independent per-position links.
- Verify the existing exporter and delay-cache workaround against the installed ns-3 version; preserve any necessary limitations.
- Numerical tables match plotted CSVs; actual run count and parameters are reported.
- A reference overlay is present, or the submission is explicitly marked incomplete.
- Distinguish measured facts, simulator assumptions, observed discrepancies and untested explanations. Use controlled checks before asserting causation.

## Approved Follow-up: Figure 5 Trajectory and Direction

Status: User approved the inferred geometry and three experiments; completed and verified on 2026-11-22. See geometry_study.md and results/geometry/validation.json. Existing baseline and noise results remain unchanged.

Reconstruct the first +x trajectory relevant to Figure 7, not the entire serpentine scan. The figure establishes a 4.2 m scan extent and a 1.1 m drawn face-to-region gap. For an explicitly approximate model, keep the BS phase center at (0,0,2.5) m and place the UE at (1.1,-0.6,1.73) m, moving +x. The lateral offset assumes the phase center lies halfway along the drawn 1.2 m LuMaMi extent and the first trajectory aligns with its top edge. Treat the front face as the phase-center plane only as an explicit assumption. BS height remains the previous 2.5 m assumption; the 1.2 m figure annotation is not a height.

Proposed configurations, all noiseless LOS with seed 20261109, runs 1–10, stream start 1, speed 0.1 m/s and 1 mm recording displacement:

| Configuration | Length / samples | Purpose |
|---|---|---|
| Existing baseline | 4.2 m / 4,201 | Reuse existing data; do not rerun or overwrite |
| Figure-5-aligned +x | 4.2 m / 4,201 | Compare the assumed initial geometry with the published observable |
| Direction control +x | 2.5 m / 2,501 | Equal-length longitudinal reference within the scan region |
| Direction control +y | 2.5 m / 2,501 | Counterfactual transverse path from the same initial position; not a paper trajectory |

Run ten realizations of each new configuration, record exact positions and velocities, export a trajectory plot, verify source-conversion Doppler using the full velocity-vector projection, and retain same-axis reference overlays and all-run summaries. Keep receiver noise fixed at zero to isolate geometry; do not mix in the previously best-performing SNR condition.

As a numerical control, recompute the correlation from the same stored samples in reverse order. Its complex correlation must be conjugate to the forward result and its magnitude unchanged within numerical tolerance. This distinguishes the effect of changing path orientation relative to the multipath geometry from merely reversing sample order. A separately initialized reverse-motion ns-3 run need not reproduce the same physical map because the simulator's evolving realization can depend on path history; do not mislabel that difference as measured directional propagation.

Do not claim direction explains the measured oscillations solely because one configuration has lower curve RMSE. Matching is descriptive, and the exact measurement phase center, height and scatterers remain unverified.

## Approved Follow-up: Noise Sensitivity and Figure 5 Review

The user requested noiseless / 1 / 6 / 11 dB comparisons and inspection of the paper's UE trajectory diagram. Preserve the existing baseline and run the noise study under the same LOS geometry, 42 s path and channel run IDs 1–10. Noise is added to the complex frequency response before normalization, using an independent assigned ns-3 RNG stream. Pair each SNR with the same underlying channel and standard-normal noise draws; scale noise only. Define SNR by mean signal power across antenna/tone entries per snapshot, not per-entry fading power. Record expected target and realized aggregate SNR. This is a simplified constant-snapshot-SNR observation model, not the original measurement's varying per-tone SNR or actual pilot estimation.

Follow-up status: completed. Forty full runs and paired-noise validation passed, with four short repeat controls. See noise_study.md and results/noise/validation.json. Figure 5 was inspected and its annotated geometry documented; no inferred phase-center geometry was silently implemented.

Create a separate A4 noisy exporter and outputs without editing A3 or the baseline data. Verify its noiseless results against all existing LOS runs, the same-seed repeat, unchanged channel witnesses across SNR settings, noise-power ratios and zero-lag invariants. Report all four curves without selecting a winning SNR as the new reproduction baseline.

Inspect PDF page 8 / printed page 6, Figure 5. Preserve a cited crop and distinguish labelled dimensions from inferred antenna phase-center coordinates. Do not silently replace baseline geometry or interpret the 1.2 m plan-view array dimension as BS height. Geometry reconstruction remains a separate follow-up unless its assumptions are explicitly adopted.

## Approved Small-Workload Follow-up: Height and Bearing

The user authorized small-workload tests following the proposed BS-height and array-bearing sensitivity checks. Use the existing noiseless LOS Figure-5-aligned 4.2 m +x trajectory. Vary one factor at a time: BS heights 1.73 and 3.0 m at bearing 0 degrees; BS bearings -30 and +30 degrees at height 2.5 m. Reuse height 2.5 m / bearing 0 degrees from the existing geometry experiment as the common reference. All compared settings use only the same first five channel run IDs, 1–5, seed 20261109 and channel stream start 1. This is exploratory, not recovery of paper parameters or a statistical convergence claim.

Run twenty new 42-second simulations, preserving previous sources/results. Verify a new exporter's default-setting regression against an existing short pilot and a full reference run. Keep first/middle/last spectrum cross-checks for each run. Report mean-curve discrepancy, paired per-run discrepancies, all curves and variability; do not compare a five-run new mean against the previous ten-run baseline mean. No noise tuning, model-table changes, external library edits or full parameter-grid search is included.

Status: completed and verified on 2026-11-22. Twenty new full runs, five reused reference runs and three pilots are recorded under results/sensitivity and results/sensitivity-pilot. See sensitivity_study.md. No original-paper parameters or oscillation mechanism were identified by this exploratory screen.

## Approved Addition: Figure 6 Channel Heatmaps

The user accepted the proposed addition of Figure 6, not Chapter VI. Implement a stationary approximate position-A observation with the existing ns-3 indoor LOS model, 3.7 GHz, 100 BS antennas, 100 tones at 180 kHz spacing, BS (0,0,2.5) m and zero bearing/downtilt. Infer the point-A location from the formal PDF's Figure 5 proportions, record the calibration, and label it schematic rather than surveyed. Preserve all previous source and results.

Export the complete complex antenna-by-tone response before normalization, cluster delays and coefficients, and one spectrum-conversion cross-check per channel run. Use seed 20261109, runs 1–10 and stream start 1. Preselect run 1 for single-snapshot heatmaps, not the best visual match; summarize run variability separately. One static observation at t=0 has no UDP/MAC workload and no 42-second simulation duration.

Recover the CIR with an IDFT along each antenna's 100 observed tones. The frequency grid implies native delay-bin spacing 1/(100*180 kHz) = 55.56 ns, and a 5.556 microsecond unambiguous delay period; do not relabel those bins as 50 ns merely because nominal bandwidth is 20 MHz. Show the first approximately 0.5 microseconds and publish native-bin arrays. Relative power uses a documented global-peak convention for each heatmap, not independently normalized antennas or an unverified absolute match to paper colors.

Add original/formal Figure 6 provenance/crop, simulated PDP and frequency-response heatmaps, side-by-side original/simulation comparison, channel/coefficient CSVs, per-run energy summaries, numerical checks (shape, finite values, FFT round-trip and Parseval, direct delay-sum reconstruction, repeatability) and an English report linked from A4. Do not compute image-pixel RMSE or claim exact reconstruction of measured position A, antenna ordering, RF-chain effects or dB normalization. Report whether the simulated maps exhibit early delay concentration and smoother frequency than spatial variation, without assuming these observations in advance.

Status: completed and verified on 2026-11-23. Ten stationary channel runs and one identical repeat, raw H/cluster exports, native-grid IDFT analysis, formal-PDF crop/comparison and figure6_study.md are delivered. See results/figure6/validation.json. No exact measured-map or absolute-dB agreement is claimed.

## Approved Deliverable: Approximately 15-Minute Presentation

The user requested an A4 presentation after completion of Figure 6. Produce English slides and English speaker notes, consistent with the earlier presentation-language preference. Target 16 main slides with suggested timings totalling 900 seconds, plus two untimed backup slides. Cover objective, observable, original/modeled settings, numerical checks, Figure 7 single-run and ensemble comparisons, noise/geometry/direction/height/bearing tests, Figure 6 processing and qualitative comparison, limitations, reproducibility and final-project connection.

Deliver editable PowerPoint, PDF preview, source ODP, reproducible builder and speaker-note Markdown with slide timings. Reuse verified data and existing figures; do not rerun simulations or fabricate missing results. Explicitly distinguish dimensionless curve error from positioning error, five-run from ten-run references, single measured trajectories from ensemble summaries, post-print Figure 7 extraction from formal-PDF Figure 6 crop, and hypothesis from verified mechanism. Figure 6 position A and dB normalization remain approximate/explicitly different. Do not imply complete neural-network reproduction, exact measured-map agreement, or identified oscillation causes.

Verify slide and note counts, metric consistency, XML/archive integrity, PDF page count, and rendered chart/table layout. No rehearsal recording is included. Suggested timing is not a measured rehearsal duration.

Status: completed and verified on 2026-11-23. Editable PPTX, PDF, source ODP, presentation.md, content/builder/validation scripts and presentation-specific figures are delivered. Validation confirms 18 PDF pages and embedded full note texts, 900 seconds of suggested main-slide timing, critical metrics, archive integrity, valid local links and no out-of-page PDF words. All pages were visually inspected; pipeline refinements were re-rendered. No actual rehearsal duration or recording is claimed.

## Approved Review and Notes for the User Reordered PDF

The user supplied `/home/karl/Downloads/M11502203_Karl_A4.pdf` and requested order/content review plus a speaking script. Review its actual 15-page order, not the earlier 18-page exported deck. Preserve the PDF and existing deck; provide feedback rather than implementing unsolicited slide edits. Save an English script in the established A4 Markdown format, with Chinese delivery cues and suggested timing totalling approximately 15 minutes. Keep Figure 6 before Figure 7 as in the supplied deck, make the pipeline branch transition explicit, and state dimensionless RMSE, nonmatching dB references, approximate A coordinates and five-versus-ten-run comparisons where they matter. Check all reviewed pages visually and against recorded metrics. No automatic commit/push or simulation rerun is authorized by this review request.

Status: completed. Reviewed the actual 15-page PDF and recorded minor wording/interpretation recommendations in presentation_karl_notes.md. Delivered 15 matching English narration sections with Chinese cues, 1,821 narration words and continuous suggested timing of 900 seconds. Local links checked. PDF and existing deck preserved; no simulations rerun. Actual rehearsal duration remains unmeasured.

## Scope Limits and Safety

No hardware, OAI, actual NR-SRS reception, full FCNN/fusion pipeline, RF/MLP training or two-dimensional radio map is required for A4. Do not silently tune parameters to match the reference. Preserve A1/A3 and existing ns-3 installations. Keep new outputs under A4 or temporary directories. No commits, new branches, external publication or destructive operations without explicit authorization.
