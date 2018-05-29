
class Network:
	def __init__(self, muxer):
		self.muxer = muxer
		self.type = "ProtoType"
		self.port = 0
		self.muxer.add_network(self)
		self.datagram_received = Event()

	def send_datagram(self, message, address):
		raise NotImplementedError

	def get_address(self, peer_suggestion):
		raise NotImplementedError

	def close(self):
		raise NotImplementedError