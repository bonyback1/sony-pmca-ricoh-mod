# 更新日志 (Changelog)

<p align="center">
  <strong><a href="CHANGELOG.md">English</a></strong> |
  <strong>简体中文</strong> |
  <strong><a href="CHANGELOG.zh-TW.md">繁體中文</a></strong>
</p>

本项目的关键变更与版本迭代记录均归档于此。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并严格遵循 [语义化版本规范 (SemVer)](https://semver.org/lang/zh-CN/)。

## [1.3.0] - 2026-09-12 (B2.1)

### 新增与增强 (运行时「自适应多语言」引擎)
- **底层 Locale 自动感知与无感分发 (`RicohHook.getLanguageType`)**:
  - 调用 Android 核心 `Locale.getDefault()` 实时读取系统语言与国家地区代码；
  - 自动将系统环境归类为 **英文/国际通用 (0)**、**繁體中文 (1, 台灣/香港/澳門)** 与 **简体中文 (2, 大陆)**，无需任何手动配置，单 APK 通用全球。
- **全动态自适应滤镜名称与指南文本 (`getFilterName` & `getFilterGuide`)**:
  - 软件菜单列表、波轮切换浮动提示与详细说明文本在相机切换语言时实时无感刷新：
    - `pop-color`：`Ricoh GR Positive Film` / `理光 GR 正片` / `理光 GR 正片`
    - `retro-photo`：`Ricoh Negative Film` / `理光 負片` / `理光 负片`
    - `richtone-mono`：`High Contrast B&W` / `高對比黑白` / `高对比黑白`
    - `rough-mono`：`Moriyama Daido B&W` / `森山大道風` / `森山大道风`
    - `watercolor`：`Cross Process` / `正負逆沖` / `正负逆冲`
- **UI 界面动态标题绑定**:
  - 取景界面 OSD 浮层标题（`AppNameView`）与选项菜单顶部标题（`mScreenTitle`）均从写死汉字改为动态调用 `RicohHook.getAppTitle()`，显示为 `Ricoh Camera`、`理光相機` 或 `理光相机`。
- **系统桌面应用图标三态本地化 (`resources.arsc`)**:
  - 资源字符串池深度重构：简体中文机身显示「理光相机」、繁体中文机身显示「理光相機」、英文及其他 30 余种语言统一呈现「Ricoh Camera」。

## [1.2.0] - 2026-09-12 (B2.0)

### 新增与增强 (理光 GR III 色彩科学深度重构 - 第一阶段)
- **硬件级白平衡偏移注入与现场保存/恢复 (Hardware White Balance Shifts)**:
  - 针对理光 GR3 胶片色调底层物理特性，在 `RicohHook` 中深度注入硬件级白平衡偏移调用：`setLightBalanceForWhiteBalance`（LB 琥珀/蓝色温偏置，范围 $[-14, +14]$）与 `setColorCompensationForWhiteBalance`（CC 绿色/洋红色彩补偿，范围 $[-14, +14]$）。
  - **理光 GR 正片**: 注入 $LB=+2$ (琥珀暖调), $CC=-1$ (微洋红补偿)，重现理光 GR3 正片特有的暖阳色底。
  - **理光负片**: 注入 $LB=+4$ (明显暖琥珀), $CC=-2$ (品红微调)，打造泛黄暖调的胶片底色。
  - **正负逆冲**: 注入 $LB=-3$ (冷青蓝), $CC=+2$ (显色绿调)，呈现戏剧化冷冲印风格。
  - **黑白滤镜**: 保持 $LB=0, CC=0$ 原生灰度平衡。
  - **用户原生现场保护与零残留恢复**: 首次激活滤镜时自动保存用户原先设置的相机白平衡偏移，在切换或退出应用时精准还原，杜绝机身全局色彩污染。
- **1024 阶 10-bit Gamma 曲线内嵌曝光补偿烘焙 (EV-Baking Tone Curves)**:
  - 避开调用 `setExposureCompensation()` 对机身物理曝光拨盘与测光标尺的干扰，直接将感光量比率 $2^{\Delta \text{EV}}$ 烘焙入 1024 点 10-bit 非线性 Gamma 表：
    - **理光 GR 正片**: 内嵌 -0.33 EV 曝光压暗烘焙，有效压制高光死白，增强天空蓝与高光浓郁色彩厚度。
    - **森山大道风**: 内嵌 -0.33 EV 曝光压暗烘焙，加剧强反差街头黑白张力。
    - **理光负片**: 内嵌 +0.33 EV 曝光提亮烘焙，配合哑光黑位抬升，模拟负片超大宽容度的高光滚降与通透柔和暗部。
- **全新高低光分色校准 3×3 颜色矩阵 (Split-Toning Normalized Matrices)**:
  - 重新优化并应用严格行和归一化（$\sum_j M_{ij} = 1024$）的 Q10 矩阵，灰阶无色偏。
  - 依托 BIONZ X ISP 的「RAW Bayer $\rightarrow$ 前置 WB 偏移 $\rightarrow$ Demosaic $\rightarrow$ 1024阶非线性 Gamma $\rightarrow$ 后置 3×3 色彩矩阵」管线机制：
    - 前置 WB 注入暖调，进入非线性 S 曲线后高低光自然解耦，后置矩阵对高光压制多余洋红并强化青绿饱和度，首次在索尼微单上完美重现理光 GR3 特有的**「暗部偏冷青、亮部微泛琥珀」高低光分色 (Split Toning)**。

## [1.1.4] - 2026-09-11 (B1.4)

### 修复与架构加固 (基于 PMCA 开发圣经规范)
- **彻底消除底层 Native `DeviceBuffer` DMA 内存泄漏**:
  - 在 `RicohHook.applyHook` 中调用 `CameraEx.setExtendedGammaTable()` 后立即调用 `GammaTable.release()`。
  - 增加严格的 `try-finally` 异常保护，确保 2KB 的底层物理 DMA 显存缓冲在抛异常时亦能无条件释放回 Linux 内核与 V4L2 驱动，彻底根治频繁按 Fn 调节参数、切菜单或回放照片时的偶发死机假死问题。
- **单次原子化 `setParameters` 提交 (修复参数级联覆盖)**:
  - 剔除了在 `applyHook` 中对 `CreativeStyleController` 和 `DROAutoHDRController` 的二次/三次 Binder IPC 间接调用，避免由于重新读取机身备份而误将中性 0 偏移覆盖。
  - 将色彩模式、对比度 0、饱和度 0、锐度 0、DRO 关、HDR 关、效果关与 RGB 矩阵全部合并入单次原子化 `setParameters(p1)` HAL 提交。
- **消除拨轮切换滤镜时的取景器黑屏与闪烁**:
  - 在 `PictureEffectPlusController.setPlusPictureEffect` 注入 `RicohHook.isRicohPreset(value)` 智能检查：
  - 在理光 5 大预设间快速切轮时，跳过原厂繁琐的过渡重置逻辑（原逻辑会清空色调曲线并写入单位矩阵 2ms 导致取景器黑闪），实现零延迟无感平滑切换，并减少 50% 的 Binder IPC 通信开销。
- **硬件色彩矩阵旁路重置**:
  - 在 `RicohHook.resetHook` 中向 `setRGBMatrix` 传入 `null` 而非全 0 或单位矩阵，触发 BIONZ X ISP 底层硬件硬件乘法器旁路逻辑，降低功耗。
- **文案错别字修正**:
  - 修正动态提示中 `"森山大道风粗粞高对比黑白"` 为 `"森山大道风粗粝高对比黑白"`。

## [1.1.3] - 2026-09-10 (B1.3)

### 修复与色彩重构
- **阻断滤镜基底与相机创意风格叠加 (修复“清澈/Clear”等风格叠加发灰发暗)**:
  - 修复了理光预设被机身原先设置的创意风格（如清澈 Clear、生动 Vivid 或对比度偏置）二次叠加污染的问题。
  - 在 `RicohHook.applyHook` 中强制将底层色彩模式锁定为标准 (`standard`)，重置对比/饱和/锐度偏置为 0，并同步更新控制器状态，确保在任何机身初始设置下均有一致准确的理光色彩。
- **全新重构 5 款滤镜胶片级 Gamma 动力学曲线 (告别数码生硬高反差)**:
  - **理光 GR 正片**: 摒弃生硬 Sigmoid 曲线，采用温和胶片动力学曲线（中灰斜率降至 1.25，暗部抬升保护层次，高光优雅平滑至 1020），重现通透暗部与丰富宽容度。
  - **理光负片**: 软化中灰反差（斜率 1.08），保留哑光黑位（35）与高光滚降（985），呈现经典胶片松弛感。
  - **高对比黑白**: 调整反差斜率至 1.81，既保持街头高密度黑白视觉张力，又找回沥青与暗部原本死黑的层次细节。
  - **森山大道风**: 曲线斜率重新平衡至 2.38，兼顾极具冲击力的黑白粗粝剪影感与真实轮廓结构。
  - **正负逆冲**: 调整反差斜率至 1.25，暗位微抬 8，确保戏剧化偏色的同时暗部干净不浑浊。
- **完善退出复位机制**:
  - 在退出或切回原厂滤镜时，安全恢复相机标准模式与 0 偏移。

## [1.1.2] - 2026-09-09 (B1.2)

### 修复与生命周期规范化
- **彻底修复退出应用反复重新唤醒死循环 Bug (Exit Loop)**:
  - 修复了点击菜单“退出应用程序”后相机反复重启进入应用的故障。
  - 在 `AppRoot.finish(FINISH_TYPE)` 中注入广播重置机制，通知系统桌面 `ScalarALauncher` 清理 `resume_key` 与 `pullingback_key`，杜绝 `DAConnectionManagerService` 在传感器状态变更时误判恢复。
  - 显式调用 `Activity.finish()` 使进程由系统 ActivityManagerService 规范回收，退出时调用 `killProcess` 释放内存。
  - 完美保留拍摄中关机/休眠再开机继续停留在本应用的断电续拍特性。

## [1.1.1] - 2026-09-09 (B1.1)

### 修复与操控交互优化
- **默认首选滤镜修复 (开机默认理光 GR 正片)**:
  - 修复了因机身 Flash 存储残留导致开机默认停留在原有旧滤镜（如第 5 项部分彩色）的问题。
  - 在 `PictureEffectPlusController.getBackupEffectValue` 中增加校验，非理光值自动回退为 `pop-color` 并自动纠偏写入存储。
  - 在 `PictureEffectPlus.onBoot`（启动源为应用列表）注入冷启动重置逻辑，从应用菜单打开时百分之百停留在第 1 个滤镜（理光 GR 正片）。
  - 保留拍摄过程中相机待机休眠或电源开关断电重启时的现场记忆。
- **按键与转盘交互兼容性**:
  - 中央确定键键码 `0xe8` 绕过按键映射拦截，确保稳定调出滤镜菜单与确认操作。
  - 方向键左右及副拨轮转动映射为上下切换，操作更加顺手灵敏。
- **构建签名**:
  - 集成 `uber-apk-signer` 生成兼容 Android 4.1.2 的 v1/v2 混合签名。

## [1.1.0] - 2026-09-08

### 新增与界面改进
- **菜单顺序置顶与即选即拍**:
  - 重构 `ApplicationTop` 菜单顺序，理光 5 大预设直接置顶为前 5 项。
  - 强制 `ExecType="SET_VALUE"`，选定滤镜即刻生效，无需进入冗余子菜单。
- **动态中文名称与指南注入**:
  - 在 `RicohHook` 与 `BaseMenuService` 中实现 `getFilterName` 和 `getFilterGuide` 动态文本 Hook，屏幕表盘实时显示滤镜中文全称与特性指南。
- **UI 与稳定性优化**:
  - 默认起始效果统一设为 `pop-color`（理光 GR 正片）。
  - 增加空指针保护（Null-safety Guard），杜绝菜单指针越界闪退。
  - 二进制补丁 `resources.arsc` 字符串池，全局显示为“理光相机”。

## [1.0.0] - 2026-09-08

### 初始发布
- **5 款经典理光胶片色彩预设**:
  - `pop-color` $ightarrow$ **理光 GR 正片**: 浓郁高饱和度与高反差 S 曲线。
  - `retro-photo` $ightarrow$ **理光负片**: 哑光抬升黑位与泛黄暖调高光。
  - `richtone-mono` $ightarrow$ **高对比黑白**: 精准 BT.601 感知亮度灰度转换与大 S 曲线。
  - `rough-mono` $ightarrow$ **森山大道风**: 强红镜通道权重与粗粝颗粒对比。
  - `watercolor` $ightarrow$ **正负逆冲**: 双色青/黄绿反转偏移曲线。
- **纯硬件 ISP 实时管线**:
  - 编写 `RicohHook` 直接对接 `com.sony.scalar.hardware.CameraEx`。
  - 零快门延迟、取景器实时预览、支持全速硬件高速连拍（`burstableTakePicture`）。
- **工具链与自动化**:
  - `tools/patch_apk.py`：全自动反编译、注入、汉化、打包签名流水线。
  - `tools/sign_apk.py`：Android 4.1.2 兼容签名工具。
  - `tools/generate_ricoh_hook.py`：Gamma 曲线与 3×3 矩阵 Smali 代码生成器。
  - `tools/update_menu_data.py`：菜单 XML 自动修补脚本。
  - `scripts/install.sh`：Wi-Fi ADB 一键安装脚本。
- **工程文档**:
  - 完整的逆向架构与 ISP 色彩管线技术指南。
  - 索尼 A6300 手机无线传输与配对说明。
