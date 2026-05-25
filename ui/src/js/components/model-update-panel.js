class ModelUpdatePanelManager {
    constructor() {
        this.loadingIndicator = document.getElementById('ota-loading-indicator');
        this.emptyState = document.getElementById('ota-empty-state');
        this.comparePanel = document.getElementById('ota-compare-panel');
        
        // Metrics DOM
        this.currRecall = document.getElementById('ota-curr-recall');
        this.currMap = document.getElementById('ota-curr-map');
        this.currLatency = document.getElementById('ota-curr-latency');
        
        this.newRecall = document.getElementById('ota-new-recall');
        this.newMap = document.getElementById('ota-new-map');
        this.newLatency = document.getElementById('ota-new-latency');
        
        this.checkPendingUpdates();
    }

    async checkPendingUpdates() {
        this.loadingIndicator.style.display = 'block';
        this.emptyState.style.display = 'none';
        this.comparePanel.style.display = 'none';
        
        try {
            const res = await fetch('http://127.0.0.1:8000/api/model/update');
            if (res.ok) {
                const data = await res.json();
                
                if (data && data.status === 'pending_approval') {
                    this.showCompare(data);
                } else {
                    this.showEmpty();
                }
            } else {
                this.showEmpty();
            }
        } catch (e) {
            console.error("[ModelUpdate] Error checking updates:", e);
            this.showEmpty();
        } finally {
            this.loadingIndicator.style.display = 'none';
        }
    }

    showCompare(data) {
        const curr = data.current_metrics || {};
        const update = data.new_metrics || {};
        
        // Populate current metrics
        const curRecallVal = curr.recall_reject !== undefined ? curr.recall_reject : (curr.recall || 0);
        this.currRecall.textContent = `${(curRecallVal * 100).toFixed(1)}%`;
        this.currMap.textContent = `${((curr.mAP50 || curr.map || 0) * 100).toFixed(1)}%`;
        this.currLatency.textContent = `${(curr.latency_ms || 0).toFixed(0)}ms`;
        
        // Populate new metrics
        const newRecallVal = update.recall_reject !== undefined ? update.recall_reject : (update.recall || 0);
        this.newRecall.textContent = `${(newRecallVal * 100).toFixed(1)}%`;
        this.newMap.textContent = `${((update.mAP50 || update.map || 0) * 100).toFixed(1)}%`;
        this.newLatency.textContent = `${(update.latency_ms || 0).toFixed(0)}ms`;
        
        // Highlight improvements
        if (newRecallVal >= curRecallVal) {
            this.newRecall.className = 'metric-val better';
        } else {
            this.newRecall.className = 'metric-val';
        }
        
        if ((update.mAP50 || update.map || 0) >= (curr.mAP50 || curr.map || 0)) {
            this.newMap.className = 'metric-val better';
        } else {
            this.newMap.className = 'metric-val';
        }
        
        if ((update.latency_ms || 9999) <= (curr.latency_ms || 0)) {
            this.newLatency.className = 'metric-val better';
        } else {
            this.newLatency.className = 'metric-val';
        }
        
        this.emptyState.style.display = 'none';
        this.comparePanel.style.display = 'block';
    }

    showEmpty() {
        this.emptyState.style.display = 'block';
        this.comparePanel.style.display = 'none';
    }

    async approve() {
        if (!confirm("Are you sure you want to approve this model update? The vision engine will load the new weights immediately.")) {
            return;
        }
        
        try {
            const res = await fetch('http://127.0.0.1:8000/api/model/update/approve', {
                method: 'POST'
            });
            
            if (res.ok) {
                alert("Model update approved and successfully loaded.");
                this.showEmpty();
                // Refresh settings/system status
                if (window.SettingsPanel) {
                    window.SettingsPanel.loadHealthData();
                }
            } else {
                alert("Failed to apply model update.");
            }
        } catch (e) {
            console.error("[ModelUpdate] Approval request failed:", e);
        }
    }

    async reject() {
        if (!confirm("Are you sure you want to reject this update? The temporary weights will be discarded.")) {
            return;
        }
        
        try {
            const res = await fetch('http://127.0.0.1:8000/api/model/update/reject', {
                method: 'POST'
            });
            
            if (res.ok) {
                alert("Model update rejected and cleaned up.");
                this.showEmpty();
            } else {
                alert("Failed to reject model update.");
            }
        } catch (e) {
            console.error("[ModelUpdate] Rejection request failed:", e);
        }
    }
}

function approveOTA() {
    if (window.ModelUpdates) {
        window.ModelUpdates.approve();
    }
}

function rejectOTA() {
    if (window.ModelUpdates) {
        window.ModelUpdates.reject();
    }
}

// Instantiate globally
window.ModelUpdatePanelManager = ModelUpdatePanelManager;
