from LibPeer.Formats import umsgpack
import os
from hashlib import sha1
from base64 import b64encode
from builtins import str

from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import defer
from LibPeer.Logging import log

from rpcudp.exceptions import MalformedMessage


class LocalDiscovery(protocol.DatagramProtocol):
	def __init__(self, server):
		self.local_nodes = []
		self.server = server

	def startProtocol(self):
		self.transport.setTTL(1)
		self.transport.joinGroup("224.0.0.246")

	def datagramReceived(self, datagram, address):
		if len(datagram) < 2:
			log.debug("received datagram too small from %s, ignoring" % repr(address))
			return

		data = umsgpack.unpackb(datagram[1:])

		if datagram[:1] == b'\xF6':
			connection_string = "mdp://%s:%s" % (address[0], str(address[1]))
			if(not connection_string in self.local_nodes):
				log.info("local peer %s just announced itself with message '%s'" % (address, data[1]))
				self.local_nodes += [connection_string,]
				node = (address[0], int(data[0]))
				self.server.bootstrap([node,])
		else:
			log.warn("malformed meta-discovery packet")

	def broadcast(self, port, message):
		data = umsgpack.packb([str(port), str(message)])
		txdata = b'\xF6' + data
		self.transport.write(txdata, ("224.0.0.246", 2246))


	





