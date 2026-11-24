# 索尼微單眼理光底片濾鏡模組 (Sony PMCA Ricoh Camera Mod)

<p align="center">
  <strong><a href="README.md">English</a></strong> |
  <strong><a href="README.zh-CN.md">简体中文</a></strong> |
  <strong>繁體中文</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Sony%20PMCA%20%2F%20Android%204.1.2-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Hardware%20ISP-Zero%20Lag%20%2F%20Burst%20OK-brightgreen?style=flat-square" alt="Hardware ISP">
  <img src="https://img.shields.io/badge/License-Apache--2.0-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Version-v2.2.0--B3.2-orange?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Testbench-29%2F29%20PASS%20(5--Tier)-brightgreen?style=flat-square" alt="Testbench">
</p>

透過底層硬體 ISP Hook 逆向工程技術，將索尼官方「相片效果+ (Picture Effect+)」應用深度改造為原生級**「理光相機」**。直接將理光 GR 經典底片色彩的 **前置硬體白平衡偏移 (WB Shift)、1024 階非線性 Gamma 曲線 (內嵌 EV 補償) 與 3×3 RGB 顏色矩陣** 協同寫入相機底層硬體暫存器，重現理光 GR 經典的高低光分色 (Split Toning) 與底片色彩厚實感，實現**零快門延遲、EVF/LCD 即時取景無殘影、原生高速連拍**的直出底片體驗。

---

## 🌟 核心特性與亮點

- 🛡️ **BIONZ X ISP 硬體暫存器徹底清洗與杜絕黑白鎖定**:
  - 徹底終結索尼相機在退出或切換黑白濾鏡時偶發殘留黑白/部分色彩的頑疾：在濾鏡切換與應用程式退出時主動清除 `setColorSelectMode("off", sEmptyIntArray)` 部分色彩暫存器，並顯式向 ISP 注入純正 3×3 單位矩陣 (`sIdentityMatrix`)；
  - 在 `onTerminateHook` 中強制啟動硬體色彩復位，配套**五階自動化測試工作台 29/29 項全通 (100% PASS)**。

- 👁️ **即時取景預覽選單與零閃爍 HAL 管線**:
  - 徹底移除選單中的不透明靜態樣張 PNG，透過 `setupLivePreviewMenu` 實現觀景窗/螢幕**即時底片濾鏡預覽**，搭配半透明指南條與高對比左側圖示軌道；
  - 新增 `sAppliedPreset` / `sAppliedCameraHash` 硬體狀態去重快取、`Locale` 快取、高頻率 `AppLog` 靜默以及單次圖示解碼最佳化，大幅降低選單切換與預覽延遲。

- 🔍 **C2 / 刪除鍵按住即時原片對比 (Before/After)**:
  - 在取景拍攝介面或即時濾鏡選單中，按住 **C2 / 刪除鍵** 即可瞬時旁路理光 ISP 暫存器，在觀景窗/螢幕上即時查看未套用濾鏡的機身原片效果，並顯示三語懸浮提示徽章（`原片對比 (Original)` / `原片对比 (Original)` / `ORIGINAL (BEFORE)`）；
  - 放開按鍵、半按快門對焦 (`pushedS1Key`) 或離開頁面時自動瞬時恢復當前理光底片預設。

- 🔄 **使用者機身參數隔離備份與無損忠實還原**:
  - 首次套用濾鏡時從即時 `CameraSetting.getParameters()` 擷取並備份使用者原有的風格設定 (`ColorMode`)、對比度 (`Contrast`)、飽和度 (`Saturation`)、銳利度 (`Sharpness`)、動態範圍最佳化 (`DRO`)、高動態範圍 (`HDR`) 以及白平衡偏移 (`LB`/`CC`)；
  - 在應用程式退出 (`resetHook`) 時 100% 無損還原機身原有設定，杜絕任何設定被重設為預設值的困擾。

- ⚡ **驅動模式原生保護與高速連拍全面解鎖**:
  - 將 `setSADriveMode()` 徹底置為無操作 (No-Op)，杜絕關閉或切換選項選單時意外竄改或重設使用者選定的連拍/定時驅動模式；
  - 剔除 `ITEM_ID_SA_USE_EFFECT` 限制並接管 `PictureEffectPlusDriveModeController.smali`，**全套 5 款底片濾鏡全線支援高速連拍 (Hi/Mid/Lo)、速度優先連拍、定時自拍與包圍曝光**。

