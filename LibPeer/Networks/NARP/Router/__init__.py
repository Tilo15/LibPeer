from LibPeer.Networks import Network
from LibPeer.Logging import log
from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats import umsgpack
from LibPeer.Networks.NARP import router_reply_codes
from LibPeer.Networks.NARP.address_util import AddressUtil
from LibPeer.Networks.NARP.Router.dummy_muxer import DummyMuxer
from LibPeer.Networks.NARP.Router.AMPP import IndependantAMPP
from LibPeer.Networks.NARP.Router.NARP import IndependantNARP
from twisted.internet import reactor
import uuid
import struct
import base64

# TODO not at all even really started
# make your own Muxer for this I think

class NARPRouter:
    def __init__(self, networks):
        self.router_id = uuid.uuid4().bytes

        self.muxer = DummyMuxer()
        self.networks = {}
        # Dict of a dict
        self.network_addresses = {}
        self.network_discoverers = {}
        self.network_narps = {}

        self.advertised_addresses = set()

        for network in networks:
            # Create a unique id for this network
            netid = uuid.uuid4().bytes
            self.networks[netid] = network

            # Subscribe to new data
            network.datagram_received.subscribe(self.datagram_received, netid)

            # Create an AMPP instance for this network
            discoverer = IndependantAMPP(network, netid, self.router_id)
            self.network_discoverers[netid] = discoverer

            # Create a NARP instance for this network
            narp = IndependantNARP(network)
            self.network_narps[netid] = narp

            # Create the dict for this network
            self.network_addresses[netid] = {}

            # Subscribe to discovered addresses
            discoverer.new_address.subscribe(self.handle_new_address)

            # Subscribe to new subscriptions
            discoverer.new_subscription.subscribe(self.propogate_subscription)

            # Start the discoverer
            discoverer.start_discoverer()

            # Start advertising
            #self.get_addresses(netid)


    def get_addresses(self, netid):
        # Get discoverer
        discoverer: IndependantAMPP = self.network_discoverers[netid]

        # Get addresses from discoverer
        discoverer.get_address().addCallback(self.got_addresses, netid)

    def got_addresses(self, addresses, netid):
        # Get the discoverer
        discoverer: IndependantAMPP = self.network_discoverers[netid]   

        # Get the network
        network: Network = self.networks[netid]    

        # Get address suggestions as BAddresses
        badds = self.handle_address_suggestions(addresses, netid)

        # Advertise each address
        for addr in badds:
            discoverer.advertise(addr, 5)

        # After the suggested amount of time, start again
        reactor.callLater(discoverer.recommended_rebroadcast_interval, self.get_addresses, netid)

    def handle_address_suggestions(self, addresses, netid):
        baddresses = set()

        network: Network = self.networks[netid]

        # Loop over each suggestion
        for address_suggestion in addresses:
            # Get the BAddress from the network using the suggestion
            net_address = network.get_address(address_suggestion[0])

            # If the address is valid
            if(type(net_address) is tuple):
                # Create a BAddress with NARP as the application
                peer_address = BAddress("NARP", net_address[0], net_address[1], address_type=network.type)

                # Log what we are seen as
                log.debug("This router can be identified as %s" % peer_address)

                # Advertise
                baddresses.add(peer_address)

                # Keep note that this is one of our addresses
                self.advertised_addresses.add(peer_address.get_hash())

            else:
                log.info("Address suggestion '%s' rejected by %s network controller" % (ss(address_suggestion[0]), network.type))

        return baddresses
        
            

    def handle_new_address(self, address: BAddress, network_id: bytes, hops_left: int):
        # Don't forward AMPP advertorials across networks
        if(address.protocol == "AMPP"):
            log.debug("Not forwarding AMPP advertorial across networks")
            return

        network: Network = self.networks[network_id]
        if(network.type != address.address_type and network.type != "NARP"):
            # TODO allow NARP addresses through when we can handle them
            log.debug("Not forwarding advetorial with incorrect network type")
            return

        # Determine next hop address
        next_hop = AddressUtil.get_next_hop_address(address)

        # Make sure it isn't one of our addresses

        # Get routable address
        new_address = self.create_routable_address(address, network_id)

        # Advertise this new address
        # TODO, loop over each network and send out the address wrapped in that network's interface's address
        for netid, discoverer in self.network_discoverers.items():
            # Skip if this is the originating network
            if(network_id == netid):
                continue

            # Query peers for our address
            discoverer.get_address().addCallback(self.network_address_determined, discoverer, new_address, netid, hops_left)


    def create_routable_address(self, address: BAddress, network_id: bytes):
        # Get the hash of the address
        address_hash = address.get_hash()

        # Store the address against the hash
        self.network_addresses[network_id][address_hash] = address

        # Create a NARP address
        new_address = BAddress(
            address.protocol,
            # Address is network ID because that is the
            # least specific part of the address
            base64.b64encode(network_id),
            # Address hash is Port because that is the
            # most specific part of the address
            base64.b64encode(address_hash),
            address.label,
            "NARP"
        )

        # Return the new routable address
        return new_address



    def network_address_determined(self, addresses, discoverer: IndependantAMPP, narp_address: BAddress, netid, ttl: int):
        # Get address suggestions as BAddresses
        badds = self.handle_address_suggestions(addresses, netid)

        log.info("Forwarding translated advertorial")

        # Loop over each address we were given
        for address in badds:
            # Save the address's protocol
            protocol = narp_address.protocol

            # Set it to an empty string
            narp_address.protocol = ""

            # Wrap the address around the routable address
            adv_address = AddressUtil.add_outer_hop(address, narp_address)

            # Set the new address's protocol to the narp_address's original protocol
            adv_address.protocol = protocol

            # Advertise this address
            discoverer.advertise(adv_address, ttl)


    def propogate_subscription(self, subscription, network_id):
        log.debug("Propogating subscription for: %s" % ", ".join(subscription.applications))
        # Send subscription to all networks
        for netid, network in self.network_addresses.items():
            # Don't send to the network of origin
            if(netid != network_id):
                discoverer: IndependantAMPP = self.network_discoverers[netid]

                # Send the subscription
                discoverer.cross_network_subscription(subscription)

    
    def datagram_received(self, datagram, address: BAddress, netid):
        # New datagram from one of our networks
        # Check if it is a NARP packet destaned for a router
        if(datagram[:5] == b"NARPR"):
            # Catch any errors
            #try:
                # Valid identifier
                data:bytes = datagram[5:]

                # Get address field length
                addrlen = struct.unpack('!Q', data[:8])[0]

                narp_address = b""

                # Catch address parsing errors
                #try:
                if True:
                    # Get the BAddress of this packet
                    narp_address = BAddress.from_serialised(data[8:addrlen+8])
                #except:
                    # Send error
                #    self.send_pran(router_reply_codes.PRAN_BAD_ADDRESS, None, address, netid)
                #    log.info("NARP user sent invalid address")
                #    return

                # Note that the BAddress is not wrapped at this point
                # Make sure the network from the address exists
                net_address = base64.b64decode(narp_address.net_address)
                if(net_address not in self.network_addresses):
                    # Send error
                    self.send_pran(router_reply_codes.PRAN_NOT_FOUND, {"Address": str(narp_address)}, address, netid)
                    log.info("Could not find destination network for packet")
                    return


                # Make sure the destination exists
                port = base64.b64decode(narp_address.port)
                if(port not in self.network_addresses[net_address]):
                    # Send error
                    self.send_pran(router_reply_codes.PRAN_NOT_FOUND, {"Address": str(narp_address)}, address, netid)
                    log.info("Could not find destination host for packet")
                    return

                # Get the destination network
                dest_network: Network = self.networks[net_address]

                # Get the destination's real address
                dest_address: BAddress = self.network_addresses[net_address][port]


                # Construct the reply address
                reply_address = self.create_routable_address(address, netid)
                reply_address.protocol = ""

                # Serialise the reply address
                serialised_reply = reply_address.get_binary_address()

                # Determine the length of the reply address
                reply_address_size = len(serialised_reply)

                # Construct new datagram
                forwarded_data = b"NARPU"
                forwarded_data += struct.pack("!Q", reply_address_size)
                forwarded_data += serialised_reply
                forwarded_data += data[addrlen+8:]

                # Catch any network errors
                #try:
                if True:
                    # Forward the data to it's destination
                    log.info("Forward packet from %s to %s" % (address, dest_address))
                    dest_network.send_datagram(forwarded_data, dest_address)
                    print(data[addrlen+8:])
                #except:
                    # Send error
                #    self.send_pran(router_reply_codes.PRAN_NETWORK_UNAVAILABLE, None, address, netid)
                #    log.error("Failed to send packet to address '%s'" % address)
                #    return

            #except Exception as e:
                # Send error
            #    self.send_pran(router_reply_codes.PRAN_INTERNAL_ERROR, None, address, netid)
            #    log.critical("Internal router error: " + str(e))
            #    return
        
        elif(datagram[:5] == b"NARPU"):
            log.debug("Got NARP user message, ignoring")

                


    
    def send_pran(self, code, message, address: BAddress, netid):
        # Get reference to the network
        network: Network = self.networks[netid]

        # Add PRAN identifier
        data = b"PRAN"

        # Add PRAN code
        data += struct.pack("!H", code)

        # If there is a message, add it
        if(message):
            # Add message
            data += umsgpack.packb(message)

        # Send it
        network.send_datagram(data, address)

