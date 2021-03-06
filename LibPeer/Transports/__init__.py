import LibPeer.Events as Events

TRANSPORT_PING        = b'\x00'
TRANSPORT_EDP         = b'\x01'
TRANSPORT_MCP         = b'\x02' #TODO
TRANSPORT_TELEMETRY   = b'\x03' #TODO
TRANSPORT_TELECOMMAND = b'\x04' #TODO
TRANSPORT_LMTP        = b'\x05'
TRANSPORT_DSTP        = b'\x06'


class Transport:
	def __init__(self, muxer, *modifiers):
		self.muxer = muxer
		self.modifiers = modifiers
		self.id = b'\xFF'
		self.muxer.add_transport(self)
		self.data_received = Events.Event()

	def send(self, data, address, channel=b'\x00'*16):
		raise NotImplementedError

	def parcel_received(self, parcel):
		raise NotImplementedError

	def pass_along(self, parcel, obj):
		"""Used internally by subclasses to pass a message onto its destination
		all transports should use this to avoid calling self.data_received directly"""
		obj = self.mod_decode(parcel.address, obj)
		self.data_received.call(self.id, parcel.address, parcel.channel, obj)

	def mod_decode(self, parcel, obj):
		for modifier in self.modifiers:
			obj = modifier.decode(obj, parcel.address)
		return obj

	def mod_encode(self, address, obj):
		for modifier in self.modifiers:
			obj = modifier.encode(obj, address)
		return obj
