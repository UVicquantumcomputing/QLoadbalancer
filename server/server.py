import sys
import time
import random
from flask import Flask, jsonify, request

app = Flask(__name__)

# State tracked per server instance
state = {
    "port": None,
    "capacity": 100,
    "current_load": 0,
    "requests_handled": 0,
}


@app.route("/status", methods=["GET"])
def status():
    """Returns current server load info for QAOA encoder to read."""
    return jsonify({
        "port":             state["port"],
        "capacity":         state["capacity"],
        "current_load":     state["current_load"],
        "load_percent":     round(state["current_load"] / state["capacity"] * 100, 2),
        "requests_handled": state["requests_handled"],
    })


@app.route("/handle", methods=["POST"])
def handle_request():
    """Simulates processing an incoming request."""
    data = request.get_json()
    weight = data.get("weight", 1)   # request cost/size sent by load balancer

    # Reject if over capacity
    if state["current_load"] + weight > state["capacity"]:
        return jsonify({"status": "rejected", "reason": "over capacity"}), 503

    # Simulate processing
    state["current_load"] += weight
    state["requests_handled"] += 1

    processing_time = random.uniform(0.05, 0.2) * weight
    time.sleep(processing_time)

    state["current_load"] = max(0, state["current_load"] - weight)

    return jsonify({
        "status":          "ok",
        "processed_by":    state["port"],
        "processing_time": round(processing_time, 4),
        "current_load":    state["current_load"],
    })


@app.route("/reset", methods=["POST"])
def reset():
    """Resets server state — useful between test runs."""
    state["current_load"] = 0
    state["requests_handled"] = 0
    return jsonify({"status": "reset", "port": state["port"]})


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python server.py <port> <capacity>")
        sys.exit(1)

    state["port"] = int(sys.argv[1])
    state["capacity"] = int(sys.argv[2])

    print(f"Starting server on port {state['port']} with capacity {state['capacity']}")
    app.run(host="0.0.0.0", port=state["port"])

