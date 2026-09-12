# 索尼微单理光胶片滤镜模组 (Sony PMCA Ricoh Camera Mod)

<p align="center">
  <strong><a href="README.md">English</a></strong> |
  <strong>简体中文</strong> |
  <strong><a href="README.zh-TW.md">繁體中文</a></strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Sony%20PMCA%20%2F%20Android%204.1.2-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Hardware%20ISP-Zero%20Lag%20%2F%20Burst%20OK-brightgreen?style=flat-square" alt="Hardware ISP">
  <img src="https://img.shields.io/badge/License-Apache--2.0-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Version-v1.3.0--B2.1-orange?style=flat-square" alt="Version">
</p>

通过底层硬件 ISP Hook 逆向技术，将索尼官方「照片效果+ (Picture Effect+)」应用深度改造为原生级**「理光相机」**。直接将理光 GR 经典胶片色彩的 **前置硬件白平衡偏置 (WB Shift)、1024 阶非线性 Gamma 曲线 (内嵌 EV 补偿) 与 3×3 RGB 颜色矩阵** 协同写入相机底层硬件寄存器，重现理光 GR 经典的高低光分色 (Split Toning) 与胶片色彩厚重感，实现**零快门延迟、EVF/LCD 实时取景无拖影、原生高速连拍**的直出胶片体验。

---

## 🌟 核心特性与亮点

- ⚡ **纯硬件 ISP 实时管线**：
  直接调用索尼相机底层私有库 `com.sony.scalar.hardware.CameraEx` 写入硬件寄存器。拍照走 `SingleProcess` $\rightarrow$ `CameraEx.burstableTakePicture()`，不调用慢速 CPU RAW 显影，对焦、快门、连拍、取景全部为原生无延迟体验。
- 🌐 **运行时自适应多语言引擎 (Locale 自动感知)**：
  - 基于 Android 底层 `Locale.getDefault()` 实时感知机身语言，无需安装不同版本 APK。
  - 应用桌面图标、取景界面 OSD、设置菜单、波轮切换浮动提示与帮助说明全自动无感切换：
    - **英文/海外国际系统**：`Ricoh Camera`、`Ricoh GR Positive Film`、`Ricoh Negative Film`、`High Contrast B&W`、`Moriyama Daido B&W`、`Cross Process`
    - **繁體中文系统 (台灣/香港)**：`理光相機`、`理光 GR 正片`、`理光 負片`、`高對比黑白`、`森山大道風`、`正負逆沖`
    - **简体中文系统 (大陆)**：`理光相机`、`理光 GR 正片`、`理光 负片`、`高对比黑白`、`森山大道风`、`正负逆冲`
- 🌈 **真·理光高低光分色 (Split Toning) 与色彩重塑**：
  - **前置硬件 WB 偏移**：精准注入 LB (色温/琥珀偏置) 与 CC (色彩补偿)，赋予正片暖阳基底与负片泛黄温和胶片底色，退出应用自动完美复位用户原始 WB。
  - **1024 阶 Gamma 内嵌 EV 烘焙**：正片与森山大道风内嵌 -0.33 EV 曝光压暗烘焙压制高光死白，负片内嵌 +0.33 EV 提亮配合黑位抬升模拟大宽容度负片质感。
  - **行和归一化 3×3 颜色矩阵**：结合前置 WB 与非线性 S 曲线，实现「暗部冷青、高光暖琥珀」的理光 GR3 经典分色。
- 🎨 **内嵌 5 款经典理光/街头胶片滤镜**：
  - **理光 GR 正片 (Ricoh Positive Film)**：真实理光 GR 正片色彩，解耦相机自带风格，高饱和青蓝天空与黄绿草木，温和胶片反差，暗部层次细腻丰富无死黑。
  - **理光 负片 (Ricoh Negative Film)**：胶片哑光曲线，黑位抬升至 36，柔和低对比微泛暖调，高光优雅滚降。
  - **高对比黑白 (High Contrast B&W)**：精准 BT.601 亮度灰度转换，大 S 反差曲线，呈现油墨般深邃质感。
  - **森山大道风 (Moriyama Daido Style)**：强红镜黑白通道加权，压暗天空，强化粗粝颗粒感与极致黑白张力。
  - **正负逆冲 (Cross Process)**：戏剧化色彩偏移曲线，暗部偏青/洋红，亮部泛黄绿。
