
import LibPeer.Networks as Networks
from LibPeer.Formats import umsgpack, baddress
from LibPeer.Events import Event
from twisted.internet import protocol
from twisted.internet import reactor
from LibPeer.UPnP import PublicPort
from LibPeer.Logging import log


class IPv4(Networks.Network):
    def __init__(self, muxer, local=False):
        self.datagram_received = Event()
        self.udp = UDP_Helper(muxer, self.datagram_received)
        self.muxer = muxer
        self.type = "IPv4"
        self.port = 3000  # todo
        self.publicPort = None
        if(local):
            while(not PublicPort.is_local_port_free(self.port)):
                self.port += 1

        else:
            self.publicPort = PublicPort()
            self.port = self.publicPort.port
            if(not self.publicPort.open):
                log.critical("network port is not forwarded to the internet")

        self.muxer.add_network(self)
        reactor.listenUDP(self.port, self.udp, "")

    def send_datagram(self, message, address):
        self.udp.sendDatagram(message, address)

    def get_address(self, peer_suggestion):
        validation = peer_suggestion.split(b'.')
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
    def __init__(self, muxer, datagram_received):
        self.datagram_received = datagram_received
        self.muxer = muxer

    def datagramReceived(self, datagram, address):
        _address = baddress.BAddress(
            None, address[0], address[1], address_type="IPv4")
        self.muxer.datagram_received(datagram, _address)
        self.datagram_received.call(datagram, _address)

    def sendDatagram(self, datagram, address):
        self.transport.write(
            datagram, (address.net_address, int(address.port)))
