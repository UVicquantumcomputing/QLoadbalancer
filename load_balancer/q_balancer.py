"""
Quantum Load Balancer Implementation
Uses a quantum circuit to select the best server based on load ratios.
Quantum logic encodes server load as rotation angles, then samples the
most favorable server state via measurement.
"""

import requests
import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
import math
import sys
import os
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from flask import Flask, request, jsonify

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from server.server_config import SERVER_CONFIG


@dataclass
class ServerStatus:
    """Tracks real-time server status"""
    id: int
    host: str
    port: int
    capacity: int
    active_connections: int = 0
    total_requests: int = 0
    total_response_time: float = 0.0
    is_healthy: bool = True
    last_health_check: float = 0.0


class QuantumLoadBalancer:
    """
    Quantum load balancer using a quantum circuit for server selection.

    Each healthy server is mapped to a qubit. The load ratio of each server
    is encoded as a rotation angle on its qubit — lightly loaded servers
    get rotations closer to |1>, heavily loaded servers closer to |0>.
    After measurement, the server whose qubit most often collapses to |1>
    is selected to handle the request.
    """

    def __init__(self, servers_config: List[Dict] = None):
        self.servers_config = servers_config or SERVER_CONFIG
        self.servers: Dict[int, ServerStatus] = {}
        self.lock = threading.Lock()

        for config in self.servers_config:
            self.servers[config['id']] = ServerStatus(
                id=config['id'],
                host=config['host'],
                port=config['port'],
                capacity=config['capacity']
            )

        print(f"Quantum Load Balancer initialized with {len(self.servers)} servers")
        for server in self.servers.values():
            print(f"  Server {server.id}: {server.host}:{server.port} (capacity: {server.capacity})")

    def get_server_status(self, server_id: int) -> Optional[Dict]:
        """Get current status from a specific server"""
        server = self.servers[server_id]
        try:
            response = requests.get(
                f"http://{server.host}:{server.port}/status",
                timeout=2
            )
            if response.status_code == 200:
                server.is_healthy = True
                server.last_health_check = time.time()
                return response.json()
        except requests.RequestException:
            server.is_healthy = False

        return None

    def calculate_load_ratio(self, server: ServerStatus) -> float:
        """Calculate load ratio: active_connections / capacity (0.0 = idle, 1.0 = full)"""
        if server.capacity == 0:
            return float('inf')
        return server.active_connections / server.capacity

    def select_best_server(self) -> Optional[ServerStatus]:
        """
        Select a server using quantum circuit sampling.

        Each healthy server gets a qubit. Its load ratio is encoded as a
        Ry rotation: a lightly loaded server rotates close to |1>, a heavily
        loaded server stays close to |0>. The circuit is sampled, and the
        server whose qubit most frequently measures |1> is selected.
        """
        with self.lock:
            healthy_servers = [s for s in self.servers.values() if s.is_healthy]

            if not healthy_servers:
                print("WARNING: No healthy servers available!")
                return None

            n = len(healthy_servers)
            qc = QuantumCircuit(n, n)

            # Encode each server's load as a rotation angle on its qubit.
            # load_ratio = 0.0 (idle)   -> angle = pi  -> |1> (most likely to be selected)
            # load_ratio = 1.0 (full)   -> angle = 0   -> |0> (least likely to be selected)
            for i, server in enumerate(healthy_servers):
                load_ratio = self.calculate_load_ratio(server)
                print(load_ratio)
                clamped = min(load_ratio, 1.0)
                angle = math.pi * (1.0 - clamped)
                qc.ry(angle, i)

            qc.measure(range(n), range(n))

            simulator = AerSimulator()
            job = simulator.run(qc, shots=1000)
            counts = job.result().get_counts()
            #print(counts)

            # Count how often each qubit measured |1| across all shots
            qubit_ones = [0] * n
            for bitstring, count in counts.items():
                # Qiskit returns bitstrings in reverse qubit order
                for i, bit in enumerate(reversed(bitstring)):
                    if bit == '1':
                        qubit_ones[i] += count

            best_index = qubit_ones.index(max(qubit_ones))
            best_server = healthy_servers[best_index]

            load_ratios = {s.id: round(self.calculate_load_ratio(s), 3) for s in healthy_servers}
            print(f"Load ratios: {load_ratios} -> Quantum selected server {best_server.id}")

            return best_server

    def route_request(self, request_weight: int = 1) -> Optional[Dict]:
        """
        Route a request to the best available server.

        Args:
            request_weight: Processing cost of the request (default: 1)

        Returns:
            Response from the selected server or None if routing failed
        """
        selected_server = self.select_best_server()

        if not selected_server:
            return {"status": "error", "message": "No healthy servers available"}

        with self.lock:
            selected_server.active_connections += 1
            selected_server.total_requests += 1

        start_time = time.time()

        try:
            response = requests.post(
                f"http://{selected_server.host}:{selected_server.port}/handle",
                json={"weight": request_weight},
                timeout=5
            )

            response_time = time.time() - start_time

            with self.lock:
                selected_server.active_connections = max(0, selected_server.active_connections - 1)
                selected_server.total_response_time += response_time

            if response.status_code == 200:
                result = response.json()
                result['load_balancer'] = 'quantum'
                result['server_selected'] = selected_server.id
                result['routing_algorithm'] = 'quantum_load_encoding'
                return result
            else:
                return {
                    "status": "rejected",
                    "server_id": selected_server.id,
                    "reason": f"Server returned {response.status_code}"
                }

        except requests.RequestException as e:
            with self.lock:
                selected_server.active_connections = max(0, selected_server.active_connections - 1)
                selected_server.is_healthy = False

            print(f"Request failed to server {selected_server.id}: {e}")
            return {"status": "error", "message": f"Server {selected_server.id} unreachable"}

    def health_check_all(self) -> Dict[int, bool]:
        """Perform health check on all servers"""
        health_status = {}
        for server_id in self.servers.keys():
            status = self.get_server_status(server_id)
            health_status[server_id] = status is not None
        return health_status

    def get_load_balancer_stats(self) -> Dict:
        """Get comprehensive load balancer statistics"""
        with self.lock:
            stats = {
                "algorithm": "quantum_load_encoding",
                "total_servers": len(self.servers),
                "healthy_servers": sum(1 for s in self.servers.values() if s.is_healthy),
                "servers": {}
            }

            for server in self.servers.values():
                avg_response_time = (
                    server.total_response_time / server.total_requests
                    if server.total_requests > 0 else 0
                )
                stats["servers"][server.id] = {
                    "active_connections": server.active_connections,
                    "total_requests": server.total_requests,
                    "capacity": server.capacity,
                    "load_ratio": self.calculate_load_ratio(server),
                    "avg_response_time": round(avg_response_time, 4),
                    "is_healthy": server.is_healthy
                }

            return stats

    def reset_all_servers(self) -> Dict:
        """Reset all servers to clean state"""
        results = {}

        for server in self.servers.values():
            try:
                response = requests.post(
                    f"http://{server.host}:{server.port}/reset",
                    timeout=2
                )
                results[server.id] = response.status_code == 200

                with self.lock:
                    server.active_connections = 0
                    server.total_requests = 0
                    server.total_response_time = 0.0
                    server.is_healthy = True

            except requests.RequestException:
                results[server.id] = False
                server.is_healthy = False

        return results


