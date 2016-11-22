#!/usr/bin/python

"Assignment 4 - Creates a parking lot topology, \
    generates flows from senders to the receiver, \
    measures throughput of each flow"
from mininet.nodelib import LinuxBridge
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, output
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import custom, quietRun, dumpNetConnections
from mininet.cli import CLI
from mininet.node import OVSSwitch, Controller
from time import sleep, time
from multiprocessing import Process
from subprocess import Popen
import termcolor as T
import argparse

import sys
import os
from util.monitor import monitor_devs_ng

def cprint(s, color, cr=True):
    """Print in color
       s: string to print
       color: color to use"""
    if cr:
        print T.colored(s, color)
    else:
        print T.colored(s, color),

parser = argparse.ArgumentParser(description="Parking lot tests")
parser.add_argument('--bw', '-b',
                    type=float,
                    help="Bandwidth of network links",
                    required=True)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    default="results")

parser.add_argument('-n',
                    type=int,
                    help=("Number of senders in the parking lot topo."
                    "Must be >= 1"),
                    required=True)

parser.add_argument('--cli', '-c',
                    action='store_true',
                    help='Run CLI for topology debugging purposes')

parser.add_argument('--time', '-t',
                    dest="time",
                    type=int,
                    help="Duration of the experiment.",
                    default=60)

# Expt parameters
args = parser.parse_args()

if not os.path.exists(args.dir):
    os.makedirs(args.dir)

lg.setLogLevel('info')


class POXBridge(Controller):
    "Custom Controller class to invoke POX forwarding.l2_learning"

    def start(self):
        "Start POX learning switch"
        self.pox = '%s/pox/pox.py' % os.environ['HOME']
        self.cmd(self.pox, 'forwarding.l2_learning &')

    def stop(self):
        "Stop POX"
        self.cmd('kill %' + self.pox)


controllers = {'poxbridge': POXBridge}
# Topology to be instantiated in Mininet
class RingTopo(Topo):
    "Parking Lot Topology"

    def __init__(self, n=1, cpu=.1, bw=10, delay=None,
                 max_queue_size=None, **params):
        """Parking lot topology with one receiver
           and n clients.
           n: number of clients
           cpu: system fraction for each host
           bw: link bandwidth in Mb/s
           delay: link delay (e.g. 10ms)"""

        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        hconfig = {'cpu': cpu}
        lconfig = {'bw': bw, 'delay': delay,
                   'max_queue_size': max_queue_size }

        #
        # uplink, hostlink, downlink = 1, 2, 3

        slist = []
        for i in range(n):
            switch = self.addSwitch('s%s' % (i + 1), cls=LinuxBridge)
            host = self.addHost('h%s' % (i + 1),**hconfig)
            self.addLink(host, switch,port1=0, port2=0, **lconfig)
            slist.append(switch)

        for i in range(n):
            if i != n - 1:
                self.addLink(slist[i], slist[i + 1],**lconfig)
            else:
                self.addLink(slist[i], slist[0],**lconfig)
        receiver = self.addHost('receiver')
        # self.addLink(receiver, slist[0],port1=0, port2=uplink, **lconfig)
        # Create the actual topology
        # receiver = self.addHost('receiver')

        # Switch ports 1:uplink 2:hostlink 3:downlink
        # # The following template code creates a parking lot topology
        # # for N = 1
        # # TODO: Replace the template code to create a parking lot topology for any arbitrary N (>= 1)
        # # Begin: Template code
        # s1 = self.addSwitch('s1')
        # h1 = self.addHost('h1', **hconfig)
        #
        # # Wire up receiver
        # self.addLink(receiver, s1,
        #               port1=0, port2=uplink, **lconfig)
        #
        # # Wire up clients:
        # self.addLink(h1, s1,
        #               port1=0, port2=hostlink, **lconfig)
        # s2 = self.addSwitch('s2')
        # h2 = self.addHost('h2', **hconfig)
        # self.addLink(s1, s2,
        #              port1=downlink, port2=uplink, **lconfig)
        # self.addLink(h2, s2,
        #              port1=0, port2=hostlink, **lconfig)
        # s3 = self.addSwitch('s3')
        # h3 = self.addHost('h3', **hconfig)
        # self.addLink(s2, s3,
        #              port1=downlink, port2=uplink, **lconfig)
        # self.addLink(h3, s3,
        #              port1=0, port2=hostlink, **lconfig)



def waitListening(client, server, port):
    "Wait until server is listening on port"
    if not 'telnet' in client.cmd('which telnet'):
        raise Exception('Could not find telnet')
    cmd = ('sh -c "echo A | telnet -e A %s %s"' %
           (server.IP(), port))
    while 'Connected' not in client.cmd(cmd):
        output('waiting for', server,
               'to listen on port', port, '\n')
        sleep(.5)

