from LibPeer.Formats.butil import sb

class Parcel:
	def __init__(self, channel, protocol, message, address):
		if(len(channel) != 16):
			raise ValueError("channel length must be 16")
		self.channel = sb(channel)
		# This is the TRANSPORT protocol, not the application protocol
		# for the APPLICATION protocol, check Parcel.address.protocol.
		self.protocol = sb(protocol)
		self.message = sb(message)
		self.address = address