- 📸 **RAW 模式限制全面終結與純淨雙格式**:
  - 徹底打破官方在純 RAW 模式下停用濾鏡選單、隱藏取景 OSD 圖示以及反灰畫質選單的枷鎖；
  - 接管 `getAvailableValue()` 與 `isAvailable()`，確保即使在純 RAW 模式下 5 款底片預設依然完全可用且取景圖示常駐；
  - 屏蔽 `INH_FEATURE_CAM_PARAMID_JPEG_QUALITY`，確保畫質選項在任何狀態下皆可自由切換，並在畫質選單中注入 `RAW與JPEG` 及 `RAW` 選項。

- 🛡️ **Tier 5 位元組碼完整性審計器與嚴格建置管線**:
  - 全新加入反編譯位元組碼審計器 (`tools/testbench/test_patched_apk.py`)，直接解包檢查目標 Smali 位元組碼，嚴密核驗生命週期 Hook、記憶體流失修復 (`mBackgroundImageView` 空指標反轉) 與選單結構；
  - 嚴格修補模式 (Strict Patch Mode)：任何官方程式碼修補失敗即刻中斷編譯，杜絕無聲失敗。

- 🛡️ **PMCA 全机型硬體防禦性架構與平滑降級**:
  - 深度適配所有 PMCA 世代相機：全面支援 PMCA 一代（Android 2.3.7 / API 10：A7、A7R、A6000、NEX-5R/6）與 PMCA 二代（Android 4.1.2 / API 16：A6300、A6500、A7M2、A7R2、RX100 系列），在不支援 10-bit 伽瑪表或色彩矩陣的老機型上平滑降級，絕不報 `NoSuchMethodError` 當機；
- ⚡ **純硬體 ISP 即時管線 (零快门延遲 / 支援高速連拍)**：
  直接呼叫索尼相機底層私有庫 `com.sony.scalar.hardware.CameraEx` 寫入硬體暫存器。拍照走 `SingleProcess` $\rightarrow$ `CameraEx.burstableTakePicture()`，不調用慢速 CPU RAW 顯影，對焦、快門、連拍、取景全部為原生零延遲體驗。
- 🌐 **執行階段自適應多語言引擎 (Locale 自動感知)**：
  - 基於 Android 底层 `Locale.getDefault()` 即時感知機身語言，無需安裝不同版本 APK。
  - 應用程式桌面圖示、取景介面 OSD、設定選單、撥輪切換浮動提示與說明指南全自動無感切換：
    - **英文/海外國際系統**：`Ricoh Camera`、`Ricoh GR Positive Film`、`Ricoh Negative Film`、`High Contrast B&W`、`Moriyama Daido B&W`、`Steve McCurry`
    - **繁體中文系統 (台灣/香港)**：`理光相機`、`理光 GR 正片`、`理光 負片`、`高對比黑白`、`森山大道風`、`麥凱瑞 Kodachrome`
    - **簡體中文系統 (大陸)**：`理光相机`、`理光 GR 正片`、`理光 负片`、`高对比黑白`、`森山大道风`、`麦凯瑞 Kodachrome`
- 🌈 **真·理光高低光分色 (Split Toning) 與色彩重塑**：
  - **前置硬體 WB 偏移**：精準注入 LB (色溫/琥珀偏置) 與 CC (色彩補償)，賦予正片暖陽基底與負片泛黃溫潤底片底色，退出應用自動完美復位使用者原始 WB。
  - **1024 階 Gamma 內嵌 EV 烘焙**：正片與森山大道風內嵌 -0.33 EV 曝光壓暗烘焙壓制高光死白，負片內嵌 +0.33 EV 提亮配合暗部抬升模擬大寬容度負片質感。
  - **行和正規化 3×3 顏色矩陣**：結合前置 WB 與非線性 S 曲線，實現「暗部冷青、高光暖琥珀」的理光 GR3 經典分色。
- 🎨 **內建 5 款經典理光與大師紀實底片濾鏡**：
  - **理光 GR 正片 (Ricoh Positive Film)**：真實理光 GR 正片色彩，解耦相機自帶風格，高飽和青藍天空與黃綠草木，溫潤底片反差，暗部層次細膩豐富無死黑。
  - **理光負片 (Ricoh Negative Film)**：底片啞光曲線，黑位抬升至 36，柔和低對比微泛暖調，高光優雅滾降。
  - **高對比黑白 (High Contrast B&W)**：精準 BT.601 亮度灰階轉換，大 S 反差曲線，呈現如油墨般深邃質感。
  - **森山大道風 (Moriyama Daido Style)**：強紅鏡黑白通道加權，壓暗天空，強化粗糲顆粒感與極致黑白張力。
  - **麥凱瑞 Kodachrome (Steve McCurry Kodachrome)**：致敬馬格南大師 Steve McCurry 經典 Kodachrome 傳奇正片色彩。徹底取代原版正負逆沖，具備正片純黑底色 ($D_{\min}=0$)、內嵌 -0.33 EV 曝光壓暗與 1.35 陡峭反差強化暗部與中階密度、非對稱柯達彩度矩陣與 LB=+2 黃金時刻暖琥珀色溫偏移，再現國家地理標誌性的濃郁暖調與極具戲劇張力的人文紀實底片感。