def progress(t):
    while t > 0:
        cprint('  %3d seconds left  \r' % (t), 'cyan', cr=False)
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print

def start_tcpprobe():
    os.system("rmmod tcp_probe 1>/dev/null 2>&1; modprobe tcp_probe")
    Popen("cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.dir, shell=True)

def stop_tcpprobe():
    os.system("killall -9 cat; rmmod tcp_probe")

def run_parkinglot_expt(net, n):
    "Run experiment"

    seconds = args.time

    # Start the bandwidth and cwnd monitors in the background
    monitor = Process(target=monitor_devs_ng,
            args=('%s/bwm.txt' % args.dir, 1.0))
    monitor.start()
    start_tcpprobe()

    # Get receiver and clients
    senderlist = []

    recvr = net.getNodeByName('receiver')
    port = 5001
    recvr.cmd('iperf -s -p', port,
              '> %s/iperf_server.txt' % args.dir, '&')
    for i in range(n):
        sender = net.getNodeByName('h%s'%(i + 1))
        waitListening(sender, recvr, port)
        sender.sendCmd('iperf -c %s -p %s -t %d -i 1 -yc > %s/iperf_%s.txt' % (recvr.IP(), 5001, seconds, args.dir, sender))
        senderlist.append(sender)
        progress(5)
    for i in range(n):
        senderlist[i].waitOutput()
        progress(1)
    # sender1 = net.getNodeByName('h1')
    # sender2 = net.getNodeByName('h2')
    # sender3 = net.getNodeByName('h3')
    # Start the receiver
    #
    # waitListening(sender2, recvr, port)
    # waitListening(sender3, recvr, port)
    # TODO: start the sender iperf processes and wait for the flows to finish
    # Hint: Use getNodeByName() to get a handle on each sender.
    # Hint: Use sendCmd() and waitOutput() to start iperf and wait for them to finish
    # Hint: waitOutput waits for the command to finish allowing you to wait on a particular process on the host
    # iperf command to start flow: 'iperf -c %s -p %s -t %d -i 1 -yc > %s/iperf_%s.txt' % (recvr.IP(), 5001, seconds, args.dir, node_name)
    # Hint (not important): You may use progress(t) to track your experiment progress
    # sender1.sendCmd('iperf -c %s -p %s -t %d -i 1 -yc > %s/iperf_%s.txt' % (recvr.IP(), 5001, seconds, args.dir, sender1))
    # sender2.sendCmd('iperf -c %s -p %s -t %d -i 1 -yc > %s/iperf_%s.txt' % (recvr.IP(), 5001, seconds, args.dir, sender2))
    # sender3.sendCmd('iperf -c %s -p %s -t %d -i 1 -yc > %s/iperf_%s.txt' % (recvr.IP(), 5001, seconds, args.dir, sender3))
    # sender1.waitOutput()
    # sender2.waitOutput()
    # sender3.waitOutput()
    # sender1.cmd('kill %iperf')
    # sender2.cmd('kill %iperf')
    # sender3.cmd('kill %iperf')
    #  Shut down monitors

    recvr.cmd('kill %iperf')

    monitor.terminate()
    stop_tcpprobe()

def check_prereqs():
    "Check for necessary programs"
    prereqs = ['telnet', 'bwm-ng', 'iperf', 'ping']
    for p in prereqs:
        if not quietRun('which ' + p):
            raise Exception((
                'Could not find %s - make sure that it is '
                'installed and in your $PATH') % p)

def main():
    "Create and run experiment"
    start = time()
    m = input("please input the size of the network n:")
    topo = RingTopo(n= m)
    host = custom(CPULimitedHost, cpu=.15)  # 15% of system bandwidth
    link = custom(TCLink, bw=args.bw, delay='1ms',
                  max_queue_size=200)

    net = Mininet(topo=topo, host=host, link=link, controller=POXBridge)

    net.start()
    for i in range(m):
        net.get('s%s' % (i + 1)).cmd('ovs-vsctl set bridge s%s stp-enable=true' % (i + 1))
        print "start STP on s%s"%(i + 1)
    print "sleep 30s for STP"
    progress(30)
    print "wake up"
    cprint("*** Dumping network connections:", "green")
    dumpNetConnections(net)

    cprint("*** Testing connectivity", "blue")

    net.pingAll()

    if args.cli:
        # Run CLI instead of experiment
        CLI(net)
    else:
        cprint("*** Running experiment", "magenta")
        run_parkinglot_expt(net, n= m)

    net.stop()
    end = time()
    os.system("killall -9 bwm-ng")
    cprint("Experiment took %.3f seconds" % (end - start), "yellow")

if __name__ == '__main__':
    check_prereqs()
    main()
