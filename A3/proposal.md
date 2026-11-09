# Revised Project Proposal — A3 Revision

## Basic Information

| Item | Value |
|---|---|
| Student | M11502203 Ping-Yu Hsieh / 謝秉祐 |
| Revised title | Improving Spatial Generalization of Simulated Uplink Channel-Fingerprint Localization Using a Lightweight MLP |
| Revision date | 2026-11-09 (Asia/Taipei) |
| Original A1 | [Original proposal](../A1/proposal.md) |
| Literature review | [A3 study note](study_note.md) |
| Planning approval | Pending instructor approval; no approval is implied by this revision |

## 1. Motivation and Research Question

The original A1 proposed replacing an RF regressor with a lightweight MLP using a measured 32-D SRS dataset. After reading Tian et al., “Deep-Learning-Based High-Precision Localization With Massive MIMO,” IEEE TMLCN, 2024 ([DOI](https://doi.org/10.1109/TMLCN.2023.3334712)), the primary workflow changes to simulated **uplink channel fingerprints**. The paper's focus on spatial sampling motivates validating the simulated channel before evaluating learned position maps.

Research question: how do sampling density and spatial train/test separation affect localization accuracy, and does a lightweight MLP outperform RF at unseen positions with identical input features and test samples?

This retains the original spatial-generalization objective. Standard NR SRS waveform generation/estimation is not claimed by the initial channel-level experiment.

## 2. System Model and Scope

One single-antenna UE transmits toward a fixed BS array in a simulated indoor environment. ns-3 produces complex multipath coefficients and delays. A documented extraction routine forms per-antenna frequency responses, from which a channel-correlation observable and localization fingerprints are computed. Python performs feature processing, training, evaluation and plotting.

Primary platform: ns-3.48, with 5G-LENA v5.1 available for later NR experiments. The initial A4 channel-level reconstruction does not require the NR scheduler or application packet traffic.

No physical radio equipment, OAI deployment, E2 interface or xApp is required. The original measured SRS dataset may be an optional separate validation dataset if available; it is no longer required for completion.

## 3. Inputs, Features, Models, and Outputs

### Inputs and Feature Construction

- Complex uplink frequency response at each known position, with carrier, sampled tones, array layout, trajectory and RNG recorded.
- A covariance feature formed from antenna correlations; preserve real diagonal values and real/imaginary off-diagonal values in a fixed order.
- For the initial compact model, use a documented 4 × 4 subarray (256 independent real covariance components) and train-only PCA to 32 components when enough training samples exist. This is a project choice, not the paper's complete pipeline.
- Record subarray indices, covariance normalization and PCA explained variance. A covariance-derived 32-D vector is not the old 16 PDP + 8 phase + 8 power SRS representation.
- Fit scaling/PCA using training samples only. Neighborhood averaging, if introduced, must never pool across a train/test boundary.

### Models

| Model | Initial configuration | Role |
|---|---|---|
| Simple nearest-neighbor/KNN regressor | Document feature distance and choose k using validation data | Sanity baseline for the generated fingerprint map |
| Random Forest | 100 trees, max depth 12, min samples per split 20 | Baseline retained from the original plan; not called an exact published-model reproduction |
| Lightweight MLP | 32 → 64 → 32 → 2, ReLU hidden layers, MSE loss | Proposed model comparison |

MLP starting settings: Adam, learning rate 0.001, batch size 64, maximum 300 epochs, early stopping patience 20. These are project defaults, selected/frozen using validation data, not reported paper settings.

### Outputs and Metrics

Estimated (x, y); per-sample Euclidean error; mean, median, distance RMSE, P90; fractions within 0.5/1 m; error CDF; serialized model size, training time, CPU inference latency. Use \(\mathrm{RMSE}=\sqrt{N^{-1}\sum_i\|\hat p_i-p_i\|^2}\) and state this convention explicitly.

## 4. Experiments

### Experiment 1 — A4 Published Channel Result

Reconstruct Tian et al. Fig. 7, the empirical spatial correlation along a UE trajectory, using Equation (11). Start with 3.7 GHz, BS 4 × 25 array at half-wavelength spacing, 100 pilot-frequency samples, UE speed 0.1 m/s and 10 ms recording intervals. Use the exact complex-average-before-magnitude statistic described in [A3 Section 4.3](study_note.md#43-a4-target-fig-7).

The ns-3 surrogate uses `InH-OfficeMixed`, forced LOS initially, and declared project coordinates/heights. A planned 4.2 m path lasts 42 s. Run seed 20261109, runs 1–10, fixed assigned streams. Obtain/digitize the original curve with attribution and compare the same axes. Analyze discrepancies without asserting reconstruction of the physical studio.

This channel experiment establishes the simulation's starting point. It does not reproduce the paper's neural-network accuracy or supply the final localization-model baseline by itself.

### Experiment 2 — Radio-Map Validation and Model Baseline

Generate a two-dimensional map only after verifying continuity along paths and consistency between scan lines/revisited coordinates. Do not initialize unrelated random scatterers for each location. If the model cannot maintain cross-path consistency, resolve the generation method before interpreting RF/MLP scores.

Use a declared 4.2 × 2.5 m region and a feasibility pilot before choosing the full grid density. Store all positions, channel parameters, streams and route order. Test repeated coordinates for stable environment-dependent fingerprints rather than path-history artifacts.

### Experiment 3 — Spatial Generalization

Compare identical RF/MLP/KNN inputs under:

1. Random frame split as an intentionally optimistic diagnostic when repeated-position samples exist.
2. Location-grouped split: no coordinate shared between train, validation and test.
3. Contiguous spatial-region holdout with train/validation separation inside the remaining area.

Use multiple held-out regions and report distance from each test point to the nearest training point. Add a spatial buffer as a sensitivity control and keep its width explicit. For a map with one snapshot per coordinate, random-position splitting is already location-grouped; do not present them as distinct experiments.

### Experiment 4 — Density and Cost

Vary spatial training density while holding the test region fixed. Separate interpolation inside training coverage from extrapolation outside its convex hull. Measure latency on the same CPU, with warm-up and fixed batch size; report median/P95 and model size rather than claiming end-to-end radio latency.

## 5. Reproducibility and Acceptance Criteria

- Channel RNG: seed 20261109, runs 1–10, assigned stream start 1; preserve each run independently.
- Proposed split seeds: 201–205; model/training seeds: 101–105. Use paired model comparisons; document which seed combinations are run and keep channel-level versus training-level variability separate.
- Publish the actual configuration and software revisions, not just version labels.
- Require finite complex channels, correct dimensions, rho(0)=1, repeatability with fixed RNG, meaningful movement variation and justified spatial behavior.
- A4 completion requires a published-curve comparison and difference analysis. A readiness plot alone does not satisfy A4.
- Final completion requires an RF/neighbor baseline and MLP comparison on the verified map. An MLP advantage is not assumed.

## 6. What Changed From A1 and Why

| Change | Reason |
|---|---|
| Measured SRS dataset is no longer the mandatory primary input | The user selected an all-simulation workflow compatible with ns-3. |
| Published uplink massive-MIMO article becomes the main reference | Connects A3 literature review to a concrete A4 channel result. |
| Add channel extraction and spatial-correlation validation | A model comparison is only meaningful if the simulated map has credible spatial structure. |
| Replace the old fixed SRS feature definitions with explicit covariance/PCA features | The new source data has different semantics; input dimension alone does not make it the same feature. |
| Retain RF/MLP and the grouped/spatial splits already in A1 | Preserve the original research objective; these are not newly invented A3 additions. |
| Add density, spatial-buffer and cross-path checks | Address the paper's sampling insights and possible simulator artifacts. |
| Remove old RF numerical errors as reproduction targets | Those numbers come from a different dataset/manuscript and cannot be compared as matched baselines. |

## 7. Deliverables and Limits

Deliverables: simulator setup/verification record; channel exporter and analysis script; A4 Fig. 7 comparison; fingerprint map and split manifests; RF/KNN/MLP training/evaluation scripts; accuracy/cost plots and final report.

Results apply to the simulated indoor environment. Cross-room/device/day generalization, exact reproduction of the measurement studio, standard-compliant SRS reception and live real-time positioning remain outside the initial scope. A reproducible negative result remains informative.
