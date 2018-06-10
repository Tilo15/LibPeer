from LibPeer.Networks import Network
from LibPeer.Logging import log
from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats import umsgpack
from LibPeer.Networks.NARP import router_reply_codes

# TODO not at all even really started
# make your own Muxer for this I think

class NARPRouter:
    def __init__(self, networks):
        self.networks = networks

        for network in self.networks:
            network.datagram_received.subscribe(self.datagram_received, network)

    
    def datagram_received(self, datagram, address, network):
