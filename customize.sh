# AdBlock Module Installer Script
# 作者: 朝歌
# GitHub: Sakurakilove

MODID="adblock_hosts"

# 打印安装信息
ui_print "========================================="
ui_print "  AdBlock Module"
ui_print "  作者: 朝歌"
ui_print "========================================="

# 检查环境
if [ -z "$KSU" ] && [ -z "$MAGISK" ]; then
    ui_print "! 此模块需要 KernelSU 或 Magisk"
    abort "请在 KernelSU/Magisk 环境中安装此模块"
fi

ui_print ""
ui_print ">>> 正在安装 AdBlock 模块..."

# 获取已安装的域名数量
if [ -f "$MODPATH/system/etc/hosts" ]; then
    DOMAIN_COUNT=$(grep -cE "^0.0.0.0[[:space:]]|^127.0.0.1[[:space:]]" "$MODPATH/system/etc/hosts" 2>/dev/null || echo "0")
    ui_print ">>> 已内置 $DOMAIN_COUNT 个广告域名"
fi

# 设置文件权限
ui_print ">>> 设置文件权限..."
set_perm_recursive "$MODPATH" 0 0 0755 0644

# 设置 WebUI 脚本执行权限
if [ -f "$MODPATH/webui/server.py" ]; then
    chmod 755 "$MODPATH/webui/server.py"
fi
if [ -f "$MODPATH/webui/server" ]; then
    chmod 755 "$MODPATH/webui/server"
fi
if [ -f "$MODPATH/servicewebui.sh" ]; then
    chmod 755 "$MODPATH/servicewebui.sh"
fi

# 打印完成信息
ui_print ""
ui_print "========================================="
ui_print "  安装完成!"
ui_print "========================================="
ui_print ""
ui_print "【功能说明】"
ui_print "  - 内置广告屏蔽列表"
ui_print "  - 每次启动自动更新广告列表"
ui_print "  - 约 79000+ 广告域名被屏蔽"
ui_print ""
ui_print "【使用注意】"
ui_print "  - 部分 HTTPS 广告可能无法屏蔽"
ui_print "  - 首次安装后请重启设备"
ui_print "========================================="
