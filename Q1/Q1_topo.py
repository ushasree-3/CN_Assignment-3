#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController 
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.topo import Topo
import time # Required for sleep

class CustomTopo( Topo ):
    "Custom topology with specific latencies."
    def build( self ):
        "Create custom topo."

        # Add Hosts
        info( '*** Adding hosts\n' )
        h1 = self.addHost( 'h1', ip='10.0.0.2/24' )
        h2 = self.addHost( 'h2', ip='10.0.0.3/24' )
        h3 = self.addHost( 'h3', ip='10.0.0.4/24' )
        h4 = self.addHost( 'h4', ip='10.0.0.5/24' )
        h5 = self.addHost( 'h5', ip='10.0.0.6/24' )
        h6 = self.addHost( 'h6', ip='10.0.0.7/24' )
        h7 = self.addHost( 'h7', ip='10.0.0.8/24' )
        h8 = self.addHost( 'h8', ip='10.0.0.9/24' )

        # Add Switches
        info( '*** Adding switches\n' )
        # Specifying protocols='OpenFlow13' is good practice when using a specific controller version
        s1 = self.addSwitch( 's1', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s2 = self.addSwitch( 's2', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s3 = self.addSwitch( 's3', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s4 = self.addSwitch( 's4', cls=OVSKernelSwitch, protocols='OpenFlow13')

        # Define Link Options
        host_link_opts = dict(delay='5ms')
        switch_link_opts = dict(delay='7ms')

        # Add Links
        info( '*** Adding links\n' )
        # Host to Switch Links
        self.addLink( h1, s1, **host_link_opts )
        self.addLink( h2, s1, **host_link_opts )
        self.addLink( h3, s2, **host_link_opts )
        self.addLink( h4, s2, **host_link_opts )
        self.addLink( h5, s3, **host_link_opts )
        self.addLink( h6, s3, **host_link_opts )
        self.addLink( h7, s4, **host_link_opts )
        self.addLink( h8, s4, **host_link_opts )
        # Switch to Switch Links
        self.addLink( s1, s2, **switch_link_opts )
        self.addLink( s2, s3, **switch_link_opts )
        self.addLink( s3, s4, **switch_link_opts )
        self.addLink( s4, s1, **switch_link_opts )
        self.addLink( s1, s3, **switch_link_opts ) # The diagonal link creating loops


def run():
    "Create and run the network."
    topo = CustomTopo()

    info( '*** Creating network\n' )
    # Connect to the external controller (like ovs-testcontroller)
    # Assumes controller is running on 127.0.0.1:6633
    net = Mininet( topo=topo,
                   link=TCLink, # Use TCLink for latency settings
                   controller=lambda name: RemoteController( name, ip='127.0.0.1', port=6633 ),
                   switch=OVSKernelSwitch, # Use OVSKernelSwitch
                   autoSetMacs=True) # Assign MACs automatically


    info( '*** Starting network\n')
    net.start()

    # *** ENABLE OVS INTERNAL STP ***
    # This is ESSENTIAL for handling loops when the controller doesn't do it.
    info( '*** Enabling STP on OVS switches\n')
    for sw_name in ['s1', 's2', 's3', 's4']:
        switch = net.get(sw_name)
        # Use ovs-vsctl to enable STP on the bridge associated with the switch
        switch.cmd(f'ovs-vsctl set bridge {sw_name} stp_enable=true')
        info(f'Enabled STP on {sw_name}')

    # *** WAIT FOR STP CONVERGENCE ***
    # This is ESSENTIAL. STP needs time to figure out the topology and block ports.
    info( '*** Waiting for STP convergence (approx. 45 seconds)...\n')
    time.sleep(45) # Adjust delay if needed, but ~30-60s is typical for STP convergence

    # Start the Mininet Command Line Interface
    info( '*** Running CLI\n' )
    CLI( net )

    # Stop the network and cleanup
    info( '*** Stopping network\n' )
    # Optional but good practice: disable STP before stopping Mininet
    # This prevents leaving STP enabled on the OVS bridges if the script exits abruptly
    for sw_name in ['s1', 's2', 's3', 's4']:
         try:
             switch = net.get(sw_name)
             switch.cmd(f'ovs-vsctl set bridge {sw_name} stp_enable=false')
         except:
             pass # Ignore errors during cleanup if switch doesn't exist
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    run()