- 🔄 **硬體色彩復位保障**：切換濾鏡或退出應用程式時，自動復位單位矩陣、白平衡偏移及預設 Gamma 表，徹底防止相機機身色彩殘留或色偏。

---

## 📷 支援機型清單 (PMCA 架構)

所有支援索尼 PlayMemories Camera Apps (PMCA) 架構的索尼微單眼與黑卡隨身機均可相容安裝：

| 系列 | 支援機型 |
|:---|:---|
| **APS-C 微單眼** | A5100, A6000, A6300, A6500 |
| **全片幅微單眼** | A7, A7R, A7S, A7M2 (A7II), A7R2 (A7RII), A7S2 (A7SII) |
| **黑卡 / 隨身機** | RX100 M3 / M4 / M5, RX10 M2 / M3, RX1R II, HX90 等 |

> **註**：索尼第 3/4/5 代微單眼（如 A7M3, A7C, A6400, A6700 等）已移除 PMCA 系統，不支援本應用程式。

---

## 🚀 快速上手與安裝

### 準備工作
1. 確保電腦已安裝 `adb` 指令列工具：
   - macOS: `brew install android-platform-tools`
   - Linux: `sudo apt-get install adb`
   - Windows: 下載 [Google SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) 並加入環境變數。
2. 開啟相機 Wi-Fi 並啟動 ADB 守護行程（預設連接埠 5555）。
3. 讓電腦與相機連入同一個 Wi-Fi 網路，取得相機的 IP 位址（例如 `192.168.1.100`）。

### 方法一：Wi-Fi ADB 一鍵安裝 (推薦)

直接複製 (clone) 本儲存庫並執行內附的安裝指令碼：

```bash
git clone https://github.com/bonyback1/sony-pmca-ricoh-mod.git
cd sony-pmca-ricoh-mod

# 一鍵安裝到相機 (替換為你的相機實際 IP)
./scripts/install.sh 192.168.1.100
```

> **提示**：若不傳入 IP 參數，指令碼會跳出互動式提示引導輸入，並自動搜尋可用 APK。

