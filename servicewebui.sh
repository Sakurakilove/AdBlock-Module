# AdBlock WebUI Service Script
# 用于 Magisk 及其分支启动 WebUI

# 获取模块目录的正确方式
if [ -z "$MODDIR" ]; then
    if [ -n "${BASH_SOURCE[0]}" ]; then
        MODDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    else
        MODDIR=${0%/*}
    fi
fi

MODID="adblock_hosts"

# 获取正确的模块路径
if [ -d "/data/adb/ksu/modules/$MODID" ]; then
    MODDIR="/data/adb/ksu/modules/$MODID"
elif [ -d "/data/adb/modules/$MODID" ]; then
    MODDIR="/data/adb/modules/$MODID"
fi

WEBUI_DIR="$MODDIR/webui"
SERVER_BIN="$WEBUI_DIR/server"
SERVER_PY="$WEBUI_DIR/server.py"

# 启动 WebUI 服务
start_webui() {
    # 如果有编译好的 Go 二进制，使用它
    if [ -x "$SERVER_BIN" ]; then
        nohup "$SERVER_BIN" > /dev/null 2>&1 &
        return 0
    fi

    # 使用 Python 服务器 (推荐)
    if command -v python3 &>/dev/null; then
        if [ -f "$SERVER_PY" ]; then
            nohup python3 "$SERVER_PY" > /dev/null 2>&1 &
        else
            cd "$WEBUI_DIR"
            nohup python3 -m http.server 8888 > /dev/null 2>&1 &
        fi
        return 0
    fi

    # 使用 busybox httpd
    if command -v httpd &>/dev/null; then
        cd "$WEBUI_DIR"
        nohup httpd -p 8888 > /dev/null 2>&1 &
        return 0
    fi

    return 1
}

# 停止 WebUI 服务
stop_webui() {
    pkill -f "server.go" 2>/dev/null
    pkill -f "python3.*http.server" 2>/dev/null
    pkill -f "httpd.*8888" 2>/dev/null
}

# 根据参数执行
case "$1" in
    start)
        start_webui
        ;;
    stop)
        stop_webui
        ;;
    restart)
        stop_webui
        sleep 1
        start_webui
        ;;
    *)
        start_webui
        ;;
esac
