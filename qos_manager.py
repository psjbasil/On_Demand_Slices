"""
QoS Manager for Industrial Network
Handles QoS configuration for different network slices
"""

from mininet.log import info

class QoSManager:
    def __init__(self, total_bandwidth="10G"):  # Changed to accept string format
        """
        Initialize QoS Manager
        Args:
            total_bandwidth: Total available bandwidth (e.g., "10G", "1000M")
        """
        self.TOTAL_BANDWIDTH = self._parse_bandwidth(total_bandwidth)
        
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
        # Remove existing tc rules
        self._clear_existing_qos(net)
        
        # Calculate and apply QoS settings
        host_bandwidths = self._calculate_host_bandwidths(slice_config)
        self._apply_qos_settings(net, host_bandwidths)
    
    def _clear_existing_qos(self, net):
        """
        Remove existing tc rules from all hosts
        Args:
            net: Mininet network instance
        """
        for host in net.hosts:
            host.cmd(f'tc qdisc del dev {host.name}-eth0 root')
            info(f'Cleared existing QoS settings for {host.name}\n')
    
    def _calculate_host_bandwidths(self, slice_config):
        """
        Calculate maximum bandwidth for each host based on slice configurations
        Args:
            slice_config: Dictionary containing slice configurations
        Returns:
            Dictionary mapping host names to their maximum bandwidth
        """
        host_bandwidths = {}
        
        # Calculate bandwidth for each host based on slice membership
        for slice_name, slice_info in slice_config.items():
            slice_bandwidth = self.TOTAL_BANDWIDTH * slice_info["bandwidth_percentage"] / 100
            for host_name in slice_info["hosts"]:
                if host_name not in host_bandwidths:
                    host_bandwidths[host_name] = slice_bandwidth
                else:
                    # If host is in multiple slices, use the maximum bandwidth
                    host_bandwidths[host_name] = max(host_bandwidths[host_name], slice_bandwidth)
        
        return host_bandwidths
    
    def _apply_qos_settings(self, net, host_bandwidths):
        """
        Apply QoS settings to each host
        Args:
            net: Mininet network instance
            host_bandwidths: Dictionary mapping host names to their maximum bandwidth
        """
        for host_name, max_bandwidth in host_bandwidths.items():
            host = net.get(host_name)
            
            # Configure Token Bucket Filter (TBF)
            latency = "20ms"  # Maximum latency before packets are dropped
            burst = f"{int(max_bandwidth/8)}kb"  # Burst size (1ms worth of data)
            
            # Apply tc configuration
            cmd = (f'tc qdisc add dev {host_name}-eth0 root tbf '
                  f'rate {int(max_bandwidth)}mbit burst {burst} latency {latency}')
            host.cmd(cmd)
            
            # Log configuration
            info(f"Configured QoS for {host_name}:\n")
            info(f"  - Maximum bandwidth: {max_bandwidth}Mbps\n")
            info(f"  - Burst size: {burst}\n")
            info(f"  - Latency: {latency}\n")
            
            # Display actual tc configuration
            info(f"TC configuration for {host_name}:\n")
            info(host.cmd(f'tc qdisc show dev {host_name}-eth0') + "\n") 