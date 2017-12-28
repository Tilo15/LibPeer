class Parcel:
	def __init__(self, channel, protocol, message, address):
		if(len(channel) != 16):
			raise ValueError("channel length must be 16")
		self.channel = channel
		# This is the TRANSPORT protocol, not the application protocol
		# for the APPLICATION protocol, check Parcel.address.protocol.
		self.protocol = protocol
		self.message = message
		self.address = address

