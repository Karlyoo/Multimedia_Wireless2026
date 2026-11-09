#!/usr/bin/env python3
"""Build an editable ODP and rehearsal notes using stdlib; plot existing CSVs.

Run from any directory: python3 A3/src/build-presentation.py
Export the ODP to PPTX/PDF with LibreOffice (see presentation.md).
"""
from pathlib import Path
import csv
import zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SLIDES = [
    dict(title="從上行通道指紋到空間泛化", subtitle="A3 Literature Review + Revised Proposal", seconds=30,
         bullets=["文獻：Deep-Learning-Based High-Precision Localization With Massive MIMO", "IEEE TMLCN · Vol. 2 · pp. 19–33 · 2024", "謝秉祐 Ping-Yu Hsieh ｜ M11502203"],
         takeaway="主軸：先驗證通道的空間結構，再比較定位模型。", source="Tian et al. · DOI: 10.1109/TMLCN.2023.3334712",
         notes="今天介紹一篇以上行 massive MIMO 通道進行室內定位的論文。我會先說明問題與系統模型，再整理原文實驗及復現所需設定，最後說明我的 proposal 如何修改，以及 A4 準備復現哪一張圖。主軸是先確認模擬通道有合理的空間結構，再討論機器學習定位。"),
    dict(title="01 研究問題與重要性", subtitle="Problem / Importance", seconds=45,
         bullets=["問題：能否由 UE 的上行通道指紋，估計室內 2D 座標？", "價值：支援室內機器人與定位服務，兼顧資料和模型成本。", "論文關注：特徵、網路規模、不確定性，以及空間取樣密度。", "我的延伸：未見過的位置上，MLP 是否仍優於 Random Forest？"],
         takeaway="論文的定位方法 ≠ 本專題的 RF／MLP 比較；後者是延伸研究。", source="Paper: Sections II–V · Project: A3/proposal.md",
         notes="這篇論文的核心問題，是把上行通道當成位置的指紋，從指紋推估座標。室內有多路徑，雖然增加訊號複雜度，也能提供與位置有關的資訊。除了準確度，實際應用還要考慮蒐集多少資料，以及模型有多大。我的研究不是完整照搬論文所有網路，而是保留 A1 的 RF 和輕量 MLP 比較，進一步問：排除訓練位置後，模型是否仍能定位？這是我的延伸，不是原文已經完成的實驗。"),
    dict(title="02 最大挑戰：樣本多，不等於位置資訊多", subtitle="Challenges", seconds=55,
         bullets=["鄰近位置的通道可能高度相關：隨機分割可能高估泛化能力。", "輸入維度高：100 根天線 × 100 個頻率取樣點。", "特徵處理可能洩漏：標準化、PCA 只能 fit 訓練集。", "模擬落差：統計式室內模型不等於原論文的量測場地。"],
         takeaway="評估時，同時控制「取樣密度」與「訓練／測試空間分離」。", source="Paper: Sections IV–V · Spatial holdout: project extension",
         notes="第一個挑戰是空間相關。如果相鄰位置的通道非常像，把連續影格隨機分成訓練和測試，測試點可能幾乎就在訓練點旁邊。這種分數不一定代表模型可以處理新的區域。第二個挑戰是維度，天線和頻率組合會產生很大的輸入。第三個是資料洩漏，像 PCA 和標準化都不能先用完整資料計算。最後，ns-3 的統計式通道不是原場地的數位分身。因此我要把取樣密度、分割方式與模擬假設分開控制，避免把不同原因混在一起。"),
    dict(title="03 原論文的 System Model", subtitle="Environment / Inputs / Outputs / Metrics", seconds=60,
         cards=[("環境與方向", "靜態室內場景；機器人攜帶 UE\n單天線 UE → 100 天線 BS\n上行 pilot 量測，不是下行"),
                ("輸入與特徵", "複數通道 + 真實位置標籤\n天線域 covariance／CIR\n鄰域平均與 subarray 處理"),
                ("輸出與評估", "2D 座標與不確定性估計\n定位誤差分布\n不確定性：negative log-likelihood")],
         takeaway="LTE-like OFDM pilot 量測，不應直接稱為標準 NR-SRS 實作。", source="Paper: Sections II–IV · Equation (1)",
         notes="系統模型是一台單天線 UE 在室內移動，向基地台傳送上行 pilot，基地台使用一百根天線量測通道。定位系統的輸入是複數通道與對應位置，特徵包含天線域的 covariance 和延遲域的 CIR。原文也研究鄰域平均和子陣列等處理方法。輸出除了二維座標，也包含不確定性，所以除了定位誤差還有負對數概似評估。要特別注意，它是 LTE-like OFDM 的量測配置，不能因為是上行 pilot，就說成已經實作 NR SRS。我的第一階段會使用理想通道係數，不包含真正的 SRS 接收估測。"),
    dict(title="04 原論文實驗：哪些設定需要保留？", subtitle="Original measured setup — not an ns-3 experiment", seconds=55,
         rows=[("載波／頻寬", "3.7 GHz ／ 20 MHz"), ("天線", "BS：4 × 25、約 0.5λ 間距；UE 高 1.73 m"), ("頻率取樣", "100 個 pilot tones；LTE-like 每 12 個子載波取樣"), ("移動與記錄", "0.1 m/s；每 10 ms 一筆 ≈ 每 1 mm 一筆"), ("資料規模", "4.2 × 2.5 m²；75 條軌跡；302,500 筆 snapshots"), ("未確立的欄位", "無原始 ns-3 seeds／runs；不虛構 scheduler、MCS、HARQ")],
         takeaway="Traffic 是週期性 pilot 量測；不是需要補上一個 UDP 工作負載。", source="Paper: Section IV-A, Figs. 4–5 · Detailed qualifications: study_note.md §4.2",
         notes="為了讓 A4 可以對照，這頁整理原文的重要量測條件。載波是三點七 GHz，頻寬二十 MHz，基地台是四乘二十五陣列。UE 每秒移動零點一公尺，每十毫秒記一筆，所以相鄰樣本大約只差一毫米。資料共有七十五條軌跡、三十萬兩千五百筆。這些數字也說明，資料筆數和有效空間資訊不能直接畫等號。原文是實測，不是 ns-3 模擬，所以沒有可以直接照抄的模擬 seed 或 duration。沒有確認的 MAC 參數要標成未提供，而不是自行補上一套參數並稱為原文設定。"),
    dict(title="05 論文結果與本專題的啟發", subtitle="Experimental Results — qualitative findings", seconds=60,
         rows=[("原文觀察", "對本專題的啟發"), ("特定實測場景達到公分級定位", "證明通道指紋有潛力；不代表我的模擬必然同樣準"), ("特徵與子陣列設計影響表現", "需要固定、可追溯的特徵，再公平比較 RF／MLP"), ("空間訓練密度不足時表現下降", "加入密度實驗與 spatial holdout，不能只報隨機切分"), ("Fig. 7 顯示沿軌跡的通道相關性", "先復現可觀察的通道統計量，作為 A4 起點")],
         takeaway="Fig. 7 小位移高度相關；約 λ/8 的描述只屬於該次量測，不是通則。", source="Paper: Sections IV–V · Figs. 7, 8, 14, 17",
         notes="原文在特定室內量測資料上報告公分級定位，但我不會把這個數字當成模擬必須達到的標準，因為場地、雜訊和資料分割不同。對我的計畫更直接的啟發有三個。第一，特徵和子陣列設計會影響表現，因此要先固定輸入，再比較模型。第二，訓練位置密度會影響結果，所以不能只報一個隨機切分的分數。第三，Fig. 7 提供通道隨位置改變的相關性，是比較容易在 ns-3 建立對照的結果。原文對小位移、約八分之一波長內高度相關的描述，只能解讀成這次量測的觀察，不是任何室內模型都必須有相同門檻。"),
    dict(title="06 A4：選 Fig. 7，而不是整套深度學習", subtitle="One published result / Same observable and axes", seconds=65,
         bullets=["目標：沿 UE 軌跡的 empirical spatial correlation。", "橫軸：位移 Δd / λ，範圍 0–2；縱軸：相關量 |ρ|。", "每個位置把「天線 × 頻率」攤平成複數向量 h。", "先算正規化複數內積 → 跨位置配對平均 → 最後取絕對值。"],
         formula="ρₖ = meanᵢ [(hᵢᴴ hᵢ₊ₖ) / (‖hᵢ‖₂ ‖hᵢ₊ₖ‖₂)]",
         takeaway="這是通道統計量的復現；不是原文定位準確度或完整神經網路的復現。", source="Paper: Equation (11), Fig. 7 · Original-curve overlay still pending",
         notes="A4 只要求選一個已發表結果，因此我選 Fig. 7 的空間相關曲線，而不是一次重做整套深度學習系統。橫軸是以波長正規化的位移，範圍零到兩個波長，縱軸是相關量的大小。計算時先把每個位置的所有天線與頻率通道攤平成向量，對相隔固定距離的位置做正規化複數內積，接著對有效配對取平均，最後才取絕對值。順序很重要，先對每一對取絕對值再平均，會變成不同的統計量。完成時還要取得原圖、核對座標並疊圖。這個結果是通道驗證，不能拿來宣稱已經重現定位精度。"),
    dict(title="07 ns-3 復現規劃：對齊與差異", subtitle="Planned configuration — assumptions are explicit", seconds=55,
         rows=[("盡量對齊原文", "3.7 GHz；4 × 25 BS；100 tones；0.1 m/s；10 ms"), ("統計通道替代", "ns-3.48：InH-OfficeMixed；LOS 主實驗／NLOS 敏感度"), ("自行設定的幾何", "BS (0,0,2.5) m；UE 從 (2,2,1.73) m 向 +x 移動"), ("預計長度／重複", "4.2 m → 42 s；seed 20261109；runs 1–10；stream 1"), ("未建模部分", "原場地散射幾何、RF 鏈誤差、接收雜訊、真實 pilot 估測")],
         takeaway="初期直接取通道係數：不含封包流量、scheduler 或標準 SRS 波形解碼。", source="Project settings: study_note.md §4.4 · Not claimed as original paper parameters",
         notes="對齊的部分是載波、陣列大小、頻率取樣數、速度和取樣間隔。不相同的部分要明列：我會使用 ns-3 的 InH-OfficeMixed 統計模型，先做 LOS，再用 NLOS 當敏感度分析；基地台與 UE 座標則是我的假設。四點二公尺路徑以每秒零點一公尺移動，推得四十二秒，這不是原文回報的總量測時間。規劃跑十個 channel RNG runs。第一階段直接匯出理想通道，不跑 UDP 或 MAC scheduler；因此無法重現 RF 鏈、接收雜訊和真實 pilot 估測誤差，這些都會放進差異分析。"),
    dict(title="08 目前進度：可以跑，但尚未完成復現", subtitle="Local readiness check — not the published reference curve", seconds=65,
         chart=True,
         bullets=["已完成：ns-3.48 建置與通道測試。", "短路徑：2.56 s／257 snapshots；僅 run 1。", "已檢查：ρ(0)=1；固定 RNG 可重現。", "仍需：42 s × 10 runs、原圖疊圖、差異分析。"],
         takeaway="目前沒有原文曲線疊圖；LOS 在 2λ 仍高度相關，需解釋模型差異。", source="Local data: A3/results/{los,nlos}/correlation.csv · environment.md",
         notes="目前可以確認的是環境和通道匯出流程已經跑通，不是 A4 已經完成。左邊是本機短路徑的 LOS 和 NLOS 結果，每條都只用一個 run，總長二點五六秒、兩百五十七筆。已檢查零位移相關量為一、固定 RNG 重跑一致，以及匯出通道的數值檢查。圖上沒有原論文曲線，也沒有信賴區間，所以不能說匹配原文。尤其 LOS 到兩個波長仍有很高相關性，這正是要檢查通道模型與量測場景差異的地方。下一步是完整路徑、十個 runs、取得原圖並疊圖，再分析差異，而不是為了讓曲線好看而默默調參。"),
    dict(title="09 A1 → A3：Proposal 改了什麼、為什麼？", subtitle="Revised proposal / What changed and why", seconds=65,
         rows=[("原本 A1", "修訂後 A3 ／ 原因"), ("依賴量測的 32-D SRS 資料", "以 ns-3 模擬上行通道為主，支援全模擬流程"), ("以原稿 RF 數字為參考", "改採已發表論文的 Fig. 7，建立可比對的通道結果"), ("既有 SRS 特徵", "明確定義 covariance／train-only PCA，不混用舊特徵語意"), ("RF → 輕量 MLP；grouped／spatial splits", "保留；新增密度、空間 buffer、跨路徑一致性檢查")],
         takeaway="研究核心沒有換：公平比較 RF／MLP 在未見位置的定位表現。", source="Original: A1/proposal.md · Revised: A3/proposal.md §6",
         notes="proposal 最重要的改動，是把原本依賴量測 SRS 資料的流程，改成以 ns-3 模擬上行通道為主，所以不需要操作實體無線設備。參考依據改成已發表的 Transactions 論文，A4 則選有明確定義的 Fig. 7。輸入來源變了，特徵也必須重新定義，即使最後經 PCA 變成三十二維，也不是原本的三十二維 SRS 特徵。沒有改的是研究核心，仍然比較 RF 和輕量 MLP，而且 grouped 和 spatial split 原本 A1 就有，不能說是這次新加入的。新加入的是密度、空間 buffer 和跨路徑一致性驗證，原因是避免資料或模擬器本身造成假象。"),
    dict(title="10 後續實驗與結論", subtitle="A3 → A4 → Final", seconds=45,
         bullets=["A3：理解上行系統模型、實驗設定與空間取樣問題。", "A4：重建 Fig. 7 同一統計量，疊圖並解釋差異。", "Final：驗證 2D radio map → KNN／RF baseline → 輕量 MLP。", "固定輸入與分割；報告誤差 CDF、RMSE、P90、模型大小和延遲。"],
         takeaway="不預設 MLP 一定贏；可重現、可解釋的負結果也有價值。", source="Reference: Tian et al., IEEE TMLCN 2 (2024), 19–33 · DOI: 10.1109/TMLCN.2023.3334712",
         notes="總結來說，A3 讓我把問題從單純換模型，收斂成先驗證資料與通道的空間結構。A4 先做 Fig. 7 的通道結果對照，Final 再驗證二維 radio map，建立 KNN 和 RF baseline，最後比較輕量 MLP。比較時固定輸入和資料切分，報告誤差分布、RMSE、P90 與運算成本。模擬資料不能直接支持真實世界公分級定位，也不預設 MLP 一定贏。只要設定透明、結果能重跑，而且能說明差異，即使結果沒有變好也能回答研究問題。謝謝。"),
]


