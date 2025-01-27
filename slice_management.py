"""
SDN Controller Application for Network Slice Management
Handles slice activation, deactivation, and flow rule installation
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (
    MAIN_DISPATCHER, 
    CONFIG_DISPATCHER, 
    DEAD_DISPATCHER,
    set_ev_cls
)
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp, ether_types
from ryu.topology.api import get_switch, get_link
from ryu.controller import dpset
from ryu.app.wsgi import WSGIApplication, ControllerBase, Response, route
import json
import threading
import time

class SimpleSwitchController(ControllerBase):
    """
    WSGI Controller for Network Slice Management
    Provides REST API endpoints for slice operations
    """
    def __init__(self, req, link, data, **config):
        super(SimpleSwitchController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data['simple_switch_app']

    @route('simpleswitch', '/simpleswitch/activate_slice', methods=['POST'])
    def activate_slice(self, req, **kwargs):
        """
        REST API endpoint to activate a network slice
        Args:
            req: HTTP request containing slice_name
        Returns:
            HTTP response with activation status
        """
        try:
            body = json.loads(req.body.decode())
            slice_name = body.get('slice_name')
            if not slice_name:
                return Response(status=400, body=json.dumps({"error": "Missing slice_name"}))

            with self.simple_switch_app.lock:
                # Check if slice is already activated
                if slice_name in self.simple_switch_app.slices:
                    return Response(status=409, 
                                  body=json.dumps({"error": f"Slice '{slice_name}' is already activated"}))

                # Read topology file
                with open("/tmp/topology.json", "r") as f:
                    topology_data = json.load(f)
                
                if slice_name not in topology_data["slices"]:
                    return Response(status=400, 
                                  body=json.dumps({"error": "Invalid slice configuration"}))

                # Store slice info
                self.simple_switch_app.slices[slice_name] = topology_data["slices"][slice_name]
                self.simple_switch_app.logger.info(f"Starting to activate slice: {slice_name}")
                
                # Install flow rules
                self.simple_switch_app._install_slice_flows(slice_name)
                
                return Response(status=200,
                              body=json.dumps({"message": f"Slice '{slice_name}' activated successfully"}))

        except Exception as e:
            return Response(status=500, body=json.dumps({"error": str(e)}))

    @route('simpleswitch', '/simpleswitch/deactivate_slice', methods=['POST'])
    def deactivate_slice(self, req, **kwargs):
        """
        REST API endpoint to deactivate a network slice
        Args:
            req: HTTP request containing slice_name
        Returns:
            HTTP response with deactivation status
        """
        try:
            body = json.loads(req.body.decode())
            slice_name = body.get('slice_name')
            if not slice_name:
                return Response(status=400, body=json.dumps({"error": "Missing slice_name"}))

            with self.simple_switch_app.lock:
                if slice_name not in self.simple_switch_app.slices:
                    return Response(status=404,
                                  body=json.dumps({"error": f"Slice '{slice_name}' is not activated"}))

                # Remove flow rules
                self.simple_switch_app._remove_slice_flows(slice_name)
                
                # Remove from active slices
                del self.simple_switch_app.slices[slice_name]
                
                return Response(status=200,
                              body=json.dumps({"message": f"Slice '{slice_name}' deactivated successfully"}))

        except Exception as e:
            return Response(status=500, body=json.dumps({"error": str(e)}))

class SimpleSwitch(app_manager.RyuApp):
    """
    Main SDN Controller Application
    Manages network slices and OpenFlow rules
    """
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        """Initialize the controller application"""
        super(SimpleSwitch, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.slices = {}
        self.datapaths = {}
        self.lock = threading.Lock()
        wsgi = kwargs['wsgi']
        wsgi.register(SimpleSwitchController, {'simple_switch_app': self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Handle switch feature events
        Install default flow rules when a switch connects
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install initial flow rules
        self.install_default_flows(datapath)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        """Handle switch connection state changes"""
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info(f'Register datapath: {datapath.id}')
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info(f'Unregister datapath: {datapath.id}')
                del self.datapaths[datapath.id]

    def install_default_flows(self, datapath):
        """
        Install initial flow rules:
        1. ARP packets: normal forwarding (priority 200)
        2. Default rule: drop all other traffic (priority 0)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Handle ARP requests with normal forwarding
        match_arp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        inst_arp = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions_arp)]
        mod_arp = parser.OFPFlowMod(datapath=datapath, priority=200, match=match_arp, instructions=inst_arp)
        datapath.send_msg(mod_arp)

        # Default rule: drop all other traffic
        match_drop = parser.OFPMatch()
        inst_drop = []  # No actions means drop
        mod_drop = parser.OFPFlowMod(datapath=datapath, priority=0, match=match_drop, instructions=inst_drop)
        datapath.send_msg(mod_drop)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """
        Helper function to add a flow rule to a switch
        Args:
            datapath: Switch to add the flow to
            priority: Priority of the flow rule
            match: Match conditions for the flow
            actions: Actions to take on matching packets
            buffer_id: Buffer ID for packet out (optional)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                           actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                   priority=priority, match=match,
                                   instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                   match=match, instructions=inst)
        datapath.send_msg(mod)

    def _install_slice_flows(self, slice_name):
        """
        Install flow rules for a specific slice
        Args:
            slice_name: Name of the slice to install flows for
        """
        try:
            # Read topology configuration
            with open("/tmp/topology.json", "r") as f:
                topology_data = json.load(f)
            
            slice_info = self.slices.get(slice_name)
            if not slice_info:
                return
            
            # Get slice priority
            priority_map = {"high": 50, "medium": 30, "low": 10}
            priority = priority_map.get(slice_info["priority"], 10)
            
            # Get hosts in this slice
            hosts = slice_info["hosts"]
            
            # Install flows between all hosts in the slice
            for src_host in hosts:
                for dst_host in hosts:
                    if src_host != dst_host:
                        src_ip = topology_data["hosts"][src_host]
                        dst_ip = topology_data["hosts"][dst_host]
                        
                        # Install flow rules on all switches
                        for datapath in self.datapaths.values():
                            parser = datapath.ofproto_parser
                            ofproto = datapath.ofproto
                            
                            match = parser.OFPMatch(
                                eth_type=0x0800,
                                ipv4_src=src_ip,
                                ipv4_dst=dst_ip
                            )
                            
                            actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
                            inst = [parser.OFPInstructionActions(
                                ofproto.OFPIT_APPLY_ACTIONS, actions)]
                            
                            mod = parser.OFPFlowMod(
                                datapath=datapath,
                                priority=priority,
                                match=match,
                                instructions=inst,
                                command=ofproto.OFPFC_ADD,
                                flags=ofproto.OFPFF_SEND_FLOW_REM
                            )
                            datapath.send_msg(mod)
                            
                            self.logger.info(
                                f"Installed flow for {src_ip}->{dst_ip} on switch {datapath.id}")
                    
        except Exception as e:
            self.logger.error(f"Error installing flows for slice {slice_name}: {str(e)}")

    def _remove_slice_flows(self, slice_name):
        """
        Remove flow rules for a specific slice
        Args:
            slice_name: Name of the slice to remove flows for
        """
        try:
            # Read topology configuration
            with open("/tmp/topology.json", "r") as f:
                topology_data = json.load(f)
            
            slice_info = self.slices[slice_name]
            priority_map = {"high": 50, "medium": 30, "low": 10}
            priority = priority_map.get(slice_info["priority"], 10)
            hosts = slice_info["hosts"]

            # Remove flows between all hosts in the slice
            for src_host in hosts:
                for dst_host in hosts:
                    if src_host != dst_host:
                        src_ip = topology_data["hosts"][src_host]
                        dst_ip = topology_data["hosts"][dst_host]

                        for datapath in self.datapaths.values():
                            ofproto = datapath.ofproto
                            parser = datapath.ofproto_parser

                            match = parser.OFPMatch(
                                eth_type=0x0800,
                                ipv4_src=src_ip,
                                ipv4_dst=dst_ip
                            )
                            mod = parser.OFPFlowMod(
                                datapath=datapath,
                                command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_ANY,
                                out_group=ofproto.OFPG_ANY,
                                match=match,
                                priority=priority
                            )
                            datapath.send_msg(mod)
                            self.logger.info(f"Removed flow for {src_ip}->{dst_ip} on switch {datapath.id}")

        except Exception as e:
            self.logger.error(f"Error removing flows for slice {slice_name}: {str(e)}")