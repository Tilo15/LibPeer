import LibPeer.Events as Events
from LibPeer.Muxer import parcel
from LibPeer.Transports import Transport

# Erronious Streaming Protocol
# id = \x01

class ESP(Transport):
	def __init__(self, muxer, *modifiers):
		self.muxer = muxer
		self.modifiers = modifiers
		self.id = b'\x01'
		self.muxer.add_transport(self)
		self.data_received = Events.Event()

	def send(self, data, address, channel="\x00"*16):
		data = self.mod_encode(address, data)
		_parcel = parcel.Parcel(channel, self.id, data, address)
		self.muxer.send_parcel(_parcel)
		return Events.ImmediateReceipt()

	def parcel_received(self, _parcel):
		self.pass_along(_parcel, _parcel.message)
		
