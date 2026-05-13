// ============================================
// SymbioSync - Client-side logic
// No frameworks. No build tools. Just JS.
// ============================================

let ws = null;
let autoScroll = true;
let deviceState = { devices: {}, remembered: {}, last_scan: [], connected_count: 0 };

// Plugin status hooks: each plugin registers a callback to update itself
// when device state changes. Populated by plugin JS via control_js().
window._pluginStatusHooks = [];

// ------------------------------------------------------------------
// WebSocket
// ------------------------------------------------------------------

function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => {
        setWSStatus('connected');
    };

    ws.onclose = () => {
        setWSStatus('disconnected');
        setTimeout(connectWS, 3000);
    };

    ws.onerror = () => {
        setWSStatus('disconnected');
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
    };
}

function sendWS(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

function setWSStatus(state) {
    const dot = document.getElementById('ws-indicator');
    const text = document.getElementById('ws-status');
    if (state === 'connected') {
        dot.className = 'indicator-dot connected';
        text.textContent = 'Connected';
    } else if (state === 'scanning') {
        dot.className = 'indicator-dot scanning';
        text.textContent = 'Scanning...';
    } else {
        dot.className = 'indicator-dot';
        text.textContent = 'Reconnecting...';
    }
}

// ------------------------------------------------------------------
// Message handling
// ------------------------------------------------------------------

function handleMessage(msg) {
    switch (msg.type) {
        case 'log':
            appendLog(msg.entry);
            break;
        case 'log_history':
            msg.entries.forEach(e => appendLog(e));
            break;
        case 'status':
            updateDeviceState(msg.data);
            break;
        case 'scan_results':
            renderScanResults(msg.devices);
            document.getElementById('btn-scan').textContent = 'Scan';
            document.getElementById('btn-scan').disabled = false;
            break;
        case 'connect_result':
        case 'disconnect_result':
        case 'remember_result':
        case 'forget_result':
        case 'toggle_result':
        case 'command_result':
            break;
    }
}

// ------------------------------------------------------------------
// Tabs (supports dynamically added plugin tabs)
// ------------------------------------------------------------------

function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
        });
    });
}

initTabs();

// ------------------------------------------------------------------
// Plugin loading (dynamic tabs)
// ------------------------------------------------------------------

// Track loaded plugins for dormant state management
let loadedPlugins = [];

async function loadPlugins() {
    try {
        const resp = await fetch('/api/plugins');
        const data = await resp.json();
        const plugins = data.plugins || [];
        loadedPlugins = plugins;
        const tabBar = document.getElementById('tab-bar');
        const container = document.getElementById('plugin-tabs-container');

        // Find the Logs tab button as the insertion point
        const logsTab = tabBar.querySelector('[data-tab="logs"]');

        plugins.forEach(plugin => {
            // 1. Add tab button before Logs (with status dot)
            if (plugin.html) {
                const btn = document.createElement('button');
                btn.className = 'tab';
                btn.dataset.tab = plugin.type;
                btn.dataset.deviceType = plugin.type;
                // Status dot + label
                const dot = document.createElement('span');
                dot.className = 'tab-status-dot';
                dot.id = 'tab-dot-' + plugin.type;
                btn.appendChild(dot);
                btn.appendChild(document.createTextNode(plugin.label));
                if (plugin.dormant) {
                    btn.classList.add('tab-dormant');
                }
                tabBar.insertBefore(btn, logsTab);
            }

            // 2. Add tab content panel
            if (plugin.html) {
                const panel = document.createElement('div');
                panel.className = 'tab-content';
                panel.id = 'tab-' + plugin.type;
                panel.innerHTML = plugin.html;
                if (plugin.dormant) {
                    panel.classList.add('plugin-dormant');
                }
                container.appendChild(panel);
            }

            // 3. Execute plugin JS (even if dormant, so hooks are registered)
            if (plugin.js) {
                const script = document.createElement('script');
                script.textContent = plugin.js;
                document.body.appendChild(script);
            }
        });

        // Re-initialize tab click handlers for new tabs
        initTabs();

        // Render plugins management list
        renderPluginsList(plugins);
    } catch (e) {
        console.error('Failed to load plugins:', e);
    }
}

