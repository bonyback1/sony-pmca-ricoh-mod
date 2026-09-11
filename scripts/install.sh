#!/usr/bin/env bash
# ==============================================================================
# Sony Camera Wi-Fi ADB One-Click Installer
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Check adb
if ! command -v adb >/dev/null 2>&1; then
    echo "❌ 错误: 未检测到 'adb' 命令。"
    echo "   macOS 请执行: brew install android-platform-tools"
    echo "   Ubuntu/Debian 请执行: sudo apt-get install adb"
    exit 1
fi

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "用法: $0 [相机IP] [APK路径]"
    echo ""
    echo "示例:"
    echo "  $0 192.168.1.100"
    echo "  $0 192.168.1.100 Ricoh_Camera.apk"
    echo ""
    echo "说明: 若不传参数，脚本将交互式提示输入相机 IP，并自动搜寻可用 APK。"
    exit 0
fi

# Camera IP argument or prompt
CAMERA_IP="$1"
if [ -z "${CAMERA_IP}" ]; then
    echo -n "👉 请输入索尼相机的 Wi-Fi IP 地址 (例如 192.168.1.100): "
    read -r CAMERA_IP
fi

if [ -z "${CAMERA_IP}" ]; then
    echo "❌ 错误: 未提供相机 IP 地址，安装退出。"
    exit 1
fi

# APK path argument or autodetect
APK_PATH="$2"
if [ -z "${APK_PATH}" ]; then
    # Search common names
    for candidate in "${REPO_DIR}/Ricoh_Camera.apk" \
                     "${REPO_DIR}/PictureEffectPlus_Ricoh.apk" \
                     "${REPO_DIR}/PictureEffectPlus_Ricoh_Compat.apk" \
                     "${REPO_DIR}/release/Ricoh_Camera.apk"; do
        if [ -f "${candidate}" ]; then
            APK_PATH="${candidate}"
            break
        fi
    done
fi

if [ -z "${APK_PATH}" ] || [ ! -f "${APK_PATH}" ]; then
    echo "❌ 错误: 未找到可安装的 APK 文件。"
    echo "   请通过参数指定 APK 路径: ./scripts/install.sh <CAMERA_IP> <PATH_TO_APK>"
    echo "   或者先运行打包脚本: python3 tools/patch_apk.py -i <官方APK> -o Ricoh_Camera.apk"
    exit 1
fi

PORT="5555"
TARGET="${CAMERA_IP}:${PORT}"

echo "=================================================================="
echo "📸 正在连接索尼相机 ADB: ${TARGET} ..."
echo "=================================================================="

# Disconnect old sessions to avoid stale state
adb disconnect "${TARGET}" 2>/dev/null || true

# Connect
CONNECT_OUT=$(adb connect "${TARGET}")
echo "${CONNECT_OUT}"

if ! echo "${CONNECT_OUT}" | grep -qE "connected to|already connected"; then
    echo ""
    echo "❌ 连接相机失败！请检查以下事项："
    echo "   1. 相机是否已连入 Wi-Fi，且与电脑在同一个局域网子网；"
    echo "   2. 相机内是否已开启 ADB 守护进程（端口 5555）；"
    echo "   3. macOS 15+ (Sequoia) 用户请检查：系统设置 -> 隐私与安全性 -> 本地网络 -> 确认终端/ADB 权限已开启。"
    exit 1
fi

echo ""
echo "=== 当前已连接设备列表 ==="
adb devices

echo ""
echo "📦 正在推送并安装: $(basename "${APK_PATH}") ..."
INSTALL_RES=$(adb -s "${TARGET}" install -r "${APK_PATH}" 2>&1)
echo "${INSTALL_RES}"

if echo "${INSTALL_RES}" | grep -q "Success"; then
    echo ""
    echo "=================================================================="
    echo "🎉 安装成功！索尼相机已成功载入「理光相机」！"
    echo "   请在相机主菜单中打开「应用程序列表」-> 启动「理光相机」即可享受："
    echo "   1. 理光 GR 正片 (Ricoh Positive Film)"
    echo "   2. 理光负片    (Ricoh Negative Film)"
    echo "   3. 高对比黑白  (Ricoh High Contrast B&W)"
    echo "   4. 森山大道风  (Moriyama Daido Style)"
    echo "   5. 正负逆冲    (Ricoh Cross Process)"
    echo "=================================================================="
else
    echo ""
    echo "❌ 安装遇到错误，请查看上方输出。"
    if echo "${INSTALL_RES}" | grep -q "INSTALL_PARSE_FAILED_NO_CERTIFICATES"; then
        echo "💡 提示: 证书签名不兼容，请使用 python3 tools/sign_apk.py 对 APK 重新签名。"
    elif echo "${INSTALL_RES}" | grep -q "INSTALL_FAILED_DEXOPT"; then
        echo "💡 提示: Dex 字节码验证失败，请确认 Smali 中未包含非 native 的 ACC_SYNCHRONIZED 标志。"
    fi
    exit 1
fi
