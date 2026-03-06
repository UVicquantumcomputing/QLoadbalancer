"""
Classical Load Balancer Implementation
Uses Least Connections with Weighted Capacity algorithm
"""

import requests
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sys
import os

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


class ClassicalLoadBalancer:
    """
    Classical load balancer using Least Connections with Weighted Capacity.
    
    Algorithm: Routes to server with lowest (active_connections / capacity) ratio.
    This ensures servers are utilized proportionally to their capacity.
    """
    
    def __init__(self, servers_config: List[Dict] = None):
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
        
        print(f"Classical Load Balancer initialized with {len(self.servers)} servers")
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
        """Calculate load ratio: active_connections / capacity"""
        if server.capacity == 0:
            return float('inf')
        return server.active_connections / server.capacity

    def select_best_server(self) -> Optional[ServerStatus]:
        """
        Select server using Least Connections with Weighted Capacity.
        Returns server with lowest load ratio that is healthy.
        """
        with self.lock:
            healthy_servers = [s for s in self.servers.values() if s.is_healthy]
            
            if not healthy_servers:
                print("WARNING: No healthy servers available!")
                return None
            
            # Find server with minimum load ratio
            best_server = min(healthy_servers, key=self.calculate_load_ratio)
            
            load_ratios = {s.id: self.calculate_load_ratio(s) for s in healthy_servers}
            print(f"Load ratios: {load_ratios} -> Selected server {best_server.id}")
            
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
                result['load_balancer'] = 'classical'
                result['server_selected'] = selected_server.id
                result['routing_algorithm'] = 'least_connections_weighted'
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
                "algorithm": "least_connections_weighted_capacity",
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


def main():
    """Demo of classical load balancer"""
    print("=== Classical Load Balancer Demo ===")
    
    balancer = ClassicalLoadBalancer()
    
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
    main()