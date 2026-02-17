package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

const (
	MODID       = "adblock_hosts"
	CONFIG_FILE = "config.json"
)

var (
	MODDIR      string
	CONFIG_PATH string
	HOSTS_FILE  string
	LOG_FILE    string
)

type Config struct {
	Enabled    bool   `json:"enabled"`
	SourceURL  string `json:"source_url"`
	LastUpdate int64  `json:"last_update"`
}

type StatusResponse struct {
	Success     bool   `json:"success"`
	Enabled     bool   `json:"enabled"`
	SourceURL   string `json:"source_url"`
	DomainCount int    `json:"domain_count"`
	LastUpdate  int64  `json:"last_update"`
	LastCheck   int64  `json:"last_check"`
}

type LogEntry struct {
	Time int64  `json:"time"`
	Msg  string `json:"msg"`
}

type LogsResponse struct {
	Success bool      `json:"success"`
	Logs    []LogEntry `json:"logs"`
}

type APIResponse struct {
	Success    bool        `json:"success"`
	Error      string      `json:"error,omitempty"`
	Timestamp  int64       `json:"timestamp,omitempty"`
	DomainCount int        `json:"domain_count,omitempty"`
}

func init() {
	// 获取模块目录
	MODDIR = getModDir()
	CONFIG_PATH = filepath.Join(MODDIR, CONFIG_FILE)
	HOSTS_FILE = filepath.Join(MODDIR, "system/etc/hosts")
	LOG_FILE = filepath.Join(MODDIR, "update.log")
}

func getModDir() string {
	// 尝试多个可能的路径 - KSU 优先
	paths := []string{
		"/data/adb/ksu/modules/" + MODID,
		"/data/adb/modules/" + MODID,
		"/data/local/tmp/" + MODID,
	}

	for _, p := range paths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	// 如果都不存在，返回默认路径
	return "/data/adb/modules/" + MODID
}

func loadConfig() Config {
	cfg := Config{
		Enabled:    true,
		SourceURL:  "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
		LastUpdate: 0,
	}

	data, err := os.ReadFile(CONFIG_PATH)
	if err != nil {
		return cfg
	}

	json.Unmarshal(data, &cfg)
	return cfg
}

func saveConfig(cfg Config) error {
	data, _ := json.MarshalIndent(cfg, "", "  ")
	return os.WriteFile(CONFIG_PATH, data, 0644)
}

func countDomains() int {
	data, err := os.ReadFile(HOSTS_FILE)
	if err != nil {
		return 0
	}

	count := 0
	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "0.0.0.0 ") || strings.HasPrefix(line, "127.0.0.1 ") {
			if !strings.HasPrefix(line, "#") {
				count++
			}
		}
	}
	return count
}

func logMsg(msg string) {
	os.MkdirAll(filepath.Dir(LOG_FILE), 0755)
	f, err := os.OpenFile(LOG_FILE, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	timestamp := time.Now().Unix()
	fmt.Fprintf(f, "[%d] %s\n", timestamp, msg)
}

func getLogs() []LogEntry {
	var logs []LogEntry

	data, err := os.ReadFile(LOG_FILE)
	if err != nil {
		return logs
	}

	re := regexp.MustCompile(`\[(\d+)\] (.+)`)
	lines := strings.Split(string(data), "\n")

	for i := len(lines) - 1; i >= 0 && len(logs) < 100; i-- {
		matches := re.FindStringSubmatch(lines[i])
		if matches != nil {
			t, _ := strconv.ParseInt(matches[1], 10, 64)
			logs = append(logs, LogEntry{Time: t, Msg: matches[2]})
		}
	}

	return logs
}

// API 处理器
func handleStatus(w http.ResponseWriter, r *http.Request) {
	cfg := loadConfig()
	domainCount := countDomains()

	json.NewEncoder(w).Encode(StatusResponse{
		Success:     true,
		Enabled:     cfg.Enabled,
		SourceURL:   cfg.SourceURL,
		DomainCount: domainCount,
		LastUpdate:  cfg.LastUpdate,
		LastCheck:   time.Now().Unix(),
	})
}

func handleToggle(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Enabled bool `json:"enabled"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		json.NewEncoder(w).Encode(APIResponse{Success: false, Error: "Invalid request"})
		return
	}

	cfg := loadConfig()
	cfg.Enabled = req.Enabled
	saveConfig(cfg)

	logMsg(fmt.Sprintf("插件已%s", map[bool]string{true: "启用", false: "禁用"}[req.Enabled]))

	json.NewEncoder(w).Encode(APIResponse{Success: true})
}

func handleSetSource(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		URL string `json:"url"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		json.NewEncoder(w).Encode(APIResponse{Success: false, Error: "Invalid request"})
		return
	}

	cfg := loadConfig()
	cfg.SourceURL = req.URL
	saveConfig(cfg)

	logMsg("数据源已更新: " + req.URL)

	json.NewEncoder(w).Encode(APIResponse{Success: true})
}

