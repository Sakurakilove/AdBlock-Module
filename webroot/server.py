#!/usr/bin/env python3
# AdBlock WebUI Server
# 支持静态文件服务和 API 请求

import http.server
import socketserver
import json
import os
import subprocess
import re
import time

MODID = "adblock_hosts"

def get_mod_dir():
    # 首先尝试检测模块实际安装位置
    # 检查常见路径
    paths = [
        "/data/adb/ksu/modules/adblock_hosts",
        "/data/adb/modules/adblock_hosts",
        "/data/local/tmp/adblock_hosts",
    ]
    for p in paths:
        if os.path.isdir(p):
            return p

    # 尝试通过当前工作目录向上查找
    cwd = os.getcwd()
    # 如果当前目录就是模块目录
    if os.path.isfile(os.path.join(cwd, "module.prop")):
        return cwd

    # 尝试父目录
    parent = os.path.dirname(cwd)
    if os.path.isfile(os.path.join(parent, "module.prop")):
        return parent

    # 查找包含module.prop的目录
    for root, dirs, files in os.walk("/data"):
        if "module.prop" in files:
            mod_dir = os.path.join(root)
            # 检查是否是adblock模块
            prop_file = os.path.join(mod_dir, "module.prop")
            try:
                with open(prop_file, 'r') as f:
                    content = f.read()
                    if 'id=adblock_hosts' in content or MODID in content:
                        return mod_dir
            except:
                pass

    return paths[0]

MODDIR = get_mod_dir()
CONFIG_FILE = os.path.join(MODDIR, "config.json")
HOSTS_FILE = os.path.join(MODDIR, "system/etc/hosts")
LOG_FILE = os.path.join(MODDIR, "update.log")

def load_config():
    cfg = {
        "enabled": True,
        "source_url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "last_update": 0
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg.update(json.load(f))
        except:
            pass
    return cfg

def save_config(cfg):
    # 设置配置文件权限为 600 (所有者读写)
    os.umask(0o077)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)
    os.umask(0o022)

