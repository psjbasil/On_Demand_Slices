"""
GUI Server for Network Slice Management
Provides web interface and REST API endpoints for slice operations
"""

from flask import Flask, render_template, request, jsonify
import requests
import logging
import json

app = Flask(__name__)
TOPOLOGY_FILE = "/tmp/topology.json"
RYU_API_URL = "http://localhost:8080"

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    """
    Render the main page of the web interface
    Returns:
        HTML template for the main page
    """
    return render_template('index.html')

@app.route('/api/topology')
def get_topology():
    """
    Get the network topology information
    Returns:
        JSON response containing network topology data
        - nodes: list of switches and hosts
        - links: list of connections between nodes
        - hosts: mapping of host IDs to IP addresses
        - slices: network slice configurations
    """
    try:
        with open(TOPOLOGY_FILE, 'r') as f:
            topology = json.load(f)
        return jsonify(topology)
    except Exception as e:
        logging.error(f"Error reading topology file: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/slices')
def get_slices():
    """
    Get all configured network slices
    Returns:
        JSON response containing slice configurations:
        - hosts: list of hosts in each slice
        - bandwidth_percentage: allocated bandwidth for the slice
        - priority: slice priority level (high/medium/low)
        - description: slice description
    """
    try:
        with open(TOPOLOGY_FILE, 'r') as f:
            topology_data = json.load(f)
        return jsonify(topology_data["slices"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/slices/<slice_name>/activate', methods=['POST'])
def activate_slice(slice_name):
    """
    Activate a specific network slice
    Args:
        slice_name: Name of the slice to activate
    Returns:
        JSON response with activation status
        - success: activation success message
        - error: error message if activation fails
    """
    try:
        response = requests.post(
            f"{RYU_API_URL}/simpleswitch/activate_slice",
            json={"slice_name": slice_name},
            timeout=30
        )
        # Forward Ryu controller's response
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timeout"}), 504
    except Exception as e:
        logging.error(f"Error activating slice: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/slices/<slice_name>/deactivate', methods=['POST'])
def deactivate_slice(slice_name):
    """
    Deactivate a specific network slice
    Args:
        slice_name: Name of the slice to deactivate
    Returns:
        JSON response with deactivation status
        - success: deactivation success message
        - error: error message if deactivation fails
    """
    try:
        response = requests.post(
            f"{RYU_API_URL}/simpleswitch/deactivate_slice",
            json={"slice_name": slice_name},
            timeout=30
        )
        # Forward Ryu controller's response
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timeout"}), 504
    except Exception as e:
        logging.error(f"Error deactivating slice: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_slice_ips(slice_name):
    try:
        with open(TOPOLOGY_FILE, "r") as f:
            topology = json.load(f)
    except FileNotFoundError:
        logging.error("Topology file not found")
        return []

    host_ips = topology.get("hosts", {})
    slices = topology.get("slices", {})
    hosts = slices.get(slice_name, [])
    ips = []
    for host in hosts:
        ip = host_ips.get(host)
        if ip:
            ips.append(ip)
            logging.debug(f"Found IP for {host}: {ip}")
        else:
            logging.warning(f"No valid IP found for {host}")
    return ips

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)  