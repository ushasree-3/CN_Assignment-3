#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController, Host
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.topo import Topo
import time

# --- Topology Definition ---
class NatTopo( Topo ):
    "Final topology with NAT setup using OVS and required configurations."
    def build( self ):
        "Create custom topology."

        # --- IP Configuration ---
        h1_ip = '10.1.1.2/24'
        h2_ip = '10.1.1.3/24'
        h9_private_gw_ip = '10.1.1.1' # Gateway IP for h1, h2 (lives on h9's br0)

        # --- Add Hosts ---
        info( '*** Adding private hosts (h1, h2)\n' )
        h1 = self.addHost( 'h1', ip=h1_ip, defaultRoute=f'via {h9_private_gw_ip}' )
        h2 = self.addHost( 'h2', ip=h2_ip, defaultRoute=f'via {h9_private_gw_ip}' )

        info( '*** Adding NAT gateway host (h9)\n' )
        h9 = self.addHost( 'h9' ) # IPs configured dynamically after start

        info( '*** Adding public hosts (h3-h8)\n' )
        # Routes added dynamically after start
        h3 = self.addHost( 'h3', ip='10.0.0.4/24' )
        h4 = self.addHost( 'h4', ip='10.0.0.5/24' )
        h5 = self.addHost( 'h5', ip='10.0.0.6/24' )
        h6 = self.addHost( 'h6', ip='10.0.0.7/24' )
        h7 = self.addHost( 'h7', ip='10.0.0.8/24' )
        h8 = self.addHost( 'h8', ip='10.0.0.9/24' ) # Ensure no conflict with h9's IPs

        # --- Add Switches (OVS) ---
        info( '*** Adding OVS switches (s1-s4)\n' )
        s1 = self.addSwitch( 's1', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s2 = self.addSwitch( 's2', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s3 = self.addSwitch( 's3', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s4 = self.addSwitch( 's4', cls=OVSKernelSwitch, protocols='OpenFlow13')

        # --- Define Link Options ---
        host_link_opts = dict(delay='5ms')
        switch_link_opts = dict(delay='7ms')

        # --- Add Links ---
        # Link order determines default interface names on h9
        info( '*** Adding links\n' )
        # Public side: h9 to s1 (h9-eth0)
        self.addLink( h9, s1, intfName1='h9-eth0', **host_link_opts )
        # Private side: h1 to h9 (h9-eth1), h2 to h9 (h9-eth2)
        self.addLink( h1, h9, intfName1='h1-eth0', intfName2='h9-eth1', **host_link_opts )
        self.addLink( h2, h9, intfName1='h2-eth0', intfName2='h9-eth2', **host_link_opts )

        # Original public hosts to switches
        self.addLink( h3, s2, **host_link_opts )
        self.addLink( h4, s2, **host_link_opts )
        self.addLink( h5, s3, **host_link_opts )
        self.addLink( h6, s3, **host_link_opts )
        self.addLink( h7, s4, **host_link_opts )
        self.addLink( h8, s4, **host_link_opts )

        # Original Switch to Switch Links (maintain loops for STP)
        self.addLink( s1, s2, **switch_link_opts )
        self.addLink( s2, s3, **switch_link_opts )
        self.addLink( s3, s4, **switch_link_opts )
        self.addLink( s4, s1, **switch_link_opts )
        self.addLink( s1, s3, **switch_link_opts )


# --- NAT Configuration Function ---
def configureNATNode( natNode, publicIP, publicIntf, publicSubnetIP,
                      privateIP, privateIntf1, privateIntf2, privateSubnet ):
    """Configure the NAT node (h9) with an internal bridge, NAT, and forwarding."""

    info(f'*** Configuring NAT gateway {natNode.name}\n')

    # 1. Create bridge on h9 for private network
    info(f'   Creating bridge br0 on {natNode.name}\n')
    natNode.cmd('brctl addbr br0')

    # 2. Add private interfaces to the bridge
    info(f'   Adding interfaces {privateIntf1}, {privateIntf2} to br0\n')
    natNode.cmd(f'brctl addif br0 {privateIntf1}')
    natNode.cmd(f'brctl addif br0 {privateIntf2}')

    # 3. Assign private gateway IP to the bridge interface
    info(f'   Assigning Private IP {privateIP} to br0\n')
    natNode.cmd(f'ip addr add {privateIP} dev br0')

    # 4. Bring up the bridge and associated physical private interfaces
    info(f'   Bringing up interfaces br0, {privateIntf1}, {privateIntf2}\n')
    natNode.cmd(f'ip link set dev {privateIntf1} up')
    natNode.cmd(f'ip link set dev {privateIntf2} up')
    natNode.cmd(f'ip link set dev br0 up')

    # 5. Assign public IP(s) to the physical public interface
    info(f'   Assigning Public IP {publicIP} to {publicIntf}\n')
    natNode.cmd(f'ip addr add {publicIP} dev {publicIntf}')
    if publicSubnetIP:
      info(f'   Assigning Public Subnet IP {publicSubnetIP} to {publicIntf}\n')
      natNode.cmd(f'ip addr add {publicSubnetIP} dev {publicIntf}')
    natNode.cmd(f'ip link set dev {publicIntf} up')

    # 6. Enable IP forwarding on h9
    info(f'   Enabling IP forwarding on {natNode.name}\n')
    natNode.cmd( 'sysctl -w net.ipv4.ip_forward=1' )

    # 7. Add route on h9 to reach the 'external' 10.0.0.0/24 network (if needed)
    # This should be handled implicitly if publicSubnetIP (e.g., 10.0.0.10/24) is set.
    # No explicit route command needed here if using the secondary IP approach.

    # 8. Configure iptables for NAT and Forwarding
    info('   Configuring iptables rules...\n')
    natNode.cmd('iptables -F')          # Flush filter table FORWARD chain
    natNode.cmd('iptables -t nat -F')   # Flush nat table chains (PREROUTING, POSTROUTING)

    # --- NAT Rule (Handles Outbound: h1/h2 -> Public) ---
    info('      Adding MASQUERADE rule for outbound traffic\n')
    natNode.cmd(f'iptables -t nat -A POSTROUTING -s {privateSubnet} -o {publicIntf} -j MASQUERADE')

    # --- FORWARDING Rules (Control traffic passing THROUGH h9) ---
    info('      Adding FORWARD rules\n')
    # Allow return traffic for connections initiated from private side
    natNode.cmd(f'iptables -A FORWARD -i {publicIntf} -o br0 -m state --state RELATED,ESTABLISHED -j ACCEPT')
    # Allow all outbound traffic from private side to public side
    natNode.cmd(f'iptables -A FORWARD -i br0 -o {publicIntf} -j ACCEPT')
    # Allow incoming ICMP Echo Requests (Ping) from public side to private side
    info('      Allowing incoming ICMP Echo Requests (ping)\n')
    natNode.cmd(f'iptables -A FORWARD -i {publicIntf} -o br0 -p icmp --icmp-type echo-request -j ACCEPT')

    # --- Port Forwarding for iperf3 (h6 -> h1 on port 5201) ---
    info('      Adding Port Forwarding for h1 (iperf3 port 5201)\n')
    h1_private_ip = privateSubnet.split('.')[0:3] + ['2'] # Derive 10.1.1.2
    h1_private_ip = '.'.join(h1_private_ip)
    # DNAT rule: Rewrite destination for incoming packets
    natNode.cmd(f'iptables -t nat -A PREROUTING -i {publicIntf} -p tcp --dport 5201 -j DNAT --to-destination {h1_private_ip}:5201')
    # Allow forwarding of these specific packets after DNAT
    natNode.cmd(f'iptables -A FORWARD -i {publicIntf} -o br0 -p tcp -d {h1_private_ip} --dport 5201 -j ACCEPT')

    info(f'*** NAT/Firewall configuration on {natNode.name} complete\n')


# --- Main Execution ---
def run():
    "Create and run the network with NAT and STP."
    topo = NatTopo()

    info( '*** Creating network\n' )
    net = Mininet( topo=topo,
                   link=TCLink,
                   controller=lambda name: RemoteController( name, ip='127.0.0.1', port=6633 ),
                   switch=OVSKernelSwitch,
                   autoSetMacs=True,
                   host=Host ) # Using default Host

    info( '*** Starting network\n')
    net.start()

    # --- OVS STP Configuration ---
    info( '*** Enabling STP on OVS switches s1-s4\n')
    for sw_name in ['s1', 's2', 's3', 's4']:
        switch = net.get(sw_name)
        switch.cmd(f'ovs-vsctl set bridge {sw_name} stp_enable=true')
        info(f'   Enabled STP on {sw_name}')
    info( '*** Waiting for STP convergence (approx. 45 seconds)...\n')
    time.sleep(45) # Adjust if needed, but crucial
    # --- End STP Configuration ---

    # --- Define IPs and Interfaces for NAT Node ---
    # Ensure these IPs don't conflict with other hosts
    h9_public_ip_primary = '172.16.10.10/24' # The "official" public IP
    h9_public_ip_secondary = '10.0.0.10/24' # IP on same subnet as h3-h8 for routing
    h9_private_ip_bridge = '10.1.1.1/24'    # IP for the internal bridge br0
    private_subnet_cidr = '10.1.1.0/24'
    # Interface names determined by link order in build()
    h9_public_interface = 'h9-eth0'
    h9_private_interface1 = 'h9-eth1'
    h9_private_interface2 = 'h9-eth2'

    # --- Configure NAT Node h9 ---
    h9 = net.get('h9')
    configureNATNode(
        natNode = h9,
        publicIP = h9_public_ip_primary,
        publicSubnetIP = h9_public_ip_secondary,
        privateIP = h9_private_ip_bridge,
        publicIntf = h9_public_interface,
        privateIntf1 = h9_private_interface1,
        privateIntf2 = h9_private_interface2,
        privateSubnet = private_subnet_cidr
    )
    # --- End NAT Configuration ---

    # --- Add Routes on Public Hosts (h3-h8) for Return Traffic ---
    info('*** Adding static routes on public hosts (h3-h8) to reach private subnet\n')
    # Gateway is h9's IP on the 10.0.0.0/24 network
    h9_lan_gateway_ip = h9_public_ip_secondary.split('/')[0] # e.g., 10.0.0.10
    for h_name in ['h3', 'h4', 'h5', 'h6', 'h7', 'h8']:
        host = net.get(h_name)
        # Add route to the private network via h9's secondary public IP
        host.cmd(f'ip route add {private_subnet_cidr} via {h9_lan_gateway_ip}')
        info(f'   Route to {private_subnet_cidr} via {h9_lan_gateway_ip} added on {h_name}')
    # --- End Static Routes ---

    # Add a small delay to ensure configurations settle
    info('*** Waiting briefly for configurations to settle...\n')
    time.sleep(5)

    # --- Force ARP Entry for h8 to reach h9's Gateway IP ---
    info('*** Adding static ARP entry on h8 for h9 gateway\n')
    h8_node = net.get('h8')
    h9_node = net.get('h9')
    h9_lan_gateway_ip = '10.0.0.10' # Defined earlier
    h9_public_interface = 'h9-eth0' # Defined earlier
    # Get h9's MAC address on the public interface
    h9_public_mac = h9_node.MAC(intf=h9_public_interface)
    if h9_public_mac:
        h8_node.cmd(f'arp -s {h9_lan_gateway_ip} {h9_public_mac}')
        info(f'   Static ARP for {h9_lan_gateway_ip} -> {h9_public_mac} added on h8')
    else:
        info(f'   Warning: Could not get MAC for {h9_node.name} interface {h9_public_interface}')
    # --- End Static ARP Entry ---


    info( '*** Running CLI - Test commands listed in Q2\n' )
    CLI( net )

    # ... (rest of the cleanup code) ...

if __name__ == '__main__':
    setLogLevel( 'info' )
    run()
