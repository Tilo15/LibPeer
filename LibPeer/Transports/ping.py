import LibPeer.Events as Events
from LibPeer.Muxer import parcel
from LibPeer.Formats import umsgpack, baddress
from LibPeer.Transports import Transport
import time
import uuid
from LibPeer.Logging import log

# Erronious Streaming Protocol
# id = \x00

class Ping(Transport):
	def __init__(self, muxer, *modifiers):
		self.muxer = muxer
		self.modifiers = [] # Disable modifiers for ping
		self.id = b'\x00'
		self.muxer.add_transport(self)
		self.data_received = Events.Event()
		self.ping_receipts = {}

	def send(self, data, address, channel=b'\x00'*16):
		rec = Events.Receipt()
		pid = uuid.uuid4()
		self.ping_receipts[pid.bytes] = rec
		self.send_ping(pid.bytes, data, address, channel)

		return rec

	def parcel_received(self, parcel):

		message = parcel.message
		data = umsgpack.unpackb(message)

		# is it a ping or a pong?
		if(data[1] == "PING"):
			self.send_ping(data[0], data[4], parcel.address, parcel.channel, "PONG", data[3])
			log.info("replied with PONG to a PING from %s" % str(parcel.address))

		elif(data[1] == "PONG"):
			# If we have something waiting on this pong, tell them we have it
			if(data[0] in self.ping_receipts):
				self.ping_receipts[data[0]].success()

			# Pass along the ping result
			res = PingResult(data)
			self.pass_along(parcel, res)

		else:
			log.warn("malformed ping request")


	def send_ping(self, ping_id, message, address, channel, ping="PING", timestamp=None):
		if(timestamp == None):
			timestamp = time.time()*1000
		# Construct the ping message
		data = umsgpack.packb([ping_id, ping, address.get_binary_address(), timestamp, message])
		# Send it
		_parcel = parcel.Parcel(channel, self.id, data, address)
		self.muxer.send_parcel(_parcel)






class PingResult:
	def __init__(self, data):
		self.ping_id = data[0]
		self.address = baddress.BAddress.from_serialised(data[2])
		self.time = time.time()*1000 - int(data[3])
		self.data = data[4]
