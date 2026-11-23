# Speaking Notes for Karl's Revised A4 Slides

對應檔案：`/home/karl/Downloads/M11502203_Karl_A4.pdf`，共 15 頁。以下依照這份 PDF 的頁序撰寫，英文為可直接講的內容，中文為提示。目標約 15 分鐘，包含指圖與停頓；這是時間分配，尚未實際計時排練。

## 順序與內容檢查

現在的順序可以保留：先介紹兩個觀察目標與設定，再用 Fig. 6 說明通道特徵，接著用 Fig. 7 比較空間相關性，最後解釋差異測試、限制與下一步。沒有發現投影片數字與既有分析結果不一致。

| 頁數 | 建議修正或補充 |
| --- | --- |
| 1 | `Baseline Reproduce` 改為 `Baseline Reproduction`；期刊名稱前後的字面星號移除。 |
| 3 | 目前流程中的 correlation 是 Fig. 7 分支。講稿會先說明 Fig. 6 從同一個通道矩陣計算功率與 IDFT，避免讓人以為 Fig. 6 也經過 correlation。 |
| 5 | `From Frequency to Delay Time` 建議改為 `From Frequency to Delay Domain`。 |
| 6 | 標題建議用 `Paper Fig. 6 vs. Simulation`，補上 `Qualitative comparison only; different dB references.`，兩邊顏色不能直接當作相同絕對功率比較。 |
| 7、12 | 可在口頭說明即可：RMSE 是無單位的相關性曲線誤差；第 12 頁基準 0.1844 來自五次模擬，前面的 0.1445 來自十次。 |

以下講稿已納入這些說明。原始 PDF 與先前簡報未修改。

## Slide 1 · Title · 0:00–0:30

提示：介紹論文與這次實作範圍即可，不必逐字唸作者、期刊。

Good morning. Today I will present my A4 baseline reproduction, based on the paper “Deep-Learning-Based High-Precision Localization With Massive MIMO.”

My goal is to reproduce the channel observations behind the localization system using ns-3. I focus on two results: the channel maps in Figure 6 and the spatial correlation curve in Figure 7. I will show the comparisons, explain the remaining differences, and discuss what I learned from several controlled tests.

## Slide 2 · Reconstructing Uplink Channel Structure · 0:30–0:55

提示：依序指左邊 Fig. 6 與右邊 Fig. 7。

These are the two results I selected from the paper. Figure 6 shows how channel power changes across antennas, frequency, and delay. Figure 7 shows how similar the channel remains as the user moves.

Both are useful before training a localization model, because the model depends on the spatial structure contained in these channel measurements.

## Slide 3 · Observable and Processing Pipeline · 0:55–1:50

提示：先講共用輸入，再區分 Fig. 6 與 Fig. 7 兩個處理分支。

The input is an uplink channel from the user equipment to the base station. At each user position, I reconstruct a complex channel matrix with one hundred antennas and one hundred frequency tones.

There are two analysis branches. For Figure 6, I calculate frequency-domain power and apply an inverse discrete Fourier transform across tones to obtain delay-domain power.

For Figure 7, shown in this pipeline, I compare pairs of channel snapshots at different spatial separations. I normalize the snapshot pairs, average their complex correlations, and then take the magnitude. This processing order matters because averaging magnitudes would produce a different statistic.

Finally, I compare the simulated result with the paper using the same axes. These are channel-model experiments; they do not require generating an actual uplink pilot waveform.

## Slide 4 · Original Settings and Declared Assumptions · 1:50–3:00

提示：區分論文提供、自己解讀與自己假設的設定，不要把整張表都說成論文原設定。

This table separates paper-aligned settings from simulation assumptions. I use a carrier frequency of three point seven gigahertz and a four-by-twenty-five antenna array, giving one hundred antennas with approximately half-wavelength spacing.

The user moves at zero point one meters per second. Sampling every ten milliseconds gives one millimeter between snapshots. The one-hundred-tone grid uses one-hundred-eighty-kilohertz spacing, based on my interpretation of the LTE frequency grid.

The original Figure 7 baseline uses an indoor mixed-office LOS channel. The assumed base station height is two point five meters, and the user begins at two, two, one point seven three meters, moving along positive x. The assumed path is four point two meters, or forty-two seconds.

For repeatability, I keep the seed fixed and use run numbers one through ten. These generate different channel realizations. Later slides test approximate paper geometry and other assumptions separately.

## Slide 5 · Figure 6: From Frequency to Delay Time · 3:00–4:10

提示：指出這是固定位置的一次觀測，與上一頁移動路徑不同。55.56 ns 可慢一點唸。

For Figure 6, I take a stationary channel snapshot at approximate point A. Its horizontal coordinates are estimated from the paper's schematic, while the user height is one point seven three meters. This is not a surveyed position reported by the authors.

