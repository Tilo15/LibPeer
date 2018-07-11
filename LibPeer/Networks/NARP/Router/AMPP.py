from LibPeer.Discovery.AMPP import AMPP
from LibPeer.Discovery.AMPP.advertorial import Advertorial
from LibPeer.Discovery.AMPP.subscription import Subscription
from LibPeer.Formats.baddress import BAddress
from LibPeer.Networks.NARP.address_util import AddressUtil
from LibPeer.Events import Event
import base64

class IndependantAMPP(AMPP):
    def __init__(self, network, network_id, router_id, broadcast_ttl = 30):
        # Call base constructor
        AMPP.__init__(self, ["AMPP"], broadcast_ttl, router_id)

        # Save the network ID
        self.network_id = network_id

        # Save and add the network
        self.network = network
        self.add_network(network)

        # Create a dict of address hashes
        self.address_table = {}

        # Create an event to fire when a new peer
        # is discovered
        self.new_address = Event()

        # A set of subscription ids to stop many
        # firings of the new_subscription event
        self.notified_subscriptions = set()

        # Fired when a new subscription request was received
        self.new_subscription = Event()


    def add_to_cache(self, advertorial: Advertorial):
        # When we save an advertorial, tell the router
        self.new_address.call(advertorial.address, self.network_id, advertorial.hops_left)

        self.cached_advertorials[advertorial.id] = advertorial
        self.clean_cache()

    def cross_network_subscription(self, subscription):
        # Send subscription message to all peers
        for peer in self.ampp_peers.values():
            # Call this to bypass sending notifications to other networks
            AMPP.send_subsrciption(self, subscription, peer)


    def send_subsrciption(self, subscription: Subscription, peer):
        # If this is a new subscription...
        if(subscription.id not in self.notified_subscriptions):
            self.notified_subscriptions.add(subscription.id)
            # Notify the other networks
            self.new_subscription.call(subscription, self.network_id)
        
        # Base method
        AMPP.send_subsrciption(self, subscription, peer)

    def advertise(self, peer_address, ttl=30):
        advertorial = Advertorial()
        advertorial.address = peer_address
        advertorial.hops_left = ttl
        advertorial.lifespan = self.recommended_rebroadcast_interval
        self.send_advertorial(advertorial)

        self.subscribe()

        # Cache any non AMPP advertorials that pass through
        if(peer_address.protocol != "AMPP"):
            self.add_to_cache(advertorial)