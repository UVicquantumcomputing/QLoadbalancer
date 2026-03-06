# Quantum Load Balancer - Todo List

**Project Goal**: Quantum Computing Club simulation demonstrating QAOA-based load balancing vs classical approaches

---

## Phase 1: Foundation & Setup
- [ ] **Complete README with project overview** - Document QAOA approach, club goals, quantum vs classical comparison
- [ ] **Create requirements.txt and setup** - Qiskit, Flask, numpy, matplotlib for visualization

## Phase 2: Classical Baseline 
- [X] **Implement classical load balancer baseline** - Weighted Least Connections

## Phase 3: Core Quantum Implementation
- [ ] **Build QAOA problem encoding (3 servers)** - Map server loads to Hamiltonian, define cost function
- [ ] **Create IBM Qiskit interface module** - Handle quantum circuit execution, result processing
- [ ] **Implement main quantum load balancer** - Integrate QAOA results with routing decisions

## Phase 4: Testing & Analysis
- [ ] **Add basic metrics collection** - Response times, server utilization, routing decisions
- [ ] **Create synthetic traffic generator** - Simple request patterns for testing, other request patterns for testing if successful
- [ ] **Document different traffic patterns** - Burst loads, gradual increases, mixed patterns
- [ ] **Build results analysis and comparison** - Classical vs quantum performance visualization

## Phase 5: Demo & Presentation
- [ ] **Create demo scripts for club presentation** - Easy-to-run examples showing quantum advantage
- [ ] **Add performance benchmarking tools** - Automated tests for different scenarios

---

## Notes
- **Target**: 3 servers for simplification
- **Environment**: Local development, IBM Quantum via Qiskit
- **Focus**: Quantum approach with classical comparison
- **Traffic**: Start with simple synthetic loads

## Project Structure
- `/demo/` - Demo and example files
- `/scripts/` - Utility scripts (startup, testing, etc.)
- `/load_balancer/` - Classical and quantum load balancer implementations
- `/server/` - Backend server code and configuration
- `/traffic/` - Traffic generation and analysis tools
- `/qaoa/` - Quantum algorithm implementations


other
demo scripts
benchmarking tools
visualizations/charts/plots