class BenchmarkManager {
    constructor() {
        this.listGroup = document.getElementById('benchmarks-list-group');
        this.editorPanel = document.getElementById('benchmark-editor-panel');
        this.editForm = document.getElementById('benchmark-edit-form');
        this.editorTitle = document.getElementById('editor-title');
        
        this.filenameInput = document.getElementById('edit-benchmark-filename');
        this.nameInput = document.getElementById('edit-benchmark-name');
        this.deleteBtn = document.getElementById('btn-delete-benchmark');
        
        // Defect types map to input suffix
        this.defects = ['crack', 'dark_spot', 'fungus', 'thorn_split'];
        
        this.loadBenchmarksList();
    }

    async loadBenchmarksList() {
        try {
            const res = await fetch('http://127.0.0.1:8000/api/config/benchmarks');
            if (res.ok) {
                const benchmarks = await res.json();
                this.listGroup.innerHTML = '';
                
                if (benchmarks.length === 0) {
                    this.listGroup.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 12px;">No benchmarks configured.</div>';
                    return;
                }
                
                benchmarks.forEach(bench => {
                    const name = bench.replace('.json', '');
                    const item = document.createElement('div');
                    item.className = 'nav-link';
                    item.style.justifyContent = 'space-between';
                    item.style.marginBottom = '6px';
                    
                    const nameSpan = document.createElement('span');
                    nameSpan.textContent = name;
                    item.appendChild(nameSpan);
                    
                    const actionsDiv = document.createElement('div');
                    actionsDiv.style.display = 'flex';
                    actionsDiv.style.gap = '8px';
                    
                    const editBtn = document.createElement('button');
                    editBtn.textContent = '✏️';
                    editBtn.style.background = 'none';
                    editBtn.style.border = 'none';
                    editBtn.style.cursor = 'pointer';
                    editBtn.onclick = (e) => {
                        e.stopPropagation();
                        this.loadBenchmark(name);
                    };
                    actionsDiv.appendChild(editBtn);
                    
                    const useBtn = document.createElement('button');
                    useBtn.textContent = '✅';
                    useBtn.style.background = 'none';
                    useBtn.style.border = 'none';
                    useBtn.style.cursor = 'pointer';
                    useBtn.title = 'Set as Active Benchmark';
                    useBtn.onclick = (e) => {
                        e.stopPropagation();
                        this.setActiveBenchmark(name);
                    };
                    actionsDiv.appendChild(useBtn);
                    
                    item.appendChild(actionsDiv);
                    this.listGroup.appendChild(item);
                });
            }
        } catch (e) {
            console.error("[Benchmark] Failed to load benchmarks list:", e);
        }
    }

