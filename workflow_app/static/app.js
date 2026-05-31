document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const imagesPathInput = document.getElementById("images-path");
    const labelsPathInput = document.getElementById("labels-path");
    const btnScan = document.getElementById("btn-scan");
    const modeOptions = document.querySelectorAll(".mode-option");
    const radioModes = document.getElementsByName("exec-mode");
    const btnRun = document.getElementById("btn-run");
    const statusBadge = document.getElementById("status-badge");
    const btnToggleConfig = document.getElementById("btn-toggle-config");
    const btnCloseConfig = document.getElementById("btn-close-config");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    const toggleText = document.getElementById("toggle-text");
    const sidebar = document.querySelector(".sidebar");
    
    const singleImageControl = document.getElementById("single-image-control");
    const singleImageSelect = document.getElementById("single-image-select");
    const imagesDatalist = document.getElementById("images-list");
    
    const randomNControl = document.getElementById("random-n-control");
    const randomNCount = document.getElementById("random-n-count");
    
    // Stats elements
    const statTotal = document.getElementById("stat-total");
    const statHits = document.getElementById("stat-hits");
    const statRate = document.getElementById("stat-rate");
    const statRuntime = document.getElementById("stat-runtime");
    
    // Display elements
    const displayImageName = document.getElementById("display-image-name");
    const displayImageRuntime = document.getElementById("display-image-runtime");
    const displayHitBadge = document.getElementById("display-hit-badge");
    const originalImageWrapper = document.getElementById("original-image-wrapper");
    const annotatedImageWrapper = document.getElementById("annotated-image-wrapper");
    
    // Details panel
    const gtClassesContainer = document.getElementById("gt-classes-container");
    const hitClassesContainer = document.getElementById("hit-classes-container");
    const missedClassesContainer = document.getElementById("missed-classes-container");
    const predictionsTableBody = document.getElementById("predictions-table-body");
    
    // Gallery and Logs
    const galleryGrid = document.getElementById("gallery-grid");
    const consoleLogs = document.getElementById("console-logs");
    
    // Upload elements
    const uploadZone = document.getElementById("upload-zone");
    const uploadFileInput = document.getElementById("upload-file-input");
    const uploadProgressContainer = document.getElementById("upload-progress-container");
    const uploadProgressFill = document.getElementById("upload-progress-fill");
    const uploadProgressStatus = document.getElementById("upload-progress-status");
    const uploadProgressPercent = document.getElementById("upload-progress-percent");
    const uploadedFilesBadge = document.getElementById("uploaded-files-badge");
    const btnClearUploads = document.getElementById("btn-clear-uploads");
    
    // Application state
    let resultsList = [];
    let currentSelectedImage = null;
    let availableImages = [];
    let userSelectedImage = false;
    let currentRunTimestamp = Date.now();

    // Helper to log to the console log component
    function logToConsole(message, type = "info") {
        const timeStamp = new Date().toLocaleTimeString();
        if (type === "clear") {
            consoleLogs.textContent = message;
            return;
        }
        
        let prefix = "💡 ";
        if (type === "error") prefix = "❌ ERROR: ";
        else if (type === "success") prefix = "✅ SUCCESS: ";
        else if (type === "cmd") prefix = "💻 RUNNING: ";
        
        consoleLogs.textContent += `\n[${timeStamp}] ${prefix}${message}`;
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Scan directories to fetch available image names
    async function scanImages() {
        const path = imagesPathInput.value.trim();
        logToConsole(`Scanning directory: ${path}...`);
        
        try {
            const response = await fetch(`/api/images?images_path=${encodeURIComponent(path)}`);
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Failed to scan directory");
            }
            
            const data = await response.json();
            availableImages = data.images;
            
            // Populate datalist
            imagesDatalist.innerHTML = "";
            availableImages.forEach(imgName => {
                const option = document.createElement("option");
                option.value = imgName;
                imagesDatalist.appendChild(option);
            });
            
            logToConsole(`Successfully scanned ${data.count} images from directory.`, "success");
            
            // Update placeholder in input
            if (availableImages.length > 0) {
                singleImageSelect.placeholder = "Type to search...";
                // Autofill first image if empty
                if (!singleImageSelect.value) {
                    singleImageSelect.value = availableImages[0];
                }
            } else {
                singleImageSelect.placeholder = "No images found";
            }
            
        } catch (error) {
            logToConsole(error.message, "error");
            statusBadge.textContent = "Error";
            statusBadge.style.background = "var(--color-danger-bg)";
            statusBadge.style.color = "var(--color-danger)";
            statusBadge.style.borderColor = "rgba(255, 82, 82, 0.3)";
        }
    }

    // Toggle controls visibility based on selected mode
    function handleModeChange(selectedMode) {
        // Remove active class from all options
        modeOptions.forEach(opt => opt.classList.remove("active"));
        
        // Find corresponding radio and check it
        const radio = document.querySelector(`input[name="exec-mode"][value="${selectedMode}"]`);
        if (radio) {
            radio.checked = true;
            // Add active class to parent div
            radio.closest(".mode-option").classList.add("active");
        }
        
        // Toggle visibility of conditional controls
        if (selectedMode === "single") {
            singleImageControl.classList.remove("hidden");
            randomNControl.classList.add("hidden");
            if (availableImages.length === 0) {
                scanImages();
            }
        } else if (selectedMode === "random_n") {
            singleImageControl.classList.add("hidden");
            randomNControl.classList.remove("hidden");
        } else {
            singleImageControl.classList.add("hidden");
            randomNControl.classList.add("hidden");
        }
        logToConsole(`Switched execution mode to: ${selectedMode}`);
    }

    // Set up mode selectors click handlers
    modeOptions.forEach(option => {
        option.addEventListener("click", (e) => {
            const radio = option.querySelector('input[type="radio"]');
            if (radio) {
                handleModeChange(radio.value);
            }
        });
    });

    btnScan.addEventListener("click", scanImages);
    
    // Toggle Configuration Sidebar Drawer open/close functions
    function openConfig() {
        sidebar.classList.add("open");
        sidebarBackdrop.classList.add("show");
        toggleText.textContent = "Close Config";
    }
    
    function closeConfig() {
        sidebar.classList.remove("open");
        sidebarBackdrop.classList.remove("show");
        toggleText.textContent = "Show Config";
    }

    btnToggleConfig.addEventListener("click", () => {
        if (sidebar.classList.contains("open")) {
            closeConfig();
        } else {
            openConfig();
        }
    });

    btnCloseConfig.addEventListener("click", closeConfig);
    sidebarBackdrop.addEventListener("click", closeConfig);
    
    // Fetch and display previous results on load
    async function loadPreviousResults() {
        try {
            const labelsPath = labelsPathInput.value.trim();
            const response = await fetch(`/api/results?labels_path=${encodeURIComponent(labelsPath)}`);
            if (response.ok) {
                const results = await response.json();
                if (results && results.length > 0) {
                    renderResults(results);
                    logToConsole("Loaded previous evaluation results.");
                }
            }
        } catch (e) {
            console.error("Failed to load previous results", e);
        }
    }
    
    // Check configuration on startup
    async function checkServerConfig() {
        try {
            const response = await fetch("/api/config");
            if (response.ok) {
                const config = await response.json();
                if (config.cloud_mode) {
                    document.body.classList.add("cloud-mode");
                    logToConsole("Cloud mode active. Path inputs hidden, local upload enabled.", "info");
                } else {
                    document.body.classList.remove("cloud-mode");
                    logToConsole("Local mode active. Custom directory scanning enabled.", "info");
                }
            }
        } catch (e) {
            console.error("Failed to check server configuration", e);
        }
    }

    // Setup file upload handlers
    if (uploadZone && uploadFileInput) {
        uploadZone.addEventListener("click", () => {
            uploadFileInput.click();
        });

        uploadFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                uploadFiles(e.target.files);
            }
        });

        // Drag and drop event handlers
        ["dragenter", "dragover"].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadZone.classList.add("drag-active");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadZone.classList.remove("drag-active");
            }, false);
        });

        uploadZone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                uploadFiles(files);
            }
        });
    }

    async function uploadFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        // Show progress bar
        uploadProgressContainer.classList.remove("hidden");
        uploadProgressFill.style.width = "0%";
        uploadProgressPercent.textContent = "0%";
        uploadProgressStatus.textContent = `Uploading ${files.length} file(s)...`;
        logToConsole(`Uploading ${files.length} file(s)...`, "info");

        try {
            // We use XMLHttpRequest to track upload progress in real-time
            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/api/upload", true);

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    uploadProgressFill.style.width = `${percent}%`;
                    uploadProgressPercent.textContent = `${percent}%`;
                }
            };

            xhr.onload = async () => {
                uploadProgressContainer.classList.add("hidden");
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    logToConsole(`Successfully uploaded ${response.count} files!`, "success");
                    
                    // Switch paths to upload dirs
                    imagesPathInput.value = "uploads/images";
                    labelsPathInput.value = "uploads/labels";
                    
                    // Update cache buster timestamp for uploaded images
                    currentRunTimestamp = Date.now();
                    
                    // Update badges
                    uploadedFilesBadge.style.display = "inline-flex";
                    uploadedFilesBadge.textContent = `${response.uploaded.filter(f => !f.endsWith('.txt')).length} custom images`;
                    btnClearUploads.style.display = "inline-flex";
                    
                    // Scan uploaded directory and trigger load
                    await scanImages();
                } else {
                    logToConsole(`Upload failed with status: ${xhr.status}`, "error");
                    alert("Upload failed. Check logs.");
                }
            };

            xhr.onerror = () => {
                uploadProgressContainer.classList.add("hidden");
                logToConsole("Upload encountered a network error.", "error");
                alert("Upload failed due to network error.");
            };

            xhr.send(formData);

        } catch (err) {
            uploadProgressContainer.classList.add("hidden");
            logToConsole(`Upload error: ${err.message}`, "error");
        }
    }

    // Clear uploads button handler
    if (btnClearUploads) {
        btnClearUploads.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to clear all custom uploaded files?")) {
                return;
            }
            
            try {
                const response = await fetch("/api/uploads", { method: "DELETE" });
                if (response.ok) {
                    const data = await response.json();
                    logToConsole(`Cleared all uploaded files (deleted ${data.deleted_count} files).`, "success");
                    
                    // Reset paths to default
                    imagesPathInput.value = "durian/test/images";
                    labelsPathInput.value = "durian/test/labels";
                    
                    // Hide badges
                    uploadedFilesBadge.style.display = "none";
                    btnClearUploads.style.display = "none";
                    
                    // Re-scan
                    await scanImages();
                } else {
                    throw new Error("Failed to clear uploads");
                }
            } catch (e) {
                logToConsole(e.message, "error");
            }
        });
    }

    // Initial scan and load previous results on load
    checkServerConfig().then(() => {
        scanImages().then(() => {
            loadPreviousResults();
        });
    });

    // Reset results dashboard and main views
    function resetUIForRun() {
        statTotal.textContent = "...";
        statHits.textContent = "...";
        statRate.textContent = "...";
        statRuntime.textContent = "...";
        
        displayImageName.textContent = "Evaluating...";
        displayImageRuntime.textContent = "Workflow running in background...";
        displayHitBadge.innerHTML = "";
        
        originalImageWrapper.innerHTML = `
            <div class="placeholder-text skeleton" style="width: 100%; height: 100%;">
                <span class="placeholder-icon">⏳</span>
                <span>Inference executing...</span>
            </div>
        `;
        annotatedImageWrapper.innerHTML = `
            <div class="placeholder-text skeleton" style="width: 100%; height: 100%;">
                <span class="placeholder-icon">⏳</span>
                <span>Inference executing...</span>
            </div>
        `;
        
        gtClassesContainer.innerHTML = '<span class="tag">Loading...</span>';
        hitClassesContainer.innerHTML = '<span class="tag">Loading...</span>';
        missedClassesContainer.innerHTML = '<span class="tag">Loading...</span>';
        
        predictionsTableBody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; color: var(--text-secondary); padding: 1.5rem;">
                    Waiting for predictions...
                </td>
            </tr>
        `;
        
        galleryGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 2rem;" class="skeleton">
                Analyzing dataset, please wait...
            </div>
        `;
    }

    // Display details of a specific image result in comparison panel
    function displayResultDetails(result) {
        currentSelectedImage = result;
        
        // Highlight active gallery item
        const galleryItems = document.querySelectorAll(".gallery-item");
        galleryItems.forEach(item => {
            if (item.dataset.image === result.image) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        displayImageName.textContent = result.image;
        displayImageRuntime.textContent = `API Runtime: ${result.runtime_seconds}s`;
        
        // Set Hit Badge
        if (result.hit) {
            displayHitBadge.innerHTML = '<span class="badge badge-hit">✅ HIT</span>';
        } else {
            displayHitBadge.innerHTML = '<span class="badge badge-miss">❌ MISS</span>';
        }

        // Set Images
        const imgPath = imagesPathInput.value.trim();
        const originalImgUrl = `/api/image?type=original&filename=${encodeURIComponent(result.image)}&path=${encodeURIComponent(imgPath)}&t=${currentRunTimestamp}`;
        
        originalImageWrapper.innerHTML = `
            <img src="${originalImgUrl}" alt="Original image" id="original-img-el" style="max-width: 100%; max-height: 100%; object-fit: contain;">
            <div id="original-bbox-container" style="position: absolute; pointer-events: none; z-index: 10;"></div>
        `;
        
        annotatedImageWrapper.innerHTML = `<img src="/api/image?type=annotated&filename=${encodeURIComponent(result.image)}&t=${currentRunTimestamp}" alt="Annotated workflow output">`;

        const originalImgEl = document.getElementById("original-img-el");
        const originalContainer = document.getElementById("original-bbox-container");

        function adjustBboxOverlay() {
            if (!originalImgEl || !originalContainer) return;
            if (originalImgEl.naturalWidth === 0 || originalImgEl.naturalHeight === 0) return;
            
            // Calculate visible image size (accounting for object-fit contain letterboxing)
            const width = originalImgEl.clientWidth;
            const height = originalImgEl.clientHeight;
            const naturalWidth = originalImgEl.naturalWidth;
            const naturalHeight = originalImgEl.naturalHeight;

            const naturalAspect = naturalWidth / naturalHeight;
            const elementAspect = width / height;

            let renderedWidth, renderedHeight, renderedLeft, renderedTop;

            if (elementAspect > naturalAspect) {
                // Letterboxed on left and right
                renderedHeight = height;
                renderedWidth = height * naturalAspect;
                renderedLeft = (width - renderedWidth) / 2;
                renderedTop = 0;
            } else {
                // Letterboxed on top and bottom
                renderedWidth = width;
                renderedHeight = width / naturalAspect;
                renderedLeft = 0;
                renderedTop = (height - renderedHeight) / 2;
            }

            // Adjust container position and dimensions relative to parent wrapper
            const wrapperLeft = originalImgEl.offsetLeft;
            const wrapperTop = originalImgEl.offsetTop;
            
            originalContainer.style.left = `${wrapperLeft + renderedLeft}px`;
            originalContainer.style.top = `${wrapperTop + renderedTop}px`;
            originalContainer.style.width = `${renderedWidth}px`;
            originalContainer.style.height = `${renderedHeight}px`;

            // Draw bounding boxes inside container
            originalContainer.innerHTML = "";
            if (result.expected_boxes && result.expected_boxes.length > 0) {
                result.expected_boxes.forEach(box => {
                    const left = (box.x_center - box.width / 2) * 100;
                    const top = (box.y_center - box.height / 2) * 100;
                    const w = box.width * 100;
                    const h = box.height * 100;
                    
                    const boxEl = document.createElement("div");
                    boxEl.className = "bbox-overlay";
                    boxEl.style.left = `${left}%`;
                    boxEl.style.top = `${top}%`;
                    boxEl.style.width = `${w}%`;
                    boxEl.style.height = `${h}%`;
                    
                    const labelEl = document.createElement("div");
                    labelEl.className = "bbox-overlay-label";
                    labelEl.textContent = box.class;
                    
                    boxEl.appendChild(labelEl);
                    originalContainer.appendChild(boxEl);
                });
            }
        }

        // Set up ResizeObserver to adjust bounding boxes on dimensions change
        if (window.originalImgResizeObserver) {
            window.originalImgResizeObserver.disconnect();
        }
        
        window.originalImgResizeObserver = new ResizeObserver(() => {
            adjustBboxOverlay();
        });
        window.originalImgResizeObserver.observe(originalImgEl);

        originalImgEl.onload = adjustBboxOverlay;
        if (originalImgEl.complete) {
            adjustBboxOverlay();
        }

        // Set Classes
        gtClassesContainer.innerHTML = "";
        if (result.expected_classes.length > 0) {
            result.expected_classes.forEach(cls => {
                const tag = document.createElement("span");
                tag.className = "tag tag-expected";
                tag.textContent = cls;
                gtClassesContainer.appendChild(tag);
            });
        } else {
            gtClassesContainer.innerHTML = '<span class="tag">None</span>';
        }

        hitClassesContainer.innerHTML = "";
        if (result.hit_classes.length > 0) {
            result.hit_classes.forEach(cls => {
                const tag = document.createElement("span");
                tag.className = "tag tag-hit";
                tag.textContent = cls;
                hitClassesContainer.appendChild(tag);
            });
        } else {
            hitClassesContainer.innerHTML = '<span class="tag">None</span>';
        }

        missedClassesContainer.innerHTML = "";
        if (result.missed_classes.length > 0) {
            result.missed_classes.forEach(cls => {
                const tag = document.createElement("span");
                tag.className = "tag tag-missed";
                tag.textContent = cls;
                missedClassesContainer.appendChild(tag);
            });
        } else {
            missedClassesContainer.innerHTML = '<span class="tag">None</span>';
        }

        // Set Predictions Table
        predictionsTableBody.innerHTML = "";
        if (result.predictions && result.predictions.length > 0) {
            result.predictions.forEach(pred => {
                const row = document.createElement("tr");
                
                const clsCell = document.createElement("td");
                clsCell.style.fontWeight = "600";
                clsCell.textContent = pred.class;
                
                const confCell = document.createElement("td");
                const confPercent = Math.round(pred.confidence * 100);
                confCell.innerHTML = `
                    <div>${confPercent}%</div>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confPercent}%"></div>
                    </div>
                `;
                
                const bboxCell = document.createElement("td");
                bboxCell.style.color = "var(--text-secondary)";
                bboxCell.style.fontSize = "0.75rem";
                if (pred.x !== null && pred.y !== null) {
                    bboxCell.textContent = `[x:${Math.round(pred.x)}, y:${Math.round(pred.y)}, w:${Math.round(pred.width)}, h:${Math.round(pred.height)}]`;
                } else {
                    bboxCell.textContent = "N/A";
                }
                
                row.appendChild(clsCell);
                row.appendChild(confCell);
                row.appendChild(bboxCell);
                predictionsTableBody.appendChild(row);
            });
        } else {
            predictionsTableBody.innerHTML = `
                <tr>
                    <td colspan="3" style="text-align: center; color: var(--text-secondary); padding: 1rem;">
                        No detections from model
                    </td>
                </tr>
            `;
        }
    }

    // Build Results Dashboard and Gallery Grid
    function renderResults(results) {
        resultsList = results;
        
        if (results.length === 0) {
            logToConsole("Workflow execution returned empty results.", "warning");
            
            // Empty states
            statTotal.textContent = "0";
            statHits.textContent = "0";
            statRate.textContent = "0%";
            statRuntime.textContent = "0s";
            
            displayImageName.textContent = "No results";
            displayImageRuntime.textContent = "Check logs for errors";
            displayHitBadge.innerHTML = "";
            originalImageWrapper.innerHTML = `
                <div class="placeholder-text">
                    <span class="placeholder-icon">⚠️</span>
                    <span>No evaluation data found</span>
                </div>
            `;
            annotatedImageWrapper.innerHTML = `
                <div class="placeholder-text">
                    <span class="placeholder-icon">⚠️</span>
                    <span>No evaluation data found</span>
                </div>
            `;
            galleryGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 2rem;">
                    No results to display.
                </div>
            `;
            return;
        }

        // 1. Calculate Stats
        const total = results.length;
        const hits = results.filter(r => r.hit).length;
        const hitRate = ((hits / total) * 100).toFixed(1);
        const avgRuntime = (results.reduce((acc, curr) => acc + curr.runtime_seconds, 0) / total).toFixed(3);

        statTotal.textContent = total;
        statHits.textContent = hits;
        statRate.textContent = `${hitRate}%`;
        statRuntime.textContent = `${avgRuntime}s`;

        // 2. Populate Gallery
        galleryGrid.innerHTML = "";
        const imgPath = imagesPathInput.value.trim();
        
        results.forEach(result => {
            const item = document.createElement("div");
            item.className = "gallery-item";
            item.dataset.image = result.image;
            
            const badgeClass = result.hit ? "gallery-badge-hit" : "gallery-badge-miss";
            const badgeText = result.hit ? "HIT" : "MISS";
            
            item.innerHTML = `
                <div class="gallery-thumb">
                    <img src="/api/image?type=original&filename=${encodeURIComponent(result.image)}&path=${encodeURIComponent(imgPath)}&t=${currentRunTimestamp}" alt="${result.image}" loading="lazy">
                </div>
                <div class="gallery-info">
                    <div class="gallery-name" title="${result.image}">${result.image}</div>
                    <div class="gallery-meta">
                        <span class="gallery-badge ${badgeClass}">${badgeText}</span>
                        <span style="font-size: 0.65rem; color: var(--text-secondary);">${result.runtime_seconds}s</span>
                    </div>
                </div>
            `;
            
            item.addEventListener("click", () => {
                displayResultDetails(result);
            });
            
            galleryGrid.appendChild(item);
        });

        // 3. Display first result in comparison by default
        displayResultDetails(results[0]);
    }

    // Run workflow action
    btnRun.addEventListener("click", async () => {
        // Determine selected mode
        let selectedMode = "all";
        radioModes.forEach(r => {
            if (r.checked) selectedMode = r.value;
        });

        const imagesPath = imagesPathInput.value.trim();
        const labelsPath = labelsPathInput.value.trim();
        
        // Prepare request body
        const requestBody = {
            mode: selectedMode,
            images_path: imagesPath,
            labels_path: labelsPath
        };

        if (selectedMode === "single") {
            const singleImg = singleImageSelect.value.trim();
            if (!singleImg) {
                logToConsole("Please select or enter an image filename for Single Image mode.", "error");
                alert("Please specify a target image.");
                return;
            }
            requestBody.image = singleImg;
        } else if (selectedMode === "random_n") {
            const count = parseInt(randomNCount.value);
            if (isNaN(count) || count < 1) {
                logToConsole("Please specify a valid count N > 0.", "error");
                alert("Please enter a valid count of images.");
                return;
            }
            requestBody.n = count;
        }

        // Set visual loading state
        btnRun.disabled = true;
        btnRun.innerHTML = '<div class="spinner"></div> Running Workflow...';
        statusBadge.textContent = "Running";
        statusBadge.style.background = "var(--color-warning-bg)";
        statusBadge.style.color = "var(--color-warning)";
        statusBadge.style.borderColor = "rgba(255, 193, 7, 0.3)";
        
        // Update cache buster timestamp for the new run
        currentRunTimestamp = Date.now();
        
        logToConsole("Triggering durian defect classifier workflow runner in background...", "clear");
        logToConsole(`Mode: ${selectedMode} | Images Path: ${imagesPath} | Labels Path: ${labelsPath}`, "info");
        
        resetUIForRun();
        
        userSelectedImage = false; // reset selection lock on run start

        try {
            const response = await fetch("/api/run", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            
            if (!response.ok) {
                const errMsg = data.detail || "Workflow failed to initiate";
                throw new Error(errMsg);
            }

            logToConsole("Workflow execution started in background...", "info");
            
            // Set up polling loop to display real-time logs, stats, and gallery items
            let pollInterval = setInterval(async () => {
                try {
                    // 1. Fetch current status
                    const statusRes = await fetch("/api/status");
                    const statusData = await statusRes.json();
                    
                    // 2. Fetch logs in real-time
                    const logsRes = await fetch("/api/logs");
                    const logsData = await logsRes.json();
                    if (logsData.logs) {
                        consoleLogs.textContent = logsData.logs;
                        consoleLogs.scrollTop = consoleLogs.scrollHeight;
                    }
                    
                    // 3. Fetch intermediate results in real-time
                    const resultsRes = await fetch(`/api/results?labels_path=${encodeURIComponent(labelsPath)}`);
                    const resultsData = await resultsRes.json();
                    
                    if (resultsData && resultsData.length > 0) {
                        resultsList = resultsData;
                        
                        // Render Dashboard Stats
                        const total = resultsData.length;
                        const hits = resultsData.filter(r => r.hit).length;
                        const hitRate = ((hits / total) * 100).toFixed(1);
                        const avgRuntime = (resultsData.reduce((acc, curr) => acc + curr.runtime_seconds, 0) / total).toFixed(3);

                        statTotal.textContent = total;
                        statHits.textContent = hits;
                        statRate.textContent = `${hitRate}%`;
                        statRuntime.textContent = `${avgRuntime}s`;
                        
                        // Render Gallery
                        galleryGrid.innerHTML = "";
                        const imgPath = imagesPathInput.value.trim();
                        resultsData.forEach(result => {
                            const item = document.createElement("div");
                            item.className = "gallery-item";
                            item.dataset.image = result.image;
                            if (currentSelectedImage && currentSelectedImage.image === result.image) {
                                item.classList.add("active");
                            }
                            
                            const badgeClass = result.hit ? "gallery-badge-hit" : "gallery-badge-miss";
                            const badgeText = result.hit ? "HIT" : "MISS";
                            
                            item.innerHTML = `
                                <div class="gallery-thumb">
                                    <img src="/api/image?type=original&filename=${encodeURIComponent(result.image)}&path=${encodeURIComponent(imgPath)}&t=${currentRunTimestamp}" alt="${result.image}" loading="lazy">
                                </div>
                                <div class="gallery-info">
                                    <div class="gallery-name" title="${result.image}">${result.image}</div>
                                    <div class="gallery-meta">
                                        <span class="gallery-badge ${badgeClass}">${badgeText}</span>
                                        <span style="font-size: 0.65rem; color: var(--text-secondary);">${result.runtime_seconds}s</span>
                                    </div>
                                </div>
                            `;
                            
                            item.addEventListener("click", () => {
                                userSelectedImage = true;
                                displayResultDetails(result);
                            });
                            
                            galleryGrid.appendChild(item);
                        });

                        // Auto-display the latest result if the user hasn't selected another image
                        if (!userSelectedImage && resultsData.length > 0) {
                            const latestResult = resultsData[resultsData.length - 1];
                            displayResultDetails(latestResult);
                        }
                    }

                    // 4. Handle process termination
                    if (statusData.status === "completed") {
                        clearInterval(pollInterval);
                        logToConsole("Workflow execution completed successfully.", "success");
                        
                        statusBadge.textContent = "Done";
                        statusBadge.style.background = "var(--color-success-bg)";
                        statusBadge.style.color = "var(--color-success)";
                        statusBadge.style.borderColor = "rgba(0, 230, 118, 0.3)";
                        
                        btnRun.disabled = false;
                        btnRun.innerHTML = '<span>🚀</span> Run Workflow';
                    } else if (statusData.status === "failed") {
                        clearInterval(pollInterval);
                        logToConsole(`Workflow execution failed (Exit code: ${statusData.exit_code})`, "error");
                        if (statusData.error) {
                            logToConsole(`Error detail:\n${statusData.error}`, "error");
                        }
                        
                        statusBadge.textContent = "Failed";
                        statusBadge.style.background = "var(--color-danger-bg)";
                        statusBadge.style.color = "var(--color-danger)";
                        statusBadge.style.borderColor = "rgba(255, 82, 82, 0.3)";
                        
                        btnRun.disabled = false;
                        btnRun.innerHTML = '<span>🚀</span> Run Workflow';
                    }
                    
                } catch (err) {
                    logToConsole(`Polling error: ${err.message}`, "error");
                }
            }, 1000);
            
        } catch (error) {
            logToConsole(error.message, "error");
            statusBadge.textContent = "Failed";
            statusBadge.style.background = "var(--color-danger-bg)";
            statusBadge.style.color = "var(--color-danger)";
            statusBadge.style.borderColor = "rgba(255, 82, 82, 0.3)";
            
            btnRun.disabled = false;
            btnRun.innerHTML = '<span>🚀</span> Run Workflow';
        }
    });
});

