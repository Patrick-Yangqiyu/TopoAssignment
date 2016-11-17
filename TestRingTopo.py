#!/usr/bin/python
from this import s

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI
class SingleSwitchTopo(Topo):

  "Single switch connected to n hosts."
  def __init__(self, n=2):
    # Initialize topology and default options
    Topo.__init__(self)
    slist = []
    for i in range(n):
        switch = self.addSwitch('s%s' % (i + 1),cls=OVSSwitch)
        host = self.addHost('h%s' % ( i + 1))
        self.addLink(host, switch)
        slist.append(switch)
    for i in range(n):
      if i != n-1:
          self.addLink(slist[i],slist[i + 1])
      else:
          self.addLink(slist[i],slist[0])

def simpleTest():
  "Create and test a simple network"
  m = 4
  topo = SingleSwitchTopo(n=m)
  net = Mininet(topo)
  net.start()
  for i in range(m):
      net.get('s%s'%(i + 1)).cmd('ovs-vsctl set bridge s%s stp-enable=true'%(i+1))

  CLI(net)
  print "Dumping host connections"
  dumpNodeConnections(net.hosts)
  print "Testing network connectivity"
  net.pingAll()
  net.stop()

if __name__ == '__main__':
  # Tell mininet to print useful information
  setLogLevel('info')
  simpleTest()
