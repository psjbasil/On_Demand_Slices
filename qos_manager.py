"""
QoS Manager for Industrial Network
Handles QoS configuration for different network slices using HTB
"""

from mininet.log import info
import json
import time

class QoSManager:
    def __init__(self, total_bandwidth="10G"):
        """
        Initialize QoS Manager
        Args:
            total_bandwidth: Total available bandwidth (e.g., "10G", "1000M")
        """
        self.TOTAL_BANDWIDTH = self._parse_bandwidth(total_bandwidth)
        info(f"Total bandwidth set to: {self.TOTAL_BANDWIDTH}Mbps\n")
        
    def _parse_bandwidth(self, bw_str):
        """
        Convert bandwidth string to Mbps
        Args:
            bw_str: Bandwidth string (e.g., "10G", "100M", "1000K")
        Returns:
            int: Bandwidth in Mbps
        """
        if isinstance(bw_str, (int, float)):
            return int(bw_str)
            
        value = int(bw_str[:-1])
        unit = bw_str[-1].upper()
        if unit == 'G':
            return value * 1000
        elif unit == 'M':
            return value
        elif unit == 'K':
            return value / 1000
        return value
    
    def configure_qos(self, net, slice_config):
        """
        Configure QoS parameters for all hosts based on slice configurations
        Args:
            net: Mininet network instance
            slice_config: Dictionary containing slice configurations
        """
        # Wait for topology file to be created
        max_retries = 5
        for i in range(max_retries):
            try:
                with open("/tmp/topology.json", "r") as f:
                    self.topology_data = json.load(f)
                break
            except FileNotFoundError:
                if i < max_retries - 1:
                    info(f"Waiting for topology file, retry {i+1}/{max_retries}\n")
                    time.sleep(1)
                else:
                    info("Error: Could not find topology file\n")
                    return

        # Remove existing tc rules
        self._clear_existing_qos(net)
        
        # Calculate slice bandwidths and host memberships
        slice_bandwidths = self._calculate_slice_bandwidths(slice_config)
        host_slices = self._get_host_slices(slice_config)
        
        # Apply HTB configuration to each host
        self._apply_htb_settings(net, slice_bandwidths, host_slices, slice_config)
    
    def _clear_existing_qos(self, net):
        """
        Remove existing tc rules from all hosts
        Args:
            net: Mininet network instance
        """
        for host in net.hosts:
            host.cmd(f'tc qdisc del dev {host.name}-eth0 root')
            info(f'Cleared existing QoS settings for {host.name}\n')
    
    def _calculate_slice_bandwidths(self, slice_config):
        """
        Calculate bandwidth for each slice based on percentage
        Returns: Dictionary mapping slice names to their bandwidth
        """
        slice_bandwidths = {}
        for slice_name, slice_info in slice_config.items():
            bandwidth = self.TOTAL_BANDWIDTH * slice_info["bandwidth_percentage"] / 100
            slice_bandwidths[slice_name] = bandwidth
            info(f"Slice {slice_name} bandwidth: {bandwidth}Mbps "
                 f"({slice_info['bandwidth_percentage']}% of total)\n")
        return slice_bandwidths
    
    def _get_host_slices(self, slice_config):
        """
        Get all slices that each host belongs to
        Returns: Dictionary mapping host names to list of slice names
        """
        host_slices = {}
        for slice_name, slice_info in slice_config.items():
            for host in slice_info["hosts"]:
                if host not in host_slices:
                    host_slices[host] = []
                host_slices[host].append(slice_name)
        return host_slices
    
    def _apply_htb_settings(self, net, slice_bandwidths, host_slices, slice_config):
        """
        Apply HTB qdisc and class configuration to each host
        """
        priority_map = {"high": 1, "medium": 2, "low": 3}
        
        for host_name, slices in host_slices.items():
            host = net.get(host_name)
            
            # Clear any existing tc configuration
            host.cmd(f'tc qdisc del dev {host_name}-eth0 root')
            
            # Create root HTB qdisc with default class
            host.cmd(f'tc qdisc add dev {host_name}-eth0 root handle 1: htb default 999')
            
            # Calculate total bandwidth for this host
            total_bw = sum(slice_bandwidths[slice_name] for slice_name in slices)
            total_bw_kbps = int(total_bw * 1000)  # Convert to kbps
            
            # Calculate burst size (reduced to 10ms at rate for better control)
            burst = int(total_bw_kbps * 0.01)  # 10ms worth of data
            
            # Create root class with total bandwidth
            host.cmd(f'tc class add dev {host_name}-eth0 parent 1: classid 1:1 htb '
                    f'rate {total_bw_kbps}kbit ceil {total_bw_kbps}kbit '
                    f'burst {burst}k cburst {burst}k')
            
            # Create default class with minimal bandwidth
            host.cmd(f'tc class add dev {host_name}-eth0 parent 1:1 classid 1:999 htb '
                    f'rate 1000kbit ceil {total_bw_kbps}kbit burst 16k cburst 16k')
            
            # Create classes for each slice this host belongs to
            for i, slice_name in enumerate(slices, start=1):
                class_id = i * 10
                bandwidth = slice_bandwidths[slice_name]
                bandwidth_kbps = int(bandwidth * 1000)  # Convert to kbps
                slice_burst = int(bandwidth_kbps * 0.01)  # 10ms worth of data
                priority = priority_map.get(slice_config[slice_name]["priority"], 3)
                
                # Add HTB class for the slice with tighter burst control
                host.cmd(f'tc class add dev {host_name}-eth0 parent 1:1 classid 1:{class_id} htb '
                        f'rate {bandwidth_kbps}kbit ceil {bandwidth_kbps}kbit '
                        f'burst {slice_burst}k cburst {slice_burst}k prio {priority}')
                
                # Add fq_codel qdisc with shorter target and interval
                host.cmd(f'tc qdisc add dev {host_name}-eth0 parent 1:{class_id} handle {class_id}: '
                        f'fq_codel flows 1024 quantum 1514 target 1ms interval 20ms memory_limit 256k')
                
                # Add filters for each destination in the slice
                for other_host in slice_config[slice_name]["hosts"]:
                    if other_host != host_name:
                        other_ip = self.topology_data["hosts"][other_host]
                        host.cmd(f'tc filter add dev {host_name}-eth0 protocol ip parent 1: '
                                f'prio {priority} u32 match ip dst {other_ip} flowid 1:{class_id}')
            
            # Add ICMP and ARP filters to default class
            host.cmd(f'tc filter add dev {host_name}-eth0 protocol ip parent 1: '
                    f'prio 9 u32 match ip protocol 1 0xff flowid 1:999')
            host.cmd(f'tc filter add dev {host_name}-eth0 protocol arp parent 1: '
                    f'prio 9 u32 match u32 0 0 flowid 1:999')
            
            # Log configuration
            info(f"\nConfigured HTB QoS for {host_name}:\n")
            info(f"  - Total bandwidth: {total_bw}Mbps ({total_bw_kbps}kbps)\n")
            info(f"  - Member of slices: {', '.join(slices)}\n")
            for slice_name in slices:
                info(f"  - Slice {slice_name}: {slice_bandwidths[slice_name]}Mbps "
                     f"(Priority: {slice_config[slice_name]['priority']})\n")
            
            info("\nHTB Class Configuration:\n")
            info(host.cmd(f'tc -s class show dev {host_name}-eth0') + "\n")
            info("Queue Disciplines:\n")
            info(host.cmd(f'tc -s qdisc show dev {host_name}-eth0') + "\n")
            info("Filters:\n")
            info(host.cmd(f'tc -s filter show dev {host_name}-eth0') + "\n") 