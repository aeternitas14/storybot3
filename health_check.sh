#!/bin/bash

# Check if both processes are running
if ! pgrep -f "python3 instagram_monitor.py" > /dev/null; then
    echo "Instagram monitor is not running"
    exit 1
fi

if ! pgrep -f "python3 run_bot.py" > /dev/null; then
    echo "Bot is not running"
    exit 1
fi

# Check if the health endpoint is responding
if ! curl -s https://localhost:443/health | grep -q "healthy"; then
    echo "Health check failed"
    exit 1
fi

echo "All systems operational"
exit 0 