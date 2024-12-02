from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
import json

class IndustrialTopo(Topo):
    def build(self):
        # 添加主交换机
        s1 = self.addSwitch('s1', cls=OVSSwitch)

        # 添加生产控制系统交换机及其连接的主机
        s2 = self.addSwitch('s2', cls=OVSSwitch)
        h1 = self.addHost('h1', ip='10.0.0.1/24')  # 生产控制系统服务器
        h2 = self.addHost('h2', ip='10.0.0.2/24')  # 生产控制设备1
        h3 = self.addHost('h3', ip='10.0.0.3/24')  # 生产控制设备2
        self.addLink(h1, s2)
        self.addLink(h2, s2)
        self.addLink(h3, s2)
        self.addLink(s2, s1)

        # 添加监控和维护系统交换机及其连接的主机
        s3 = self.addSwitch('s3', cls=OVSSwitch)
        h4 = self.addHost('h4', ip='10.0.0.4/24')  # 监控和维护服务器
        h5 = self.addHost('h5', ip='10.0.0.5/24')  # 监控设备
        self.addLink(h4, s3)
        self.addLink(h5, s3)
        self.addLink(s3, s1)

        # 添加办公网络交换机及其连接的主机
        s4 = self.addSwitch('s4', cls=OVSSwitch)
        h6 = self.addHost('h6', ip='10.0.0.6/24')  # 办公电脑1
        h7 = self.addHost('h7', ip='10.0.0.7/24')  # 办公电脑2
        h8 = self.addHost('h8', ip='10.0.0.8/24')  # 打印机
        self.addLink(h6, s4)
        self.addLink(h7, s4)
        self.addLink(h8, s4)
        self.addLink(s4, s1)

def run_mininet():
    topo = IndustrialTopo()
    net = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633))

    net.start()

    # 保存拓扑数据到文件
    nodes = topo.nodes()
    links = topo.links()
    host_ips = {host.name: host.IP() for host in net.hosts}
    slices_data = {
        "production_control": ["h1", "h2", "h3"],
        "monitoring_maintenance": ["h4", "h5"],
        "office_network": ["h6", "h7", "h8"]
    }
    topology_data = {
        "nodes": [{"id": node} for node in nodes],
        "links": [{"source": link[0], "target": link[1]} for link in links],
        "hosts": host_ips,
        "slices": slices_data
    }
    with open("/tmp/topology.json", "w") as f:
        json.dump(topology_data, f)

    print("Topology data saved to /tmp/topology.json")

    # 进入 Mininet CLI
    CLI(net)

    net.stop()

# 添加 topos 字典
topos = {'industrialtopo': (lambda: IndustrialTopo())}

if __name__ == '__main__':
    setLogLevel('info')
    run_mininet()
