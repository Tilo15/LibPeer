import time
from twisted.internet.task import LoopingCall

from LibPeer.Discovery.DHT import DHT
from twisted.internet import reactor
from LibPeer.Logging import log
import sys

from LibPeer.Discovery.LAN import LAN
from LibPeer.Formats.baddress import BAddress, label_from_text

log.startLogging(sys.stdout)

def peers(results):
    print
    print "-- Peers as at %i: -----------------------------------------------------" % time.time()
    for peer in results:
        print(str(peer))

    print "-"*80
    print

def advertised(result):
    print "Advertised address!"

def getPeers(t):
    t.get_peers("com.pcthingz.test", label_from_text("hello, world")).addCallback(peers)


def gotAddress(addresses, t):
    print "Addresses: ", addresses
    for a in addresses:
        peer_address = BAddress("com.pcthingz.test", a, 1235, label_from_text("hello, world"))
        t.advertise(peer_address).addCallback(advertised)


def broadcast(t):
    t.get_address().addCallback(gotAddress, t)

def bootstrapDone(result, t):
    loop = LoopingCall(broadcast, t)
    loop.start(t.recommended_rebroadcast_interval)

    loop2 = LoopingCall(getPeers, t)
    loop2.start(10)

t = DHT()
t.start_discoverer([]).addCallback(bootstrapDone, t)

reactor.run()
