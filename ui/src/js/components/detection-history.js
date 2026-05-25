class DetectionHistoryManager {
    constructor() {
        this.tableBody = document.getElementById('history-table-body');
        this.searchInput = document.getElementById('history-search-input');
        
        this.prevBtn = document.getElementById('btn-prev-page');
        this.nextBtn = document.getElementById('btn-next-page');
        this.pageNumIndicator = document.getElementById('page-num-indicator');
        
        this.limit = 10;
        this.skip = 0;
        this.currentPage = 1;
        this.searchQuery = '';
        
        this.loadHistory();
    }

    async loadHistory() {
        try {
            let url = `http://127.0.0.1:8000/api/detections?skip=${this.skip}&limit=${this.limit}`;
            if (this.searchQuery) {
                url += `&batch_id=${encodeURIComponent(this.searchQuery)}`;
            }
            
            const res = await fetch(url);
            if (res.ok) {
                let detections = await res.json();
                if (detections && typeof detections === 'object' && !Array.isArray(detections)) {
                    detections = detections.detections || [];
                }
                this.renderDetections(detections);
                
                // Toggle pagination buttons
                this.prevBtn.disabled = this.currentPage === 1;
                this.nextBtn.disabled = detections.length < this.limit;
                this.pageNumIndicator.textContent = `Page ${this.currentPage}`;
            }
        } catch (e) {
            console.error("[History] Failed to load detection logs:", e);
            this.tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--color-reject);">Failed to load history data.</td></tr>';
        }
    }

    renderDetections(detections) {
        if (!detections || detections.length === 0) {
            this.tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No records found.</td></tr>';
            return;
        }
        
        this.tableBody.innerHTML = '';
        
        detections.forEach((det, idx) => {
            const tr = document.createElement('tr');
            
            // STT (Numbering)
            const tdIdx = document.createElement('td');
            tdIdx.textContent = this.skip + idx + 1;
            tr.appendChild(tdIdx);
            
            // Timestamp
            const tdTime = document.createElement('td');
            tdTime.textContent = det.timestamp || '-';
            tr.appendChild(tdTime);
            
            // Batch ID
            const tdBatch = document.createElement('td');
            tdBatch.textContent = det.batch_id || '-';
            tr.appendChild(tdBatch);
            
            // Grade
            const tdGrade = document.createElement('td');
            const gradeBadge = document.createElement('span');
            gradeBadge.className = `event-grade ${det.final_grade.toLowerCase()}`;
            gradeBadge.textContent = det.final_grade;
            tdGrade.appendChild(gradeBadge);
            tr.appendChild(tdGrade);
            
            // Defects List
            const tdDefects = document.createElement('td');
            let defectTypes = [];
            try {
                if (det.defect_types) {
                    defectTypes = typeof det.defect_types === 'string' ? JSON.parse(det.defect_types) : det.defect_types;
                }
            } catch (e) {
                defectTypes = [det.defect_types];
            }
            tdDefects.textContent = defectTypes.length > 0 ? defectTypes.join(', ') : 'None (A)';
            tr.appendChild(tdDefects);
            
            // Confidence
            const tdConf = document.createElement('td');
            const confPct = Math.round((det.confidence || 0) * 100);
            tdConf.textContent = `${confPct}%`;
            tr.appendChild(tdConf);
            
            this.tableBody.appendChild(tr);
        });
    }

    search() {
        this.searchQuery = this.searchInput.value.trim();
        this.skip = 0;
        this.currentPage = 1;
        this.loadHistory();
    }

    changePage(direction) {
        if (direction === -1 && this.currentPage > 1) {
            this.currentPage--;
            this.skip = (this.currentPage - 1) * this.limit;
        } else if (direction === 1) {
            this.currentPage++;
            this.skip = (this.currentPage - 1) * this.limit;
        }
        this.loadHistory();
    }

    downloadReport(format) {
        // Find batch_id: use search query or ask user. Default to active batch
        let batchId = this.searchQuery;
        
        if (!batchId) {
            // Check if there is an active batch
            if (window.BatchControls && window.BatchControls.infoBatchId.textContent !== '-') {
                batchId = window.BatchControls.infoBatchId.textContent;
            }
        }
        
        if (!batchId) {
            alert("Please type a Batch ID in the search box to download its report.");
            return;
        }
        
        const url = `http://127.0.0.1:8000/api/reports/${batchId}/${format}`;
        console.log(`[History] Downloading ${format} report from: ${url}`);
        window.open(url, '_blank');
    }
}

function searchHistory() {
    if (window.HistoryLogs) {
        window.HistoryLogs.search();
    }
}

function changePage(direction) {
    if (window.HistoryLogs) {
        window.HistoryLogs.changePage(direction);
    }
}

function downloadReport(format) {
    if (window.HistoryLogs) {
        window.HistoryLogs.downloadReport(format);
    }
}

// Instantiate globally
window.DetectionHistoryManager = DetectionHistoryManager;
