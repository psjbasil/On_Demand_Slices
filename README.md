# Network Slicing with QoS Control

A Software-Defined Networking (SDN) solution that implements dynamic network slicing with QoS control. This project enables on-demand activation and deactivation of network slices through both CLI and GUI interfaces.

## Project Structure
```bash
├── slice_management.py  # Ryu controller application
├── topology.py  # Mininet topology definition
├── qos_manager.py  # QoS Manager
├── gui.py  # Flask web server
├── static/
│   ├── css/
│   │   └── style.css  # GUI styling
│   └── js/
│       └── script.js  # Frontend logic
└── templates/
└── index.html  # Web interface template
```
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
cd On_Demand_Slices/
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

## How to Verify Network Slice Activation/Deactivation

1. Initial State - Hosts in Network Topology are Not Connected by Default
```bash
mininet> pingall
*** Ping: testing ping reachability
h1 -> X X X X X X X
h2 -> X X X X X X X
h3 -> X X X X X X X
h4 -> X X X X X X X
h5 -> X X X X X X X
h6 -> X X X X X X X
h7 -> X X X X X X X
h8 -> X X X X X X X
*** Results: 100% dropped (0/56 received)
```
```bash
vagrant@comnetsemu:~$ sudo ovs-ofctl dump-flows s2
cookie=0x0, duration=1293.372s, table=0, n_packets=114, n_bytes=4788, priority=200,arp actions=NORMAL
cookie=0x0, duration=1293.372s, table=0, n_packets=70, n_bytes=5768, priority=0 actions=drop
```
2. Activate Slice - Select a Network Slice and Click Activate
![img_2.png](img_2.png)
```bash
mininet> h1 ping h2
PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.
64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=1.14 ms
64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=0.051 ms
^C
--- 10.0.0.2 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1002ms
```
```bash
vagrant@comnetsemu:~$ sudo ovs-ofctl dump-flows s2
cookie=0x0, duration=1311.509s, table=0, n_packets=114, n_bytes=4788, priority=200,arp actions=NORMAL
cookie=0x0, duration=13.104s, table=0, n_packets=0, n_bytes=0, priority=50,ip,nw_src=10.0.0.1,nw_dst=10.0.0.2 actions=NORMAL
cookie=0x0, duration=13.104s, table=0, n_packets=0, n_bytes=0, priority=50,ip,nw_src=10.0.0.1,nw_dst=10.0.0.3 actions=NORMAL
cookie=0x0, duration=13.104s, table=0, n_packets=0, n_bytes=0, priority=50,ip,nw_src=10.0.0.2,nw_dst=10.0.0.1 actions=NORMAL
cookie=0x0, duration=13.104s, table=0, n_packets=0, n_bytes=0, priority=50,ip,nw_src=10.0.0.2,nw_dst=10.0.0.3 actions=NORMAL
cookie=0x0, duration=13.104s, table=0, n_packets=0, n_bytes=0, priority=50,ip,nw_src=10.0.0.3,nw_dst=10.0.0.1 actions=NORMAL
cookie=0x0, duration=13.104s, table=0, n_packets=0, n_bytes=0, priority=50,ip,nw_src=10.0.0.3,nw_dst=10.0.0.2 actions=NORMAL
cookie=0x0, duration=1311.509s, table=0, n_packets=70, n_bytes=5768, priority=0 actions=drop
```
3. Activate All Network Slices
![img_1.png](img_1.png)
```bash
mininet> pingall
*** Ping: testing ping reachability
h1 -> h2 h3 h4 X h6 X X
h2 -> h1 h3 X X X X X
h3 -> h1 h2 X X X X X
h4 -> h1 X X h5 h6 X X
h5 -> X X X h4 X X X
h6 -> h1 X X h4 X h7 h8
h7 -> X X X X X h6 h8
h8 -> X X X X X h6 h7
*** Results: 64% dropped (20/56 received)
```
4. Deactivate Slice - Select a Network Slice and Click Deactivate
![img.png](img.png)
```bash
mininet> pingall
*** Ping: testing ping reachability
h1 -> X X h4 X h6 X X
h2 -> X X X X X X X
h3 -> X X X X X X X
h4 -> h1 X X h5 h6 X X
h5 -> X X X h4 X X X
h6 -> h1 X X h4 X h7 h8
h7 -> X X X X X h6 h8
h8 -> X X X X X h6 h7
*** Results: 75% dropped (14/56 received)
```

