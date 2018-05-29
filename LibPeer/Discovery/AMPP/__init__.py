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
        self.recommended_rebroadcast_interval = 10 # TODO change to more reasonable number
        self.networks = {}
        self.subscriptions = {}
        self.local_subscriptions = applications
        self.stored_advertorials = {}
        self.ampp_peers = {}
        self.broadcast_ttl = broadcast_ttl
        self.running = False
        self.bootstrappers = []
        self.bootstrappers_to_test = 0
        self.peer_visible_addresses = {}
        self.subscription_forwarded_ids = set()
        self.advertorial_forwarded_ids = set()

    def add_network(self, network):
        log.debug("Network of type %s registered" % network.type)
        self.networks[network.type] = network
        network.datagram_received.subscribe(self.datagram_received)

    def store_advertorial(self, advertorial):
        # If we don't have a dictionary entry for this application yet, create it
        if(advertorial.address.protocol not in self.stored_advertorials):
            self.stored_advertorials[advertorial.address.protocol] = {}
        
        # If we don't have a dictionary entry for this appliction's label, create it
        if(advertorial.address.label not in self.stored_advertorials[advertorial.address.protocol]):
            self.stored_advertorials[advertorial.address.protocol][advertorial.address.label] = set()

        # Add to 2d dictionary
        self.stored_advertorials[advertorial.address.protocol][advertorial.address.label].add(advertorial)
        



    def datagram_received(self, message, address):
        # Drop if discoverer is not running
        if(not self.running):
            return
        
        # This is an AMPP packet
        if(message[:4] == b"AMPP"):
            # Set the address protocol
            address.protocol = "AMPP"
            
            # Store the peer address
            self.ampp_peers[address.get_hash()] = address

            if(message[4:7] == b"SUB"):
                # Deserialise Subscribe Request
                subscription = Subscription.from_dict(umsgpack.unpackb(message[7:]))

                # Check to see if we have already received this message before
                if(subscription.id in self.subscription_forwarded_ids):
                    return

                # Add it if not
                self.subscription_forwarded_ids.add(subscription.id)

                subscription.address = address
                self.subscriptions[address.get_hash()] = subscription
                address_hash = address.get_hash()
                
                # Subscribe to these applications on all upstream peers
                for peer in self.ampp_peers.values():
                    if(peer.get_hash() != address_hash):
                        self.send_datagram(b"SUB" + umsgpack.packb(subscription.to_dict()), peer)


            elif(message[4:7] == b"ADV"):
                # Deserialise Advertise Request
                advertorial = Advertorial.from_dict(umsgpack.unpackb(message[7:]))

                # Check to see if we have already received this message before
                if(advertorial.id in self.advertorial_forwarded_ids):
                    return

                # Add it if not
                self.advertorial_forwarded_ids.add(advertorial.id)

                # Forward the message onto any peers who are subscribed to this application type
                self.send_advertorial(advertorial, address.get_hash())

                # If we are listening for this application, store it
                if(advertorial.address.protocol in self.local_subscriptions):
                    self.store_advertorial(advertorial)

            elif(message[4:7] == b"ADQ"):
                # Address request
                self.send_datagram(b"ADR" + address.get_binary_address(), address)

            elif(message[4:7] == b"ADR"):
                # Got an address
                reported_address = BAddress.from_serialised(message[7:])
                log.debug("%s sees us as %s" % (address, reported_address))
                self.peer_visible_addresses[reported_address.get_hash()] = reported_address.net_address


    def get_address(self):
        deferred = defer.Deferred()

        self.peer_visible_addresses = {}

        for peer in self.ampp_peers.values():
            self.send_datagram(b"ADQ", peer)
        
        # Return a result from responses soon
        reactor.callLater(3, self.check_address_query_timeout, deferred)
        return deferred

    def check_address_query_timeout(self, deferred):
        deferred.callback(self.peer_visible_addresses.values())


    def send_advertorial(self, advertorial, excludePeerHash = None):
        count = 0
        for subscription in self.subscriptions.values():
            if(advertorial.address.protocol in subscription.applications) and (subscription.address.get_hash() != excludePeerHash):
                count += 1
                self.send_datagram(b"ADV" + umsgpack.packb(advertorial.to_dict()), subscription.address)

        if(excludePeerHash == None):
            log.debug("Sent advertorial to %i peers" % count)


    def send_datagram(self, message, address):
        if(address.address_type in self.networks):
            self.networks[address.address_type].send_datagram(b"AMPP" + message, address)
        else:
            log.error("Failed to send datagram to '%s', no network of that type available" % address)


    def subscribe(self):
        # Send subscription request to all peers with our local subscriptions
        sub = Subscription()
        sub.applications = self.local_subscriptions
        for peer in self.ampp_peers.values():
            self.send_datagram(b"SUB" + umsgpack.packb(sub.to_dict()), peer)


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
        return self.deffered_result(0.1, True)

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
            else:
                bootstrapper.cancel()
        
        return deferred


    def boostrapper_available_result(self, result, bootstrapper, deferred):
        log.debug("Bootstraper test completed")
        # If the test succeeded, add to our list of available bootstrappers
        if(result):
            self.bootstrappers.append(bootstrapper)
        else:
            log.debug("A bootstrapper for network type %s is unavailable" % bootstrapers.network_type)
            bootstrapper.cancel()

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

