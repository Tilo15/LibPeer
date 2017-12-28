from LibPeer.Logging import log
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from LibPeer.Discovery.DHT.kademlia.utils import appDigest
from LibPeer.Discovery.DHT.kademlia.network import Server
from LibPeer.Discovery import Discoverer
from LibPeer.Discovery.DHT import meta_discoverer
from LibPeer.UPnP import PublicPort
import psutil
import os

from LibPeer.Formats.baddress import BAddress


class DHT(Discoverer):
    def __init__(self):
        self.recommended_rebroadcast_interval = 60
        self.server = Server()
        self.md = meta_discoverer.LocalDiscovery(self.server)

    def start_discoverer(self, cachePath):
        # Load cache if available
        if os.path.isfile(cachePath):
            self.server = self.server.loadState(cachePath)

        self.server.saveStateRegularly(cachePath, 20)

        # Get a port
        self.publicPort = PublicPort()
        if(not self.publicPort.open):
            log.error("Public port not opened, internet peers may not be able to connect to this machine")
        port = self.publicPort.port
        log.debug("using port %i" % port)

        self.server.listen(port)

        reactor.listenMulticast(2246, self.md, listenMultiple=True)

        loop = LoopingCall(self.md.broadcast, port, "DHT Local Peer Discovery, v1.0")
        loop.start(20)

        return self.server.bootstrap([])

    def _test_port(self, port):
        connections = psutil.net_connections()
        for connection in connections:
            if (connection.laddr[1] == port):
                return False
        return True

    def get_address(self):
        return self.server.inetVisibleIP()

    def advertise(self, peer_address):
        value = peer_address.get_binary_address()
        if(len(peer_address.label) != 32 and len(peer_address.label) != 0):
            raise ValueError("Invalid label size of %i" % len(peer_address.label))
        return self.server.set(appDigest(peer_address.protocol, peer_address.label), value)

    def get_peers(self, application, label=""):
        if (len(label) != 32 and len(label) != 0):
            raise ValueError("Invalid label size")
        return self.server.get(appDigest(application, label)).addCallback(self._translate_to_address_array, application)

    def _translate_to_address_array(self, value, application):
        if(value):
            return BAddress.array_from_serialised(value, application)
        else:
            return []

    def stop_discoverer(self):
        self.publicPort.close()