def count_domains():
    if not os.path.exists(HOSTS_FILE):
        return 0
    count = 0
    with open(HOSTS_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("0.0.0.0 ") or line.startswith("127.0.0.1 "):
                if not line.startswith("#"):
                    count += 1
    return count

def log_msg(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{int(time.time())}] {msg}\n")

def get_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            for line in reversed(f.readlines()):
                m = re.match(r'\[(\d+)\] (.+)', line.strip())
                if m:
                    logs.append({"time": int(m.group(1)), "msg": m.group(2)})
                    if len(logs) >= 100:
                        break
    return logs

def do_update(source_url):
    log_msg("开始更新广告列表...")

    tmp_file = "/data/local/tmp/hosts_new"
    os.makedirs("/data/local/tmp", exist_ok=True)

    try:
        result = subprocess.run(
            ["curl", "-sSL", "--connect-timeout", "30", "--max-time", "120",
             "-o", tmp_file, source_url],
            capture_output=True, timeout=150
        )

        if result.returncode != 0:
            try:
                log_msg(f"下载失败: {result.stderr.decode('utf-8', errors='ignore')}")
            except:
                log_msg("下载失败")
            return False, "下载失败"

        if not os.path.exists(tmp_file) or os.path.getsize(tmp_file) < 1000:
            log_msg("下载的文件无效")
            return False, "下载文件无效"

        lines = []
        with open(tmp_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("0.0.0.0 ") or line.startswith("127.0.0.1 "):
                    if not line.startswith("#"):
                        lines.append(line)

        hosts_content = "# AdBlock Hosts\n# Generated: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
        hosts_content += "127.0.0.1 localhost\n"
        hosts_content += "::1 localhost\n\n"
        hosts_content += "\n".join(lines)

        with open(HOSTS_FILE, 'w') as f:
            f.write(hosts_content)

        os.remove(tmp_file)

        cfg = load_config()
        cfg['last_update'] = int(time.time())
        save_config(cfg)

        log_msg(f"更新成功! 域名数: {len(lines)}")
        return True, str(len(lines))

    except Exception as e:
        log_msg(f"更新错误: {str(e)}")
        return False, str(e)

class AdBlockHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 防止路径遍历攻击
        if '..' in self.path:
            self.send_error(403, 'Forbidden')
            return

        try:
            if self.path == '/api/status':
                cfg = load_config()
                self.send_json({
                    "success": True,
                    "enabled": cfg["enabled"],
                    "source_url": cfg["source_url"],
                    "domain_count": count_domains(),
                    "last_update": cfg["last_update"],
                    "last_check": int(time.time())
                })
            elif self.path == '/api/logs':
                self.send_json({"success": True, "logs": get_logs()})
            else:
                # Serve static files from webroot directory
                # 移除开头的/，确保路径正确
                path = self.path.lstrip('/')
                if self.path == '/' or self.path == '/index.html':
                    path = 'webroot/index.html'
                else:
                    path = 'webroot' + self.path

                # 尝试找到文件
                if os.path.isfile(path):
                    # 确定Content-Type
                    content_type = 'text/html'
                    if path.endswith('.css'):
                        content_type = 'text/css'
                    elif path.endswith('.js'):
                        content_type = 'application/javascript'
                    elif path.endswith('.json'):
                        content_type = 'application/json'
                    elif path.endswith('.png'):
                        content_type = 'image/png'
                    elif path.endswith('.jpg') or path.endswith('.jpeg'):
                        content_type = 'image/jpeg'

                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    with open(path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    # 文件不存在，返回404
                    self.send_error(404, 'File not found')
        except Exception as e:
            # 确保任何异常都返回有效的JSON响应
            self.send_json({"success": False, "error": str(e)})

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode()
        except Exception as e:
            self.send_json({"success": False, "error": "Invalid request: " + str(e)})
            return

        try:
            if self.path == '/api/toggle':
                data = json.loads(body) if body else {}
                cfg = load_config()
                cfg['enabled'] = data.get('enabled', True)
                save_config(cfg)
                log_msg(f"插件已{'启用' if cfg['enabled'] else '禁用'}")
                self.send_json({"success": True})

            elif self.path == '/api/setSource':
                data = json.loads(body) if body else {}
                url = data.get('url', '')
                if url:
                    cfg = load_config()
                    cfg['source_url'] = url
                    save_config(cfg)
                    log_msg(f"数据源已更新: {url}")
                    self.send_json({"success": True})
                else:
                    self.send_json({"success": False, "error": "URL 不能为空"})

            elif self.path == '/api/update':
                cfg = load_config()
                if not cfg['enabled']:
                    self.send_json({"success": False, "error": "插件已禁用"})
                    return

                success, result = do_update(cfg['source_url'])
                if success:
                    self.send_json({
                        "success": True,
                        "timestamp": int(time.time()),
                        "domain_count": int(result)
                    })
                else:
                    self.send_json({"success": False, "error": result})

            elif self.path == '/api/clearLog':
                if os.path.exists(LOG_FILE):
                    os.remove(LOG_FILE)
                self.send_json({"success": True})

            else:
                self.send_json({"success": False, "error": "Unknown endpoint"})

        except Exception as e:
            # 确保任何异常都返回有效的JSON响应
            self.send_json({"success": False, "error": str(e)})

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # 禁用日志输出

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def check_port(port):
    """检查端口是否已被占用"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(('127.0.0.1', port))
        s.close()
        return True  # 端口已被占用
    except:
        return False  # 端口未被占用

def main():
    os.chdir(MODDIR)
    PORT = 8888

    # 检查端口是否已被占用
    if check_port(PORT):
        print(f"端口 {PORT} 已被占用，跳过启动")
        log_msg(f"WebUI 端口 {PORT} 已被占用，跳过启动")
        return

    with ReusableTCPServer(("", PORT), AdBlockHandler) as httpd:
        print(f"AdBlock WebUI starting on http://localhost:{PORT}")
        log_msg("WebUI 服务启动")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
