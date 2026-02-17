# AdBlock 广告屏蔽模块

基于 StevenBlack hosts 的广告屏蔽模块，适用于 KernelSU 和 Magisk。

## 功能特性

- 内置 79000+ 广告域名屏蔽
- 自动定期更新广告列表（24小时检查一次）
- WebUI 管理界面（端口 8888）
- 支持自定义数据源
- 支持手动一键更新

## 安装

1. 下载模块 ZIP 文件
2. 打开 KernelSU Manager / Magisk Manager
3. 点击右下角"模块"图标
4. 从本地安装选择 ZIP 文件
5. 重启设备

## 使用方法

### WebUI 管理界面

设备启动后，WebUI 服务会自动启动。访问以下地址：

```
http://localhost:8888
```

或者通过 KernelSU/Magisk 管理器中的模块列表点击打开。

### 功能说明

- **插件状态**: 启用或禁用广告屏蔽功能
- **数据源**: 选择广告域名数据来源（StevenBlack/neoHosts/AdAway）
- **手动更新**: 手动触发广告列表更新
- **运行日志**: 查看模块运行状态和更新记录

### 命令行更新

也可以通过 WebUI 或手动执行更新：

```bash
# 手动更新广告列表
curl -sSL "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts" -o /data/adb/modules/adblock_hosts/system/etc/hosts
```

## 数据源

推荐使用以下数据源（已内置预设）：

| 数据源 | URL |
|--------|-----|
| StevenBlack Hosts | `https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts` |
| neoHosts | `https://raw.githubusercontent.com/neoo-lol/neohosts/master/hosts` |
| AdAway | `https://adaway.org/hosts.txt` |

## 工作原理

本模块通过修改系统的 hosts 文件，将广告域名解析到 127.0.0.1（本地回环地址），从而实现广告屏蔽。

## 已知问题

- 部分应用使用 HTTPS 加载广告，可能无法被 hosts 屏蔽
- 部分广告域名可能被遗漏，可手动添加

## 文件结构

```
AdBlock/
├── module.prop           # 模块信息
├── customize.sh          # 安装脚本
├── service.sh           # 启动服务脚本
├── servicewebui.sh      # WebUI 服务脚本
├── system/etc/hosts     # hosts 屏蔽列表
├── webroot/             # WebUI 静态文件
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── server.py
└── README.md            # 说明文档
```

## 常见问题

### Q: WebUI 无法访问？

A: 请确保：
1. 设备已重启
2. 模块已启用
3. 检查服务是否启动：`ps -ef | grep server.py`

### Q: 广告仍然显示？

A: 可能原因：
1. DNS 缓存未刷新 - 重启设备或清除 DNS 缓存
2. 广告使用 HTTPS 加载 - 需要其他屏蔽方式
3. 广告域名不在列表中

### Q: 如何查看日志？

A: 通过 WebUI 的"运行日志"功能，或查看模块目录下的 `update.log` 文件。

## 更新日志

### v1.2 (2026-02-17)
- 修复 WebUI 无法访问的问题
- 修复 JSON 解析错误
- 增强路径检测逻辑
- 改进错误处理和日志输出
- 添加 Magisk 环境支持

### v1.1
- 添加 WebUI 管理界面
- 支持自动更新
- 添加预设数据源

### v1.0
- 初始版本
- 基于 StevenBlack hosts
