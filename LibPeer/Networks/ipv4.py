
import LibPeer.Networks as Networks
from LibPeer.Formats import umsgpack, baddress
from twisted.internet import protocol
from twisted.internet import reactor
from LibPeer.Logging import log

class IPv4(Networks.Network):
    def __init__(self, muxer):
        self.udp = UDP_Helper(muxer)
        self.muxer = muxer
        self.type = "IPv4"
	self.port = 1234 # todo
        self.muxer.add_network(self)
	reactor.listenUDP(self.port, self.udp, "")

    def send_datagram(self, message, address):
        self.udp.sendDatagram(message, address)

    def get_address(self, peer_suggestion):
	return (peer_suggestion, self.port)
	



class UDP_Helper(protocol.DatagramProtocol):
    def __init__(self, muxer):
        self.muxer = muxer

    def datagramReceived(self, datagram, address):
        _address = baddress.BAddress(None, address[0], address[1], address_type="IPv4")
        self.muxer.datagram_received(datagram, _address)


    def sendDatagram(self, datagram, address):
        self.transport.write(datagram, (address.net_address, int(address.port)))


