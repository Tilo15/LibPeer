from LibPeer.Discovery.DHT import DHT
from twisted.internet import reactor
from twisted.python import log
import sys

from LibPeer.Discovery.LAN import LAN
from LibPeer.Formats.baddress import BAddress, label_from_text

log.startLogging(sys.stdout)

def peers(results):
    print "Found peers:"
    for peer in results:
        print(str(peer))

def advertised(result):
    print(result)
    print "Advertised address!"
    t.get_peers("com.pcthingz.test", label_from_text("hello, world")).addCallback(peers)


def gotAddress(addresses, t):
    print "Addresses: ", addresses
    for a in addresses:
        peer_address = BAddress("com.pcthingz.test", a, 1234, label_from_text("hello, world"))
        t.advertise(peer_address).addCallback(advertised)


def bootstrapDone(result, t):
    t.get_address().addCallback(gotAddress, t)


t = DHT()
t.start_discoverer([("192.168.1.74", 7565)]).addCallback(bootstrapDone, t)

reactor.run()