function renderPluginsList(plugins) {
    const pluginsList = document.getElementById('plugins-list');
    if (!pluginsList) return;

    if (!plugins || plugins.length === 0) {
        pluginsList.innerHTML = '<div class="empty-state"><div>No plugins registered</div></div>';
        return;
    }

    pluginsList.innerHTML = plugins.map(p => `
        <div class="device-item ${p.dormant ? 'disconnected' : 'connected'}">
            <div class="device-info">
                <div class="device-name">${esc(p.label)}</div>
                <div class="device-meta">${esc(p.description)}</div>
                ${p.dormant ? '<div style="font-size: 0.8rem; color: var(--accent-warm); margin-top: 6px;">When you reactivate this plugin, you may need to cycle power on your device and reconnect via the Connect tab.</div>' : ''}
            </div>
            <div class="device-actions">
                <span class="badge ${p.dormant ? 'badge-dormant' : 'badge-connected'}">
                    ${p.dormant ? 'Dormant' : 'Active'}
                </span>
                <button class="btn btn-small ${p.dormant ? 'btn-primary' : ''}"
                    title="${p.dormant ? 'Click to reactivate this plugin' : 'Click to make this plugin go dormant'}"
                    onclick="togglePlugin('${esc(p.type)}')">
                    ${p.dormant ? 'Wake' : 'Dormant'}
                </button>
            </div>
        </div>
    `).join('');
}

async function togglePlugin(pluginType) {
    try {
        const resp = await fetch(`/api/plugins/${pluginType}/toggle`, { method: 'POST' });
        const data = await resp.json();
        if (data.ok) {
            const isDormant = data.state === 'dormant';

            // Update tab button visual
            const tabBtn = document.querySelector(`.tab[data-tab="${pluginType}"]`);
            if (tabBtn) {
                if (isDormant) {
                    tabBtn.classList.add('tab-dormant');
                } else {
                    tabBtn.classList.remove('tab-dormant');
                }
            }

            // Update tab content panel
            const panel = document.getElementById('tab-' + pluginType);
            if (panel) {
                if (isDormant) {
                    panel.classList.add('plugin-dormant');
                } else {
                    panel.classList.remove('plugin-dormant');
                }
            }

            // Update the plugins list
            const plugin = loadedPlugins.find(p => p.type === pluginType);
            if (plugin) plugin.dormant = isDormant;
            renderPluginsList(loadedPlugins);
        }
    } catch (e) {
        console.error('Failed to toggle plugin:', e);
    }
}

// ------------------------------------------------------------------
// Scan
// ------------------------------------------------------------------

function doScan() {
    const btn = document.getElementById('btn-scan');
    btn.textContent = 'Scanning...';
    btn.disabled = true;
    setWSStatus('scanning');
    sendWS({ action: 'scan' });
}

function renderScanResults(devices) {
    const container = document.getElementById('scan-results');
    if (!devices || devices.length === 0) {
        container.innerHTML = '<div class="empty-state"><div>No compatible devices found. Make sure your device is on and in range.</div></div>';
        setWSStatus('connected');
        return;
    }

    setWSStatus('connected');
    container.innerHTML = devices.map(d => `
        <div class="scan-item">
            <div class="device-info">
                <div class="device-name">${esc(d.name)}</div>
                <div class="device-meta">${esc(d.address)} / ${esc(d.type)}</div>
            </div>
            <div class="device-actions">
                <span class="scan-rssi">${d.rssi ? d.rssi + ' dBm' : ''}</span>
                <button class="btn btn-primary btn-small" onclick="connectDevice('${esc(d.address)}')">Connect</button>
                <button class="btn btn-small" onclick="rememberDevice('${esc(d.address)}', '${esc(d.name)}', '${esc(d.type)}')">Remember</button>
            </div>
        </div>
    `).join('');
}

// ------------------------------------------------------------------
// Device actions (shared across all plugins)
// ------------------------------------------------------------------

function connectDevice(addr) {
    sendWS({ action: 'connect', address: addr });
}

function disconnectDevice(addr) {
    sendWS({ action: 'disconnect', address: addr });
}

function rememberDevice(addr, name, type) {
    sendWS({ action: 'remember', address: addr, name: name, device_type: type });
}

function forgetDevice(addr) {
    sendWS({ action: 'forget', address: addr });
}

function toggleEnabled(addr, enabled) {
    sendWS({ action: 'toggle_enabled', address: addr, enabled: enabled });
}

// ------------------------------------------------------------------
// Device state rendering (Connect tab + plugin hooks)
// ------------------------------------------------------------------

// Track last successful contact per device type
let lastContactByType = {};

