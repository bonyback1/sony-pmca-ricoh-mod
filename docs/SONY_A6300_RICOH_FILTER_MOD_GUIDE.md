# 索尼 A6300 / A6000 官方「照片效果+」修改为「理光相机」滤镜全流程技术文档

> **验证状态**：已在索尼 ILCE-6300（固件 v2.01 / Android 4.1.2）真机上成功安装并运行，硬件 ISP 色彩管线及 UI 拟物表盘均运行完美。

---

## 一、 整体架构与色彩渲染管线

索尼官方 PMCA 应用「照片效果+ (Picture Effect+)」在底层有两套渲染管线：
1. **纯硬件 ISP 实时管线（零延迟、极速省电、连拍可用）**：
   - 官方单滤镜直接走相机硬件 ISP 处理，通过底层私有库 `com.sony.scalar.hardware.CameraEx` 写入硬件寄存器。
   - 拍照走 `SingleProcess` $\rightarrow$ `CameraEx.burstableTakePicture()`，不调用慢速的 CPU RAW 显影，对焦、快门、连拍、EVF 实时取景全为原生无延迟。
2. **5 款经典理光/胶片滤镜硬件参数定义**：
   - **理光 GR 正片 (Ricoh Positive Film)** (槽位 `pop-color`):
     - RGB 矩阵：`[1180, -110, -46, -50, 1140, -66, -30, -80, 1134]`
     - Gamma 曲线：经典高反差 S 曲线（暗部扎实，高光收缩）。
   - **理光负片 (Ricoh Negative Film)** (槽位 `retro-photo`):
     - RGB 矩阵：`[1040, -10, -10, -30, 1010, 10, -40, -20, 1000]`
     - Gamma 曲线：胶片哑光曲线（黑位轻微抬升至 35，柔和低对比微泛暖调）。
   - **高对比黑白 (High Contrast B&W)** (槽位 `richtone-mono`):
     - RGB 矩阵：`[306, 601, 117, 306, 601, 117, 306, 601, 117]`（精准 BT.601 亮度灰度转换）
     - Gamma 曲线：大 S 曲线，油墨般深黑与清脆纯白。
   - **森山大道风 (Moriyama Daido Style)** (槽位 `rough-mono`):
     - RGB 矩阵：`[563, 358, 103, 563, 358, 103, 563, 358, 103]`（强红镜黑白通道加权，压暗天空，强化粗粝质感）
     - Gamma 曲线：极致对比度曲线（暗部大面积压黑至 0，亮部直切纯白，极具视觉冲击力）。
   - **正负逆冲 (Cross Process)** (槽位 `watercolor`):
     - RGB 矩阵：`[1150, -100, 30, 100, 1100, -120, -80, 50, 1030]`（暗部偏青/洋红，亮部泛黄绿）
     - Gamma 曲线：戏剧化反差曲线。
   - **硬件防偏色复位**：
     - 切换至其他滤镜或退出时自动写入 `setExtendedGammaTable(null)` 及单位矩阵 `[1024, 0, 0, 0, 1024, 0, 0, 0, 1024]`。

---

## 二、 逆向修改与 Hook 注入点

### 1. 业务逻辑与 Smali 注入
- 目标控制器：`com.sony.imaging.app.pictureeffectplus.shooting.camera.PictureEffectPlusController`
- 核心 Hook 方法：`setPlusPictureEffect(Ljava/lang/String;)Z`
- **注入实现**：
  - 新增辅助类：`com.sony.imaging.app.pictureeffectplus.shooting.camera.RicohHook`
  - 当检测到选中的滤镜 ID 为目标槽位（如 `pop-color`）时：
    1. 调用 `setPictureEffect("off")` 关闭机身原生硬件效果（消除硬件通道冲突）；
    2. 计算并注入理光 1024 点 Gamma 曲线与 RGB 矩阵；
    3. 提交 `CameraSetting.setParameters(...)`；
    4. 返回后跳过原厂的 `setValue` 逻辑。
  - **防崩溃关键点**：`RicohHook.smali` 中任何非 native 的方法**绝不能添加 `synchronized` 访问标志**（否则 Dalvik dexopt 会报 `Bogus method access flags 29`，必须使用内置的 `monitor-enter` / `monitor-exit`）。

### 2. 菜单与汉化修改
- **菜单定义**：`assets/MenuData.xml`
  - 找到对应的 Layer2 节点（如 `ItemId="pop-color"`），修改其属性：
    `Title="理光 GR 正片"`
