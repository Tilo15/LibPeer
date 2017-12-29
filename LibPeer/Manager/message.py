from LibPeer.Formats import baddress
from LibPeer.Buffer import Buffer
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

	def get_buffer(self, max_length=1073741824):
		buffer = Buffer(self.timestamp, self.peer.address, self.channel, max_length)
		# Add current message to buffer
		buffer.data_received(self.transport.protoId, self.address, self.channel, self.data)
		return buffer

