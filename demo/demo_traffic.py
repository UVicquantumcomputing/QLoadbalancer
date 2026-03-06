"""
Integrated Demo: Classical Load Balancer + Traffic Generator

Run this after starting servers and load balancer to see the system in action.
"""

import sys
import os
import time

# Add parent directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from traffic.traffic_generator import (
    TrafficGenerator, 
    ConstantTraffic, 
    BurstTraffic, 
    RampTraffic,
    MixedTraffic
)


def quick_demo():
    """Quick demo showing classical load balancer with traffic patterns"""
    print("=== Classical Load Balancer + Traffic Generator Demo ===")
    print()
    
    generator = TrafficGenerator("http://localhost:8080")
    
    # Test different patterns
    patterns = [
        ("Constant Load", ConstantTraffic(duration=8, base_rate=4)),
        ("Burst Load", BurstTraffic(duration=10, base_rate=2, burst_rate=12, burst_duration=2)),
        ("Ramp Load", RampTraffic(duration=8, start_rate=1, end_rate=8)),
    ]
    
    for pattern_name, pattern in patterns:
        print(f"\n{'='*50}")
        print(f"Testing: {pattern_name}")
        print(f"{'='*50}")
        
        # Run the traffic pattern
        results = generator.run_traffic_pattern(pattern, concurrent_workers=3)
        
        # Show summary
        summary = generator.get_traffic_summary()
        
        print(f"\n--- Results Summary ---")
        print(f"Total requests: {summary.get('total_requests', 0)}")
        print(f"Success rate: {summary.get('success_rate', 0):.1f}%")
        print(f"Avg response time: {summary.get('avg_response_time', 0):.3f}s")
        print(f"Server distribution: {summary.get('server_distribution', {})}")
        
        # Brief pause between tests
        time.sleep(1)
    
    print(f"\n{'='*50}")
    print("Demo completed! Check load balancer stats with:")
    print("  curl http://localhost:8080/stats")
    print(f"{'='*50}")


if __name__ == "__main__":
    quick_demo()