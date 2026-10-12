# A2 XR Pose ns-3 簡報講稿（約 8–10 分鐘）

## Slide 1 — Title（約 30 秒）

這份作業的目標是完成 ns-3 安裝與執行，並實作一個自己的流量模型。我選擇的是 3GPP TR 26.926 第 5.9.2 節的 XR Pose uplink model，模擬 XR 裝置將最新姿態回報給伺服器。

## Slide 2 — Setup and reproducibility（約 1 分鐘）

本次使用 ns-3.44，執行平台是 Ubuntu 22.04.5、x86-64。模擬期間為 60 秒，總共預期產生 6,000 個封包。建置時遇到的問題是受限制環境中的 ccache 目錄無法寫入，因此以 `CCACHE_DISABLE=1` 完成建置。繪圖時原本也出現 Matplotlib GUI 與 Wayland 警告，後來改用 Agg 非 GUI backend。

## Slide 3 — 3GPP model（約 1 分鐘）

規格定義四個重點：Pose 每 1 ms 提供給應用程式、封包總長度 100 bytes、每 10 ms 傳送最新 Pose，以及上行延遲目標不超過 10 ms。UDP、Point-to-Point 拓撲與固定 Pose 都是本實驗的選擇。規格沒有要求位置一定要改變，因此基準模型先固定位置與朝向，只讓取樣時間更新。

## Slide 4 — Topology and packet（約 1.5 分鐘）

拓撲只有一台 XR 裝置和一台伺服器，以 10 Mbps、單向傳播延遲 1 ms 的 Point-to-Point 鏈路連接。100-byte IP packet 包含 20-byte IPv4、8-byte UDP、12-byte自訂 Report header，以及 60-byte Pose payload。Report header 的序號用來檢查遺失，send timestamp 用來算網路延遲；Pose 內的 sample timestamp 用來算收到時的 Pose age。

## Slide 5 — PMF and CDF（約 1 分鐘）

左邊顯示封包大小分布，所有封包都是 100 bytes，所以 PMF 在 100 bytes 的機率為 1，CDF 也在 100 bytes 從 0 跳到 1。下方的 inter-arrival 分布相同，所有間隔都是 10 ms。圖形雖然簡單，但這正是固定大小、固定週期模型應該得到的結果。

## Slide 6 — Run evidence（約 1.5 分鐘）

左圖顯示前 20 個封包，每條線是一包，間隔固定為 10 ms。中間以每秒為統計窗口，實測 IP offered rate 全程為 80 kbps，等於 100 bytes 乘 8 bits 再乘每秒 100 包。右邊延遲 CDF 在 1.0816 ms 就達到 100%，遠低於紅色的 10 ms 目標。

## Slide 7 — PCAP（約 1 分鐘）

PCAP 顯示封包時間為 1.000、1.010、1.020 秒，確認週期是 10 ms。鏈路層擷取長度是 102 bytes，是因為 Point-to-Point PCAP 在 100-byte IPv4 packet 外還有 2-byte PPP header。Wireshark 可以用 `udp.port == 5000` 過濾，確認 IPv4 total length 為 100、UDP length 為 80、UDP payload 為 72 bytes。

## Slide 8 — Conclusion（約 1 分鐘）

最後共傳送並收到 6,000 個封包，遺失率為 0；封包大小與週期完全符合設定；平均與最大延遲都是 1.0816 ms，所有封包均符合 10 ms 目標。選擇 UDP 是因為 Pose 很快會過期，收到下一筆新 Pose 比重傳舊 Pose 更有價值。後續才會加入移動、無線損失、jitter 或壅塞。
