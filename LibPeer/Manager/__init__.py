from LibPeer.Logging import log
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from LibPeer.Muxer import Muxer
import LibPeer.Events as Events
import LibPeer.Transports as Transports
from LibPeer.Transports import ping
from LibPeer.Manager import peer
from LibPeer.Manager import message
from LibPeer.Formats import baddress
from LibPeer.Formats.butil import ss, stf

import threading
import sys

class Manager:
	def __init__(self, application, discoverer):
		self.application = application
		self.threaded = False
		self.discoverable = False
		self.muxer = Muxer()
		self.transports = {}
		self.peer_hashmap = {}
		self.advertised_address_hashes = set()
		self.labels = []
		self.search_labels = []
		self.message_received = Events.KeyedEvent()
		self.discoverer = discoverer
		self.loop_counter = 0

		self.add_transport(ping.Ping)


	def add_network(self, networkClass, **kwargs):
		"""Add a network type to the manager,
		returns the newly created Network object"""
		net = networkClass(self.muxer, **kwargs)
		return net


	def add_transport(self, transportClass, *modifiers, **kwargs):
		"""Add a transport type to the manager,
		returns the newly created Transport object"""
		trans = transportClass(self.muxer, *modifiers, **kwargs)
		self.transports[trans.id] = trans
		trans.data_received.subscribe(self.callback)
		return trans


	def run(self):
		"""Run the Peer stack"""
		self.threaded = True
		threading.Thread(target=self.run_blocking).start()


	def run_blocking(self):
		"""Run the Peer stack on the current thread"""		
		loop = LoopingCall(self.loop)
		loop.start(1)
		self.discoverer.start_discoverer().addCallback(self.bootstrap_complete)
		reactor.run(installSignalHandlers=False)

	def bootstrap_complete(self, data):
		log.info("Discoverer is now running")


	def ping(self, address, message="Default Ping Message"):
		"""Ping an address"""
		return self.transports[Transports.TRANSPORT_PING].send(message, address)


	def callback(self, transId, address, channel, data):
		if(transId == Transports.TRANSPORT_PING):
			# Print out the pingback information
			log.info("got PONG from %s in %ims" % (str(address), data.time))

		if(address.get_hash() not in self.advertised_address_hashes):
			# Is this a new peer?
			if(address.get_hash() not in self.peer_hashmap):
				# Yes, add it to our list!
				self.peer_hashmap[address.get_hash()] = peer.Peer(self, address)
			
			# Get the peer
			currentPeer = self.peer_hashmap[address.get_hash()]

			# Update the time of the last interaction
			currentPeer.touch()
			
			# Create a message
			_message = message.Message(self.transports[transId], currentPeer, channel, data)

			# Emit an event for this channel with the message
			self.message_received.call(channel, _message)

		else:
			log.debug("got message from local machine; ignoring")

	def loop(self):
		if(self.discoverable and self.loop_counter % self.discoverer.recommended_rebroadcast_interval == 0):
			# If we are in discoverable mode, get our address so we can broadcast it
			self.discoverer.get_address().addCallback(self.broadcast_address)

		# Every six seconds
		if(self.loop_counter % 6 == 0):
			# Search for peers
			self.discoverer.get_peers(self.application).addCallback(self.discovered_peers)
	
			# Search for peers by labels
			for label in self.search_labels:
				self.discoverer.get_peers(self.application, label).addCallback(self.discovered_peers)

		self.loop_counter += 1

	def broadcast_address(self, addresses):
		log.debug("We appear as the following addresses to our peers:")
		for address_suggestion in addresses:
			log.debug("    %s through %s" % stf(address_suggestion[0], address_suggestion[1]))
			network = self.muxer.networks[address_suggestion[1]]
			net_address = network.get_address(address_suggestion[0])
			if(type(net_address) is tuple):
				peer_address = baddress.BAddress(self.application, net_address[0], net_address[1], address_type=network.type)
				self.discoverer.advertise(peer_address).addCallback(self.advertised)
				self.advertised_address_hashes.add(peer_address.get_hash())
				for label in self.labels:
					peer_address = baddress.BAddress(self.application, net_address[0], net_address[1], label, network.type)
					self.discoverer.advertise(peer_address).addCallback(self.advertised)
					self.advertised_address_hashes.add(peer_address.get_hash())
			else:
				log.debug("Address suggestion '%s' rejected by %s network controller" % (ss(address_suggestion[0]), network.type))


	def advertised(self, res):
		log.debug("Successfully advertised this peer")


	def discovered_peers(self, peers):
		for address in peers:
			key = address.get_hash()
			# Don't add ourselves
			if(key not in self.advertised_address_hashes):
				# Do we have this peer?
				if(key in self.peer_hashmap):
					# If the label has not been associated with this peer, add it
					if(address.label != "" and address.label not in self.peer_hashmap[key].labels):
						self.peer_hashmap[key].labels.append(address.label)

					# Touch the peer
					self.peer_hashmap[key].touch()
					
				else:
					# Create the peer object
					p = peer.Peer(self, address)
					# If we were given a label, add that too
					if(address.label != ""):
						p.labels.append(address.label)

					# Save the peer
					self.peer_hashmap[address.get_hash()] = p
					
		

	def add_label(self, label):
		"""Add a label to this peer"""
		self.labels.append(label)

	def remove_label(self, label):
		"""Remove a label from this peer"""
		self.labels.pop(self.labels.index(label))


	def set_discoverable(self, discoverable):
		"""Enable or disable broadcasting of this peer's existance over the network"""
		self.discoverable = discoverable


	def subscribe(self, callback, channel=b'\x00'*16):
		"""Subscribe to messages from the network, optionally subscribing to a different channel"""
		self.message_received.subscribe(channel, callback)


	def get_peers(self, label=None):
		"""Get a list of peers, ordered by time of most recent interaction
		and optionally filtered on a label"""
		items = []
		for item in self.peer_hashmap.values():
			if(label != None):
				if(label in item.labels):
					items.append(item)
			else:
				items.append(item)

		if(label != None and label not in self.search_labels):
			self.search_labels.append(label)
			
		return sorted(items, key=(lambda i: i.last_interaction))


	def call(self, function, *args):
		"""Safely run a task in the networking thread"""
		reactor.callFromThread(function, *args)

	def stop(self):
		log.debug("stopping discoverer")
		self.discoverer.stop_discoverer()

		log.debug("stopping networks")
		for net in self.muxer.networks.values():
			net.close()

		log.debug("stopping reactor")
		self.call(reactor.stop)
		


