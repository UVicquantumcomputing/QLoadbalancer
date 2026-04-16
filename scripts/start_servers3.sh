#!/bin/bash
# TODO: setup so reads from server_config.py?
echo "Starting QLoadbalancer servers..."

python3 ../server/server.py 5001 100 &
python3 ../server/server.py 5002 80  &
python3 ../server/server.py 5003 120 &

echo "Servers running on ports 5001, 5002, 5003"
echo "Use 'pkill -f server.py' to stop all servers"
