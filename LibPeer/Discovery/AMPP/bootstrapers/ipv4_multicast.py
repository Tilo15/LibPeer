from LibPeer.Discovery.AMPP.bootstrapers import Bootstrapper
from LibPeer.Discovery.LAN import LAN
from LibPeer.Logging import log
from LibPeer.Formats.baddress import BAddress
from twisted.internet import reactor, defer

class IPv4_Multicast(Bootstrapper):
    def __init__(self):
        self.network_type = "IPv4"
        self.recommended_advertise_interval = 10
        self.discoverer = LAN()
        self.discoverer.start_discoverer(None).addCallback(self.discoverer_ready)

    def discoverer_ready(self, success):
        log.debug("LAN discovery ready")

    def get_ampp_peers(self):
        return self.discoverer.get_peers("AMPP")

    def test_availability(self, network):
        deferred = defer.Deferred()
        reactor.callLater(0.1, deferred.callback, True)
        return deferred

    def advertise(self, network):
        deferred = defer.Deferred()
        log.debug("Querying for local IPv4 address")
        self.discoverer.get_address().addCallback(self.got_address, deferred, network)
        return deferred

    def got_address(self, addresses, deferred, network):
        for address in addresses:
            result = network.get_address(address)
            if(type(result) is tuple):
                self.discoverer.advertise(BAddress("AMPP", result[0], result[1], address_type=network.type))
            else:
                log.warn("LAN discoverer returned an invalid IPv4 address")
        
        deferred.callback(True)

    def cancel(self):
        self.discoverer.stop_discoverer()