function updateDeviceState(data) {
    deviceState = data;

    // Update device count in header
    document.getElementById('device-count').textContent =
        `${data.connected_count} device${data.connected_count !== 1 ? 's' : ''}`;

    // Update tab status dots per device type
    const connectedTypes = {};
    Object.values(data.devices || {}).forEach(d => {
        if (d.connected) {
            connectedTypes[d.device_type] = true;
            lastContactByType[d.device_type] = Date.now();
        }
    });
    document.querySelectorAll('.tab-status-dot').forEach(dot => {
        const type = dot.id.replace('tab-dot-', '');
        const isLive = connectedTypes[type] || false;
        dot.classList.toggle('live', isLive);
        // Update tooltip with last contact
        if (isLive) {
            dot.title = 'Connected';
        } else if (lastContactByType[type]) {
            const ago = Math.round((Date.now() - lastContactByType[type]) / 1000);
            if (ago < 60) dot.title = 'Last contact: ' + ago + 's ago';
            else if (ago < 3600) dot.title = 'Last contact: ' + Math.round(ago / 60) + 'm ago';
            else dot.title = 'Last contact: ' + Math.round(ago / 3600) + 'h ago';
        } else {
            dot.title = 'Not connected';
        }
    });

    // Render Connect tab lists
    renderRemembered(data.remembered);
    renderConnected(data.devices);

    // Call all plugin status hooks
    window._pluginStatusHooks.forEach(function(hook) {
        try { hook(data); } catch (e) { console.error('Plugin hook error:', e); }
    });
}