From the complex channel matrix, I first calculate the squared magnitude to obtain the frequency-power map. Then I apply an inverse transform along the frequency axis for each antenna and calculate the delay-power map.

The delay grid must follow the actual tone spacing. One hundred tones at one-hundred-eighty kilohertz give a native delay-bin spacing of about fifty-five point five six nanoseconds. I do not relabel it as fifty nanoseconds based on the nominal bandwidth.

I also check direct channel reconstruction, the transform round trip, and energy conservation. This experiment is a static observation at time zero, rather than a forty-two-second moving simulation.

## Slide 6 · Paper Image vs. Preselected Simulated Run 1 · 4:10–5:30

提示：先指原圖，再指模擬圖；先說可比的結構，再說色階與細節限制。

The left side shows the paper's Figure 6, and the right side shows simulated run one. Run one was selected in advance, rather than chosen because it looked closest to the paper.

In the delay domain, the simulated energy is concentrated near the beginning of the delay window. In the frequency domain, the simulated map is relatively smooth across tones, while power also varies across antenna indices.

However, the simulated frequency map has much weaker contrast than the measured map. For run one, its full frequency-power dynamic range is only about two point two decibels. It does not reproduce the deep dips and detailed patterns in the measurement.

There is also an important plotting difference. My simulated panels use their own global peak as the zero-decibel reference. The paper's absolute color levels are not reconstructed. Therefore, this is a qualitative comparison of channel structure, and matching colors do not establish matching absolute power.

## Slide 7 · Figure 7: One Trajectory Versus One Run · 5:30–6:45

提示：指橫軸、縱軸與兩條線，再解釋 0.2670。

Now I move to Figure 7. The horizontal axis is spatial separation normalized by wavelength, and the vertical axis is channel-correlation magnitude.

This plot compares the paper's reference curve with the preselected LOS simulation run one. The reference curve was extracted from the accepted post-print. I use only the overlapping distance range and do not extrapolate the simulated curve to the final reference point.

The curve RMSE is approximately zero point two six seven. This is a dimensionless discrepancy between correlation curves, not a localization error measured in meters.

The simulation shows spatial decorrelation, but its decay and oscillations differ from the paper. A single simulated realization can have a substantially different shape. To understand how much this depends on the channel realization, the next slide includes all ten runs.

## Slide 8 · Figure 7: Variability Across Channel Runs · 6:45–7:50

提示：指平均線與陰影，強調陰影不是 confidence interval。

Here I summarize ten LOS channel runs. The mean simulated curve has an RMSE of approximately zero point one seven one four, which is smaller than the error of run one.

The shaded region shows the observed minimum and maximum across these ten runs. It is not a confidence interval. The spread shows that the channel realization has a large influence on the curve.

There is also a difference in what is being summarized: the paper reports a measured trajectory, while this mean combines multiple simulated channel realizations. The ensemble is useful for studying variability, but it is not the same experimental object as one measured trajectory.

The remaining question is whether a few controlled changes can explain the mismatch. I start with observation noise.

## Slide 9 · Does Observation Noise Explain the Gap? · 7:50–9:10

提示：先說同一組通道，再比較 noiseless 與 6 dB。不要說已找出論文 SNR。

I compare four observation conditions: no added noise, and one, six, and eleven decibels. Each condition uses the same ten underlying channel runs, so the comparison is paired.

Noise is added to the complex channel observations before the correlation normalization. The SNR is defined using each snapshot's average signal power. This is a simplified observation model, rather than a reconstruction of the paper's receiver and pilot processing.

At six decibels, the mean-curve RMSE decreases from about zero point one seven one four to zero point one two zero seven, an improvement of approximately thirty percent. One decibel makes the mean-curve agreement worse, so adding more noise does not always help.

This test shows that noise affects the comparison. It does not identify the paper's actual SNR, and it does not recover the complete oscillation pattern. Noise is one sensitivity factor, rather than a confirmed explanation of the measured curve.

## Slide 10 · Aligning the Approximate UE Trajectory · 9:10–10:20

提示：說明根據 Fig. 5 比例估計，不是取得作者的精確座標。

Next, I use the paper's Figure 5 to improve the approximate geometry. The schematic provides useful dimensions and the direction of the first scan line, but it does not provide a complete set of surveyed antenna and user coordinates.

I set the approximate user start to one point one, minus zero point six, one point seven three meters. The base station height remains an assumption. The horizontal offset and lateral centering are also declared approximations.

Keeping the positive-x path and the same ten run numbers, the mean-curve RMSE decreases to approximately zero point one four four five, about sixteen percent below the original baseline.

However, only four out of ten individual runs improve. This means better agreement of the ensemble mean does not imply consistent improvement for every realization, or prove that the true experimental geometry has been recovered.

## Slide 11 · Direction Matters; Sample Order Does Not · 10:20–11:25

提示：明確區分「真的換走的方向」與「同一份資料倒序」。