# Flask application for HTTP interface
app = Flask(__name__)
load_balancer = None


@app.route('/route', methods=['POST'])
def route_request():
    """HTTP endpoint for routing requests"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400

    request_weight = data.get('weight', 1)
    request_id = data.get('request_id', 'unknown')

    if not load_balancer:
        return jsonify({"status": "error", "message": "Load balancer not initialized"}), 500

    result = load_balancer.route_request(request_weight)

    if result:
        result['request_id'] = request_id
        result['timestamp'] = time.time()
        return jsonify(result)
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to route request",
            "request_id": request_id
        }), 503


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get load balancer statistics"""
    if not load_balancer:
        return jsonify({"status": "error", "message": "Load balancer not initialized"}), 500
    stats = load_balancer.get_load_balancer_stats()
    stats['timestamp'] = time.time()
    return jsonify(stats)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check all servers"""
    if not load_balancer:
        return jsonify({"status": "error", "message": "Load balancer not initialized"}), 500
    health_status = load_balancer.health_check_all()
    return jsonify({
        "status": "ok",
        "servers": health_status,
        "timestamp": time.time()
    })


@app.route('/reset', methods=['POST'])
def reset_servers():
    """Reset all servers"""
    if not load_balancer:
        return jsonify({"status": "error", "message": "Load balancer not initialized"}), 500
    reset_results = load_balancer.reset_all_servers()
    return jsonify({
        "status": "ok",
        "reset_results": reset_results,
        "timestamp": time.time()
    })


def run_load_balancer_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the quantum load balancer as HTTP server"""
    global load_balancer

    print("=== Starting Quantum Load Balancer Server ===")
    load_balancer = QuantumLoadBalancer()

    print(f"\nLoad balancer API endpoints:")
    print(f"  POST http://{host}:{port}/route   - Route requests")
    print(f"  GET  http://{host}:{port}/stats   - Get statistics")
    print(f"  GET  http://{host}:{port}/health  - Health check")
    print(f"  POST http://{host}:{port}/reset   - Reset servers")
    print(f"\nStarting server on http://{host}:{port}")
    print("Press Ctrl+C to stop")

    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down load balancer server...")


def main():
    """Demo of quantum load balancer"""
    print("=== Quantum Load Balancer Demo ===")

    balancer = QuantumLoadBalancer()

    print("\nPerforming health check...")
    health = balancer.health_check_all()
    print(f"Server health: {health}")

    print("\nSimulating requests...")
    for i in range(10):
        print(f"\nRequest {i+1}:")
        result = balancer.route_request(request_weight=1)
        print(f"  Result: {result}")
        time.sleep(0.1)

    print("\n=== Final Statistics ===")
    stats = balancer.get_load_balancer_stats()
    for server_id, server_stats in stats["servers"].items():
        print(f"Server {server_id}: {server_stats}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        host = "localhost" if len(sys.argv) < 3 else sys.argv[2]
        port = 8080 if len(sys.argv) < 4 else int(sys.argv[3])
        run_load_balancer_server(host, port)
    else:
        main()