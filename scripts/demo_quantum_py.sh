#!/bin/bash

# Demo script showing quantum load balancer + traffic generator integration
# This script demonstrates a quantum load balancer using 

echo "=== Quantum Load Balancer Demo ==="
echo "Testing Quantum Load Balancer with Traffic Generator"
echo ""

# Check if Python is available
if ! which python &> /dev/null; then
    echo "Error: Python is required but not installed"
    exit 1
fi

echo "Step 1: Starting backend servers..."
bash start_servers.sh &
SERVER_PID=$!

# Wait for servers to start
echo "Waiting for servers to start..."
sleep 5

# Check if servers are running
echo "Checking server health..."
for port in 5001 5002 5003; do
    if curl -s "http://localhost:$port/status" > /dev/null; then
        echo "  ✓ Server on port $port is running"
    else
        echo "  ✗ Server on port $port failed to start"
    fi
done

echo ""
echo "Step 2: Starting Quantum load balancer..."
cd ../load_balancer
python q_balancer.py --server localhost 8080 &
LB_PID=$!
cd -

# Wait for load balancer to start
echo "Waiting for load balancer to start..."
sleep 7

# Test load balancer health
if curl -s "http://localhost:8080/health" > /dev/null; then
    echo "  ✓ Quantum load balancer is running on http://localhost:8080"
else
    echo "  ✗ Load balancer failed to start"
    kill $SERVER_PID $LB_PID 2>/dev/null
    exit 1
fi

echo ""
echo "Step 3: Running traffic generation tests..."
cd ../traffic
python traffic_generator.py
cd -

echo ""
echo "Step 4: Getting final statistics..."
curl -s "http://localhost:8080/stats" | python -m json.tool

echo ""
echo "Demo completed! Cleaning up..."

# Kill background processes
kill $LB_PID 2>/dev/null
pkill -f "server.py" 2>/dev/null

echo "All processes stopped."