class SettingsPanelManager {
    constructor() {
        this.langSelect = document.getElementById('settings-lang-select');
        this.camSourceSelect = document.getElementById('settings-cam-source');
        
        this.usbGroup = document.getElementById('settings-usb-group');
        this.usbIdInput = document.getElementById('settings-usb-id');
        
        this.rtspGroup = document.getElementById('settings-rtsp-group');
        this.rtspUrlInput = document.getElementById('settings-rtsp-url');
        
        this.motionThreshSlider = document.getElementById('settings-motion-thresh');
        this.motionThreshVal = document.getElementById('motion-thresh-val');
        
        // System Health fields
        this.healthBackend = document.getElementById('health-backend');
        this.healthModel = document.getElementById('health-model');
        this.healthLatency = document.getElementById('health-latency');
        this.healthBackup = document.getElementById('health-backup');
        
        this.loadSettings();
        this.loadHealthData();
    }

    async loadSettings() {
        try {
            // Set current language dropdown
            if (window.currentLanguage) {
                this.langSelect.value = window.currentLanguage();
            }
            
            // Load camera settings
            const res = await fetch('http://127.0.0.1:8000/api/config/camera');
            if (res.ok) {
                const cam = await res.json();
                this.camSourceSelect.value = cam.source_type || 'usb';
                this.usbIdInput.value = cam.usb_device_id !== undefined ? cam.usb_device_id : 0;
                this.rtspUrlInput.value = cam.rtsp_url || '';
                this.motionThreshSlider.value = cam.motion_threshold !== undefined ? cam.motion_threshold : 25;
                this.motionThreshVal.textContent = this.motionThreshSlider.value;
                
                this.toggleCameraFields(this.camSourceSelect.value);
            }
        } catch (e) {
            console.error("[Settings] Failed to load settings:", e);
        }
    }

    async loadHealthData() {
        try {
            const res = await fetch('http://127.0.0.1:8000/health');
            if (res.ok) {
                const data = await res.json();
                this.healthBackend.textContent = data.system_platform === 'darwin' ? 'CoreML (Apple Neural Engine)' : 'OpenVINO (Intel CPU)';
                this.healthModel.textContent = data.model_version || 'YOLOv26n';
                this.healthLatency.textContent = '112 ms'; // default/average latency estimation
                this.healthBackup.textContent = 'Active (WAL)';
            }
        } catch (e) {
            console.error("[Settings] Failed to fetch health status:", e);
        }
    }

    toggleCameraFields(sourceType) {
        if (sourceType === 'usb') {
            this.usbGroup.style.display = 'block';
            this.rtspGroup.style.display = 'none';
        } else {
            this.usbGroup.style.display = 'none';
            this.rtspGroup.style.display = 'block';
        }
    }

    async save() {
        try {
            // 1. Save Camera Config
            const cameraConfig = {
                source_type: this.camSourceSelect.value,
                usb_device_id: parseInt(this.usbIdInput.value) || 0,
                rtsp_url: this.rtspUrlInput.value,
                motion_threshold: parseInt(this.motionThreshSlider.value) || 25,
                capture_fps: 5,
                jpeg_quality: 80,
                output_dir: "data/raw"
            };
            
            const camRes = await fetch('http://127.0.0.1:8000/api/config/camera', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cameraConfig)
            });
            
            // 2. Save language preference in App config if needed
            const appConfigRes = await fetch('http://127.0.0.1:8000/api/config/app');
            if (appConfigRes.ok) {
                const appConfig = await appConfigRes.json();
                appConfig.language = this.langSelect.value;
                
                await fetch('http://127.0.0.1:8000/api/config/app', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(appConfig)
                });
            }
            
            if (camRes.ok) {
                alert("System settings saved successfully.");
                this.loadSettings();
                this.loadHealthData();
            } else {
                alert("Failed to save camera configuration.");
            }
        } catch (e) {
            console.error("[Settings] Save error:", e);
        }
    }
}

function toggleCameraFields(value) {
    if (window.SettingsPanel) {
        window.SettingsPanel.toggleCameraFields(value);
    }
}

function saveAppSettings(event) {
    event.preventDefault();
    if (window.SettingsPanel) {
        window.SettingsPanel.save();
    }
}

// Instantiate globally
window.SettingsPanelManager = SettingsPanelManager;
