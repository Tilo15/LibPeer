from twisted.internet import reactor, defer
from twisted.python import log
from twisted.internet.task import LoopingCall
from LibPeer.Discovery import Discoverer
from netifaces import interfaces, ifaddresses, AF_INET
from LibPeer.Discovery.LAN.samband import Samband


class LAN(Discoverer):
    def __init__(self):
        self.recommended_rebroadcast_interval = 10
        self.samband = Samband()

    def start_discoverer(self, cachePath):
	# Lan doesn't cache.
        reactor.listenMulticast(1944, self.samband, listenMultiple=True)

        return self._deffered_result(1, True)

    def get_address(self):
        ip_list = self._get_address()
        return self._deffered_result(0.1, ip_list)

    def _get_address(self):
        ip_list = []
        for interface in interfaces():
            addresses = ifaddresses(interface)
            if(AF_INET in addresses):
                for link in addresses[AF_INET]:
                    if(link['addr'] != '127.0.0.1'):
                        ip_list.append(link['addr'].encode('ascii','ignore'))
        return ip_list

    def advertise(self, peer_address):
        self.samband.broadcast(peer_address.get_binary_address())
        return self._deffered_result(0.1, True)

    def get_peers(self, application, label=""):
        return self._deffered_result(0.1, self.samband.get_peers())

    def _deffered_result(self, length=0.1,  *args):
        # The interface requires a callback, so give it one
        deferred = defer.Deferred()
        reactor.callLater(length, deferred.callback, *args)
        return deferred