### 方法二：使用 PMCA-GUI 刷機工具
亦可使用開源的 [pmca-gui](https://github.com/ma1co/Sony-PMCA-RE) 搭配 USB 傳輸線將打包好的 APK 安裝至相機。

---

## 🛠️ 進階開發：一鍵 Patch 建置管線

本專案提供了完整的自動化 Patch 建置工具鏈，開發者可使用官方基底包自行客製與編譯：

```bash
# 1. 確保已安裝 apktool 與 python3
brew install apktool

# 2. 執行一鍵建置管線
python3 tools/patch_apk.py -i /path/to/Sony_PictureEffectPlus.apk -o Ricoh_Camera.apk
```

管線將全自動執行以下程序：
1. **反編譯**：使用 `apktool d -r` 解包官方 base 包（保留資源二進位，避免 aapt 私有符號衝突）。
2. **Hook 注入**：將 `src/smali/RicohHook.smali` 注入目標包控制層。
3. **Smali 補丁**：修補 `PictureEffectPlusController.smali`、`BaseMenuService.smali`、`PictureEffectPlusOptionMenuLayout.smali` 與 `AppRoot.smali`。
4. **選單中文化與排序**：修改 `assets/MenuData.xml` 中的濾鏡名稱並置頂理光預設。
5. **回編譯**：`apktool b` 重新建置 classes.dex 與 APK。
6. **舊系統相容簽名**：呼叫 `tools/sign_apk.py` 產生 Android 4.1.2 相容的 v1 JAR 簽名。

---

## 🔬 架構解析與關鍵避坑經驗

詳細技術設計請參閱 [SONY_A6300_RICOH_FILTER_MOD_GUIDE.md](docs/SONY_A6300_RICOH_FILTER_MOD_GUIDE.md)。以下為核心逆向避坑措施：

1. **USB PMCA 官方白名單簽名驗證**：
   - *現象*：USB 刷機在 `Installing 0%` 報錯 `Communication error 100`。
   - *原因*：索尼原廠守護行程 `scalarainstaller` 對 `com.sony.*` 應用程式強制驗證母金鑰簽名。
   - *解決*：改走 Wi-Fi ADB 安裝，直接呼叫系統原生 Package Manager，徹底繞過原廠安裝器驗證。
2. **macOS 15+ (Sequoia) 區域網路權限攔截**：
   - *现象*：`adb connect <IP>:5555` 報錯 `No route to host` (Errno 65)。
   - *原因*：macOS Sequoia 引入了區域網路隱私權限機制，阻止未經授權的程序向區域網路發送封包。
   - *解決*：在「系統設定 $\rightarrow$ 隱私權與安全性 $\rightarrow$ 區域網路」中授予終端機/IDE 網路存取權限。
3. **Android 4.1.2 憑證簽名相容性**：
   - *現象*：`INSTALL_PARSE_FAILED_NO_CERTIFICATES`。
   - *原因*：現代 JDK 21+ 的 jarsigner 預設夾帶現代 CMS 保護屬性（`id-aa-cmsAlgorithmProtect`），2012 年索尼相機內運行的 Apache Harmony 無法解析。
   - *解決*：使用本專案撰寫的 `tools/sign_apk.py`（基於純淨 OpenSSL smime `-noattr -binary` 簽名）。
4. **Dalvik Dexopt 位元組碼校驗限制**：
   - *現象*：`INSTALL_FAILED_DEXOPT`，記錄檔顯示 `Bogus method access flags 29 @ 5`。
   - *原因*：DEX 規範嚴禁非 native 方法在方法修飾詞中夾帶 `ACC_SYNCHRONIZED (0x20)`。
   - *解決*：Smali 中統一使用 `monitor-enter` / `monitor-exit`，絕不濫用 synchronized 訪問旗標。
5. **Native DeviceBuffer DMA 記憶體釋放保護**：
   - *現象*：高頻切換選單或瀏覽相片後相機偶發當機或取景器畫面凍結。
   - *原因*：底層 `CameraEx$GammaTable` 是實體 DMA 記憶體，未顯式釋放會耗盡驅動程式緩衝池。
   - *解決*：在提交 HAL 後嚴格執行 `table.release()`，確保長時間穩定拍攝。

---

## 📂 專案工程結構

```text
├── .github/
│   ├── workflows/ci.yml       # 持續整合自動化測試工作流程
│   └── ISSUE_TEMPLATE/        # Issue 反饋與功能請求範本
├── docs/                      # 核心開發文件與使用教學
│   ├── SONY_A6300_RICOH_FILTER_MOD_GUIDE.md
│   └── A6300连接手机App指南.md
├── src/                       # 核心開原始碼
│   ├── smali/RicohHook.smali  # 硬體 ISP 暫存器操作與色彩注入核心類別
│   ├── patches/               # Smali 控制器補丁檔案
│   └── luts/                  # 經典理光底片色彩 3D LUT 檔案 (.CUB)
├── tools/                     # 跨平台一鍵開發建置工具
│   ├── patch_apk.py           # 一鍵逆向、注入、重打包與簽名管線
│   ├── sign_apk.py            # Android 4.1.2 相容簽名工具
│   ├── generate_ricoh_hook.py # Gamma 曲線與矩陣 Smali 產生器
│   └── update_menu_data.py    # 選單 XML 自動化修改器
├── scripts/
│   └── install.sh             # Wi-Fi ADB 一鍵部署安裝指令碼
├── .gitignore                 # 安全與忽略規則 (隔離官方二進位檔與私鑰)
├── CHANGELOG.md               # 版本迭代歷史記錄
├── LICENSE                    # Apache 2.0 開源許可證與免責條款
├── README.md                  # English Documentation
├── README.zh-CN.md            # 簡體中文說明文件
└── README.zh-TW.md            # 繁體中文說明文件
```

---

## 📜 免責聲明 (Disclaimer)

1. 本專案為獨立開源逆向工程與色彩科學研究專案，僅供學習、交流與技術研究使用。
2. "Sony"、"PlayMemories Camera Apps"、"PMCA"、"Ricoh"、"GR" 均為對應商標持有人之註冊商標。本專案與索尼公司（Sony Corporation）或理光公司（Ricoh Company, Ltd.）無任何隸屬、授權或關聯關係。
3. 請遵循當地版權法規，不得將官方專有二進位包用於商業散布。使用本工具對相機進行軟硬體改動均由使用者自行承擔風險。

---

## 🤝 參與貢獻與交流

歡迎提交 Issue 或 Pull Request！
- 歡迎提供更多經典相機/底片色彩數據（Fujifilm 經典負片、Kodak 柯達金、Leica 黑白等）。
- 欢迎反饋更多索尼微單眼機型的真機測試報告。