    async loadBenchmark(name) {
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/config/benchmarks/${name}`);
            if (res.ok) {
                const bench = await res.json();
                this.showEditor(name, bench);
            }
        } catch (e) {
            console.error("[Benchmark] Failed to fetch benchmark details:", e);
        }
    }

    async setActiveBenchmark(name) {
        try {
            const rulesRes = await fetch('http://127.0.0.1:8000/api/config/rules');
            if (rulesRes.ok) {
                const rules = await rulesRes.json();
                rules.active_benchmark = name;
                
                const updateRes = await fetch('http://127.0.0.1:8000/api/config/rules', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(rules)
                });
                
                if (updateRes.ok) {
                    alert(`Active benchmark successfully updated to: ${name}`);
                    // Reload batch controls dropdown
                    if (window.BatchControls) {
                        window.BatchControls.loadBenchmarks();
                        window.BatchControls.checkCurrentBatch();
                    }
                }
            }
        } catch (e) {
            console.error("[Benchmark] Failed to set active benchmark:", e);
        }
    }

    showEditor(filename = '', data = null) {
        this.editorPanel.style.display = 'block';
        this.filenameInput.value = filename;
        
        if (data) {
            this.editorTitle.textContent = `Edit Benchmark: ${data.name}`;
            this.nameInput.value = data.name;
            this.deleteBtn.style.display = 'block';
            
            // Populate defect rules
            const rules = data.defect_rules || {};
            this.defects.forEach(defect => {
                const dRule = rules[defect] || { max_count_A: 0, max_count_B: 0, max_count_C: 0, force_reject: false, max_area_ratio: 0.0 };
                
                document.getElementById(`rule-max-a-${defect}`).value = dRule.max_count_A;
                document.getElementById(`rule-max-b-${defect}`).value = dRule.max_count_B;
                document.getElementById(`rule-max-c-${defect}`).value = dRule.max_count_C;
                document.getElementById(`rule-force-${defect}`).checked = dRule.force_reject;
                
                const areaSlider = document.getElementById(`rule-area-${defect}`);
                const areaPct = Math.round(dRule.max_area_ratio * 100);
                areaSlider.value = areaPct;
                document.getElementById(`area-val-${defect}`).textContent = `${areaPct}%`;
            });
        } else {
            this.editorTitle.textContent = 'Create New Benchmark';
            this.nameInput.value = '';
            this.deleteBtn.style.display = 'none';
            
            // Populate default values
            this.defects.forEach(defect => {
                document.getElementById(`rule-max-a-${defect}`).value = 0;
                document.getElementById(`rule-max-b-${defect}`).value = defect === 'fungus' ? 0 : 1;
                document.getElementById(`rule-max-c-${defect}`).value = defect === 'fungus' ? 0 : 2;
                document.getElementById(`rule-force-${defect}`).checked = defect === 'fungus';
                
                const areaSlider = document.getElementById(`rule-area-${defect}`);
                const areaPct = defect === 'fungus' ? 0 : 5;
                areaSlider.value = areaPct;
                document.getElementById(`area-val-${defect}`).textContent = `${areaPct}%`;
            });
        }
        
        // Scroll to editor
        this.editorPanel.scrollIntoView({ behavior: 'smooth' });
    }

    async save() {
        const name = this.nameInput.value.trim();
        if (!name) return;
        
        // Build JSON representation matching standard_qc_v1 structure
        const benchmarkData = {
            name: name,
            created_by: "operator",
            created_at: new Date().toISOString(),
            defect_rules: {
                reject: { max_count_A: 0, max_count_B: 0, max_count_C: 0, force_reject: true, max_area_ratio: 0.0 }
            },
            global_rules: {
                max_total_defects_A: 0,
                max_total_defects_B: 1,
                max_total_defects_C: 3,
                max_total_area_ratio_A: 0.0,
                max_total_area_ratio_B: 0.03,
                max_total_area_ratio_C: 0.08
            }
        };

        this.defects.forEach(defect => {
            const maxA = parseInt(document.getElementById(`rule-max-a-${defect}`).value) || 0;
            const maxB = parseInt(document.getElementById(`rule-max-b-${defect}`).value) || 0;
            const maxC = parseInt(document.getElementById(`rule-max-c-${defect}`).value) || 0;
            const force = document.getElementById(`rule-force-${defect}`).checked;
            const area = (parseInt(document.getElementById(`rule-area-${defect}`).value) || 0) / 100.0;
            
            benchmarkData.defect_rules[defect] = {
                max_count_A: maxA,
                max_count_B: maxB,
                max_count_C: maxC,
                force_reject: force,
                max_area_ratio: area
            };
        });

        // Generate filename from name: e.g. "Standard QC v1" -> "standard_qc_v1"
        const filename = name.toLowerCase().replace(/[^a-z0-9_]/g, '_') + '.json';
        
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/config/benchmarks/${filename.replace('.json', '')}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(benchmarkData)
            });

            if (res.ok) {
                alert("Benchmark saved successfully.");
                this.editorPanel.style.display = 'none';
                await this.loadBenchmarksList();
                
                // Refresh batch controls dropdown
                if (window.BatchControls) {
                    window.BatchControls.loadBenchmarks();
                }
            } else {
                alert("Failed to save benchmark profile.");
            }
        } catch (e) {
            console.error("[Benchmark] Save error:", e);
        }
    }

    async delete() {
        const name = this.filenameInput.value;
        if (!name) return;
        
        if (!confirm(`Are you sure you want to delete benchmark profile: ${name}?`)) return;
        
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/config/benchmarks/${name}`, {
                method: 'DELETE'
            });

            if (res.ok) {
                alert("Benchmark deleted successfully.");
                this.editorPanel.style.display = 'none';
                await this.loadBenchmarksList();
                
                // Refresh batch controls dropdown
                if (window.BatchControls) {
                    window.BatchControls.loadBenchmarks();
                }
            } else {
                alert("Failed to delete benchmark profile.");
            }
        } catch (e) {
            console.error("[Benchmark] Delete error:", e);
        }
    }
}

function showNewBenchmarkForm() {
    if (window.Benchmarks) {
        window.Benchmarks.showEditor();
    }
}

function saveBenchmark(event) {
    event.preventDefault();
    if (window.Benchmarks) {
        window.Benchmarks.save();
    }
}

function deleteBenchmark() {
    if (window.Benchmarks) {
        window.Benchmarks.delete();
    }
}

// Instantiate globally
window.BenchmarkManager = BenchmarkManager;