def xmltext(text, style="Body"):
    return "".join(f'<text:p text:style-name="{style}">{escape(line) or " "}</text:p>' for line in text.split("\n"))


def frame(x, y, w, h, text, style="Body", box="Plain"):
    return (f'<draw:frame draw:style-name="{box}" svg:x="{x}cm" svg:y="{y}cm" '
            f'svg:width="{w}cm" svg:height="{h}cm"><draw:text-box>'
            + xmltext(text, style) + '</draw:text-box></draw:frame>')


def rectangle(x, y, w, h, style):
    return f'<draw:rect draw:style-name="{style}" svg:x="{x}cm" svg:y="{y}cm" svg:width="{w}cm" svg:height="{h}cm"/>'


def make_plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5), dpi=180)
    for key, label, color in [("los", "LOS / run 1", "#087f8c"), ("nlos", "NLOS / run 1", "#ed8943")]:
        with (ROOT / "results" / key / "correlation.csv").open() as f:
            rows = list(csv.DictReader(f))
        ax.plot([float(r['distance_lambda']) for r in rows], [float(r['abs_rho']) for r in rows], label=label, color=color, lw=2.8)
    ax.set(xlim=(0, 2), ylim=(0, 1.05), xlabel=r"Separation $\Delta d / \lambda$", ylabel=r"$|\rho|$", title="Local readiness only — 2.56 s, 257 snapshots")
    ax.grid(alpha=.2)
    ax.legend(loc="lower left")
    fig.tight_layout()
    out = ROOT / "results" / "presentation-readiness.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def build(english=False):
    slides = SLIDES
    if english:
        from presentation_english import SLIDES as slides
    stem = 'A3-literature-review-en' if english else 'A3-literature-review'
    assert sum(s['seconds'] for s in slides) == 600
    chart = make_plot()
    ns = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
          'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
          'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
          'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
          'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
          'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
          'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" '
          'xmlns:xlink="http://www.w3.org/1999/xlink"')
    textstyles = []
    for name, size, color, weight in [('Title', 29, '#142d4e', 'bold'), ('Sub', 14, '#087f8c', 'normal'), ('Body', 21, '#213047', 'normal'), ('Cell', 17, '#213047', 'normal'), ('Card', 18, '#213047', 'normal'), ('CardTitle', 22, '#087f8c', 'bold'), ('Take', 17, '#ffffff', 'bold'), ('Foot', 9, '#607080', 'normal'), ('Note', 13, '#213047', 'normal')]:
        textstyles.append(f'<style:style style:name="{name}" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0.28cm" fo:line-height="125%"/><style:text-properties fo:font-family="Noto Sans CJK TC" style:font-family-asian="Noto Sans CJK TC" fo:font-size="{size}pt" style:font-size-asian="{size}pt" fo:color="{color}" fo:font-weight="{weight}" style:font-weight-asian="{weight}"/></style:style>')
    graphics = ''.join(f'<style:style style:name="{name}" style:family="graphic"><style:graphic-properties draw:stroke="none" draw:fill="{fill}" draw:fill-color="{color}" fo:padding="0cm" draw:textarea-vertical-align="top"/></style:style>' for name, fill, color in [('Plain', 'none', '#ffffff'), ('Navy', 'solid', '#142d4e'), ('Teal', 'solid', '#087f8c'), ('Pale', 'solid', '#eff4f8'), ('White', 'solid', '#ffffff')])
    automatic = ''.join(textstyles) + graphics + '<style:style style:name="Page" style:family="drawing-page"><style:drawing-page-properties draw:fill="solid" draw:fill-color="#ffffff"/></style:style>'
    pages = []
    md = ['# A3 — 10 分鐘簡報與中文講稿', '', '共 11 頁；建議時間合計 10:00（不含 Q&A）。投影片為中文，保留必要英文術語。', '', '主文來源：[文獻筆記](study_note.md)、[修訂 proposal](proposal.md)、[本機驗證](environment.md)。', '', 'PowerPoint 的備忘稿區亦附逐頁講稿。第 9 頁是本機短路徑試跑，並非已完成的 A4 復現。', '']
    if english:
        md = ['# A3 — English Presentation and Speaker Notes', '', '11 slides; suggested timing totals 10:00, excluding Q&A. Actual delivery time depends on speaking pace; rehearse before presenting.', '', 'Sources: [Literature review](study_note.md), [revised proposal](proposal.md), [local verification](environment.md).', '', 'Speaker notes are embedded in the PowerPoint. Slide 9 shows local readiness checks, not a completed A4 reproduction.', '']
    elapsed = 0
    for idx, s in enumerate(slides, 1):
        body = rectangle(0, 0, 33.867, .22, 'Teal')
        body += frame(1.2, .65, 31.3, 1.55, s['title'], 'Title')
        body += frame(1.25, 2.2, 31, .7, s['subtitle'], 'Sub')
        if s.get('cards'):
            for i, (title, content) in enumerate(s['cards']):
                x = 1.25 + i * 10.5
                body += rectangle(x, 4.0, 10, 9.5, 'Pale')
                body += frame(x+.4, 4.6, 9.2, 1.4, title, 'CardTitle')
                body += frame(x+.4, 6.3, 9.2, 6.8, content, 'Card')
        elif s.get('rows'):
            y = 3.65
            rh = min(2.1, 11.5 / len(s['rows']))
            for i, (left, right) in enumerate(s['rows']):
                body += rectangle(1.25, y, 31.3, rh-.1, 'Pale' if i % 2 == 0 else 'White')
                body += frame(1.6, y+.2, 8.5, rh-.2, left, 'Cell')
                body += frame(10.4, y+.2, 21.6, rh-.2, right, 'Cell')
                y += rh
        elif s.get('chart'):
            body += '<draw:frame draw:style-name="Plain" svg:x="1.1cm" svg:y="3.8cm" svg:width="20cm" svg:height="11.11cm"><draw:image xlink:href="Pictures/readiness.png" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>'
            for i, bullet in enumerate(s['bullets']):
                body += frame(21.5, 4.1+i*2.5, 11, 2.2, bullet, 'Card')
        else:
            for i, bullet in enumerate(s['bullets']):
                body += frame(1.5, 3.7+i*2.2, 30.5, 1.85, '•  ' + bullet, 'Body')
            if s.get('formula'):
                body += frame(2.0, 13.0, 30, 1.0, s['formula'], 'Card')
        body += rectangle(0, 16.0, 33.867, 1.7, 'Navy')
        body += frame(1.2, 16.32, 31.2, 1.2, s['takeaway'], 'Take')
        body += frame(1.2, 18.05, 29.9, .65, s['source'], 'Foot')
        body += frame(31.5, 18.05, 1.7, .65, f'{idx:02d} / 11', 'Foot')
        timing = f'Suggested time: {s["seconds"]} seconds' if english else f'建議 {s["seconds"]} 秒'
        notes = (f'<presentation:notes><draw:frame presentation:class="notes" svg:x="1cm" svg:y="1cm" svg:width="24cm" svg:height="15cm"><draw:text-box>' + xmltext(f'{timing}\n{s["notes"]}', 'Note') + '</draw:text-box></draw:frame></presentation:notes>')
        pages.append(f'<draw:page draw:name="Slide{idx}" draw:style-name="Page" draw:master-page-name="Default">{body}{notes}</draw:page>')
        start = f'{elapsed//60}:{elapsed%60:02d}'
        elapsed += s['seconds']
        end = f'{elapsed//60}:{elapsed%60:02d}'
        heading = f'## {idx}. {s["title"]} ({start}–{end}; {s["seconds"]} seconds)' if english else f'## {idx}. {s["title"]}（{start}–{end}；{s["seconds"]} 秒）'
        md.extend([heading, '', s['subtitle'], ''])
        for bullet in s.get('bullets', []):
            md.append('- ' + bullet)
        for left, right in s.get('rows', s.get('cards', [])):
            md.append('- ' + left + (': ' if english else '：') + right.replace('\n', '; ' if english else '；'))
        md.extend(['', '> ' + s['takeaway'], '', 'Speaker notes:' if english else '講稿：', '', s['notes'], '', ('Source: ' if english else '來源：') + s['source'], ''])
    content = f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {ns} office:version="1.2"><office:automatic-styles>{automatic}</office:automatic-styles><office:body><office:presentation>{"".join(pages)}</office:presentation></office:body></office:document-content>'
    styles = f'<?xml version="1.0" encoding="UTF-8"?><office:document-styles {ns} office:version="1.2"><office:styles/><office:automatic-styles><style:page-layout style:name="Layout"><style:page-layout-properties fo:page-width="33.867cm" fo:page-height="19.05cm" style:print-orientation="landscape"/></style:page-layout></office:automatic-styles><office:master-styles><style:master-page style:name="Default" style:page-layout-name="Layout"/></office:master-styles></office:document-styles>'
    manifest = '<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.presentation"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="Pictures/readiness.png" manifest:media-type="image/png"/></manifest:manifest>'
    with zipfile.ZipFile(ROOT / (stem + '.odp'), 'w') as z:
        z.writestr('mimetype', 'application/vnd.oasis.opendocument.presentation', compress_type=zipfile.ZIP_STORED)
        z.writestr('content.xml', content)
        z.writestr('styles.xml', styles)
        z.writestr('META-INF/manifest.xml', manifest)
        z.write(chart, 'Pictures/readiness.png')
    md.extend(['## 重建與匯出', '', '```bash', 'python3 A3/src/build-presentation.py', 'libreoffice -env:UserInstallation=file:///tmp/a3-slides-lo --headless --convert-to pptx --outdir A3 A3/A3-literature-review.odp', 'libreoffice -env:UserInstallation=file:///tmp/a3-slides-lo --headless --convert-to pdf --outdir A3 A3/A3-literature-review.odp', '```', '', '## Q&A 備用', '', '- **這是上行還是下行？** 上行：UE 傳送，BS 接收。', '- **這是標準 NR SRS 嗎？** 不是；初期直接擷取通道係數，沒有 SRS 波形估測。', '- **為何不用 UDP？** 選的 observable 是通道相關性，原文是 pilot 量測；channel-only 實驗不需要 application traffic。', '- **A4 已完成嗎？** 尚未；短路徑檢查已完成，完整多 runs 與原文疊圖待做。', '- **和 A1 還有關係嗎？** 保留 RF／MLP 與空間泛化問題，變更資料來源並增加通道驗證。', '- **曲線不同怎麼辦？** 報告設定差異，分析統計模型、幾何、RF 與雜訊因素，不宣稱已重建實體場地。', ''])
    if english:
        # Replace the shared Chinese export/FAQ appendix, keeping all slide notes.
        md = md[:md.index('## 重建與匯出')]
        md.extend(['## Rebuild and Export', '', '```bash', 'python3 A3/src/build-presentation.py --english', f'libreoffice -env:UserInstallation=file:///tmp/a3-slides-lo --headless --convert-to pptx --outdir A3 A3/{stem}.odp', f'libreoffice -env:UserInstallation=file:///tmp/a3-slides-lo --headless --convert-to pdf --outdir A3 A3/{stem}.odp', '```', '', '## Q&A Preparation', ''])
        from presentation_english import FAQ
        md.extend(f'- **{question}** {answer}' for question, answer in FAQ)
        md.append('')
    (ROOT / ('presentation-en.md' if english else 'presentation.md')).write_text('\n'.join(md), encoding='utf-8')
    print('Built 11 slides; rehearsal timing 600 seconds; notes and ODP ready.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--english', action='store_true', help='Build separate English slides and notes.')
    build(english=parser.parse_args().english)
