
class Bootstrapper:
    def __init__(self):
        self.network_type = "" # Eg. IPv4
        self.recommended_advertise_interval = 10
    
    def get_ampp_peers(self):
        '''Returns a deffered result of a list of BAddresses'''
        raise NotImplemented()

    def advertise(self, network):
        '''Returns a deffered result when the AMPP peer has been advertised'''
        raise NotImplemented()

    def test_availability(self, network):
        '''Returns a defferred result with a boolean which is set to true if this discoverer is operable under the current network conditions'''
        raise NotImplemented()

# Easy list of all the bootstrapper classes
from LibPeer.Discovery.AMPP.bootstrapers.ipv4_multicast import IPv4_Multicast

BOOTSTRAPPERS = [IPv4_Multicast,]