## How to Verify Network Slice Bandwidth
1. Activate All Network Slices
2. Execute the Following Commands in Mininet
```bash
mininet>  h1 tc qdisc show dev h1-eth0
qdisc tbf 8011: root refcnt 2 rate 5Gbit burst 639375b lat 20.0ms
mininet> h4 tc qdisc show dev h4-eth0
qdisc tbf 801c: root refcnt 2 rate 4Gbit burst 500Kb lat 20.0ms
mininet>  h5 tc qdisc show dev h5-eth0
qdisc tbf 8015: root refcnt 2 rate 3Gbit burst 383625b lat 20.0ms
mininet>  h7 tc qdisc show dev h7-eth0
qdisc tbf 8017: root refcnt 2 rate 2Gbit burst 250Kb lat 20.0ms

mininet> h1 iperf -s &
mininet> h2 iperf -c h1 -t 10 -P 4
------------------------------------------------------------
Client connecting to 10.0.0.1, TCP port 5001
TCP window size: 85.3 KByte (default)
------------------------------------------------------------
[  5] local 10.0.0.2 port 54088 connected with 10.0.0.1 port 5001
[  6] local 10.0.0.2 port 54090 connected with 10.0.0.1 port 5001
[  3] local 10.0.0.2 port 54084 connected with 10.0.0.1 port 5001
[  4] local 10.0.0.2 port 54086 connected with 10.0.0.1 port 5001
[ ID] Interval       Transfer     Bandwidth
[  4]  0.0-10.0 sec  1.04 GBytes   891 Mbits/sec
[  6]  0.0-10.0 sec  1.06 GBytes   914 Mbits/sec
[  3]  0.0-10.0 sec  1.42 GBytes  1.22 Gbits/sec
[  5]  0.0-10.0 sec  1.29 GBytes  1.10 Gbits/sec
[SUM]  0.0-10.0 sec  4.82 GBytes  4.12 Gbits/sec
mininet> h4 iperf -c h1 -t 10 -P 4
------------------------------------------------------------
Client connecting to 10.0.0.1, TCP port 5001
TCP window size: 85.3 KByte (default)
------------------------------------------------------------
[  3] local 10.0.0.4 port 47366 connected with 10.0.0.1 port 5001
[  5] local 10.0.0.4 port 47370 connected with 10.0.0.1 port 5001
[  6] local 10.0.0.4 port 47372 connected with 10.0.0.1 port 5001
[  4] local 10.0.0.4 port 47368 connected with 10.0.0.1 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  1.06 GBytes   912 Mbits/sec
[  4]  0.0-10.0 sec  1.02 GBytes   872 Mbits/sec
[  5]  0.0-10.0 sec   870 MBytes   728 Mbits/sec
[  6]  0.0-10.0 sec   993 MBytes   831 Mbits/sec
[SUM]  0.0-10.0 sec  3.90 GBytes  3.34 Gbits/sec
mininet> h4 iperf -s &
mininet> h5 iperf -c h4 -t 10 -P 4
------------------------------------------------------------
Client connecting to 10.0.0.4, TCP port 5001
TCP window size: 85.3 KByte (default)
------------------------------------------------------------
[  3] local 10.0.0.5 port 34336 connected with 10.0.0.4 port 5001
[  6] local 10.0.0.5 port 34342 connected with 10.0.0.4 port 5001
[  4] local 10.0.0.5 port 34338 connected with 10.0.0.4 port 5001
[  5] local 10.0.0.5 port 34340 connected with 10.0.0.4 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec   703 MBytes   589 Mbits/sec
^C[  6]  0.0-10.0 sec   846 MBytes   707 Mbits/sec
[  4]  0.0-80.6 sec   737 MBytes  76.7 Mbits/sec
[  5]  0.0-10.0 sec   784 MBytes   656 Mbits/sec
[SUM]  0.0-80.6 sec  3.00 GBytes   319 Mbits/sec
mininet> h6 iperf -s &
mininet> h7 iperf -c h6 -t 10 -P 4
------------------------------------------------------------
Client connecting to 10.0.0.6, TCP port 5001
TCP window size: 85.3 KByte (default)
------------------------------------------------------------
[  3] local 10.0.0.7 port 60870 connected with 10.0.0.6 port 5001
[  5] local 10.0.0.7 port 60874 connected with 10.0.0.6 port 5001
[  6] local 10.0.0.7 port 60876 connected with 10.0.0.6 port 5001
[  4] local 10.0.0.7 port 60872 connected with 10.0.0.6 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec   539 MBytes   451 Mbits/sec
[  4]  0.0-10.0 sec   412 MBytes   346 Mbits/sec
[  5]  0.0-10.0 sec   439 MBytes   368 Mbits/sec
[  6]  0.0-10.0 sec   518 MBytes   432 Mbits/sec
[SUM]  0.0-10.0 sec  1.86 GBytes  1.59 Gbits/sec
```