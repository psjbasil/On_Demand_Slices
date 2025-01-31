from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import json
from qos_manager import QoSManager

class IndustrialTopo(Topo):
    """
    Industrial Network Topology
    Defines the network structure with switches, hosts, and slice configurations
    """
    def __init__(self):
        # Initialize configuration before super().__init__()
        self.config = {
            # Switch definitions with descriptions
            "switches": {
                "s1": "Core Switch",
                "s2": "Production Area Switch",
                "s3": "Monitoring Area Switch",
                "s4": "Office Area Switch"
            },
            # Host definitions with IP addresses and descriptions
            "hosts": {
                "h1": {"ip": "10.0.0.1/24", "description": "PLC Controller"},
                "h2": {"ip": "10.0.0.2/24", "description": "Industrial Robot"},
                "h3": {"ip": "10.0.0.3/24", "description": "Automated Production Line"},
                "h4": {"ip": "10.0.0.4/24", "description": "Monitoring Server"},
                "h5": {"ip": "10.0.0.5/24", "description": "Data Collection Device"},
                "h6": {"ip": "10.0.0.6/24", "description": "Engineer Workstation"},
                "h7": {"ip": "10.0.0.7/24", "description": "Management Terminal"},
                "h8": {"ip": "10.0.0.8/24", "description": "Remote Access Terminal"}
            },
            # Network slice definitions
            "slices": {
                "production_control": {
                    "hosts": ["h1", "h2", "h3"],
                    "bandwidth_percentage": 50,
                    "priority": "high",
                    "description": "Production control slice for industrial control systems"
                },
                "monitoring_maintenance": {
                    "hosts": ["h4", "h5"],
                    "bandwidth_percentage": 30,
                    "priority": "medium",
                    "description": "Monitoring and maintenance slice for system monitoring"
                },
                "office_access": {
                    "hosts": ["h6", "h7", "h8"],
                    "bandwidth_percentage": 20,
                    "priority": "low",
                    "description": "Office network slice for daily office access"
                },
                "emergency_response": {
                    "hosts": ["h1", "h4", "h6"],
                    "bandwidth_percentage": 40,
                    "priority": "high",
                    "description": "Emergency response slice for cross-area urgent communication"
                }
            }
        }
        # Call super().__init__() after initializing config
        super(IndustrialTopo, self).__init__()

    def build(self):
        """Build the network topology"""
        # Create switches
        for switch_id, description in self.config["switches"].items():
            self.addSwitch(switch_id)

        # Create hosts with their IP addresses
        for host_id, host_info in self.config["hosts"].items():
            self.addHost(host_id, ip=host_info["ip"])

        # Add core switch links
        self.addLink('s1', 's2')  # Core to production
        self.addLink('s1', 's3')  # Core to monitoring
        self.addLink('s1', 's4')  # Core to office

        # Define host groups by area
        production_hosts = ['h1', 'h2', 'h3']
        monitoring_hosts = ['h4', 'h5']
        office_hosts = ['h6', 'h7', 'h8']

        # Connect hosts to their respective area switches
        for host in production_hosts:
            self.addLink('s2', host)
        for host in monitoring_hosts:
            self.addLink('s3', host)
        for host in office_hosts:
            self.addLink('s4', host)

    def configure_qos(self, net):
        """Configure QoS parameters for all hosts"""
        qos_manager = QoSManager(total_bandwidth="10G")  # Using string format
        qos_manager.configure_qos(net, self.config["slices"])

def run_mininet():
    """Initialize and run the Mininet network"""
    topo = IndustrialTopo()
    
    # Wait for controller to start
    info('*** Waiting for controller at 127.0.0.1:6633 ...\n')
    
    # Create Mininet instance
    net = Mininet(
        topo=topo, 
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633),
        autoSetMacs=True,
        waitConnected=True
    )
    
    try:
        net.start()
        
        # Configure QoS settings
        info('*** Configuring QoS ...\n')
        topo.configure_qos(net)
        
        # Generate and save topology data for the controller
        topology_data = {
            "nodes": [
                {"id": switch_id, "type": "switch", "description": desc}
                for switch_id, desc in topo.config["switches"].items()
            ] + [
                {"id": host_id, "type": "host", "description": info["description"]}
                for host_id, info in topo.config["hosts"].items()
            ],
            "links": [{"source": link[0], "target": link[1], "capacity": 1000 if 's1' in link else 100} 
                     for link in topo.links()],
            "hosts": {host_id: info["ip"].split('/')[0] for host_id, info in topo.config["hosts"].items()},
            "slices": topo.config["slices"]
        }
        
        # Save topology data to file
        try:
            with open("/tmp/topology.json", "w") as f:
                json.dump(topology_data, f, indent=4)
            info("*** Topology data saved to /tmp/topology.json\n")
        except Exception as e:
            info(f"*** Error saving topology data: {str(e)}\n")

        info('*** Running CLI\n')
        CLI(net)
    finally:
        info('*** Stopping network\n')
        net.stop()

topos = {'industrialtopo': IndustrialTopo}

if __name__ == '__main__':
    setLogLevel('info')
    run_mininet()