class GradeDisplayManager {
    constructor() {
        this.badge = document.getElementById('huge-grade-badge');
        this.reasonsContainer = document.getElementById('grade-reasons-container');
        this.alertBanner = document.getElementById('critical-alert-banner');
        
        // Defect progress bars and labels
        this.bars = {
            crack: {
                bar: document.getElementById('conf-bar-crack'),
                lbl: document.getElementById('conf-val-crack')
            },
            dark_spot: {
                bar: document.getElementById('conf-bar-dark_spot'),
                lbl: document.getElementById('conf-val-dark_spot')
            },
            fungus: {
                bar: document.getElementById('conf-bar-fungus'),
                lbl: document.getElementById('conf-val-fungus')
            },
            thorn_split: {
                bar: document.getElementById('conf-bar-thorn_split'),
                lbl: document.getElementById('conf-val-thorn_split')
            }
        };
    }

    updateGrade(grade, reasons = [], detections = []) {
        if (!grade) return;
        
        // Update badge text
        this.badge.textContent = grade;
        
        // Clean old classes
        this.badge.className = 'grade-badge-huge';
        
        // Add new class based on grade
        const lowerGrade = grade.toLowerCase();
        if (lowerGrade === 'a') {
            this.badge.classList.add('grade-a');
        } else if (lowerGrade === 'b') {
            this.badge.classList.add('grade-b');
        } else if (lowerGrade === 'c') {
            this.badge.classList.add('grade-c');
        } else if (lowerGrade === 'reject') {
            this.badge.classList.add('grade-reject');
        }

        // Handle reasons
        if (reasons && reasons.length > 0) {
            this.reasonsContainer.textContent = reasons.join(', ');
            this.reasonsContainer.style.display = 'block';
        } else {
            this.reasonsContainer.style.display = 'none';
        }

        // Critical defect alarm (Fungus or Reject)
        const hasFungus = detections.some(d => d.class === 'fungus');
        if (lowerGrade === 'reject' || hasFungus) {
            this.alertBanner.classList.add('active');
            // Remove alert banner after 4 seconds
            if (this.alertTimeout) clearTimeout(this.alertTimeout);
            this.alertTimeout = setTimeout(() => {
                this.alertBanner.classList.remove('active');
            }, 4000);
        } else {
            this.alertBanner.classList.remove('active');
        }

        // Update confidence progress bars
        this.updateDefectConfidence(detections);
    }

    updateDefectConfidence(detections) {
        // Reset all confidences to 0
        const maxConfidences = {
            crack: 0,
            dark_spot: 0,
            fungus: 0,
            thorn_split: 0
        };

        // Find max confidence per class
        detections.forEach(det => {
            const cls = det.class;
            if (cls in maxConfidences) {
                maxConfidences[cls] = Math.max(maxConfidences[cls], det.confidence || 0);
            }
        });

        // Update DOM elements
        for (const [cls, value] of Object.entries(maxConfidences)) {
            const pct = Math.round(value * 100);
            if (this.bars[cls]) {
                this.bars[cls].bar.style.width = `${pct}%`;
                this.bars[cls].lbl.textContent = `${pct}%`;
            }
        }
    }
}

// Instantiate globally
window.GradeDisplay = GradeDisplayManager;
