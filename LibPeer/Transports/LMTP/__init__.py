import LibPeer.Events
from LibPeer.Muxer import parcel
from LibPeer.Transports import Transport
from LibPeer.Transports.LMTP import transaction
from LibPeer.Logging import log
from LibPeer.Formats.butil import *
import uuid
import binascii

# Large Message Transport Protocol
# id = \x05

class LMTP(Transport):
	def __init__(self, muxer, *modifiers):
		self.muxer = muxer
		self.modifiers = modifiers
		self.id = b'\x05'
		self.muxer.add_transport(self)
		self.data_received = LibPeer.Events.Event()
		self.delay_target = 0.1

		self.transactions = {}
		self.oldTransactions = set()

	def send(self, data, address, channel="\x00"*16):
        # Run modifiers
		data = self.mod_encode(address, data)

        # Create an ID for this transaction
		transId = uuid.uuid4().bytes

		# Create the transaction
		trans = transaction.Transaction(transId, address, channel, self.transaction_send, self.delay_target)

		# Subscribe to the cancel event
		trans.on_cancel.subscribe(self.transaction_canceled)

		# Save the transaction
		self.transactions[transId] = trans
		
		# Start the transaction
		trans.start(data)

		# Return a receipt
		return trans.receipt

	def parcel_received(self, _parcel):
		id = _parcel.message[:16]
		data = _parcel.message[16:]

		if(id in self.transactions):
			self.transactions[id].data_received(data)
		
		elif(id in self.oldTransactions):
			log.debug("ignoring parcel for transaction '%s' which has already completed" % b2s(binascii.hexlify(id)))

		else:
			log.debug("got new transaction with id '%s'" % b2s(binascii.hexlify(id)))
			# Create new transaction to service parcel
			trans = transaction.Transaction(id, _parcel.address, _parcel.channel, self.transaction_send, self.delay_target)

			# Subscribe to the cancel event
			trans.on_cancel.subscribe(self.transaction_canceled)

			# Subscribe to the complete event
			trans.on_complete.subscribe(self.transaction_received)

			# Save the transaction
			self.transactions[id] = trans

			# Notify the transaction of new data
			trans.data_received(data)

	def transaction_send(self, transaction, data):
		message = transaction.id + data
		_parcel = parcel.Parcel(transaction.channel, self.id, message, transaction.address)
		self.muxer.send_parcel(_parcel)


	def transaction_received(self, id, address, channel, data):
		# Remove the transaction
		self.oldTransactions.add(id)
		del self.transactions[id]
		# Serve the data
		data = self.mod_decode(address, data)
		self.data_received.call(self.id, address, channel, data)

	def transaction_canceled(self, id):
		self.oldTransactions.add(id)
		del self.transactions[id]
		log.info("transaction '%s' canceled" % b2s(binascii.hexlify(id)))