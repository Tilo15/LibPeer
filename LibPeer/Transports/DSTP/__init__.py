import LibPeer.Events
from LibPeer.Muxer import parcel
from LibPeer.Transports import Transport
from LibPeer.Transports.LMTP import transaction
from LibPeer.Logging import log
import uuid

# Data Stream Transport Protocol
# id = \x06

class DSTP(Transport):
	def __init__(self, muxer, *modifiers):
		self.muxer = muxer
		self.modifiers = modifiers
		self.id = b'\x06'
		self.muxer.add_transport(self)
		self.data_received = LibPeer.Events.Event()
		self.delay_target = 0.1

	def send(self, data, address, channel="\x00"*16):
        pass

	def parcel_received(self, _parcel):
        pass