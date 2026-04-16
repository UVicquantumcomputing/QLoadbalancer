"""
Traffic Generator for Load Balancer Testing

Generates synthetic traffic patterns to test classical and quantum load balancers.
Supports various traffic patterns and collects performance metrics.
"""

import time
import random
import threading
import requests
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import statistics


@dataclass
class TrafficRequest:
    """Represents a single traffic request"""
    id: int
    weight: int = 1
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class RequestResult:
    """Results from a processed request"""
    request_id: int
    success: bool
    server_id: Optional[int]
    response_time: float
    status_code: Optional[int]
    error_message: Optional[str]
    timestamp: float
    load_balancer_type: Optional[str] = None


class TrafficPattern:
    """Base class for different traffic generation patterns"""
    
    def __init__(self, duration: float, base_rate: float = 10):
        self.duration = duration  # seconds
        self.base_rate = base_rate  # requests per second
        
    def get_requests_per_second(self, elapsed_time: float) -> float:
        """Return requests per second at given elapsed time"""
        return self.base_rate
        
    def get_request_weight(self) -> int:
        """Return weight for next request (processing cost)"""
        return 1


class ConstantTraffic(TrafficPattern):
    """Constant rate traffic"""
    pass


class BurstTraffic(TrafficPattern):
    """Traffic with sudden bursts"""
    
    def __init__(self, duration: float, base_rate: float = 10, 
                 burst_rate: float = 50, burst_duration: float = 5):
        super().__init__(duration, base_rate)
        self.burst_rate = burst_rate
        self.burst_duration = burst_duration
        
    def get_requests_per_second(self, elapsed_time: float) -> float:
        # Burst every 20 seconds
        cycle_time = elapsed_time % 20
        if cycle_time < self.burst_duration:
            return self.burst_rate
        return self.base_rate


class RampTraffic(TrafficPattern):
    """Gradually increasing traffic"""
    
    def __init__(self, duration: float, start_rate: float = 5, end_rate: float = 30):
        super().__init__(duration, start_rate)
        self.start_rate = start_rate
        self.end_rate = end_rate
        
    def get_requests_per_second(self, elapsed_time: float) -> float:
        progress = min(elapsed_time / self.duration, 1.0)
        return self.start_rate + (self.end_rate - self.start_rate) * progress


class RandomTraffic(TrafficPattern):
    """Random traffic with varying loads"""
    
    def get_requests_per_second(self, elapsed_time: float) -> float:
        # Random between 50% to 150% of base rate
        return self.base_rate * random.uniform(0.5, 1.5)
        
    def get_request_weight(self) -> int:
        # Random request sizes (1-5)
        return random.randint(1, 5)


class MixedTraffic(TrafficPattern):
    """Mixed pattern with different request types"""
    
    def get_request_weight(self) -> int:
        # 70% lightweight, 20% medium, 10% heavy requests
        rand = random.random()
        if rand < 0.7:
            return 5  # Light
        elif rand < 0.9:
            return 8  # Medium  
        else:
            return 14  # Heavy


