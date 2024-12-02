from flask import Flask, render_template, request, jsonify
import requests
import logging
import json  # 添加这一行以导入 json 模块

app = Flask(__name__)
TOPOLOGY_FILE = "/tmp/topology.json"
RYU_API_URL = "http://localhost:8080"

# 设置日志记录
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/topology', methods=['GET'])
def get_topology():
    try:
        with open(TOPOLOGY_FILE, "r") as f:
            topology = json.load(f)
    except FileNotFoundError:
        logging.error("Topology file not found")
        topology = {"nodes": [], "links": []}
    return jsonify(topology)

@app.route('/api/slices', methods=['GET'])
def get_slices():
    try:
        with open(TOPOLOGY_FILE, "r") as f:
            topology = json.load(f)
        slices = topology.get("slices", {})
    except FileNotFoundError:
        logging.error("Topology file not found")
        slices = {}
    return jsonify(slices)

@app.route('/api/slices/<slice_name>/activate', methods=['POST'])
def activate_slice(slice_name):
    ips = get_slice_ips(slice_name)
    if not ips:
        logging.error(f"No valid IPs found for the slice: {slice_name}")
        return jsonify({"error": "No valid IPs found for the slice"}), 400

    response = requests.post(f"{RYU_API_URL}/simpleswitch/activate_slice", json={"slice_name": slice_name})
    if response.status_code != 200:
        logging.error(f"Error activating slice: {response.text}")
        return jsonify({"error": response.text}), response.status_code

    return jsonify(response.json()), 200

@app.route('/api/slices/<slice_name>/deactivate', methods=['POST'])
def deactivate_slice(slice_name):
    ips = get_slice_ips(slice_name)
    if not ips:
        logging.error(f"No valid IPs found for the slice: {slice_name}")
        return jsonify({"error": "No valid IPs found for the slice"}), 400

    response = requests.post(f"{RYU_API_URL}/simpleswitch/deactivate_slice", json={"slice_name": slice_name})
    if response.status_code != 200:
        logging.error(f"Error deactivating slice: {response.text}")
        return jsonify({"error": response.text}), response.status_code

    return jsonify(response.json()), 200

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
    app.run(host='0.0.0.0', debug=True)  # 监听所有网络接口
