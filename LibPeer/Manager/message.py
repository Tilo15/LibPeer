from LibPeer.Formats import baddress
import time

class Message:
	def __init__(self, transport, peer, channel, data):
		self.transport = transport
		self.peer = peer
		self.channel = channel
		self.data = data
		self.timestamp = time.time()

	def reply(self, data):
		return self.peer.send_message(self.transport, data, self.channel)

	def age(self):
		return self.timestamp - time.time()

