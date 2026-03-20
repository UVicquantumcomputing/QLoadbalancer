'''
Quantum Load Balancer Impelmentation
This file will probably be classical portion of the quantum load balancer
i.e. detecting traffic, sending problem structure to qaoa, recieving and routing'''

import requests
import time
import threading
import sys
import os
from dataclasses import dataclass
from flask import Flask, request, jsonify

# Add parent directory to path for importing server config
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
    """"""
    
    def __init__(self,, servers_config: List[Dict] = None):
        self.servers_config = servers_config or SERVER_CONFIG
        self.servers: Dict[int, ServerStatus] = {}
        self.lock = threading.Lock()  # Thread safety for connection tracking
        
        # Initialize server status tracking
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
    
    def """format problem into qaoa"""
    def """send/recieve problem from qaoa program"""
    def """parse response from qaoa program"""
    
    def route_request(self, request_weight: int = 1) -> Optional[Dict]:
        """
        Route a request to the best available server.
        
        Args:
            request_weight: Processing cost of the request (default: 1)
            
        Returns:
            Response from the selected server or None if routing failed
        """
        selected_server = self.""""""()
        
        if not selected_server:
            return {"status": "error", "message": "No healthy servers available"}
        
        # Increment connection count
        with self.lock:
            selected_server.active_connections += 1
            selected_server.total_requests += 1
        
        start_time = time.time()
        
        try:
            # Send request to selected server
            response = requests.post(
                f"http://{selected_server.host}:{selected_server.port}/handle",
                json={"weight": request_weight},
                timeout=5
            )
            
            response_time = time.time() - start_time
            
            # Update metrics
            with self.lock:
                selected_server.active_connections = max(0, selected_server.active_connections - 1)
                selected_server.total_response_time += response_time
            
            if response.status_code == 200:
                result = response.json()
                result['load_balancer'] = 'quantum'
                result['server_selected'] = selected_server.id
                result['routing_algorithm'] = 'qaoa'
                return result
            else:
                # Server rejected request (likely over capacity)
                return {
                    "status": "rejected", 
                    "server_id": selected_server.id,
                    "reason": f"Server returned {response.status_code}"
                }
                
        except requests.RequestException as e:
            # Mark server as unhealthy and decrement connection count
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
                    "algorithm": "qaoa",
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
                    
                    # Reset local tracking
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
    """HTTP endpoint for routing requests (used by traffic generator)"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400
    
    request_id = data.get('request_id', 'unknown')
    
    if not load_balancer:
        return jsonify({"status": "error", "message": "Load balancer not initialized"}), 500
    
    # Route the request
    result = load_balancer.route_request()
    
    if result:
        # Add request metadata to response
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
    
    # Health check
    print("\nPerforming health check...")
    health = balancer.health_check_all()
    print(f"Server health: {health}")
    
    # Simulate some requests - simple 10 repeated requests.
    print("\nSimulating requests...")
    for i in range(10):
        print(f"\nRequest {i+1}:")
        result = balancer.route_request(request_weight=1)
        print(f"  Result: {result}")
        time.sleep(0.1)  # Small delay between requests
    
    # Show final stats
    print("\n=== Final Statistics ===")
    stats = balancer.get_load_balancer_stats()
    for server_id, server_stats in stats["servers"].items():
        print(f"Server {server_id}: {server_stats}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        # Run as HTTP server for integration with traffic generator
        host = "localhost" if len(sys.argv) < 3 else sys.argv[2]  
        port = 8080 if len(sys.argv) < 4 else int(sys.argv[3])
        run_load_balancer_server(host, port)
    else:
        # Run standalone demo
        main()
    main()