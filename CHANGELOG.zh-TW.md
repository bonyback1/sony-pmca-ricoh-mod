# 更新日誌 (Changelog)

<p align="center">
  <strong><a href="CHANGELOG.md">English</a></strong> |
  <strong><a href="CHANGELOG.zh-CN.md">简体中文</a></strong> |
  <strong>繁體中文</strong>
</p>

本專案的所有重要變更與版本更新記錄均歸檔於此。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
並嚴格遵循 [語意化版本規範 (SemVer)](https://semver.org/lang/zh-TW/)。

## [1.6.0] - 2026-09-18 (B2.4)

### 新增與增強 (全面解鎖 RAW+JPEG 與純 RAW 拍攝模式)
- **突破原廠畫質限制：全面解鎖 RAW+JPEG 與純 RAW 輸出**:
  - 徹底打破索尼官方相片效果應用程式僅允許儲存 JPEG (Fine/Standard) 的底層硬編碼限制；
  - 在選單設定檔 `MenuData.xml` 的 `setPictureStorageFormat` 畫質選項層級中動態注入 `setPictureStorageFormat_rawjpeg` (RAW與JPEG) 與 `setPictureStorageFormat_raw` (RAW)；
  - 在 `PictureQualityController.smali` 中注入 `RicohHook.filterQualityAvailability`，成功接管並重寫 `AvailableInfo.isAvailable()` 畫質可用性判斷邏輯；
  - 拍攝時不僅即時產生濃郁的理光底片色彩直出 JPEG，更同步完整儲存索尼 14-bit 無損 ARW 原始負片檔案，快拍分享與後期深度調色兩不誤。
- **三語自適應畫質選單與指南**:
  - 針對新增的 RAW 畫質選項注入英文（`RAW & JPEG` / `RAW`）、繁體中文（`RAW與JPEG` / `RAW`）與簡體中文（`RAW与JPEG` / `RAW`）的錶盤標題及詳細功能指南說明。

## [1.5.0] - 2026-09-13 (B2.3)

### 新增與增強 (真·理光 GR3 3D LUT 逆向分解與色彩科學基準)
- **真·理光 GR3 3D LUT 動力學逆向分解**:
  - 直接從真實理光 GR3 官方機型取樣產生的 3D LUT 色彩檔案（`GR3-P-V3 Plady.cube`、`GR3-N-V3 Plady.cube`、`GR3-HiBW Plady.cube`）中，數學逆向分解出原生 1024 階 10-bit 非線性 Gamma 曲線與 3×3 顏色矩陣；
  - **理光 GR 正片**: 徹底告別經驗調參，全面注入真實 GR3 正片微曲率動態範圍曲線與高低光分色矩陣，高飽和青藍天空與暖陽質感達到官方母版級還原；
  - **理光負片**: 依循真實 GR3 負片色彩特徵，精準再現底片消光黑位提升與優雅高光滾降；
  - **高對比黑白**: 擷取真機灰階亮度加權與陡峭黑白對比度曲線。
- **色彩科學自動化基準測試套件 (`tools/color_bench/`)**:
  - 全新加入基於 X-Rite 24 色卡與 DPReview 攝影棚實測資料的 $\Delta E_{00}$ 色差評估引擎；
  - 提供 `decompose_cube.py` 自動化 LUT 分解器與互動式 HTML 色彩評測報告產生器。
- **智慧安裝指令稿升級 (`scripts/install.sh`)**:
  - 新增 `INSTALL_PARSE_FAILED_INCONSISTENT_CERTIFICATES` 自動探測與修復：若相機中殘留不同簽名的舊版本，指令稿將自動解除安裝衝突版本並重新無感安裝，徹底杜絕安裝失敗；
- **純正 V1 SHA-1 摘要規範化 (`tools/sign_apk.py`)**:
  - 明確增加 OpenSSL `-md sha1` 摘要參數，保障舊機型 Apache Harmony 憑證解析穩定性。

## [1.4.0] - 2026-09-13 (B2.2)

### 新增與增強 (全機型跨代硬體相容與四階自動化測試工作台)
- **PMCA 全機型硬體防禦性架構與平滑降級**:
  - 對所有二代專屬硬體 API（`setRGBMatrix([I)V`、`createGammaTable()`、`write()`、`setExtendedGammaTable()`、`release()`）引入防禦性 `try-catch` 與非重擲回退機制；
  - 徹底杜絕初代 PMCA 機型（Android 2.3.7 / API 10，如 A7、A7R、A6000、NEX-5R/6）上的 `NoSuchMethodError` 當機，在不支援 10-bit 伽瑪表或色彩矩陣的硬體上平滑降級至基礎 ISP 參數控制；
  - 深度防護脆弱 HAL 硬體暫存器（`setColorMode`、`setDROMode`、`setHDRMode`），避免在不同機型韌體上因硬體拒絕導致相機主執行緒崩潰；
  - 嚴格保障 DMA 記憶體安全生命週期：`GammaTable.release()` 在正常與異常分支均百分之百觸發，消除核心 DMA Slab 洩漏風險。
- **純正 PMCA 相容 V1 JAR 簽名器與內建 4 位元組 ZipAlign 引擎**:
  - 全面替代現代 `uber-apk-signer`，使用 `tools/sign_apk.py`（基於 OpenSSL `smime -sign -noattr -binary`）產生純淨 V1 JAR 簽名；
  - 保證零 APK Signature Scheme v2/v3 區塊，且零 CMS 簽名屬性（如 `signingTime` 與 OID `1.2.840.113549.1.9.52`），徹底根除 Android 2.3.7 / 4.1.2 Apache Harmony `JarVerifier` 的 `INSTALL_PARSE_FAILED_NO_CERTIFICATES` 報錯；
  - 簽名引擎原生內建純 Python 4 位元組記憶體對齊（ZipAlign）：自動為所有未壓縮儲存檔案（包含 `resources.arsc`、圖片與字型資源）填充 `extra` 欄位，確保資料偏移嚴格整除 4，擺脫對系統外部 `zipalign` 命令的依賴；
  - 統一複用專案根目錄偵錯憑證（`debug.keystore` -> `tools/debug.pem`），保證相機在升級安裝時無需解除安裝即可平滑覆蓋。
- **四階全方位自動化測試工作台 (`tools/testbench/`)**:
  - 全新建立針對 PMCA 全機型的跨代驗證測試套件：
    - **Tier 1 (Dalvik 位元組碼驗證器)**：Smali 語法平衡、暫存器訊框界限、API 10 操作碼安全性、例外區塊順序、型別合併衝突（5 項全通）；
    - **Tier 2 (PMCA 架構符號稽核器)**：通用架構符號合規性、初代機當機隱患、脆弱 HAL 防護、DMA 記憶體安全（4 項全通）；
    - **Tier 3 (按鍵互動人體工學模擬器)**：雙轉盤/多轉盤切換、單轉盤與十字鍵循環、RX 系列鏡頭控制環、A5100 純觸控導航、中心鍵 `0xe8` 穿透（5 項全通）；
    - **Tier 4 (APK 打包與簽名驗證器)**：V1 簽名結構完整性、SHA-1 摘要純淨度、排除 v2/v3 簽名區塊、排除 CMS 簽名屬性、4 位元組 ZipAlign 對齊（5 項全通）；
  - `PictureEffectPlus_Ricoh.apk` 與 `Ricoh_Camera.apk` 均實現 **19/19 項 100% 全通 (PASS)**。

## [1.3.0] - 2026-09-12 (B2.1)

### 新增與增強 (執行階段「自適應多語言」引擎)
- **底層 Locale 自動感知與無感分發 (`RicohHook.getLanguageType`)**:
  - 呼叫 Android 核心 `Locale.getDefault()` 即時讀取系統語言與國家地區代碼；
  - 自動將系統環境歸類為 **英文/國際通用 (0)**、**繁體中文 (1, 台灣/香港/澳門)** 與 **簡體中文 (2, 大陸)**，無需任何手動設定，單一 APK 通用全球。
- **全動態自適應濾鏡名稱與指南文字 (`getFilterName` & `getFilterGuide`)**:
  - 軟體選單列表、轉盤切換浮動提示與詳細說明文字在相機切換語言時即時無感重新整理：
    - `pop-color`：`Ricoh GR Positive Film` / `理光 GR 正片` / `理光 GR 正片`
    - `retro-photo`：`Ricoh Negative Film` / `理光 負片` / `理光 负片`
    - `richtone-mono`：`High Contrast B&W` / `高對比黑白` / `高对比黑白`
    - `rough-mono`：`Moriyama Daido B&W` / `森山大道風` / `森山大道风`
    - `watercolor`：`Cross Process` / `正負逆沖` / `正负逆冲`
- **UI 介面動態標題綁定**:
  - 取景介面 OSD 浮層標題（`AppNameView`）與選項選單頂部標題（`mScreenTitle`）均從固定漢字改為動態呼叫 `RicohHook.getAppTitle()`，顯示為 `Ricoh Camera`、`理光相機` 或 `理光相机`。
- **系統桌面應用程式圖示三態在地化 (`resources.arsc`)**:
  - 資源字串池深度重構：繁體中文機身顯示「理光相機」、簡體中文機身顯示「理光相机」、英文及其他 30 餘種語言統一呈現「Ricoh Camera」。

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
  - `pop-color` $
ightarrow$ **理光 GR 正片**: 濃郁高飽和度與高反差 S 曲線。
  - `retro-photo` $
ightarrow$ **理光負片**: 消光提升黑位與泛黃暖調高光。
  - `richtone-mono` $
ightarrow$ **高對比黑白**: 精準 BT.601 感知亮度灰階轉換與大 S 曲線。
  - `rough-mono` $
ightarrow$ **森山大道風**: 強紅鏡通道權重與粗獷顆粒對比。
  - `watercolor` $
ightarrow$ **正負逆沖**: 雙色青/黃綠反轉偏移曲線。
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
