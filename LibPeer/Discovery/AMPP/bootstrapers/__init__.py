
class Bootstrapper:
    def __init__(self):
        self.network_type = "" # Eg. IPv4
        self.recommended_advertise_interval = 10
    
    def get_ampp_peers(self):
        '''Returns a deffered result of a list of BAddresses'''
        raise NotImplementedError

    def advertise(self, network):
        '''Returns a deffered result when the AMPP peer has been advertised'''
        raise NotImplementedError

    def test_availability(self, network):
        '''Returns a defferred result with a boolean which is set to true if this discoverer is operable under the current network conditions'''
        raise NotImplementedError

    def cancel(self):
        '''Cancel this bootstrapper, ending any background processes'''
        raise NotImplementedError

# Easy list of all the bootstrapper classes
from LibPeer.Discovery.AMPP.bootstrapers.ipv4_multicast import IPv4_Multicast
from LibPeer.Discovery.AMPP.bootstrapers.DNS import DNS

BOOTSTRAPPERS = [IPv4_Multicast, DNS]