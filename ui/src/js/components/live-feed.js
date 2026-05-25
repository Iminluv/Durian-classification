class LiveFeedReceiver {
    constructor(canvasId, placeholderId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.placeholder = document.getElementById(placeholderId);
        this.ws = null;
        this.image = new Image();
        
        // Setup image onload handler to draw to canvas
        this.image.onload = () => {
            this.canvas.width = this.image.naturalWidth;
            this.canvas.height = this.image.naturalHeight;
            this.ctx.drawImage(this.image, 0, 0);
            
            if (this.placeholder.style.display !== 'none') {
                this.placeholder.style.display = 'none';
            }
        };
    }

    connect(host = "127.0.0.1", port = "8000") {
        const wsUrl = `ws://${host}:${port}/ws/live`;
        console.log(`[LiveFeed] Connecting to WS: ${wsUrl}`);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onmessage = (event) => {
            // Draw received base64 JPEG to canvas
            this.image.src = 'data:image/jpeg;base64,' + event.data;
        };

        this.ws.onclose = () => {
            console.warn("[LiveFeed] Connection lost.");
            this.showPlaceholder();
            // Reconnect after 3 seconds
            setTimeout(() => this.connect(host, port), 3000);
        };

        this.ws.onerror = (err) => {
            console.error("[LiveFeed] WS error:", err);
            this.ws.close();
        };
    }

    showPlaceholder() {
        this.placeholder.style.display = 'flex';
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
}

// Instantiate globally
window.LiveFeed = LiveFeedReceiver;