class TrafficGenerator:
    """
    Main traffic generator that sends requests to load balancer
    and collects performance metrics.
    """
    
    def __init__(self, load_balancer_url: str = "http://localhost:8080"):
        self.load_balancer_url = load_balancer_url.rstrip('/')
        self.results: List[RequestResult] = []
        self.is_running = False
        self.request_counter = 0
        self.lock = threading.Lock()
        
    def generate_request_id(self) -> int:
        """Generate unique request ID"""
        with self.lock:
            self.request_counter += 1
            return self.request_counter
            
    def send_request(self, request: TrafficRequest) -> RequestResult:
        """Send a single request to the load balancer"""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.load_balancer_url}/route",
                json={"weight": request.weight, "request_id": request.id},
                timeout=10
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                return RequestResult(
                    request_id=request.id,
                    success=True,
                    server_id=result_data.get('server_selected'),
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=None,
                    timestamp=start_time,
                    load_balancer_type=result_data.get('load_balancer')
                )
            else:
                return RequestResult(
                    request_id=request.id,
                    success=False,
                    server_id=None,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"HTTP {response.status_code}",
                    timestamp=start_time
                )
                
        except requests.RequestException as e:
            response_time = time.time() - start_time
            return RequestResult(
                request_id=request.id,
                success=False,
                server_id=None,
                response_time=response_time,
                status_code=None,
                error_message=str(e),
                timestamp=start_time
            )
            
    def run_traffic_pattern(self, pattern: TrafficPattern, 
                           concurrent_workers: int = 5) -> List[RequestResult]:
        """
        Execute a traffic pattern for the specified duration.
        
        Args:
            pattern: Traffic pattern to execute
            concurrent_workers: Number of concurrent request threads
        """
        print(f"Starting traffic generation: {pattern.__class__.__name__}")
        print(f"Duration: {pattern.duration}s, Base rate: {pattern.base_rate} req/s")
        print(f"Concurrent workers: {concurrent_workers}")
        
        self.results = []
        self.is_running = True
        start_time = time.time()
        
        # Thread pool for sending requests
        request_queue = []
        worker_threads = []
        
        def worker():
            """Worker thread that processes requests"""
            while self.is_running:
                if request_queue:
                    with self.lock:
                        if request_queue:
                            request = request_queue.pop(0)
                        else:
                            continue
                    
                    # Send request and store result
                    result = self.send_request(request)
                    
                    with self.lock:
                        self.results.append(result)
                else:
                    time.sleep(0.01)  # Brief pause when queue empty
        
        # Start worker threads
        for _ in range(concurrent_workers):
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            worker_threads.append(thread)
        
        # Generate requests according to pattern
        last_request_time = start_time
        
        try:
            while time.time() - start_time < pattern.duration:
                elapsed = time.time() - start_time
                current_rate = pattern.get_requests_per_second(elapsed)
                
                # Calculate time between requests
                if current_rate > 0:
                    interval = 1.0 / current_rate
                    
                    if time.time() >= last_request_time + interval:
                        # Create new request
                        request = TrafficRequest(
                            id=self.generate_request_id(),
                            weight=pattern.get_request_weight()
                        )
                        
                        with self.lock:
                            request_queue.append(request)
                            
                        last_request_time = time.time()
                
                time.sleep(0.001)  # Small sleep to prevent busy waiting
                
        except KeyboardInterrupt:
            print("\nTraffic generation interrupted by user")
        
        finally:
            # Stop workers and wait for pending requests to complete
            self.is_running = False
            print("Waiting for pending requests to complete...")
            
            # Wait a bit for pending requests
            time.sleep(2)
            
        total_time = time.time() - start_time
        print(f"Traffic generation completed in {total_time:.2f}s")
        print(f"Generated {len(self.results)} total requests")
        
        return self.results.copy()
    
    def get_traffic_summary(self) -> Dict[str, Any]:
        """Generate summary statistics from traffic results"""
        if not self.results:
            return {"error": "No results available"}
        
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        summary = {
            "total_requests": len(self.results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(self.results) * 100,
        }
        
        if successful_results:
            response_times = [r.response_time for r in successful_results]
            summary.update({
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
            })
            
            # Server distribution
            server_counts = {}
            for result in successful_results:
                server_id = result.server_id
                server_counts[server_id] = server_counts.get(server_id, 0) + 1
            
            summary["server_distribution"] = server_counts
            
            # Load balancer type
            lb_types = [r.load_balancer_type for r in successful_results if r.load_balancer_type]
            if lb_types:
                summary["load_balancer_type"] = lb_types[0]
        
        return summary


def demo_traffic_patterns():
    """Demonstrate different traffic patterns"""
    print("=== Traffic Generator Demo ===")
    print("Note: Make sure load balancer is running on localhost:8080")
    
    generator = TrafficGenerator()
    
    patterns = [
        ("Constant Traffic", ConstantTraffic(duration=10, base_rate=10)),
        ("Burst Traffic", BurstTraffic(duration=15, base_rate=30, burst_rate=15, burst_duration=3)),
        ("Ramp Traffic", RampTraffic(duration=12, start_rate=20, end_rate=100)),
        ("Random Traffic", RandomTraffic(duration=8, base_rate=6)),
        ("Mixed Traffic", MixedTraffic(duration=10, base_rate=5)),
    ]
    
    for pattern_name, pattern in patterns:
        print(f"\n{'='*50}")
        print(f"Testing: {pattern_name}")
        print(f"{'='*50}")
        
        results = generator.run_traffic_pattern(pattern, concurrent_workers=10)
        summary = generator.get_traffic_summary()
        
        print(f"\n--- Results for {pattern_name} ---")
        print(f"Total requests: {summary.get('total_requests', 0)}")
        print(f"Success rate: {summary.get('success_rate', 0):.1f}%")
        
        if 'avg_response_time' in summary:
            print(f"Avg response time: {summary['avg_response_time']:.3f}s")
            print(f"Server distribution: {summary.get('server_distribution', {})}")
        
        # Brief pause between patterns
        time.sleep(2)


if __name__ == "__main__":
    demo_traffic_patterns()
