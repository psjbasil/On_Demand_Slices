from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp
from ryu.topology.api import get_switch, get_link
from ryu.controller import dpset
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import json
from ryu.lib.packet.ether_types import ETH_TYPE_IP, ETH_TYPE_ARP
import threading

class SimpleSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.slices = {}
        self.lock = threading.Lock()  # 使用锁来保护对 slices 的访问
        wsgi = kwargs['wsgi']
        wsgi.register(SimpleSwitchController, {'simple_switch_app': self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 初始流表规则
        self.install_default_flows(datapath)

    def install_default_flows(self, datapath):
        """安装初始流表规则"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 处理 ARP 请求（正常转发）
        match_arp = parser.OFPMatch(eth_type=ETH_TYPE_ARP)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        inst_arp = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions_arp)]
        mod_arp = parser.OFPFlowMod(datapath=datapath, priority=200, match=match_arp, instructions=inst_arp)
        datapath.send_msg(mod_arp)

        # 表尾规则：丢弃其他流量
        match_drop = parser.OFPMatch()
        inst_drop = []  # 无操作
        mod_drop = parser.OFPFlowMod(datapath=datapath, priority=0, match=match_drop, instructions=inst_drop)
        datapath.send_msg(mod_drop)

    def activate_slice(self, slice_name):
        """激活网络切片"""
        with self.lock:
            if slice_name in self.slices:
                return {"status": "error", "message": f"Slice '{slice_name}' is already activated"}, 409

            try:
                with open("/tmp/topology.json", "r") as f:
                    topology_data = json.load(f)
            except FileNotFoundError:
                return {"status": "error", "message": "Topology file not found"}, 404
            except json.JSONDecodeError:
                return {"status": "error", "message": "Invalid JSON format in topology file"}, 400

            slices_data = topology_data.get("slices", {})
            host_ips = topology_data.get("hosts", {})

            if slice_name not in slices_data:
                return {"status": "error", "message": f"No such slice: {slice_name}"}, 404

            # 获取切片内主机 IP
            hosts_in_slice = slices_data[slice_name]
            host_ip_list = [host_ips[host] for host in hosts_in_slice]

            self.slices[slice_name] = []
            for dp in self.dpset.dps.values():
                ofproto = dp.ofproto
                parser = dp.ofproto_parser

                for src_ip in host_ip_list:
                    for dst_ip in host_ip_list:
                        if src_ip == dst_ip:
                            continue  # 跳过源IP和目标IP相同的规则
                        match = parser.OFPMatch(eth_type=ETH_TYPE_IP, ipv4_src=src_ip, ipv4_dst=dst_ip)
                        actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
                        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                        mod = parser.OFPFlowMod(datapath=dp, priority=100, match=match, instructions=inst)
                        dp.send_msg(mod)

                self.slices[slice_name].append(dp.id)

            return {"status": "success", "message": f"Slice '{slice_name}' activated successfully"}, 200

    def deactivate_slice(self, slice_name):
        """停用网络切片"""
        with self.lock:
            if slice_name not in self.slices:
                return {"status": "error", "message": f"No such slice: {slice_name}"}, 404

            try:
                with open("/tmp/topology.json", "r") as f:
                    topology_data = json.load(f)
            except FileNotFoundError:
                return {"status": "error", "message": "Topology file not found"}, 404
            except json.JSONDecodeError:
                return {"status": "error", "message": "Invalid JSON format in topology file"}, 400

            slices_data = topology_data.get("slices", {})
            host_ips = topology_data.get("hosts", {})

            if slice_name not in slices_data:
                return {"status": "error", "message": f"No such slice: {slice_name}"}, 404

            host_ip_list = [host_ips[host] for host in slices_data[slice_name]]

            for dp_id in self.slices[slice_name]:
                dp = self.dpset.get(dp_id)
                if dp is None:
                    continue

                ofproto = dp.ofproto
                parser = dp.ofproto_parser

                for src_ip in host_ip_list:
                    for dst_ip in host_ip_list:
                        if src_ip == dst_ip:
                            continue  # 跳过源IP和目标IP相同的规则
                        match = parser.OFPMatch(eth_type=ETH_TYPE_IP, ipv4_src=src_ip, ipv4_dst=dst_ip)
                        mod = parser.OFPFlowMod(
                            datapath=dp,
                            command=ofproto.OFPFC_DELETE,
                            out_port=ofproto.OFPP_ANY,
                            out_group=ofproto.OFPG_ANY,
                            match=match
                        )
                        dp.send_msg(mod)

            del self.slices[slice_name]
            return {"status": "success", "message": f"Slice '{slice_name}' deactivated successfully"}, 200

class SimpleSwitchController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SimpleSwitchController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data['simple_switch_app']

    @route('simpleswitch', '/simpleswitch/activate_slice', methods=['POST'])
    def activate_slice(self, req, **kwargs):
        try:
            body = json.loads(req.body.decode())
            slice_name = body.get('slice_name')
            if not slice_name:
                return Response(status=400, content_type='application/json; charset=utf-8', body=json.dumps({"status": "error", "message": "Missing slice_name"}))

            result, status_code = self.simple_switch_app.activate_slice(slice_name)
            return Response(status=status_code, content_type='application/json; charset=utf-8', body=json.dumps(result))
        except Exception as e:
            error_message = {"status": "error", "message": str(e)}
            self.logger.error(f"Error activating slice: {json.dumps(error_message)}")
            return Response(status=500, content_type='application/json; charset=utf-8', body=json.dumps(error_message))

    @route('simpleswitch', '/simpleswitch/deactivate_slice', methods=['POST'])
    def deactivate_slice(self, req, **kwargs):
        try:
            body = json.loads(req.body.decode())
            slice_name = body.get('slice_name')
            if not slice_name:
                return Response(status=400, content_type='application/json; charset=utf-8', body=json.dumps({"status": "error", "message": "Missing slice_name"}))

            result, status_code = self.simple_switch_app.deactivate_slice(slice_name)
            return Response(status=status_code, content_type='application/json; charset=utf-8', body=json.dumps(result))
        except Exception as e:
            error_message = {"status": "error", "message": str(e)}
            self.logger.error(f"Error deactivating slice: {json.dumps(error_message)}")
            return Response(status=500, content_type='application/json; charset=utf-8', body=json.dumps(error_message))