- **应用名称**：
  - `resources.arsc` 中的应用名称、启动器名全部汉化为 **「理光相机」**。
  - 在 `PictureEffectPlus.smali` 和 `AppContext.smali` 中硬编码标题为 `理光相机`，彻底杜绝多语言降级回退。

---

## 三、 四大关键技术坑位与避坑经验

### 坑位 1：USB 安装（PMCA 协议）对 `com.sony.*` 的白名单限制
- **现象**：修改原厂 APK 后用 `pmca-console install` 走 USB 刷机，在 `Installing 0%` 报错 `Communication error 100`。
- **根因**：机内索尼官方守护进程 `scalarainstaller` 对 `com.sony.*` 开头的包强制验证索尼母密钥签名。
- **解决办法**：
  - **最优解**：通过 Wi-Fi 开启相机 ADB（端口 5555），直接通过 Android 系统的原生包管理器安装，完全绕过索尼原厂安装器验证；
  - **备选解**：完全修改包名（如改成 `com.ricoh.camera`），并剔除 `ACCESS_SURFACE_FLINGER` 系统级签名权限。

### 坑位 2：macOS Sequoia 本地网络权限拦截
- **现象**：`adb connect 192.168.123.142:5555` 报 `No route to host`（Errno 65）。
- **根因**：macOS 15+（Sequoia）新增了「本地网络隐私权限」，后台进程在向局域网 IP 发送数据包时会被系统内核直接拦截。
- **解决办法**：在「系统设置 $\rightarrow$ 隐私与安全性 $\rightarrow$ 本地网络」中，开启对应终端或应用的管理权限。

### 坑位 3：Android 4.1.2 的旧版证书解析兼容性
- **现象**：`adb install` 报 `Failure [INSTALL_PARSE_FAILED_NO_CERTIFICATES]`，底层的 logcat 显示 `java.lang.SecurityException: Incorrect signature at JarUtils.verifySignature`。
- **根因**：现代 OpenJDK 26 的 `jarsigner` 默认加入了现代 CMS 签名属性（`id-aa-cmsAlgorithmProtect`），而 2012 年 Android 4.1.2 内置的 Apache Harmony 运行时无法识别此类现代属性。
- **解决办法**：使用 Google 官方兼容的 `uber-apk-signer`（内置官方 `apksig` 引擎，支持 v1+v2+v3 同时向后兼容到 API 1）进行对齐与签名：
  ```bash
  java -jar /tmp/uber-apk-signer.jar -a my_app.apk -o /tmp/signed_dir --allowResign
  ```

### 坑位 4：Dalvik 虚拟机的 Dexopt 字节码校验
- **现象**：`adb install` 报 `Failure [INSTALL_FAILED_DEXOPT]`，机身 logcat 显示 `E/dalvikvm: Bogus method access flags 29 @ 5`。
- **根因**：DEX 规范中，非 native 方法严禁在方法修饰符中包含 `ACC_SYNCHRONIZED (0x20)` 标志。
- **解决办法**：在 smali 中，方法头声明为 `.method public static`，同步操作在方法体内使用 `monitor-enter` / `monitor-exit` 实现。

---

## 四、 后续添加/替换更多滤镜的操作指南

如果后续想替换更多理光预设（如**高对比黑白**、**负片**、**正负逆冲**等），只需复用现有架构：

1. **挑选替换槽位**：
   在 `assets/MenuData.xml` 中挑选要替换的官方效果（例如 `posterization`、`high-contrast-monochrome`、`toy-camera` 等）。
2. **在 `RicohHook.smali` 中增加分支逻辑**：
   ```smali
   # 示例：如果是负片效果
   const-string v0, "negative-film"
   invoke-virtual {p1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
   move-result v0
   if-eqz v0, :cond_neg
   # 设置负片专用矩阵与 Gamma 表
   ...
   ```
3. **打包、签名与推送一条龙**：
   ```bash
   # 1. 编译
   apktool b /Users/zhuqi/Documents/a6300/decompiled/Sony_A6300_pictureeffectplus_ricoh -o /tmp/ricoh_new.apk
   # 2. 官方标准兼容签名
   java -jar /tmp/uber-apk-signer.jar -a /tmp/ricoh_new.apk -o /tmp/signed_out --allowResign
   # 3. Wi-Fi ADB 一键安装
   adb -s 192.168.123.142:5555 install -r /tmp/signed_out/ricoh_new-aligned-debugSigned.apk
   ```
