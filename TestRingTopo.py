#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
class SingleSwitchTopo(Topo):

  "Single switch connected to n hosts."
  def __init__(self, n=2):
    # Initialize topology and default options
    Topo.__init__(self)
    slist = []
    for i in range(n):
        if i == 0:
            switch = self.addSwitch('s%i' % (i + 1),stp = 1)
        else:
            switch = self.addSwitch('s%i' % (i + 1))
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
  topo = SingleSwitchTopo(n=4)
  net = Mininet(topo)
  net.start()
  print "Dumping host connections"
  dumpNodeConnections(net.hosts)
  print "Testing network connectivity"
  net.pingAll()
  net.stop()

if __name__ == '__main__':
  # Tell mininet to print useful information
  setLogLevel('info')
  simpleTest()
