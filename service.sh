# AdBlock 模块 - 定期更新脚本
# 此脚本会在设备启动后定期检查并更新广告列表

# 获取模块目录的正确方式
if [ -z "$MODDIR" ]; then
    MODDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# 模块 ID (与 module.prop 中定义一致)
MODID="adblock_hosts"

HOSTS_FILE="$MODDIR/system/etc/hosts"

# 检测运行环境并使用正确的模块路径
if [ -d "/data/adb/ksu/modules" ]; then
    # KernelSU
    UPDATE_LOG_DIR="/data/adb/ksu/modules/$MODID"
elif [ -d "/data/adb/modules" ]; then
    # Magisk
    UPDATE_LOG_DIR="/data/adb/modules/$MODID"
else
    # 备用路径
    UPDATE_LOG_DIR="$MODDIR/.update"
fi

UPDATE_LOG="$UPDATE_LOG_DIR/update.log"
UPDATE_URL="https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
CHECK_INTERVAL=86400  # 检查间隔: 24小时 (秒)

# 记录日志
log_msg() {
    # 确保日志目录存在
    mkdir -p "$UPDATE_LOG_DIR" 2>/dev/null
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$UPDATE_LOG"
}

# 检查是否需要更新
should_update() {
    if [ ! -f "$UPDATE_LOG" ]; then
        return 0  # 从未更新过
    fi

    local last_update
    # 使用兼容 Android 的 stat 格式
    last_update=$(stat -f "%m" "$UPDATE_LOG" 2>/dev/null || stat -c %Y "$UPDATE_LOG" 2>/dev/null || echo "0")
    local now
    now=$(date +%s)

    if [ $((now - last_update)) -ge $CHECK_INTERVAL ]; then
        return 0  # 需要更新
    fi
    return 1  # 不需要更新
}

# 更新广告列表
do_update() {
    log_msg "开始检查广告列表更新..."

    # 确保日志目录存在
    mkdir -p "$UPDATE_LOG_DIR"

    # 临时文件 - 使用数据分区以确保可写
    local tmp_hosts="$MODDIR/hosts_new_$$"
    if [ ! -w "$MODDIR" ]; then
        tmp_hosts="/data/local/tmp/hosts_new_$$"
        mkdir -p /data/local/tmp
    fi

    # 下载新的 hosts 文件，保留错误输出以便调试
    local curl_exit_code
    local curl_output
    curl_output=$(curl -sSL --connect-timeout 30 --max-time 120 "$UPDATE_URL" -o "$tmp_hosts" 2>&1)
    curl_exit_code=$?

    if [ $curl_exit_code -ne 0 ]; then
        log_msg "下载失败 (curl 退出码: $curl_exit_code): $curl_output"
        rm -f "$tmp_hosts"
        return 1
    fi

    # 验证下载的文件
    if [ ! -s "$tmp_hosts" ]; then
        log_msg "下载的文件为空"
        rm -f "$tmp_hosts"
        return 1
    fi

    # 提取有效的 hosts 行
    if grep -q "0.0.0.0" "$tmp_hosts"; then
        local new_count
        new_count=$(grep -E "^(127\.0\.0\.1|0\.0\.0\.0)[[:space:]]" "$tmp_hosts" | grep -v "^#" | wc -l)

        if [ "$new_count" -lt 1000 ]; then
            log_msg "警告: 下载的域名数量过少 ($new_count)，可能下载失败"
            rm -f "$tmp_hosts"
            return 1
        fi

        # 备份旧文件 (保留备份以便失败时恢复)
        if cp "$HOSTS_FILE" "${HOSTS_FILE}.bak" 2>/dev/null; then
            : # 备份成功
        else
            log_msg "警告: 无法创建备份文件"
        fi

        # 提取并保存新的 hosts
        grep -E "^(127\.0\.0\.1|0\.0\.0\.0)[[:space:]]" "$tmp_hosts" | grep -v "^#" > "$HOSTS_FILE"

        # 设置权限
        chmod 644 "$HOSTS_FILE" 2>/dev/null

        # 验证写入成功后再删除备份和临时文件
        if [ -s "$HOSTS_FILE" ]; then
            rm -f "$tmp_hosts" "${HOSTS_FILE}.bak"
            log_msg "广告列表已更新! 当前域名数: $new_count"
        else
            # 写入失败，恢复备份
            [ -f "${HOSTS_FILE}.bak" ] && cp "${HOSTS_FILE}.bak" "$HOSTS_FILE"
            rm -f "$tmp_hosts" "${HOSTS_FILE}.bak"
            log_msg "错误: hosts 文件写入失败，已恢复备份"
            return 1
        fi

        # 通知系统重新加载 hosts (需要 root 权限)
        # 方法1: 使用 ndc 通知 netd
        if command -v ndc &>/dev/null; then
            ndc resolver flushif lo 2>/dev/null && log_msg "DNS 缓存已刷新" || log_msg "DNS 刷新失败"
        fi

        # 方法2: 清除 DNS 缓存 (分步执行避免断网)
        if command -v svc &>/dev/null; then
            svc wifi disable 2>/dev/null
            svc wifi enable 2>/dev/null
        fi

        return 0
    else
        log_msg "下载的文件格式不正确: $curl_output"
        rm -f "$tmp_hosts"
        return 1
    fi
}

# 主程序
log_msg "AdBlock 更新服务启动"

# 检查并更新
if should_update; then
    do_update
else
    log_msg "距离上次更新不足24小时，跳过检查"
fi

log_msg "更新服务完成"

# ========== WebUI 服务启动 ==========
start_webui() {
    local webui_dir="$MODDIR/webui"
    local server_bin="$webui_dir/server"
    local server_py="$webui_dir/server.py"

    # 如果有编译好的 Go 二进制
    if [ -x "$server_bin" ]; then
        nohup "$server_bin" > /dev/null 2>&1 &
        return 0
    fi

    # 使用 Python 服务器 (推荐)
    if command -v python3 &>/dev/null; then
        if [ -f "$server_py" ]; then
            nohup python3 "$server_py" > /dev/null 2>&1 &
        else
            cd "$webui_dir"
            nohup python3 -m http.server 8888 > /dev/null 2>&1 &
        fi
        return 0
    fi

    # 使用 busybox httpd
    if command -v httpd &>/dev/null; then
        cd "$webui_dir"
        nohup httpd -p 8888 > /dev/null 2>&1 &
        return 0
    fi

    return 1
}

# KSU 环境自动启动 WebUI
if [ -n "$KSU" ] || [ -d "/data/adb/ksu" ]; then
    start_webui
fi
