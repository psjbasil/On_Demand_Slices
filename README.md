# Network Slicing with QoS Control

A Software-Defined Networking (SDN) solution that implements dynamic network slicing with QoS control. This project enables on-demand activation and deactivation of network slices through both CLI and GUI interfaces.

## Features

- **Dynamic Network Slicing**: Activate and deactivate network slices on demand
- **QoS Control**: Bandwidth allocation and priority management for each slice
- **Web-based GUI**: Visual management interface for network slices
- **Real-time Visualization**: D3.js-based network topology visualization
- **REST API**: Full API support for slice management operations

## System Architecture

### Components

1. **SDN Controller (Ryu)**
   - Manages OpenFlow switches
   - Handles flow rule installation
   - Provides REST API endpoints

2. **Web Interface**
   - Flask-based web server
   - Interactive topology visualization
   - Slice management controls

3. **Network Topology**
   - Industrial network simulation
   - Multiple network areas (Production, Monitoring, Office)
   - QoS-enabled links

### Network Slices

- **Production Control** (50% bandwidth, High priority)
  - Industrial control systems
  - Real-time operations

- **Emergency Response** (40% bandwidth, High priority)
  - Cross-area urgent communication
  - Priority access during emergencies

- **Monitoring & Maintenance** (30% bandwidth, Medium priority)
  - System monitoring
  - Data collection

- **Office Access** (20% bandwidth, Low priority)
  - Regular office network access
  - Non-critical operations

## Prerequisites

- Python 3.+
- Ryu SDN Framework
- Mininet
- Flask
- D3.js (included)

## Usage
1. Clone the repository:
```bash
git clone <repository-url>
cd On-Demand-Slices/
```

2. Start the Ryu controller:
```bash
sudo ryu-manager slice_management.py
```

3. Start the network topology:
```bash
sudo python topology.py
```

4. Launch the web interface:
```bash
python gui.py
```

5. Access the GUI at `http://localhost:5000`

## API Endpoints

- `GET /api/topology` - Get network topology
- `GET /api/slices` - List all slices
- `POST /api/slices/<slice_name>/activate` - Activate a slice
- `POST /api/slices/<slice_name>/deactivate` - Deactivate a slice

## Project Structure
