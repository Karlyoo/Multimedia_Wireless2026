# Project Context

## Repository

Course: Multimedia Wireless Networks (ET5907701), NTUST. Student: Ping-Yu Hsieh, M11502203. Repository: Karlyoo/Multimedia_Wireless2026. Existing branch: main.

## File Index

| Path | Role |
|---|---|
| README.md | Course submission links |
| A1/ | Original proposal and background notes |
| A2/ | Previous ns-3 scenario and evidence |
| A3/proposal.md | Revised all-simulation uplink localization proposal |
| A3/src/ | Original channel exporter used by A4 |
| A4/PRD.md | Approved experiment and presentation specifications |
| A4/study_note.md | Figure 7 baseline, settings, results and limitations |
| A4/src/README.md | Flowcharts, source index and rebuild commands |
| A4/*_study.md | Noise, geometry, small sensitivity tests and Figure 6 |
| A4/results/ | Raw CSVs, manifests, validation records and figures |
| A4/reference/ | Attributed reference crops, Figure 7 points and provenance |
| A4/A4-baseline-reproduction-en.pptx | English presentation; PDF/ODP alongside it |
| A4/presentation.md | English speaker notes and timings |
| A4/presentation_karl_notes.md | Notes matching Karl's revised 15-page PDF, review suggestions and Chinese delivery cues |
| docs/HANDOFF_PROMPT.md | Detailed live handoff and unresolved limitations |

## Architecture and Dependencies

A4 uses an existing ns-3.48 build at `/home/karl/projects/ns-3.48-nr`. Exporters generate uplink complex channels; Python computes channel correlation, delay/frequency power and comparison figures. The baseline entry point includes A3 source, so A4 is not an isolated standalone download. GCC 12, NumPy, Matplotlib and Poppler support the workflow; LibreOffice exports presentation files. No hardware, OAI, packet scheduler or actual NR-SRS estimator is required by these channel-level experiments.

External service: the existing GitHub origin. External simulator source is not part of this repository and was not modified. The user-supplied formal paper PDF remains outside the repository; attributed excerpts and provenance are included.

## Decision Boundaries

Figure 7 is a channel-statistic baseline, not a learned-positioning baseline. Figure 6 is a qualitative heatmap reconstruction at an approximate point A with explicit dB/delay-grid conventions. Five-run and ten-run summaries must remain distinct. No exact measurement match or unique cause of oscillations is established. Final RF/KNN/MLP work must first validate cross-path/revisited-position consistency.
