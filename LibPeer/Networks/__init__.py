
class Network:
	def __init__(self, muxer):
		self.muxer = muxer
		self.type = "ProtoType"
		self.port = 0
		self.muxer.add_network(self)

	def send_datagram(self, message, address):
		raise NotImplemented()

	def get_address(self, peer_suggestion):
		raise NotImplemented()

	def close(self):
		raise NotImplemented()