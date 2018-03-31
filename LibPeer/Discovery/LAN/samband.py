import hashlib
import uuid

import time

from LibPeer.Formats import umsgpack
from LibPeer.Discovery.LAN.localpeer import LocalPeer
from twisted.internet import protocol
from LibPeer.Logging import log

# Values and names here may or may not be easter eggs


class Samband(protocol.DatagramProtocol):
    def __init__(self, ttl=40):
        self.peers = {}
        self.seenMessages = []
        self.ttl = ttl

    def startProtocol(self):
        self.transport.setTTL(1)
        self.transport.joinGroup("224.0.0.63")

    def datagramReceived(self, datagram, address):
        if len(datagram) < 10:
            log.debug("received datagram too small from %s, ignoring" % str(address))
            return

        if datagram[:8] == b'\xF0\x9F\x87\xAE\xF0\x9F\x87\xB8':
            data = umsgpack.unpackb(datagram[8:])
            if(data[0] not in self.seenMessages):
                self.seenMessages += [data[0],]
                # If the data is a string for some reason make it bytes
                for i in range(len(data)):
                    if(type(data[i]) is str):
                        data[i] = data[i].encode("utf-8")

                # Verify checksum
                checksum = hashlib.sha256(data[1] + data[0]).digest()
                if(checksum == data[2]):
                    # Valid packet
                    peer = LocalPeer(data[1])
                    self.peers[hashlib.sha256(data[1]).digest()] = peer
                    log.debug("local peer %s just uncovered itself via samband" % str(address))
                else:
                    log.warn("corrupt samband packet")
        self._clean()

    def broadcast(self, message):
        messageId = uuid.uuid4()
        checksum = hashlib.sha256(message + messageId.bytes).digest()
        data = umsgpack.packb([str(messageId), str(message), checksum])
        txdata = b'\xF0\x9F\x87\xAE\xF0\x9F\x87\xB8' + data
        self.transport.write(txdata, ("224.0.0.63", 1944))

    def _clean(self):
        for key in dict(self.peers):
            try:
                if(self.peers[key].timestamp + self.ttl < time.time()):
                    del self.peers[key]
            except:
                pass

    def get_peers(self):
        self._clean()
        peers = dict(self.peers)
        return (peers[key].address for key in peers)
        
        
