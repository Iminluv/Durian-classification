#!/bin/bash

# Ensure we are in the repository directory
cd "$(dirname "$0")"

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Error: Port 8000 is already in use. Please stop any running instances first."
    exit 1
fi

echo "🚀 Starting Durian Classification Workflow App..."
# Start FastAPI backend in background using the virtualenv python
.venv/bin/python workflow_app/app.py > backend.log 2>&1 &
BACKEND_PID=$!

echo "🌐 Creating secure tunnel online..."
# Start localtunnel in background
npx localtunnel --port 8000 > tunnel.log 2>&1 &
TUNNEL_PID=$!

# Trap Ctrl+C (SIGINT) to clean up processes on exit
cleanup() {
    echo -e "\n🛑 Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $TUNNEL_PID 2>/dev/null
    rm -f backend.log tunnel.log
    echo "Domain shut down successfully."
    exit 0
}
trap cleanup SIGINT

# Wait a few seconds for the tunnel URL to generate
sleep 4

# Display the URL
if grep -q "your url is" tunnel.log; then
    URL=$(grep "your url is" tunnel.log | sed 's/your url is: //')
    echo -e "\n============================================="
    echo -e "🎉 App is now accessible online!"
    echo -e "URL: \033[1;36m$URL\033[0m"
    echo -e "============================================="
else
    echo "Tunnel is starting. Check tunnel.log for the URL."
fi

echo "Press Ctrl+C at any time to shut down the domain and stop the server."

# Keep script running to maintain the background processes
while true; do
    sleep 1
done
