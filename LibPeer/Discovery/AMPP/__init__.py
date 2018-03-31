# Advertorial Message Passing Protocol

from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats import umsgpack
from LibPeer.Discovery.AMPP.subscription import Subscription
from LibPeer.Discovery.AMPP.advertorial import Advertorial
from LibPeer.Discovery.AMPP.bootstrapers import BOOTSTRAPPERS
from LibPeer.Discovery import Discoverer
from LibPeer.Logging import log
from twisted.internet import reactor, defer

class AMPP(Discoverer):
    def __init__(self, applications, broadcast_ttl = 30):
        self.recommended_rebroadcast_interval = 60
        self.networks = {}
        self.subscriptions = {}
        self.local_subscriptions = applications
        self.stored_advertorials = {}
        self.ampp_peers = {}
        self.broadcast_ttl = broadcast_ttl
        self.running = False
        self.bootstrappers = []
        self.bootstrappers_to_test = 0
        self.peer_visible_addresses = []

    def add_network(self, network):
        log.debug("Network of type %s registered" % network.type)
        self.networks[network.type] = network
        network.datagram_received.subscribe(self.datagram_received)

    def store_advertorial(self, advertorial):
        # If we don't have a dictionary entry for this application yet, create it
        if(advertorial.application not in self.stored_advertorials):
            self.stored_advertorials[advertorial.application] = {}
        
        # If we don't have a dictionary entry for this appliction's label, create it
        if(advertorial.address.label not in self.stored_advertorials[advertorial.application]):
            self.stored_advertorials[advertorial.address.label] = set()

        # Add to 2d dictionary
        self.stored_advertorials[advertorial.application][advertorial.address.label].add(advertorial)
        



    def datagram_received(self, message, address):
        # Drop if discoverer is not running
        if(not self.running):
            return
        
        # This is an AMPP packet
        if(message[:4] == "AMPP"):
            
            # Store the peer address
            self.ampp_peers[address.get_hash()] = address

            if(message[4:7] == "SUB"):

                # Deserialise Subscribe Request
                subscription = Subscription.from_dict(umsgpack.unpackb(message[7:]))
                subscription.address = address
                self.subscriptions[address.get_hash()] = subscription
                address_hash = address.get_hash()
                
                # Subscribe to these applications on all upstream peers
                for peer in self.ampp_peers.itervalues():
                    if(peer.get_hash() != address_hash):
                        self.send_datagram("SUB" + umsgpack.packb(subscription.to_dict()), peer)


            elif(message[4:7] == "ADV"):
                # Deserialise Advertise Request
                advertorial = Advertorial.from_dict(umsgpack.unpackb(message[7:]))

                # Forward the message onto any peers who are subscribed to this application type
                self.send_advertorial(advertorial)

                # If we are listening for this application, store it
                if(advertorial.application in self.local_subscriptions):
                    self.store_advertorial(advertorial)

            elif(message[4:7] == "ADQ"):
                # Address request
                self.send_datagram("ADR" + address.get_binary_address(), address)

            elif(message[4:7] == "ADR"):
                # Got an address
                reported_address = BAddress.from_serialised(message[7:])
                log.debug("%s sees us as %s" % address, reported_address)
                self.peer_visible_addresses = reported_address.net_address


    def get_address(self):
        deferred = defer.Deferred()

        self.peer_visible_addresses = []

        for peer in self.ampp_peers.itervalues():
            self.send_datagram("ADQ", peer)
        
        # Return a result from responses soon
        reactor.callLater(3, self.check_address_query_timeout, deferred)
        return deferred

    def check_address_query_timeout(self, deferred):
        deferred.callback(self.peer_visible_addresses)


    def send_advertorial(self, advertorial):
        for subscription in self.subscriptions.itervalues():
            if(advertorial.address.protocol in subscription.applications):
                self.send_datagram("ADV" + umsgpack.packb(advertorial.to_dict()), subscription.address)


    def send_datagram(self, message, address):
        if(address.address_type in self.networks):
            self.networks[address.address_type].send_datagram("AMPP" + message, address)
        else:
            log.error("Failed to send datagram to '%s', no network of that type available" & address)


    def subscribe(self):
        # Send subscription request to all peers with our local subscriptions
        sub = Subscription()
        sub.applications = self.local_subscriptions
        for peer in self.ampp_peers:
            self.send_datagram("SUB" + umsgpack.packb(sub.to_dict()))


    def deffered_result(self, length=0.1,  *args):
        # The interface requires a callback, so give it one
        deferred = defer.Deferred()
        reactor.callLater(length, deferred.callback, *args)
        return deferred


    def advertise(self, peer_address):
        advertorial = Advertorial()
        advertorial.address = peer_address
        advertorial.hops_left = self.broadcast_ttl
        advertorial.lifespan = self.recommended_rebroadcast_interval
        self.send_advertorial(advertorial)

        # Now, make sure our subscriptions haven't expired
        self.subscribe()

        # Notify the caller that this task has completed
        self._deffered_result(0.1, True)

    def get_peers(self, application, label=""):
        peers = []
        if(application in self.stored_advertorials):
            if(label in self.stored_advertorials[application]):
                for advertorial in self.stored_advertorials[application][label]:
                    if(advertorial.is_current()):
                        peers.append(advertorial.address)
                        # TODO fix memeory leak where expired advertorials don't get deleted


        return self.deffered_result(0.1, peers)


    def start_discoverer(self, cachePath):
        deferred = defer.Deferred()

        # Instansiate bootstrappers
        for bs in BOOTSTRAPPERS:
            bootstrapper = bs()
            if(bootstrapper.network_type in self.networks):
                log.debug("Bootstraper test started")
                self.bootstrappers_to_test += 1
                bootstrapper.test_availability(self.networks[bootstrapper.network_type]).addCallback(self.boostrapper_available_result, bootstrapper, deferred)

        
        return deferred


    def boostrapper_available_result(self, result, bootstrapper, deferred):
        log.debug("Bootstraper test completed")
        # If the test succeeded, add to our list of available bootstrappers
        if(result):
            self.bootstrappers.append(bootstrapper)
        else:
            log.debug("A bootstrapper for network type %s is unavailable" % bootstrapers.network_type)

        # If we have tested them all, let the starter know that the process is complete
        self.bootstrappers_to_test -= 1
        if(self.bootstrappers_to_test == 0):
            self.running = True

            # Start advertising
            for bs in self.bootstrappers:
                self.run_bootstrapper_advertise(bs)
            
            # Finally, pass the all clear to the caller of start_discoverer
            deferred.callback(True)


    def run_bootstrapper_advertise(self, bootstrapper):
        if(self.running):
            log.debug("Advertising AMPP on %s interface" % bootstrapper.network_type)
            net = self.networks[bootstrapper.network_type]
            bootstrapper.advertise(net).addCallback(self.boostrapper_finished_run, bootstrapper)

    def boostrapper_finished_run(self, success, bootstrapper):
        log.debug("Querying %s bootstrapper for peers" % bootstrapper.network_type)
        bootstrapper.get_ampp_peers().addCallback(self.bootstrapper_got_peers, bootstrapper)

    def bootstrapper_got_peers(self, peers, bootstrapper):
        # Store any new peers
        for address in peers:
            self.ampp_peers[address.get_hash()] = address
        
        # Advertise again after the recommended interval
        reactor.callLater(bootstrapper.recommended_advertise_interval, self.run_bootstrapper_advertise, bootstrapper)

    def stop_discoverer(self):
        self.running = False

