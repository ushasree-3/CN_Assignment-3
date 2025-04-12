#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.topo import Topo

class CustomTopo( Topo ):
    def build( self ):
        info( '*** Adding hosts\n' )
        h1 = self.addHost( 'h1', ip='10.0.0.2/24' )
        h2 = self.addHost( 'h2', ip='10.0.0.3/24' )
        h3 = self.addHost( 'h3', ip='10.0.0.4/24' )
        h4 = self.addHost( 'h4', ip='10.0.0.5/24' )
        h5 = self.addHost( 'h5', ip='10.0.0.6/24' )
        h6 = self.addHost( 'h6', ip='10.0.0.7/24' )
        h7 = self.addHost( 'h7', ip='10.0.0.8/24' )
        h8 = self.addHost( 'h8', ip='10.0.0.9/24' )
        info( '*** Adding switches\n' )
        s1 = self.addSwitch( 's1', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s2 = self.addSwitch( 's2', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s3 = self.addSwitch( 's3', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s4 = self.addSwitch( 's4', cls=OVSKernelSwitch, protocols='OpenFlow13')
        host_link_opts = dict(delay='5ms')
        switch_link_opts = dict(delay='7ms')
        info( '*** Adding links\n' )
        self.addLink( h1, s1, **host_link_opts )
        self.addLink( h2, s1, **host_link_opts )
        self.addLink( h3, s2, **host_link_opts )
        self.addLink( h4, s2, **host_link_opts )
        self.addLink( h5, s3, **host_link_opts )
        self.addLink( h6, s3, **host_link_opts )
        self.addLink( h7, s4, **host_link_opts )
        self.addLink( h8, s4, **host_link_opts )
        self.addLink( s1, s2, **switch_link_opts )
        self.addLink( s2, s3, **switch_link_opts )
        self.addLink( s3, s4, **switch_link_opts )
        self.addLink( s4, s1, **switch_link_opts )
        self.addLink( s1, s3, **switch_link_opts ) # The diagonal link


def run():
    topo = CustomTopo()
    info( '*** Creating network\n' )
    net = Mininet( topo=topo,
                   link=TCLink,
                   controller=lambda name: RemoteController( name, ip='127.0.0.1', port=6633 ),
                   switch=OVSKernelSwitch,
                   autoSetMacs=True)
    info( '*** Starting network\n')
    net.start()
    info( '*** Running CLI\n' )
    CLI( net )
    info( '*** Stopping network\n' )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    run()