- 🔄 **硬件色彩复位保障**：切换滤镜或退出应用时，自动复位单位矩阵、白平衡偏移及默认 Gamma 表，彻底防止相机机身色彩残留或偏色。

---

## 📷 支持机型列表 (PMCA 架构)

所有支持索尼 PlayMemories Camera Apps (PMCA) 框架的索尼微单与黑卡均可兼容安装：

| 系列 | 支持机型 |
|:---|:---|
| **APS-C 微单** | A5100, A6000, A6300, A6500 |
| **全画幅微单** | A7, A7R, A7S, A7M2 (A7II), A7R2 (A7RII), A7S2 (A7SII) |
| **黑卡 / 便携机** | RX100 M3 / M4 / M5, RX10 M2 / M3, RX1R II, HX90 等 |

> **注**：索尼第 3/4/5 代微单（如 A7M3, A7C, A6400, A6700 等）已移除 PMCA 系统，不支持本应用。

---

## 🚀 快速上手与安装

### 准备工作
1. 确保电脑已安装 `adb` 命令行工具：
   - macOS: `brew install android-platform-tools`
   - Linux: `sudo apt-get install adb`
   - Windows: 下载 [Google SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) 并加入环境变量。
2. 开启相机 Wi-Fi 并启动 ADB 守护进程（默认端口 5555）。
3. 让电脑与相机连入同一个 Wi-Fi 网络，获取相机的 IP 地址（例如 `192.168.1.100`）。

### 方法一：Wi-Fi ADB 一键安装 (推荐)

直接克隆本仓库并执行自带的安装脚本：

```bash
git clone https://github.com/bonyback1/sony-pmca-ricoh-mod.git
cd sony-pmca-ricoh-mod

# 一键安装到相机 (替换为你的相机实际 IP)
./scripts/install.sh 192.168.1.100
```

> **提示**：若不传 IP 参数，脚本会弹出交互式提示引导你输入，并自动搜寻可用 APK。

