
import LibPeer.Networks as Networks
from LibPeer.Formats import umsgpack, baddress
from twisted.internet import protocol
from twisted.internet import reactor
from LibPeer.UPnP import PublicPort
from LibPeer.Logging import log


class IPv4(Networks.Network):
    def __init__(self, muxer, local=False):
        self.udp = UDP_Helper(muxer)
        self.muxer = muxer
        self.type = "IPv4"
        self.port = 3000  # todo
        self.publicPort = None
        if(local):
            while(not PublicPort.is_local_port_free(port)):
                port += 1

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
        return (peer_suggestion, self.port)

    def close(self):
        if(self.publicPort):
            self.publicPort.close()


class UDP_Helper(protocol.DatagramProtocol):
    def __init__(self, muxer):
        self.muxer = muxer

    def datagramReceived(self, datagram, address):
        _address = baddress.BAddress(
            None, address[0], address[1], address_type="IPv4")
        self.muxer.datagram_received(datagram, _address)

    def sendDatagram(self, datagram, address):
        self.transport.write(
            datagram, (address.net_address, int(address.port)))
