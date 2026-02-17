// AdBlock WebUI - 前端逻辑

(function() {
    'use strict';

    // API 基础路径
    const API_BASE = '/api';

    // 状态
    let state = {
        enabled: true,
        sourceUrl: '',
        domainCount: 0,
        lastUpdate: null,
        lastCheck: null
    };

    // DOM 元素
    const elements = {
        enableToggle: document.getElementById('enableToggle'),
        statusBadge: document.getElementById('statusBadge'),
        statusDot: document.querySelector('.status-dot'),
        statusText: document.querySelector('.status-text'),
        sourceDesc: document.getElementById('sourceDesc'),
        updateDesc: document.getElementById('updateDesc'),
        domainCount: document.getElementById('domainCount'),
        updateTime: document.getElementById('updateTime'),
        lastCheck: document.getElementById('lastCheck'),
        logContainer: document.getElementById('logContainer'),
        logPanel: document.getElementById('logPanel'),
        sourceModal: document.getElementById('sourceModal'),
        sourceUrl: document.getElementById('sourceUrl'),
        loading: document.getElementById('loading'),
        toast: document.getElementById('toast')
    };

    // 初始化
    async function init() {
        showLoading(true);
        await loadStatus();
        setupEventListeners();
        showLoading(false);
    }

    // API 请求
    async function apiRequest(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, finalOptions);
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || '请求失败');
            }
            return data;
        } catch (error) {
            console.error('API 请求失败:', error);
            showToast(error.message, 'error');
            throw error;
        }
    }

    // 加载状态
    async function loadStatus() {
        try {
            const data = await apiRequest('/status');
            state = { ...state, ...data };

            // 更新 UI
            elements.enableToggle.checked = state.enabled;
            updateStatusBadge(state.enabled);
            elements.sourceDesc.textContent = `当前: ${getSourceName(state.sourceUrl)}`;
            elements.updateDesc.textContent = `上次更新: ${formatTime(state.lastUpdate)}`;
            elements.domainCount.textContent = formatNumber(state.domainCount);
            elements.updateTime.textContent = formatTime(state.lastUpdate);
            elements.lastCheck.textContent = formatTime(state.lastCheck);
        } catch (error) {
            console.error('加载状态失败:', error);
        }
    }

    // 更新状态显示
    function updateStatusBadge(enabled) {
        if (enabled) {
            elements.statusDot.classList.add('active');
            elements.statusText.textContent = '已启用';
        } else {
            elements.statusDot.classList.remove('active');
            elements.statusText.textContent = '已禁用';
        }
    }

    // 获取数据源名称
    function getSourceName(url) {
        if (!url) return '默认';
        if (url.includes('StevenBlack')) return 'StevenBlack Hosts';
        if (url.includes('neoolution')) return 'neoHosts';
        if (url.includes('adaway')) return 'AdAway';
        return '自定义';
    }

    // 格式化数字
    function formatNumber(num) {
        if (!num || num < 0) return '0';
        if (num >= 10000) return (num / 10000).toFixed(1) + '万';
        return num.toString();
    }

    // 格式化时间
    function formatTime(timestamp) {
        if (!timestamp) return '从未';
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
        if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';

        return date.toLocaleDateString('zh-CN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // 设置事件监听
    function setupEventListeners() {
        // 开关切换
        elements.enableToggle.addEventListener('change', async (e) => {
            const enabled = e.target.checked;
            try {
                await apiRequest('/toggle', {
                    method: 'POST',
                    body: JSON.stringify({ enabled })
                });
                updateStatusBadge(enabled);
                showToast(enabled ? '已启用' : '已禁用', 'success');
            } catch (error) {
                elements.enableToggle.checked = !enabled;
            }
        });

        // 编辑数据源
        document.getElementById('editSource').addEventListener('click', (e) => {
            e.stopPropagation();
            openSourceModal();
        });

        // 手动更新
        document.getElementById('btnUpdate').addEventListener('click', async (e) => {
            e.stopPropagation();
            await doUpdate();
        });

        // 查看日志
        document.getElementById('btnLog').addEventListener('click', async (e) => {
            e.stopPropagation();
            await openLogPanel();
        });

        // 关闭日志面板
        document.getElementById('closeLog').addEventListener('click', () => {
            elements.logPanel.classList.remove('active');
        });

        // 刷新日志
        document.getElementById('refreshLog').addEventListener('click', loadLogs);

        // 清空日志
        document.getElementById('clearLog').addEventListener('click', async () => {
            try {
                await apiRequest('/clearLog', { method: 'POST' });
                elements.logContainer.innerHTML = '<p class="log-empty">日志已清空</p>';
                showToast('日志已清空', 'success');
            } catch (error) {
                // ignore
            }
        });

        // 数据源弹窗
        document.getElementById('closeSource').addEventListener('click', closeSourceModal);
        document.getElementById('cancelSource').addEventListener('click', closeSourceModal);
        document.querySelector('.modal-backdrop').addEventListener('click', closeSourceModal);
        document.getElementById('saveSource').addEventListener('click', saveSource);

        // 预设数据源
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                elements.sourceUrl.value = btn.dataset.url;
                document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });

        // 点击卡片触发事件
        document.getElementById('toggleCard').addEventListener('click', () => {
            elements.enableToggle.checked = !elements.enableToggle.checked;
            elements.enableToggle.dispatchEvent(new Event('change'));
        });

        document.getElementById('sourceCard').addEventListener('click', () => openSourceModal());
        document.getElementById('updateCard').addEventListener('click', () => doUpdate());
        document.getElementById('logCard').addEventListener('click', () => openLogPanel());
    }

    // 打开数据源弹窗
    function openSourceModal() {
        elements.sourceUrl.value = state.sourceUrl || '';
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.url === state.sourceUrl);
        });
        elements.sourceModal.classList.add('active');
    }

    // 关闭数据源弹窗
    function closeSourceModal() {
        elements.sourceModal.classList.remove('active');
    }

    // 保存数据源
    async function saveSource() {
        const url = elements.sourceUrl.value.trim();
        if (!url) {
            showToast('请输入数据源 URL', 'error');
            return;
        }

        showLoading(true);
        try {
            await apiRequest('/setSource', {
                method: 'POST',
                body: JSON.stringify({ url })
            });
            state.sourceUrl = url;
            elements.sourceDesc.textContent = `当前: ${getSourceName(url)}`;
            closeSourceModal();
            showToast('数据源已保存', 'success');
        } catch (error) {
            // ignore
        }
        showLoading(false);
    }

    // 执行更新
    async function doUpdate() {
        showLoading(true);
        try {
            showToast('正在更新...', 'success');
            const data = await apiRequest('/update', { method: 'POST' });
            state.lastUpdate = data.timestamp;
            state.domainCount = data.domainCount;
            elements.updateDesc.textContent = `上次更新: ${formatTime(state.lastUpdate)}`;
            elements.domainCount.textContent = formatNumber(state.domainCount);
            showToast(`更新成功，${data.domainCount} 个域名`, 'success');
        } catch (error) {
            // ignore
        }
        showLoading(false);
    }

    // 打开日志面板
    async function openLogPanel() {
        elements.logPanel.classList.add('active');
        await loadLogs();
    }

    // 加载日志
    async function loadLogs() {
        try {
            const data = await apiRequest('/logs');
            if (!data.logs || data.logs.length === 0) {
                elements.logContainer.innerHTML = '<p class="log-empty">暂无日志</p>';
                return;
            }

            elements.logContainer.innerHTML = data.logs.map(log => {
                const time = new Date(log.time * 1000).toLocaleString('zh-CN');
                const level = log.msg.includes('失败') || log.msg.includes('错误') ? 'error' :
                              log.msg.includes('成功') || log.msg.includes('更新') ? 'success' : '';
                return `<div class="log-entry ${level}">
                    <span class="log-time">${time}</span>
                    <span class="log-msg">${escapeHtml(log.msg)}</span>
                </div>`;
            }).join('');
        } catch (error) {
            elements.logContainer.innerHTML = '<p class="log-empty">加载日志失败</p>';
        }
    }

    // HTML 转义
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 显示/隐藏加载
    function showLoading(show) {
        elements.loading.classList.toggle('active', show);
    }

    // 显示提示
    function showToast(message, type = '') {
        const toast = elements.toast;
        toast.querySelector('.toast-message').textContent = message;
        toast.className = 'toast show';
        if (type) toast.classList.add(type);

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    // 启动
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