This experiment separates two different questions. First, does changing the physical path direction affect the channel correlation? Second, does reversing the order of the same stored samples affect it?

For the first question, I compare equal-length positive-x and positive-y paths from the same starting point. Near two wavelengths, the mean correlation is about zero point four seven six for x and zero point one one one for y. The y-direction value is lower in all ten matched runs.

For the second question, reversing the same stored samples preserves the correlation magnitude, with numerical differences below seven times ten to the minus thirteen.

Therefore, physical orientation matters in this simulation, while simply reversing sample order does not. This establishes sensitivity to the path, but does not identify the cause of the paper's oscillations or prove consistency across separately generated paths.

## Slide 12 · Small Tests: Height and Array Bearing · 11:25–12:30

提示：先解釋五次基準，再指出最低平均值與最一致改善不是同一設定。

I also perform a small screening test of base station height and array bearing, changing one factor at a time. Each setting uses the same five run numbers.

The reference RMSE here is zero point one eight four four. It differs from the previous geometry result because this slide uses five runs rather than ten. All comparisons within this table use the matched five-run reference.

A height of three meters gives the smallest mean-curve RMSE, about zero point one five zero, but improves only three individual runs. A bearing of minus thirty degrees gives a mean-curve RMSE of about zero point one six five and improves all five individual runs.

These results show that height and array orientation can influence the curve. The sample is small, and I have not tested a combined optimum. They do not tell us the actual height or bearing used in the measurement.

## Slide 13 · What Explains the Remaining Difference? · 12:30–13:30

提示：直接回答有找到影響因素，但沒有唯一原因，不要把假說說成論文結論。

The tests establish that observation noise, approximate geometry, physical path direction, height, and array bearing can change the simulated result.

What remains unreproduced is the detailed measured pattern: the full oscillation structure in Figure 7 and the fine channel-map structure in Figure 6.

Scene-specific multipath, relative path phases, and receiver processing are plausible contributors. However, my experiments do not isolate them as the cause. The paper describes the correlation decay, but does not provide an explicit explanation for each oscillation.

My conclusion is that several assumptions affect agreement, but I have not identified a unique mechanism that explains the measured curve. A better numerical fit alone would not establish that mechanism.

## Slide 14 · Reproducibility and Delivered Evidence · 13:30–14:25

提示：不用逐項唸所有數字，強調別人能依參數、seed、run 重跑。

The submission includes the study notes, flowchart, simulation and analysis source code, numerical results, and reference overlays.

For Figure 7, the original baseline contains ten LOS and ten NLOS runs. The noise study has forty runs, the trajectory study has thirty, and the height-and-bearing study adds twenty runs while reusing five reference runs. Figure 6 uses ten stationary channel observations and one repeat check. These are separate experiment sets, with some deliberately reused controls.

The records include parameters, seeds, run numbers, execution manifests, and data hashes. Validation checks cover channel reconstruction, spectrum conversion, transform consistency, and repeatability. This makes the comparison inspectable and repeatable, including the parts that do not match the paper.

## Slide 15 · Conclusion and Final-Project Connection · 14:25–15:00

提示：結論停在完成範圍與下一步，不要宣稱已完成定位網路復現。

To conclude, I completed reproducible simulation comparisons for two channel observables from the paper. The results capture some channel structure, but do not reproduce every measured detail or establish a unique cause of the differences.

For the final project, my next step is to check whether the simulated radio map is consistent across paths and revisited positions. After that, I can evaluate localization methods such as KNN, random forests, and neural networks.

Thank you.

## 備用回答，不計入 15 分鐘

**Q: Why did you reproduce channel statistics instead of localization accuracy?**

The channel statistics are published results that can be examined before training the localization system. They let me verify the simulation input and its spatial behavior. The full learned localization and fusion system is outside this A4 implementation.

**Q: Is six decibels the correct setting from the paper?**

No. It improves this comparison under my simplified noise model, but that does not identify the measurement's actual SNR or receiver processing.

**Q: Why does the same seed have different curves?**

The seed is fixed, but each run number selects a different random stream sequence. Repeating the same seed, run number, parameters, and processing reproduces the same result in the recorded environment.

**Q: Did you find why the paper's curve oscillates?**

I found factors that change the simulated curve, but not a unique cause of the measured oscillations. Explaining them would require additional scene or measurement information and more targeted tests.

## 查核依據

- [Baseline study and numerical results](study_note.md#5-numerical-results)
- [Figure 6 processing and comparison](figure6_study.md)
- [Noise experiment](noise_study.md)
- [Geometry and direction experiments](geometry_study.md)
- [Matched five-run sensitivity tests](sensitivity_study.md)
- [Simulation and analysis source](src/README.md)

These notes follow the user's revised 15-page PDF. The earlier [presentation notes](presentation.md) refer to the original 18-slide deck and have been preserved.
