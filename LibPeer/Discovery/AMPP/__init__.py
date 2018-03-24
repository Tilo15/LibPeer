# Advertorial Message Passing Protocol TODO

from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats import umsgpack
from LibPeer.Discovery.AMPP.subscription import Subscription
from LibPeer.Discovery.AMPP.advertorial import Advertorial

class AMPP(Discoverer):
    def __init__(self, applications):
        self.recommended_rebroadcast_interval = 60
        self.networks = {}
        self.subscriptions = {}
        self.local_subscriptions = applications
        self.stored_advertorials = set()
        self.ampp_peers = {}

    def add_network(self, network):
        self.networks[network.type] = network

    def datagram_received(self, message, address):
        # This is an AMPP packet
        if(self.message[:4] == "AMPP"):
            # Store the peer address
            self.ampp_peers[address.get_hash()] = address

            if(self.message[4:7] == "SUB"):
                # Deserialise Subscribe Request
                subscription = Subscription.from_dict(umsgpack.unpackb(message[7:]))
                subscription.address = address
                self.subscriptions[address.get_hash()] = subscription
                address_hash = address.get_hash()
                # Subscribe to these applications on all upstream peers
                for peer in self.ampp_peers:
                    if(peer.get_hash() != address_hash):
                        self.send_datagram("SUB" + umsgpack.packb(subscription.to_dict()), peer)


            elif(self.message[4:7] == "ADV"):
                # Deserialise Advertise Request
                advertorial = Advertorial.from_dict(umsgpack.unpackb(message[7:]))
                # Forward the message onto any peers who are subscribed to this application type
                for subscription in self.subscriptions.itervalues():
                    if(advertorial.application in subscription.applications):
                        self.send_datagram("ADV" + umsgpack.packb(advertorial.to_dict()), subscription.address)
                # If we are listening for this application, store it
                if(advertorial.application in self.local_subscriptions):
                    self.stored_advertorials.add(advertorial)


    def send_datagram(self, message, address):
        self.networks[address.address_type].send_datagram("AMPP" + message, address)

    def subscribe(self):
        # Send subscription request to all peers with our local subscriptions
        sub = Subscription()
        sub.applications = self.local_subscriptions
        for peer in self.ampp_peers:
            self.send_datagram("SUB" + umsgpack.packb(sub.to_dict()))

