# 更新日誌 (Changelog)

<p align="center">
  <strong><a href="CHANGELOG.md">English</a></strong> |
  <strong><a href="CHANGELOG.zh-CN.md">简体中文</a></strong> |
  <strong>繁體中文</strong>
</p>

本專案的所有重要變更與版本更新記錄均歸檔於此。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
並嚴格遵循 [語意化版本規範 (SemVer)](https://semver.org/lang/zh-TW/)。

## [1.2.0] - 2026-09-12 (B2.0)

### 新增與增強 (理光 GR III 色彩科學深度重構 - 第一階段)
- **硬體級白平衡偏移注入與現場儲存/還原 (Hardware White Balance Shifts)**:
  - 針對理光 GR3 底片色調底層物理特性，在 `RicohHook` 中深度注入硬體級白平衡偏移呼叫：`setLightBalanceForWhiteBalance`（LB 琥珀/藍色溫偏移，範圍 $[-14, +14]$）與 `setColorCompensationForWhiteBalance`（CC 綠色/洋紅色彩補償，範圍 $[-14, +14]$）。
  - **理光 GR 正片**: 注入 $LB=+2$ (琥珀暖調), $CC=-1$ (微洋紅補償)，重現理光 GR3 正片特有的暖陽基底。
  - **理光負片**: 注入 $LB=+4$ (明顯暖琥珀), $CC=-2$ (品紅微調)，營造泛黃暖調的底片底色。
  - **正負逆沖**: 注入 $LB=-3$ (冷青藍), $CC=+2$ (顯色綠調)，呈現戲劇化冷沖印風格。
  - **黑白濾鏡**: 保持 $LB=0, CC=0$ 原生灰階平衡。
  - **使用者原生現場保護與零殘留還原**: 首次啟動濾鏡時自動儲存使用者原先設定的相機白平衡偏移，在切換或退出應用程式時精準還原，杜絕機身全局色彩污染。
- **1024 階 10-bit Gamma 曲線內嵌曝光補償烘焙 (EV-Baking Tone Curves)**:
  - 避開呼叫 `setExposureCompensation()` 對機身實體曝光轉盤與測光標尺的干擾，直接將感光量比率 $2^{\Delta \text{EV}}$ 烘焙入 1024 點 10-bit 非線性 Gamma 表：
    - **理光 GR 正片**: 內嵌 -0.33 EV 曝光壓暗烘焙，有效抑制高光死白，增強天空藍與高光濃郁色彩厚度。
    - **森山大道風**: 內嵌 -0.33 EV 曝光壓暗烘焙，加劇強反差街頭黑白張力。
    - **理光負片**: 內嵌 +0.33 EV 曝光提亮烘焙，配合消光黑位提升，模擬負片超大寬容度的高光滾降與通透柔和暗部。
- **全新高低光分色校準 3×3 顏色矩陣 (Split-Toning Normalized Matrices)**:
  - 重新最佳化並應用嚴格列和正規化（$\sum_j M_{ij} = 1024$）的 Q10 矩陣，灰階無色偏。
  - 依託 BIONZ X ISP 的「RAW Bayer $\rightarrow$ 前置 WB 偏移 $\rightarrow$ Demosaic $\rightarrow$ 1024 階非線性 Gamma $\rightarrow$ 後置 3×3 色彩矩陣」管線機制：
    - 前置 WB 注入暖調，進入非線性 S 曲線後高低光自然解耦，後置矩陣對高光壓制多餘洋紅並強化青綠飽和度，首次在索尼相機上完美重現理光 GR3 特有的**「暗部偏冷青、亮部微泛琥珀」高低光分色 (Split Toning)**。

## [1.1.4] - 2026-09-11 (B1.4)

### 修復與架構加固 (基於 PMCA 開發聖經規範)
- **徹底消除底層 Native `DeviceBuffer` DMA 記憶體流失**:
  - 在 `RicohHook.applyHook` 中呼叫 `CameraEx.setExtendedGammaTable()` 後立即呼叫 `GammaTable.release()`。
  - 增加嚴格的 `try-finally` 例外保護，確保 2KB 的底層實體 DMA 顯示記憶體緩衝在拋出例外時亦能無條件釋放回 Linux 核心與 V4L2 驅動程式，徹底根除頻繁按 Fn 調節參數、切換選單或回放相片時的偶發當機假死問題。
- **單次不可分割 (Atomic) `setParameters` 提交 (修復參數重疊覆蓋)**:
  - 剔除了在 `applyHook` 中對 `CreativeStyleController` 和 `DROAutoHDRController` 的二次/三次 Binder IPC 間接呼叫，避免由於重新讀取機身備份而誤將中性 0 偏移覆蓋。
  - 將色彩模式、對比度 0、飽和度 0、銳利度 0、DRO 關、HDR 關、效果關與 RGB 矩陣全部合併入單次原子化 `setParameters(p1)` HAL 提交。
- **消除撥輪切換濾鏡時的取景器黑屏與閃爍**:
  - 在 `PictureEffectPlusController.setPlusPictureEffect` 注入 `RicohHook.isRicohPreset(value)` 智慧檢查：
  - 在理光 5 大預設間快速切換轉盤時，略過原廠繁瑣的過渡重設邏輯（原邏輯會清空色調曲線並寫入單位矩陣 2ms 導致取景器黑閃），實現零延遲平滑切換，並減少 50% 的 Binder IPC 通訊開銷。
- **硬體色彩矩陣旁路重設**:
  - 在 `RicohHook.resetHook` 中向 `setRGBMatrix` 傳入 `null` 而非全 0 或單位矩陣，觸發 BIONZ X ISP 底層硬體乘法器旁路邏輯，降低功耗。
- **文案錯別字修正**:
  - 修正動態提示中 `"森山大道风粗粞高对比黑白"` 為 `"森山大道風粗粝高對比黑白"`。

## [1.1.3] - 2026-09-10 (B1.3)

### 修復與色彩重構
- **阻斷濾鏡基底與相機風格外觀疊加 (修復「清澈/Clear」等風格疊加發灰發暗)**:
  - 修復了理光預設被機身原先設定的風格外觀（如清澈 Clear、生動 Vivid 或對比度偏移）二次疊加污染的問題。
  - 在 `RicohHook.applyHook` 中強制將底層色彩模式鎖定為標準 (`standard`)，重設對比/飽和/銳利度偏移為 0，並同步更新控制器狀態，確保在任何機身初始設定下均有一致準確的理光色彩。
- **全新重構 5 款濾鏡底片級 Gamma 動力學曲線 (告別數位生硬高反差)**:
  - **理光 GR 正片**: 拋棄生硬 Sigmoid 曲線，採用溫和底片動力學曲線（中灰斜率降至 1.25，暗部提升保護層次，高光平滑至 1020），重現通透暗部與豐富寬容度。
  - **理光負片**: 軟化中灰反差（斜率 1.08），保留消光黑位（35）與高光滾降（985），呈現經典底片放鬆感。
  - **高對比黑白**: 調整反差斜率至 1.81，既保持街頭高密度黑白視覺張力，又找回瀝青與暗部原本死黑的層次細節。
  - **森山大道風**: 曲線斜率重新平衡至 2.38，兼顧極具衝擊力的黑白粗獷剪影感與真實輪廓結構。
  - **正負逆沖**: 調整反差斜率至 1.25，暗位微抬 8，確保戲劇化偏色的同時暗部乾淨不混濁。
- **完善退出重設機制**:
  - 在退出或切回原廠濾鏡時，安全恢復相機標準模式與 0 偏移。

## [1.1.2] - 2026-09-09 (B1.2)

### 修復與生命週期規範化
- **徹底修復退出應用程式反覆重新喚醒死迴圈 Bug (Exit Loop)**:
  - 修復了點選選單「退出應用程式」後相機反覆重啟進入應用程式的故障。
  - 在 `AppRoot.finish(FINISH_TYPE)` 中注入廣播重設機制，通知系統桌面 `ScalarALauncher` 清理 `resume_key` 與 `pullingback_key`，杜絕 `DAConnectionManagerService` 在感應器狀態變更時誤判恢復。
  - 明確呼叫 `Activity.finish()` 使行程由系統 ActivityManagerService 規範回收，退出時呼叫 `killProcess` 釋放記憶體。
  - 完美保留拍攝中關機/睡眠再開機繼續停留在本應用程式的斷電續拍特性。

## [1.1.1] - 2026-09-09 (B1.1)

### 修復與操作互動最佳化
- **預設首選濾鏡修復 (開機預設理光 GR 正片)**:
  - 修復了因機身 Flash 儲存殘留導致開機預設停留在原有舊濾鏡（如第 5 項部分彩色）的問題。
  - 在 `PictureEffectPlusController.getBackupEffectValue` 中增加驗證，非理光值自動回退為 `pop-color` 並自動修正寫入儲存。
  - 在 `PictureEffectPlus.onBoot`（啟動來源為應用程式清單）注入冷啟動重設邏輯，從應用程式選單開啟時百分之百停留在第 1 個濾鏡（理光 GR 正片）。
  - 保留拍攝過程中相機待機睡眠或電源開關斷電重啟時的現場記憶。
- **按鍵與轉盤互動相容性**:
  - 中央確認鍵鍵碼 `0xe8` 略過按鍵對應攔截，確保穩定叫出濾鏡選單與確認操作。
  - 方向鍵左右及副撥輪轉動對應為上下切換，操作更加順手靈敏。
- **構建簽名**:
  - 整合 `uber-apk-signer` 產生相容 Android 4.1.2 的 v1/v2 混合簽名。

## [1.1.0] - 2026-09-08

### 新增與介面改進
- **選單順序置頂與即選即拍**:
  - 重構 `ApplicationTop` 選單順序，理光 5 大預設直接置頂為前 5 項。
  - 強制 `ExecType="SET_VALUE"`，選定濾鏡即刻生效，無需進入冗餘子選單。
- **動態中文名稱與指南注入**:
  - 在 `RicohHook` 與 `BaseMenuService` 中實現 `getFilterName` 和 `getFilterGuide` 動態文字 Hook，螢幕錶盤即時顯示濾鏡中文全名與特性指南。
- **UI 與穩定性最佳化**:
  - 預設起始效果統一設為 `pop-color`（理光 GR 正片）。
  - 增加空指標保護（Null-safety Guard），杜絕選單指標越界閃退。
  - 二進位修補 `resources.arsc` 字串池，全局顯示為「理光相機」。

## [1.0.0] - 2026-09-08

### 初始發布
- **5 款經典理光底片色彩預設**:
  - `pop-color` $ightarrow$ **理光 GR 正片**: 濃郁高飽和度與高反差 S 曲線。
  - `retro-photo` $ightarrow$ **理光負片**: 消光提升黑位與泛黃暖調高光。
  - `richtone-mono` $ightarrow$ **高對比黑白**: 精準 BT.601 感知亮度灰階轉換與大 S 曲線。
  - `rough-mono` $ightarrow$ **森山大道風**: 強紅鏡通道權重與粗獷顆粒對比。
  - `watercolor` $ightarrow$ **正負逆沖**: 雙色青/黃綠反轉偏移曲線。
- **純硬體 ISP 即時管線**:
  - 編寫 `RicohHook` 直接對接 `com.sony.scalar.hardware.CameraEx`。
  - 零快門延遲、取景器即時預覽、支援全速硬體高速連拍（`burstableTakePicture`）。
- **工具鏈與自動化**:
  - `tools/patch_apk.py`：全自動反編譯、注入、中文化、打包簽名流水線。
  - `tools/sign_apk.py`：Android 4.1.2 相容簽名工具。
  - `tools/generate_ricoh_hook.py`：Gamma 曲線與 3×3 矩陣 Smali 程式碼產生器。
  - `tools/update_menu_data.py`：選單 XML 自動修補指令稿。
  - `scripts/install.sh`：Wi-Fi ADB 一鍵安裝指令稿。
- **工程文件**:
  - 完整的逆向架構與 ISP 色彩管線技術指南。
  - 索尼 A6300 手機無線傳輸與配對說明。