### 方法二：使用 PMCA-GUI 刷机工具
也可以使用开源的 [pmca-gui](https://github.com/ma1co/Sony-PMCA-RE) 配合 USB 数据线将打包好的 APK 安装至相机。

---

## 🛠️ 进阶开发：一键 Patch 构建流水线

本项目提供了完整的自动化 Patch 构建工具链，用户可使用官方基础包自行定制与编译：

```bash
# 1. 确保已安装 apktool 与 python3
brew install apktool

# 2. 运行一键构建流水线
python3 tools/patch_apk.py -i /path/to/Sony_PictureEffectPlus.apk -o Ricoh_Camera.apk
```

流水线将全自动执行以下工序：
1. **反编译**：使用 `apktool d -r` 解包官方 base 包（保留资源二进制，杜绝 aapt 私有符号冲突）。
2. **Hook 注入**：将 `src/smali/RicohHook.smali` 注入目标包控制层。
3. **Smali 补丁**：修补 `PictureEffectPlusController.smali`、`BaseMenuService.smali`、`PictureEffectPlusOptionMenuLayout.smali` 与 `AppRoot.smali`。
4. **菜单汉化与排序**：修改 `assets/MenuData.xml` 中的滤镜名称并置顶理光预设。
5. **回编译**：`apktool b` 重新构建 classes.dex 与 APK。
6. **老旧系统兼容签名**：调用 `tools/sign_apk.py` 生成 Android 4.1.2 兼容的 v1 JAR 签名。

---

## 🔬 架构解析与关键避坑经验

详细技术设计请参阅 [SONY_A6300_RICOH_FILTER_MOD_GUIDE.md](docs/SONY_A6300_RICOH_FILTER_MOD_GUIDE.md)。以下为核心逆向坑位及解决措施：

1. **USB PMCA 官方白名单签名校验**：
   - *现象*：USB 刷机在 `Installing 0%` 报错 `Communication error 100`。
   - *原因*：索尼原厂守护进程 `scalarainstaller` 对 `com.sony.*` 应用强制验证母密钥签名。
   - *解决*：走 Wi-Fi ADB 安装，直接调用系统原生 Package Manager，彻底绕过原厂安装器验证。
2. **macOS 15+ (Sequoia) 本地网络权限拦截**：
   - *现象*：`adb connect <IP>:5555` 报 `No route to host` (Errno 65)。
   - *原因*：macOS Sequoia 引入了本地网络隐私权限机制，阻止未经授权的进程向局域网广播。
   - *解决*：在「系统设置 $\rightarrow$ 隐私与安全性 $\rightarrow$ 本地网络」中授予当前终端/IDE 网络访问权限。
3. **Android 4.1.2 证书签名兼容性**：
   - *现象*：`INSTALL_PARSE_FAILED_NO_CERTIFICATES`。
   - *原因*：现代 JDK 21+ 的 jarsigner 默认附带现代 CMS 保护属性（`id-aa-cmsAlgorithmProtect`），2012 年索尼相机内运行的 Apache Harmony 无法解析。
   - *解决*：使用本项目编写的 `tools/sign_apk.py`（基于纯净 OpenSSL smime `-noattr -binary` 签名）。
4. **Dalvik Dexopt 字节码校验限制**：
   - *现象*：`INSTALL_FAILED_DEXOPT`，日志显示 `Bogus method access flags 29 @ 5`。
   - *原因*：DEX 规范严禁非 native 方法在方法头修饰符中附带 `ACC_SYNCHRONIZED (0x20)`。
   - *解决*：Smali 中统一使用 `monitor-enter` / `monitor-exit`，绝不滥用 synchronized 访问标志。
5. **Native DeviceBuffer DMA 显存释放保护**：
   - *现象*：高频切换菜单或查看照片后相机偶然死机或取景器冻结。
   - *原因*：底层 `CameraEx$GammaTable` 是物理 DMA 显存，未显式释放会耗尽驱动缓冲池。
   - *解决*：在提交 HAL 后严格执行 `table.release()`，确保长久稳定拍摄。

---

## 📂 项目工程结构

```text
├── .github/
│   ├── workflows/ci.yml       # 持续集成自动化测试工作流
│   └── ISSUE_TEMPLATE/        # Issue 反馈与功能请求模板
├── docs/                      # 核心开发文档与使用教程
│   ├── SONY_A6300_RICOH_FILTER_MOD_GUIDE.md
│   └── A6300连接手机App指南.md
├── src/                       # 核心开源源码
│   ├── smali/RicohHook.smali  # 硬件 ISP 寄存器操作与色彩注入核心类
│   ├── patches/               # Smali 控制器补丁文件
│   └── luts/                  # 经典理光胶片色彩 3D LUT 文件 (.CUB)
├── tools/                     # 跨平台一键开发构建工具
│   ├── patch_apk.py           # 一键逆向、注入、重打包与签名流水线
│   ├── sign_apk.py            # Android 4.1.2 兼容签名工具
│   ├── generate_ricoh_hook.py # Gamma 曲线与矩阵 Smali 生成器
│   └── update_menu_data.py    # 菜单 XML 自动化修改器
├── scripts/
│   └── install.sh             # Wi-Fi ADB 一键部署安装脚本
├── .gitignore                 # 安全与忽略规则 (隔离官方二进制与私钥)
├── CHANGELOG.md               # 版本迭代历史记录
├── LICENSE                    # Apache 2.0 开源许可证与免责条款
├── README.md                  # English Documentation
├── README.zh-CN.md            # 简体中文文档
└── README.zh-TW.md            # 繁體中文文檔
```

---

## 📜 免责声明 (Disclaimer)

1. 本项目为独立开源逆向工程与色彩科学研究项目，仅供学习、交流与技术研究使用。
2. "Sony"、"PlayMemories Camera Apps"、"PMCA"、"Ricoh"、"GR" 均为对应商标持有方的注册商标。本项目与索尼公司（Sony Corporation）或理光公司（Ricoh Company, Ltd.）无任何从属、授权或关联关系。
3. 请遵循当地版权法规，不得将官方专有二进制包用于商业分发。使用本工具对相机进行软硬件改动均由使用者自行承担风险。

---

## 🤝 参与贡献与交流

欢迎提交 Issue 或 Pull Request！
- 欢迎提供更多经典相机/胶片色彩数据（Fujifilm 经典负片、Kodak 柯达金、Leica 黑白等）。
- 欢迎反馈更多索尼微单机型的真机测试报告。
