class ApplicationController {
    constructor() {
        this.wsEvents = null;
        
        // Counters state
        this.counts = {
            a: 0,
            b: 0,
            c: 0,
            reject: 0,
            total: 0
        };
        
        // DOM refs for counters
        this.domA = document.getElementById('dash-count-a');
        this.domB = document.getElementById('dash-count-b');
        this.domC = document.getElementById('dash-count-c');
        this.domReject = document.getElementById('dash-count-reject');
        this.domTotal = document.getElementById('dash-total-count');
        this.eventsList = document.getElementById('recent-events-list');
    }

    init() {
        console.log("[App] Initializing durian classifier UI application...");
        
        // Connect Live camera feed receiver
        window.LiveFeedInstance = new window.LiveFeed('live-canvas', 'video-placeholder');
        window.LiveFeedInstance.connect();
        
        // Connect event notification WebSocket
        this.connectEventsWS();
        
        // Instantiate component controllers
        window.GradeDisplay = new window.GradeDisplay();
        window.BatchControls = new window.BatchControlsManager();
        window.HistoryLogs = new window.DetectionHistoryManager();
        window.Benchmarks = new window.BenchmarkManager();
        window.ModelUpdates = new window.ModelUpdatePanelManager();
        window.SettingsPanel = new window.SettingsPanelManager();
        
        // Load initial translation values
        if (window.initI18n) {
            window.initI18n();
        }
    }

    connectEventsWS(host = "127.0.0.1", port = "8000") {
        const wsUrl = `ws://${host}:${port}/ws/events`;
        console.log(`[App] Connecting to events WS: ${wsUrl}`);
        
        const statusDot = document.getElementById('ws-status-dot');
        const statusText = document.getElementById('ws-status-text');
        
        this.wsEvents = new WebSocket(wsUrl);
        
        this.wsEvents.onopen = () => {
            console.log("[App] Events WS connected.");
            statusDot.className = 'status-dot connected';
            if (statusText && window.t) {
                statusText.textContent = window.t('status_connected');
            }
        };

        this.wsEvents.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log("[App] Event received:", data);
                
                if (data.event_type === 'detection') {
                    this.handleDetectionEvent(data);
                }
            } catch (e) {
                console.error("[App] Error parsing event message:", e);
            }
        };

        this.wsEvents.onclose = () => {
            console.warn("[App] Events WS connection closed.");
            statusDot.className = 'status-dot';
            if (statusText && window.t) {
                statusText.textContent = window.t('status_disconnected');
            }
            // Reconnect after 3 seconds
            setTimeout(() => this.connectEventsWS(host, port), 3000);
        };

        this.wsEvents.onerror = (err) => {
            console.error("[App] Events WS error:", err);
            this.wsEvents.close();
        };
    }

    handleDetectionEvent(data) {
        const grade = data.grade || 'A';
        const reasons = data.reasons || [];
        const detections = data.detections || [];
        
        // 1. Update large grade widget
        if (window.GradeDisplay) {
            window.GradeDisplay.updateGrade(grade, reasons, detections);
        }
        
        // 2. Increment counters
        const lowerGrade = grade.toLowerCase();
        if (lowerGrade in this.counts) {
            this.counts[lowerGrade]++;
        } else if (lowerGrade === 'reject') {
            this.counts.reject++;
        }
        this.counts.total++;
        this.updateCounterDOM();
        
        // 3. Append to recent events list
        this.appendEventToList(grade, reasons, data.timestamp);
        
        // 4. Refresh logs table if visible
        if (window.HistoryLogs) {
            window.HistoryLogs.loadHistory();
        }
    }

    updateCounterDOM() {
        this.domA.textContent = this.counts.a;
        this.domB.textContent = this.counts.b;
        this.domC.textContent = this.counts.c;
        this.domReject.textContent = this.counts.reject;
        this.domTotal.textContent = this.counts.total;
    }

    resetDashboardStats() {
        this.counts = { a: 0, b: 0, c: 0, reject: 0, total: 0 };
        this.updateCounterDOM();
        this.eventsList.innerHTML = '';
        if (window.GradeDisplay) {
            window.GradeDisplay.updateGrade('-', [], []);
        }
    }

    appendEventToList(grade, reasons, timestamp) {
        const item = document.createElement('div');
        item.className = 'event-item';
        
        const details = document.createElement('div');
        details.className = 'event-details';
        
        const label = document.createElement('strong');
        label.textContent = reasons.length > 0 ? reasons.join(', ') : 'Grade A (Fruit Clean)';
        details.appendChild(label);
        
        const time = document.createElement('span');
        time.className = 'event-time';
        time.textContent = timestamp || new Date().toLocaleTimeString();
        details.appendChild(time);
        
        item.appendChild(details);
        
        const gradeSpan = document.createElement('span');
        gradeSpan.className = `event-grade ${grade.toLowerCase()}`;
        gradeSpan.textContent = grade;
        item.appendChild(gradeSpan);
        
        // Prepend to list
        this.eventsList.insertBefore(item, this.eventsList.firstChild);
        
        // Limit items in display to 10
        while (this.eventsList.children.length > 10) {
            this.eventsList.removeChild(this.eventsList.lastChild);
        }
    }
}

// Sidebar Navigation tab-switching logic
function switchTab(tabId) {
    // Deactivate all nav links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => link.classList.remove('active'));
    
    // Deactivate all panels
    const panels = document.querySelectorAll('.tab-panel');
    panels.forEach(p => p.classList.remove('active'));
    
    // Activate target
    const targetLinkMap = {
        'dashboard': 'nav-dash-link',
        'batches': 'nav-batch-link',
        'benchmarks': 'nav-bench-link',
        'history': 'nav-hist-link',
        'settings': 'nav-settings-link'
    };
    
    const activeLink = document.getElementById(targetLinkMap[tabId]);
    if (activeLink) activeLink.classList.add('active');
    
    const activePanel = document.getElementById(`panel-${tabId}`);
    if (activePanel) activePanel.classList.add('active');
    
    // Auto-refresh some components on switch
    if (tabId === 'benchmarks' && window.Benchmarks) {
        window.Benchmarks.loadBenchmarksList();
    } else if (tabId === 'history' && window.HistoryLogs) {
        window.HistoryLogs.loadHistory();
    } else if (tabId === 'settings' && window.SettingsPanel) {
        window.SettingsPanel.loadSettings();
        window.SettingsPanel.loadHealthData();
        if (window.ModelUpdates) {
            window.ModelUpdates.checkPendingUpdates();
        }
    } else if (tabId === 'batches' && window.BatchControls) {
        window.BatchControls.checkCurrentBatch();
    }
}

// Bootstrap application on DOM load
window.addEventListener('DOMContentLoaded', () => {
    window.appInstance = new ApplicationController();
    window.appInstance.init();
});
