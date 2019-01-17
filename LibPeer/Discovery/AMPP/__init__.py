# Advertorial Message Passing Protocol

from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats import umsgpack
from LibPeer.Discovery.AMPP.subscription import Subscription
from LibPeer.Discovery.AMPP.advertorial import Advertorial
from LibPeer.Discovery.AMPP.bootstrapers import BOOTSTRAPPERS
from LibPeer.Discovery import Discoverer
from LibPeer.Formats.butil import sb
from LibPeer.Logging import log
from twisted.internet import reactor, defer
from copy import deepcopy
import operator
import uuid

class AMPP(Discoverer):
    def __init__(self, applications, broadcast_ttl = 30, instance_id = None):
        self.recommended_rebroadcast_interval = 5
        # This later gets changed to every five minutes after the first advertasment is sent
        # Every 5 minutes equates to approximately 41 kbps (with 100 byte packets) if connected to a million advertising peers

        self.networks = {}
        self.subscriptions = {}
        self.cached_advertorials = {}
        self.cache_limit = 100
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
        self.subscription_peers = set()

        self.instance_id = instance_id
        if(self.instance_id == None):
            self.instance_id = uuid.uuid4().bytes

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

            # Get the machine/instance identifier
            sender_id = message[4:20]

            # Ignore any packets with our instance id
            if(sender_id == self.instance_id):
                return
            
            # Store the peer address
            self.ampp_peers[address.get_hash()] = address

            if(message[20:23] == b"SUB"):
                # Deserialise Subscribe Request
                subscription = Subscription.from_dict(umsgpack.unpackb(message[23:]))

                # Check to see if we have already received this message before
                if(subscription.id in self.subscription_forwarded_ids):
                    return

                # Add it if not
                self.subscription_forwarded_ids.add(subscription.id)

                log.debug("%s asked to be subscribed to all messages for applications: %s" % (address, ", ".join(subscription.applications)) )

                # Automatically subscribe the new subscriber to the AMPP messages to help it find
                # other AMPP peers
                if("AMPP" not in subscription.applications):
                    subscription.applications.append("AMPP")

                subscription.address = address
                self.subscriptions[address.get_hash()] = subscription
                address_hash = address.get_hash()
                
                # Subscribe to these applications on all upstream peers
                for peer in self.ampp_peers.values():
                    if(peer.get_hash() != address_hash):
                        self.send_subsrciption(subscription, peer)


                if(not subscription.renewing):
                    # This is a new subscribe request, send any relevent cached peers
                    count = 0
                    for adv in self.cached_advertorials.values():
                        if(adv.address.protocol in subscription.applications):
                            # If this is an advertisment for a relevent application
                            # send it to the subscribing peer
                            self.send_datagram(b"ADV" + umsgpack.packb(adv.to_dict()), address)
                            count += 1
                    
                    log.debug("Sent %i relevent cached messages to subscribing peer" % count)



            elif(message[20:23] == b"ADV"):
                # Deserialise Advertise Request
                advertorial = Advertorial.from_dict(umsgpack.unpackb(message[23:]))

                # Check to see if we have already received this message before
                if(advertorial.id in self.advertorial_forwarded_ids):
                    return

                # Add it if not
                self.advertorial_forwarded_ids.add(advertorial.id)

                # If there is still life in it
                if(advertorial.hops_left > 0):
                    # Add message to cache
                    self.add_to_cache(advertorial)

                    # Forward the message onto any peers who are subscribed to this application type
                    self.send_advertorial(advertorial, address.get_hash())

                # If we are listening for this application, store it
                if(advertorial.address.protocol in self.local_subscriptions):
                    log.debug("Got advertorial from AMPP peer %s for address %s with %i hops left" % (address, advertorial.address, advertorial.hops_left))
                    self.store_advertorial(advertorial)

                if(advertorial.address.protocol == "AMPP"):
                    log.debug("Found additional AMPP peer %s via AMPP" % advertorial.address)
                    self.ampp_peers[advertorial.address.get_hash()] = advertorial.address

            elif(message[20:23] == b"ADQ"):
                # Address request
                self.send_datagram(b"ADR" + address.get_binary_address(), address)

            elif(message[20:23] == b"ADR"):
                # Got an address
                reported_address = BAddress.from_serialised(message[23:])
                log.debug("%s sees us as %s" % (address, reported_address))
                self.peer_visible_addresses[reported_address.get_hash()] = reported_address


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

        if(excludePeerHash == None) and (advertorial.address.protocol != "AMPP"):
            log.debug("Sent advertorial to %i peers" % count)
            if(count > 1):
                # Adjust the recommendation to every five minutes to not cause
                # network conjestion now that we have advertised to peers
                new_interval = (60 * 5)
                if(advertorial.address.protocol != "AMPP" and self.recommended_rebroadcast_interval != new_interval):
                    self.recommended_rebroadcast_interval = new_interval
                    # Now advertise with the new interval
                    self.advertise(advertorial.address)


    def send_subsrciption(self, sub, peer):
        self.send_datagram(b"SUB" + umsgpack.packb(sub.to_dict()), peer)



    def send_datagram(self, message, address):
        if(sb(address.address_type) == b"NARP"):
            log.debug("Not sending AMPP packet over NARP")

        elif(address.address_type in self.networks):
            self.networks[address.address_type].send_datagram(b"AMPP" + self.instance_id + message, address)
        else:
            log.error("Failed to send datagram to '%s', no network of that type available" % address)

    def add_to_cache(self, advertorial):
        self.cached_advertorials[advertorial.id] = advertorial
        self.clean_cache()

    def clean_cache(self):
        # Clean out old messages
        cadvs = deepcopy(self.cached_advertorials)
        for adv in cadvs.values():
            if(not adv.is_current()):
                del self.cached_advertorials[adv.id]
        
        if(self.cache_limit < len(self.cached_advertorials)):
            timeOrdered = sorted(self.cached_advertorials.values(), key=operator.attrgetter('time_received'))
            # We are still over the cache limit, delete some old entries even
            # though they haven't expired yet
            for i in range(len(self.cached_advertorials) - self.cache_limit):
                del self.cached_advertorials[timeOrdered[i].id]

    def subscribe(self):
        # Send subscription request to all peers with our local subscriptions
        sub = Subscription()
        sub.applications = self.local_subscriptions
        for peer in self.ampp_peers.values():
            # If this is the first time we've sent a subscribe message
            # to this peer, set renewing to false to get cached peers
            if(peer.get_hash() not in self.subscription_peers):
                self.subscription_peers.add(peer.get_hash())
                sub.renewing = False
            else:
                sub.renewing = True
            # Send the subscription
            self.send_subsrciption(sub, peer)


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

        # Take this opportunity to advertise the AMPP service itself
        ampp_advertorial = Advertorial()
        ampp_advertorial.address = BAddress("AMPP", peer_address.net_address, peer_address.port)
        ampp_advertorial.hops_left = int(self.broadcast_ttl / 2)
        ampp_advertorial.lifespan = self.recommended_rebroadcast_interval
        self.send_advertorial(ampp_advertorial)

        # Now, make sure our subscriptions haven't expired
        
        self.subscribe()

        # Notify the caller that this task has completed
        return self.deffered_result(0.1, True)

    def get_peers(self, application, label=""):
        # Before getting the advertorials, clean the pool
        self.clean_stored_advertorials()

        peers = []
        if(application in self.stored_advertorials):
            if(label in self.stored_advertorials[application]):
                for advertorial in self.stored_advertorials[application][label]:
                    if(advertorial.is_current()):
                        peers.append(advertorial.address)


        return self.deffered_result(0.1, peers)

    def clean_stored_advertorials(self):
        apps = self.stored_advertorials
        to_delete = set()
        for app in apps.keys():
            for label in apps[app].keys():
                for adv in apps[app][label]:
                    if(not adv.is_current()):
                        to_delete.add((app, label, adv))

        log.debug("Deleting %i expired advertorials" % len(to_delete))
        for item in to_delete:
            try:
                self.stored_advertorials[item[0]][item[1]].remove(item[2])
            except:
                log.error("Unable to remove stored advertorial")

        


    def start_discoverer(self):
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
            log.warn("A bootstrapper for network type %s is unavailable" % bootstrapers.network_type)
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

