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
    paths = [
        f"/data/adb/modules/{MODID}",
        f"/data/adb/ksu/modules/{MODID}",
        f"/data/local/tmp/{MODID}",
    ]
    for p in paths:
        if os.path.isdir(p):
            return p
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
            # Serve static files
            if self.path == '/' or self.path == '/index.html':
                self.path = '/webui/index.html'
            else:
                self.path = f'/webui{self.path}'

            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()

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

def main():
    os.chdir(MODDIR)
    PORT = 8888

    # 尝试关闭已存在的服务
    try:
        os.system(f"fuser -k {PORT}/tcp 2>/dev/null")
    except:
        pass

    with ReusableTCPServer(("", PORT), AdBlockHandler) as httpd:
        print(f"AdBlock WebUI starting on http://localhost:{PORT}")
        log_msg("WebUI 服务启动")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
