# A3 — Previous Literature-Review Draft (Superseded)

This draft is retained for history. The submitted direction is now described in [study_note.md](study_note.md), using the uplink massive-MIMO paper selected after checking the A4 requirements. Statements in this old draft are not the current proposal.

## Project Topic

**Improving Spatial Generalization of SRS-Based Indoor Localization Using a Lightweight MLP**

This literature review supports the project proposed in [A1](../A1/proposal.md). The project reuses the processed 32-dimensional uplink SRS features from the reference system, compares a Random Forest (RF) baseline with a lightweight Multilayer Perceptron (MLP), and evaluates performance at locations that are excluded from training.

> **Scope note:** The two papers below are IEEE Transactions papers. The papers use Wi-Fi/CSI fingerprinting rather than the exact SRS dataset in this project. Therefore, they provide methodological and problem-background support; the project-specific SRS preprocessing and RF baseline still come from the A1 reference paper.

---

## Paper 1 — TransLoc

### Bibliographic Information

- **Title:** TransLoc: A Heterogeneous Knowledge Transfer Framework for Fingerprint-Based Indoor Localization
- **Authors:** Lin Li, Xiansheng Guo, Mengxue Zhao, Huiyong Li, and Nirwan Ansari
- **Publication:** *IEEE Transactions on Wireless Communications*, vol. 20, no. 6, pp. 3628–3642, 2021
- **DOI:** [10.1109/TWC.2021.3052606](https://doi.org/10.1109/TWC.2021.3052606)
- **IEEE page:** [IEEE Xplore abstract](https://ieeexplore.ieee.org/abstract/document/9337208)

### Problem

Fingerprint-based indoor localization depends on a radio map collected in a particular environment. When the environment changes, the signal distribution in the target space may differ from the distribution used for training. A model trained on the original fingerprint domain may therefore lose localization accuracy.

The paper focuses on knowledge transfer between domains with distribution differences and heterogeneous feature spaces. It proposes TransLoc to transfer useful information from a source domain to a target domain while reducing irrelevant or redundant source knowledge.

### Importance

Indoor fingerprint collection is expensive and difficult to repeat whenever the environment changes. A localization model that can adapt to a new domain with very limited target-domain data would reduce the cost of maintaining the radio map.

This paper is relevant to my project because spatially separated test regions can be treated as a distribution-shift problem. A random frame split may make the task look easier because highly correlated frames from the same coordinate can appear in both training and testing. Testing on unseen coordinates or contiguous regions provides a stricter evaluation of generalization.

### Challenges

The paper identifies three main challenges:

1. Redundant source-domain samples may cause negative transfer.
2. Some transfer methods require too many target-domain samples to estimate distributions.
3. Source and target domains may have heterogeneous feature spaces.

For my project, the corresponding challenges are:

- Indoor multipath creates a nonlinear relationship between SRS features and physical coordinates.
- Frames from the same location are correlated and can cause location leakage.
- A model may perform well on known coordinates but poorly in spatially separated regions.

### System Model

The paper considers a source fingerprint domain and a target fingerprint domain. The proposed framework performs the following conceptual operations:

```text
Source-domain fingerprints + limited target-domain samples
                         ↓
       Source-domain refinement and cross-domain mapping
                         ↓
             Common feature representation
                         ↓
                 Target-location prediction
```

The paper's model is a knowledge-transfer framework rather than the lightweight MLP used in my project. The exact dataset topology, traffic model, PHY/MAC parameters, and simulation-seed settings are not available from the abstract page and should be taken from the full paper if they are needed for exact reproduction.

### Experimental Results

The paper reports simulation and real-world experiments. According to the abstract, TransLoc outperforms existing transfer-learning methods and remains robust under changing environments. It is also designed to work with only one sample in the target domain.

The paper does not directly provide the exact result needed for my project: RF versus MLP regression on the same 32-dimensional SRS dataset under spatially separated splits. Therefore, I use it to justify the evaluation problem and the need for leakage-resistant spatial testing, not as a directly reproducible baseline.

### Relevance to My Project

| Paper idea | Project implementation |
|---|---|
| Distribution discrepancy between fingerprint domains | Compare random, location-grouped, and spatially separated splits |
| Changing target domain | Hold out coordinates or contiguous indoor regions |
| Robustness to domain shift | Report mean, median, RMSE, P90, and threshold accuracy |
| Avoiding misleading evaluation | Keep all frames from one coordinate in one partition |

### Reproduction-Setting Checklist

The assignment asks for topology, traffic model, PHY/MAC parameters, simulation time, and random seeds when applicable. These two papers are not ns-3 papers, so several ns-3-specific fields are **not applicable**. The following information should not be invented from the abstract:

| Setting | Status from accessible paper information |
|---|---|
| Network topology | Indoor fingerprint-localization source and target domains; exact AP/device layout requires the full paper |
| Traffic model | Not an ns-3 packet-traffic experiment; not applicable from the abstract |
| PHY/MAC parameters | Wireless fingerprint measurements are used; exact Wi-Fi configuration requires the full paper |
| Simulation time | Simulation and real-world experiments are reported, but duration is not stated in the abstract |
| Random seeds | Not stated in the abstract |
| Evaluation metrics | Localization accuracy and robustness under domain changes; exact metric definitions require the full paper |

For my project, these items are replaced by the explicitly defined offline settings in the A1 proposal: the 32-D SRS input, the 6 m × 6 m laboratory, the three split strategies, the RF/MLP configurations, the evaluation metrics, and repeated training seeds.

---

## Paper 2 — CSI-Fingerprinting Indoor Localization via Attention-Augmented Residual CNN

### Bibliographic Information

- **Title:** CSI-Fingerprinting Indoor Localization via Attention-Augmented Residual Convolutional Neural Network
- **Publication:** *IEEE Transactions on Wireless Communications*, vol. 22, no. 8, pp. 5583–5597, 2023
- **DOI:** [10.1109/TWC.2023.3235449](https://doi.org/10.1109/TWC.2023.3235449)
- **IEEE page:** [IEEE Xplore](https://ieeexplore.ieee.org/document/10018917/)

### Problem

CSI-fingerprinting indoor localization learns a mapping from high-dimensional channel measurements to physical locations. Existing localization systems must extract useful information from complex CSI measurements, which are affected by indoor multipath and environmental conditions.

The paper addresses two related problems:

1. A positioning network may not fully use local and global information in the CSI representation.
2. A tracking system may be too dependent on a specific CSI environment, reducing its generality across environments.

### Importance

The paper is relevant because my project also treats radio measurements as fingerprints of physical position. It demonstrates that the choice of learning model and feature representation can affect both localization accuracy and generality.

My project uses a smaller input representation—32 processed SRS features—and tests whether a lightweight MLP is sufficient. This creates a controlled comparison against the existing RF model without requiring a live gNB, RU, OpenAirInterface, or positioning xApp.

### Challenges

The main challenges are:

- CSI has high dimensionality and contains both local and global spatial information.
- Indoor multipath makes the signal-to-location relationship difficult to model.
- A tracking model may overfit to one CSI environment.
- Localization accuracy and generality must be evaluated together.

The corresponding project challenges are:

- Determine whether a small MLP can learn a useful nonlinear mapping from 32-D SRS features to `(x, y)`.
- Avoid location leakage when splitting highly correlated frames.
- Test unseen coordinates and spatial regions rather than only random frames.
- Measure model size and inference latency in addition to localization error.

### System Model

The paper's system contains a CSI-fingerprint positioning network and a tracking component. The positioning network maps CSI measurements to locations, while the tracking component uses historical information to reduce trajectory error.

The simplified system used in my project is:

```text
Processed uplink SRS dataset
  32-D feature vector + ground-truth (x, y)
                         ↓
       Random / grouped / spatial data splitter
                         ↓
       RF baseline              Lightweight MLP
                         ↓
                 Predicted (x, y)
                         ↓
       Localization accuracy + computational cost
```

### Project Experimental Parameters

These are the planned parameters for my own reproduction experiment, not parameters claimed to be from the paper:

| Item | Planned setting |
|---|---|
| Input | 32-D processed SRS feature vector |
| Label | Two-dimensional coordinate `(x, y)` |
| Environment | One 6 m × 6 m indoor laboratory from the reference project |
| Baseline | Random Forest: 100 trees, maximum depth 12, minimum samples per split 20 |
| Proposed model | MLP: 32 → 64 → 32 → 2, ReLU hidden layers |
| Splits | Random frame split, location-grouped split, spatially separated split |
| Metrics | Mean error, median error, RMSE, P90 error, accuracy within 0.5 m and 1.0 m |
| Efficiency | Model size, training time, and per-sample inference latency |
| Reproducibility | Same partitions and test samples for RF and MLP; train-only normalization |

### Experimental Results

The paper reports experiments showing improved localization performance and generality compared with existing methods. The abstract confirms that the system addresses both positioning accuracy and tracking generality, but it does not include all numerical settings or tables.

For my project, the paper motivates the following measurable comparison:

- Does the MLP improve over RF on held-out coordinates?
- Does the MLP reduce the degradation between random and spatially separated splits?
- Does any accuracy improvement justify the model's training and inference cost?

### Relevance to My Project

| Paper idea | Project implementation |
|---|---|
| CSI fingerprint maps radio features to physical location | SRS feature vector maps to `(x, y)` |
| Deep model extracts useful spatial information | Lightweight MLP learns a nonlinear coordinate mapping |
| Generality across CSI environments | Generalization to held-out coordinates or regions |
| Positioning accuracy and tracking/generalization | Localization error plus split-sensitivity analysis |

### Reproduction-Setting Checklist

| Setting | Status from accessible paper information |
|---|---|
| Network topology | CSI-fingerprinting indoor localization system; exact AP/receiver arrangement requires the full paper |
| Traffic model | Not an ns-3 packet-traffic experiment; not applicable from the abstract |
| PHY/MAC parameters | CSI is used as the radio input; exact carrier, bandwidth, subcarriers, packet configuration, and hardware require the full paper |
| Simulation time | Simulation and real-world datasets are reported, but the abstract does not state the simulation duration |
| Random seeds | Not stated in the abstract |
| Evaluation metrics | Localization accuracy and generality; exact numerical results and metric definitions require the full paper |

The paper therefore provides a useful system-model reference, but it is not a direct ns-3 reproduction target. The A3 experiment will use the controlled SRS settings defined in the project proposal instead.

---

## Comparison of the Two Papers

| Aspect | TransLoc | Attention-Augmented Residual CNN | My Project |
|---|---|---|---|
| Main problem | Domain shift in fingerprint localization | CSI feature learning and generality | Spatial generalization of SRS localization |
| Input | Fingerprint features | High-dimensional CSI | 32-D processed SRS features |
| Main model | Transfer-learning framework | Attention residual CNN plus tracking | RF baseline versus lightweight MLP |
| Main evaluation concern | Source/target domain mismatch | Accuracy and generality across environments | Location leakage and unseen spatial regions |
| Directly reusable? | Problem formulation and split logic | Fingerprint-learning motivation | Experimental design and implementation |

Neither paper is an exact reproduction target for the SRS dataset. Together, they support the argument that indoor radio localization is sensitive to feature distribution and model design, while my project makes a smaller, controlled modification to the A1 reference system.

---

## Revision of the A1 Project Proposal

### What Changed

The A1 proposal originally focused on replacing the reference Random Forest regressor with a lightweight MLP and evaluating spatial generalization. After reviewing the two papers, the A3 project is revised in the following ways:

1. **The evaluation problem is made more explicit.** The project now treats random frame splitting as a potentially optimistic evaluation because frames from the same coordinate are correlated.
2. **Spatial generalization becomes the primary contribution.** Random-split accuracy is retained only as a reproduction and consistency check.
3. **Location-grouped and spatially separated splits are required.** All frames from the same coordinate must remain in one partition, and contiguous regions should be held out when the dataset permits.
4. **The comparison is expanded beyond mean error.** Median error, RMSE, P90 error, threshold accuracy, model size, and inference latency will also be reported.
5. **The scope is limited to within-environment generalization.** The project will not claim cross-room, cross-device, or cross-day generalization because the available dataset does not support those claims.

### Revised Research Question

> Given the same processed 32-dimensional SRS features and the same leakage-resistant data partitions, can a lightweight MLP predict coordinates in unseen indoor spatial regions more accurately and with acceptable computational cost than the Random Forest baseline?

### Revised Hypothesis

The MLP may outperform RF on spatially separated test regions because it can learn a smoother nonlinear mapping from radio features to coordinates. However, this is a testable hypothesis. If the MLP does not improve spatial performance, the result will show that changing the regressor alone is insufficient to overcome the spatial domain shift caused by indoor multipath.

### Limitations

- The project uses one indoor environment and one processed SRS dataset.
- The project does not implement live SRS collection or a real-time positioning xApp.
- Exact replication of the two reviewed papers is outside scope because their datasets and model pipelines differ from the A1 reference system.
- Results should not be generalized to other rooms, devices, days, or radio configurations without additional data.

## References

1. L. Li, X. Guo, M. Zhao, H. Li, and N. Ansari, “TransLoc: A Heterogeneous Knowledge Transfer Framework for Fingerprint-Based Indoor Localization,” *IEEE Transactions on Wireless Communications*, vol. 20, no. 6, pp. 3628–3642, 2021. DOI: [10.1109/TWC.2021.3052606](https://doi.org/10.1109/TWC.2021.3052606).
2. “CSI-Fingerprinting Indoor Localization via Attention-Augmented Residual Convolutional Neural Network,” *IEEE Transactions on Wireless Communications*, vol. 22, no. 8, pp. 5583–5597, 2023. DOI: [10.1109/TWC.2023.3235449](https://doi.org/10.1109/TWC.2023.3235449).
3. P.-Y. Hsieh, C.-C. Chen, N. Nikaein, and R.-G. Cheng, “Uplink SRS-Based Real-Time Indoor Localization System over OpenAirInterface,” manuscript, 2026.