function renderRemembered(remembered) {
    const container = document.getElementById('remembered-list');
    const entries = Object.entries(remembered || {});
    if (entries.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#x1F4BE;</div><div>No remembered devices yet</div></div>';
        return;
    }

    container.innerHTML = entries.map(([addr, info]) => {
        const isConnected = info.connected;
        return `
            <div class="device-item ${isConnected ? 'connected' : 'disconnected'}">
                <div class="device-info">
                    <div class="device-name">${esc(info.name || addr)}</div>
                    <div class="device-meta">${esc(addr)} / ${esc(info.type || 'unknown')}
                        <span class="badge ${isConnected ? 'badge-connected' : 'badge-disconnected'}">
                            ${isConnected ? 'Connected' : 'Disconnected'}
                        </span>
                    </div>
                </div>
                <div class="device-actions">
                    <label class="toggle" title="${info.enabled !== false ? 'Auto-connect enabled' : 'Auto-connect disabled'}">
                        <input type="checkbox" ${info.enabled !== false ? 'checked' : ''}
                            onchange="toggleEnabled('${esc(addr)}', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                    ${isConnected
                        ? `<button class="btn btn-small" onclick="disconnectDevice('${esc(addr)}')">Disconnect</button>`
                        : `<button class="btn btn-primary btn-small" title="If device does not connect, try cycling its power" onclick="connectDevice('${esc(addr)}')">Connect</button>`
                    }
                    <button class="btn btn-danger btn-small" onclick="forgetDevice('${esc(addr)}')">Forget</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderConnected(devices) {
    const container = document.getElementById('connected-list');
    const connected = Object.entries(devices || {}).filter(([_, d]) => d.connected);
    if (connected.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#x1F517;</div><div>No devices connected</div></div>';
        return;
    }

    container.innerHTML = connected.map(([addr, d]) => `
        <div class="device-item connected">
            <div class="device-info">
                <div class="device-name">${esc(d.name)}</div>
                <div class="device-meta">${esc(addr)} / ${esc(d.device_type)}
                    ${d.status.battery >= 0 ? `<span style="margin-left: 8px;">&#x1F50B; ${d.status.battery}%</span>` : ''}
                    ${d.status.model ? `<span style="margin-left: 8px;">${esc(d.status.model)}</span>` : ''}
                </div>
            </div>
            <div class="device-actions">
                <span style="font-size: 0.8rem; color: var(--text-dim);">
                    ${formatUptime(d.status.uptime_seconds)}
                </span>
                <button class="btn btn-small" onclick="disconnectDevice('${esc(addr)}')">Disconnect</button>
            </div>
        </div>
    `).join('');
}

// ------------------------------------------------------------------
// Log display
// ------------------------------------------------------------------

function appendLog(entry) {
    const container = document.getElementById('log-container');
    const el = document.createElement('div');
    el.className = 'log-entry';

    const eventClass = getEventClass(entry.event, entry.level);
    el.innerHTML = `<span class="log-ts">${entry.ts}</span> <span class="log-event ${eventClass}">[${esc(entry.event)}]</span>${entry.device ? ` <span class="log-device">${esc(entry.device)}</span>` : ''} <span class="log-detail">${esc(entry.detail)}</span>`;

    container.appendChild(el);

    while (container.children.length > 1000) {
        container.removeChild(container.firstChild);
    }

    if (autoScroll) {
        container.scrollTop = container.scrollHeight;
    }
}

function getEventClass(event, level) {
    if (level === 'error' || event.includes('FAIL')) return 'log-event-err';
    if (level === 'warn' || event === 'WARN' || event === 'DROP') return 'log-event-warn';
    if (event === 'CMD' || event === 'VIBRATE') return 'log-event-cmd';
    if (event === 'RX') return 'log-event-rx';
    if (event.includes('SCAN')) return 'log-event-scan';
    return 'log-event-info';
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    document.getElementById('btn-autoscroll').textContent = `Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
}

function clearLogs() {
    document.getElementById('log-container').innerHTML = '';
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function esc(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

function formatUptime(seconds) {
    if (!seconds || seconds <= 0) return '0s';
    if (seconds < 60) return Math.round(seconds) + 's';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ' + Math.round(seconds % 60) + 's';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h + 'h ' + m + 'm';
}

// ------------------------------------------------------------------
// Partnership profile
// ------------------------------------------------------------------

async function loadPartnershipProfile() {
    try {
        const resp = await fetch('/api/partnership-profile');
        const data = await resp.json();
        var textarea = document.getElementById('partnership-profile');
        textarea.value = data.profile || '';
        updateProfileCharCount();
    } catch (e) { /* ignore */ }
}

async function savePartnershipProfile() {
    var profile = document.getElementById('partnership-profile').value;
    var statusEl = document.getElementById('profile-status');
    try {
        const resp = await fetch('/api/partnership-profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile: profile })
        });
        const data = await resp.json();
        if (data.ok) {
            statusEl.textContent = 'Saved (' + data.length + ' chars)';
            statusEl.style.color = '#4ade80';
            setTimeout(function() { statusEl.textContent = ''; }, 3000);
        }
    } catch (e) {
        statusEl.textContent = 'Error: ' + e.message;
        statusEl.style.color = '#f87171';
    }
}

function updateProfileCharCount() {
    var textarea = document.getElementById('partnership-profile');
    var countEl = document.getElementById('profile-char-count');
    if (textarea && countEl) {
        countEl.textContent = textarea.value.length + ' chars';
    }
}

// Update char count on input
document.addEventListener('DOMContentLoaded', function() {
    var textarea = document.getElementById('partnership-profile');
    if (textarea) {
        textarea.addEventListener('input', updateProfileCharCount);
    }
    loadPartnershipProfile();
});

// ------------------------------------------------------------------
// Companion skill generation
// ------------------------------------------------------------------

let currentSkill = '';

async function generateSkill() {
    const hostOverride = document.getElementById('skill-host-override').value.trim();
    const statusEl = document.getElementById('skill-status');
    statusEl.textContent = 'Generating...';

    try {
        const params = hostOverride ? `?host_override=${encodeURIComponent(hostOverride)}` : '';
        const resp = await fetch(`/api/skill${params}`);
        const data = await resp.json();
        currentSkill = data.skill;

        const previewCard = document.getElementById('skill-preview-card');
        const preview = document.getElementById('skill-preview');
        const sizeEl = document.getElementById('skill-size');
        previewCard.style.display = '';
        preview.textContent = currentSkill;
        sizeEl.textContent = `${currentSkill.length.toLocaleString()} chars`;

        document.getElementById('btn-download-skill').disabled = false;
        document.getElementById('btn-copy-skill').disabled = false;

        statusEl.textContent = 'Skill generated from current server state.';
    } catch (e) {
        statusEl.textContent = `Error: ${e.message}`;
    }
}

function downloadSkill() {
    if (!currentSkill) return;
    const blob = new Blob([currentSkill], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'SKILL.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    document.getElementById('skill-status').textContent = 'Downloaded as SKILL.md';
}

async function copySkill() {
    if (!currentSkill) return;
    try {
        await navigator.clipboard.writeText(currentSkill);
        document.getElementById('btn-copy-skill').textContent = 'Copied!';
        setTimeout(() => {
            document.getElementById('btn-copy-skill').textContent = 'Copy to Clipboard';
        }, 2000);
    } catch (e) {
        const textarea = document.createElement('textarea');
        textarea.value = currentSkill;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        document.getElementById('btn-copy-skill').textContent = 'Copied!';
        setTimeout(() => {
            document.getElementById('btn-copy-skill').textContent = 'Copy to Clipboard';
        }, 2000);
    }
}

// ------------------------------------------------------------------
// Server restart
// ------------------------------------------------------------------

function restartServer() {
    if (!confirm('Stop all devices and restart the server?')) return;
    fetch('/api/restart', { method: 'POST' }).catch(() => {});
    setWSStatus('disconnected');
    document.getElementById('ws-status').textContent = 'Server stopping...';
}

// ------------------------------------------------------------------
// Keyboard shortcuts
// ------------------------------------------------------------------

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        // Global emergency stop -- tell all plugins to stop
        sendWS({ action: 'stop_all' });
    }
});

// ------------------------------------------------------------------
// Init
// ------------------------------------------------------------------

// Load plugins first, then connect WS
loadPlugins().then(() => {
    connectWS();
});

// Periodically request status update
setInterval(() => {
    sendWS({ action: 'status' });
}, 5000);
