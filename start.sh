#!/bin/bash
# Ayeneh Launcher

BACKEND="/home/hadi/ayeneh/Ayeneh/apps/backend"
FRONTEND="/home/hadi/ayeneh/Ayeneh/frontend"
PIDFILE="/tmp/ayeneh.pids"
PNPM="/home/hadi/.nvm/versions/node/v22.19.0/bin/pnpm"
NODE="/home/hadi/.nvm/versions/node/v22.19.0/bin"

# Stop any running instances
if [ -f "$PIDFILE" ]; then
    cat "$PIDFILE" | xargs kill 2>/dev/null
    rm -f "$PIDFILE"
fi
pkill -f "uvicorn ayeneh.main" 2>/dev/null
pkill -f "next dev" 2>/dev/null
sleep 1

# Start backend
cd "$BACKEND"
nohup env AYENEH_DATABASE_URL="sqlite+aiosqlite:////home/hadi/ayeneh/Ayeneh/ayeneh.db" AYENEH_DEBUG=true \
    python -m uvicorn ayeneh.main:app --host 0.0.0.0 --port 8000 \
    > /tmp/ayeneh-backend.log 2>&1 &
echo $! > "$PIDFILE"

sleep 3

# Start frontend with full node/pnpm paths
cd "$FRONTEND"
PATH="$NODE:$PATH" nohup $PNPM dev > /tmp/ayeneh-frontend.log 2>&1 &
echo $! >> "$PIDFILE"

sleep 5

# Verify
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "Backend: OK"
fi
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "Frontend: OK"
fi
