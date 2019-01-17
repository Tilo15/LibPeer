# This is perhaps the first serious use of the library - a standalone AMPP server that
# can be run on a headless server to aid peer discovery

import sys
from twisted.internet import reactor
from LibPeer.Discovery import AMPP
from LibPeer.Muxer import Muxer
from LibPeer.Networks.ipv4 import IPv4
from LibPeer.Logging import log

log.settings(True, 0)

def running(arg):
    log.info("Reached target state")


if(len(sys.argv) != 2):
    print("Usage:\n\tAMPP_Server <port>\n\t<port>\tThe UDP port to listen on")

else:
    port = int(sys.argv[1])
    network = IPv4(Muxer(), True, int(port))
    discoverer = AMPP.AMPP(["AMPP"]) # Passing "AMPP" in will cause it to expressly subscribe to AMPP adverts
    discoverer.add_network(network)
    discoverer.start_discoverer().addCallback(running)
    reactor.run(installSignalHandlers=False)