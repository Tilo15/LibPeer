
import LibPeer.Networks as Networks
from LibPeer.Formats import umsgpack, baddress
from LibPeer.Events import Event
from twisted.internet import protocol
from twisted.internet import reactor
from LibPeer.UPnP import PublicPort
from LibPeer.Logging import log
from LibPeer.Formats.baddress import *


class IPv4(Networks.Network):
    def __init__(self, local=False, startPort=3000, address=""):
        self.datagram_received = Event()
        self.udp = UDP_Helper(self.datagram_received)
        self.type = "IPv4"
        self.port = startPort
        self.publicPort = None
        if(local):
            while(not PublicPort.is_local_port_free(self.port)):
                self.port += 1

        else:
            self.publicPort = PublicPort()
            self.port = self.publicPort.port
            if(not self.publicPort.open):
                log.warn("Network port could not be forwarded to the internet via UPnP")

        reactor.listenUDP(self.port, self.udp, address)

    def send_datagram(self, message, address):
        self.udp.sendDatagram(message, address)

    def get_address(self, peer_suggestion):
        validation = sb(peer_suggestion).split(b'.')
        valid = len(validation) == 4
        for part in validation:
            valid = valid and len(part) < 4

        # Only return an address if it is a valid IPv4 address
        if(valid):
            return (peer_suggestion, self.port)
        else:
            return None

    def close(self):
        if(self.publicPort):
            self.publicPort.close()


class UDP_Helper(protocol.DatagramProtocol):
    def __init__(self, datagram_received):
        self.datagram_received = datagram_received

    def datagramReceived(self, datagram, address):
        _address = baddress.BAddress(
            None, address[0], address[1], address_type="IPv4")
        self.datagram_received.call(datagram, _address)

    def sendDatagram(self, datagram, address):
        self.transport.write(
            datagram, (address.net_address, int(address.port)))
