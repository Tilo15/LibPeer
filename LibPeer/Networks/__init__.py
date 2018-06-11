
class Network:
	def __init__(self):
		self.type = "ProtoType"
		self.datagram_received = Event()

	def send_datagram(self, message, address):
		raise NotImplementedError

	def get_address(self, peer_suggestion):
		raise NotImplementedError

	def close(self):
		raise NotImplementedError