class BatchControlsManager {
    constructor() {
        this.form = document.getElementById('batch-form');
        this.batchIdInput = document.getElementById('input-batch-id');
        this.operatorIdInput = document.getElementById('input-operator-id');
        this.benchmarkSelect = document.getElementById('select-batch-benchmark');
        
        this.startBtn = document.getElementById('btn-start-batch');
        this.stopBtn = document.getElementById('btn-stop-batch');
        
        // Active Info panel
        this.infoBatchId = document.getElementById('info-batch-id');
        this.infoOperator = document.getElementById('info-operator');
        this.infoBenchmark = document.getElementById('info-benchmark');
        this.infoStartTime = document.getElementById('info-start-time');
        this.infoStatus = document.getElementById('info-status');
        
        // Dashboard status indicators
        this.dashActiveBatchId = document.getElementById('dash-active-batch-id');
        
        // Load initial state
        this.loadBenchmarks();
        this.checkCurrentBatch();
    }

    async loadBenchmarks() {
        try {
            const res = await fetch('http://127.0.0.1:8000/api/config/rules');
            if (res.ok) {
                const rules = await res.json();
                
                // Fetch list of all benchmarks
                const listRes = await fetch('http://127.0.0.1:8000/api/config/benchmarks');
                if (listRes.ok) {
                    const benchmarks = await listRes.json();
                    this.benchmarkSelect.innerHTML = '';
                    
                    benchmarks.forEach(bench => {
                        const opt = document.createElement('option');
                        // Slice .json suffix if present
                        const name = bench.replace('.json', '');
                        opt.value = name;
                        opt.textContent = name;
                        if (name === rules.active_benchmark) {
                            opt.selected = true;
                        }
                        this.benchmarkSelect.appendChild(opt);
                    });
                }
            }
        } catch (e) {
            console.error("[BatchControls] Failed to load benchmarks:", e);
        }
    }

    async checkCurrentBatch() {
        try {
            // Use health or special endpoint to check active batch
            const res = await fetch('http://127.0.0.1:8000/health');
            if (res.ok) {
                const health = await res.json();
                if (health.active_batch_id) {
                    // Fetch details of active batch
                    const batchRes = await fetch(`http://127.0.0.1:8000/api/batch/${health.active_batch_id}`);
                    if (batchRes.ok) {
                        const batch = await batchRes.json();
                        this.updateUIActive(batch);
                        return;
                    }
                }
            }
            this.updateUIStopped();
        } catch (e) {
            console.error("[BatchControls] Failed to check current batch:", e);
            this.updateUIStopped();
        }
    }

    async startBatch(batchId, operatorId, benchmark) {
        try {
            const res = await fetch('http://127.0.0.1:8000/api/batch/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    batch_id: batchId,
                    operator_id: operatorId,
                    benchmark_name: benchmark
                })
            });

            if (res.ok) {
                const data = await res.json();
                console.log("[BatchControls] Batch started:", data);
                await this.checkCurrentBatch();
                
                // Clear dashboard stats
                if (window.appInstance) {
                    window.appInstance.resetDashboardStats();
                }
            } else {
                const err = await res.json();
                alert(`Error starting batch: ${err.detail || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("[BatchControls] Start batch network error:", e);
            alert("Failed to connect to backend server.");
        }
    }

    async stopBatch() {
        try {
            const res = await fetch('http://127.0.0.1:8000/api/batch/stop', {
                method: 'POST'
            });

            if (res.ok) {
                const data = await res.json();
                console.log("[BatchControls] Batch stopped:", data);
                this.updateUIStopped();
                
                // Refresh history page
                if (window.HistoryLogs) {
                    window.HistoryLogs.loadHistory();
                }
            } else {
                alert("Error stopping batch.");
            }
        } catch (e) {
            console.error("[BatchControls] Stop batch error:", e);
        }
    }

    updateUIActive(batch) {
        // Form inputs readonly
        this.batchIdInput.value = batch.batch_id || '';
        this.batchIdInput.disabled = true;
        this.operatorIdInput.value = batch.operator_id || 'operator';
        this.operatorIdInput.disabled = true;
        this.benchmarkSelect.disabled = true;
        
        this.startBtn.disabled = true;
        this.stopBtn.disabled = false;
        
        // Update Info
        this.infoBatchId.textContent = batch.batch_id;
        this.infoOperator.textContent = batch.operator_id || 'operator';
        this.infoBenchmark.textContent = batch.active_benchmark || 'default';
        this.infoStartTime.textContent = batch.start_time;
        this.infoStatus.textContent = "RUNNING";
        this.infoStatus.style.color = "var(--color-grade-a)";
        
        this.dashActiveBatchId.textContent = batch.batch_id;
        this.dashActiveBatchId.style.color = "var(--color-grade-a)";
    }

    updateUIStopped() {
        this.batchIdInput.disabled = false;
        this.operatorIdInput.disabled = false;
        this.benchmarkSelect.disabled = false;
        
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        
        this.infoStatus.textContent = "STOPPED";
        this.infoStatus.style.color = "var(--color-reject)";
        
        this.dashActiveBatchId.textContent = window.t ? window.t('no_active_batch') : "None";
        this.dashActiveBatchId.style.color = "var(--text-secondary)";
    }
}

function handleBatchSubmit(event) {
    event.preventDefault();
    if (!window.BatchControls) return;
    
    const batchId = document.getElementById('input-batch-id').value;
    const operatorId = document.getElementById('input-operator-id').value;
    const benchmark = document.getElementById('select-batch-benchmark').value;
    
    window.BatchControls.startBatch(batchId, operatorId, benchmark);
}

function stopActiveBatch() {
    if (window.BatchControls) {
        window.BatchControls.stopBatch();
    }
}

// Instantiate globally
window.BatchControlsManager = BatchControlsManager;
