# AdBlock 模块

基于 hosts 文件的广告屏蔽模块，适用于 KernelSU 和 Magisk。

## 安装

1. 下载模块 ZIP 文件
2. 打开 KernelSU Manager / Magisk Manager
3. 点击右下角"模块"图标
4. 从本地安装选择 ZIP 文件
5. 重启设备

## 卸载

1. 在管理器中禁用或删除模块
2. 重启设备

## 更新广告列表

如需更新广告域名列表，请编辑 `system/etc/hosts` 文件，添加或删除需要屏蔽的域名。

格式：`127.0.0.1 域名`

## 工作原理

本模块通过修改系统的 hosts 文件，将广告域名解析到 127.0.0.1（本地回环地址），从而实现广告屏蔽。

## 已知问题

- 部分应用使用 HTTPS 加载广告，可能无法被 hosts 屏蔽
- 部分广告域名可能被遗漏，可手动添加

## 文件结构

```
AdBlock/
├── module.prop          # 模块信息
├── customize.sh        # 安装脚本
├── system/etc/hosts    # hosts 屏蔽列表
└── README.md           # 说明文档
```