func handleUpdate(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	cfg := loadConfig()
	if !cfg.Enabled {
		json.NewEncoder(w).Encode(APIResponse{Success: false, Error: "插件已禁用"})
		return
	}

	logMsg("开始更新广告列表...")

	// 下载新 hosts
	tmpFile := filepath.Join("/data/local/tmp", "hosts_new")
	os.MkdirAll("/data/local/tmp", 0755)

	cmd := exec.Command("curl", "-sSL", "--connect-timeout", "30", "--max-time", "120",
		"-o", tmpFile, cfg.SourceURL)
	if err := cmd.Run(); err != nil {
		logMsg("下载失败: " + err.Error())
		json.NewEncoder(w).Encode(APIResponse{Success: false, Error: "下载失败"})
		return
	}

	// 检查文件
	data, err := os.ReadFile(tmpFile)
	if err != nil || len(data) < 1000 {
		logMsg("下载的文件无效")
		os.Remove(tmpFile)
		json.NewEncoder(w).Encode(APIResponse{Success: false, Error: "下载文件无效"})
		return
	}

	// 提取域名
	var lines []string
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "0.0.0.0 ") || strings.HasPrefix(line, "127.0.0.1 ") {
			if !strings.HasPrefix(line, "#") {
				lines = append(lines, line)
			}
		}
	}

	// 写入 hosts 文件
	hostsContent := "# AdBlock Hosts\n# Generated: " + time.Now().Format("2006-01-02 15:04:05") + "\n\n"
	hostsContent += "127.0.0.1 localhost\n"
	hostsContent += "::1 localhost\n\n"
	hostsContent += strings.Join(lines, "\n")

	if err := os.WriteFile(HOSTS_FILE, []byte(hostsContent), 0644); err != nil {
		logMsg("写入 hosts 失败: " + err.Error())
		json.NewEncoder(w).Encode(APIResponse{Success: false, Error: "写入失败"})
		return
	}

	os.Remove(tmpFile)

	cfg.LastUpdate = time.Now().Unix()
	saveConfig(cfg)

	domainCount := len(lines)
	logMsg(fmt.Sprintf("更新成功! 域名数: %d", domainCount))

	json.NewEncoder(w).Encode(APIResponse{
		Success:      true,
		Timestamp:    cfg.LastUpdate,
		DomainCount:  domainCount,
	})
}

func handleLogs(w http.ResponseWriter, r *http.Request) {
	logs := getLogs()
	json.NewEncoder(w).Encode(LogsResponse{Success: true, Logs: logs})
}

func handleClearLog(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	os.Remove(LOG_FILE)
	json.NewEncoder(w).Encode(APIResponse{Success: true})
}

func serveStatic(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	// 防止路径遍历攻击
	if strings.Contains(path, "..") {
		http.Error(w, "Forbidden", http.StatusForbidden)
		return
	}

	if path == "/" || path == "/index.html" {
		path = "/webroot/index.html"
	} else if !strings.HasPrefix(path, "/api") {
		// 为其他静态文件添加 /webroot 前缀
		path = "/webroot" + path
	}

	staticPath := filepath.Join(MODDIR, path)

	// 验证文件路径在模块目录内
	realPath, err := filepath.EvalSymlinks(staticPath)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if !strings.HasPrefix(realPath, MODDIR) {
		http.Error(w, "Forbidden", http.StatusForbidden)
		return
	}

	data, err := os.ReadFile(staticPath)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	// 设置 Content-Type
	contentType := "text/plain"
	switch {
	case strings.HasSuffix(path, ".html"):
		contentType = "text/html"
	case strings.HasSuffix(path, ".css"):
		contentType = "text/css"
	case strings.HasSuffix(path, ".js"):
		contentType = "application/javascript"
	case strings.HasSuffix(path, ".json"):
		contentType = "application/json"
	}

	w.Header().Set("Content-Type", contentType)
	w.Write(data)
}

func main() {
	// 确保目录存在
	os.MkdirAll(filepath.Dir(LOG_FILE), 0755)

	// 初始化配置
	cfg := loadConfig()
	if cfg.SourceURL == "" {
		cfg.SourceURL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
		saveConfig(cfg)
	}

	logMsg("WebUI 服务启动")

	// 注册路由
	http.HandleFunc("/api/status", handleStatus)
	http.HandleFunc("/api/toggle", handleToggle)
	http.HandleFunc("/api/setSource", handleSetSource)
	http.HandleFunc("/api/update", handleUpdate)
	http.HandleFunc("/api/logs", handleLogs)
	http.HandleFunc("/api/clearLog", handleClearLog)
	http.HandleFunc("/", serveStatic)

	// 启动服务器
	addr := ":8888"
	fmt.Printf("AdBlock WebUI starting on http://localhost%s\n", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		logMsg("WebUI 服务错误: " + err.Error())
	}
}
