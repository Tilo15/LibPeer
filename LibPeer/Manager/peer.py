from LibPeer.Formats import baddress
import time

class Peer:
	def __init__(self, manager, address):
		self.last_interaction = 0
		self.manager = manager
		self.address = address
		self.labels = []
	
	def ping(self):
		return self.manager.ping(self.address)
	
	def touch(self):
		self.last_interaction = time.time()

	def send_message(self, transport, data, channel=b'\x00'*16):
		if(self.manager.muxer != transport.muxer):
			raise ValueError("the provided transport does not belong to the muxer that this peer is attatched to")
		return transport.send(data, self.address, channel)

	def __str__(self):
		return str(self.address)
