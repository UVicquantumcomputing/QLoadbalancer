#!/bin/bash
echo "Starting QLoadbalancer servers..."

python servers/server.py 5001 100 &
python servers/server.py 5002 80  &
python servers/server.py 5003 120 &

echo "Servers running on ports 5001, 5002, 5003"
echo "Use 'pkill -f server.py' to stop all servers"
