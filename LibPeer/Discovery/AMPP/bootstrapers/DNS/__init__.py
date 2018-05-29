from LibPeer.Discovery.AMPP.bootstrapers import Bootstrapper
from LibPeer.Discovery.AMPP.bootstrapers.DNS.dns_discoverer import DNSDiscoverer
from LibPeer.Formats.baddress import BAddress
from LibPeer.Logging import log
from twisted.internet import defer, reactor

class DNS(Bootstrapper):
    def __init__(self):
        self.network_type = "IPv4" # Eg. IPv4
        self.recommended_advertise_interval = 3600
        self.helper = DNSDiscoverer()
    
    def get_ampp_peers(self):
        deferred = defer.Deferred()
        log.info("Doing DNS lookup for AMPP seeds")
        self.helper.get_seed_addresses().addCallback(self.got_seed_addresses, deferred)
        return deferred

    def got_seed_addresses(self, addresses, deferred):
        baddresses = []
        for address in addresses:
            baddresses.append(BAddress("AMPP", address[0], address[1], address_type=self.network_type))

        deferred.callback(baddresses)

    def advertise(self, network):
        # Can't advertise on DNS, this is a one way seed
        deferred = defer.Deferred()
        reactor.callLater(0.1, deferred.callback, True)
        return deferred

    def test_availability(self, network):
        # TODO actually test for DNS server
        deferred = defer.Deferred()
        reactor.callLater(0.1, deferred.callback, True)
        return deferred

    def cancel(self):
        return