from LibPeer.Networks import Network
from LibPeer.Logging import log
from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats import umsgpack
from LibPeer.Networks.NARP import router_reply_codes
from LibPeer.Networks.NARP.address_util import AddressUtil
from LibPeer.Networks.NARP.Router.dummy_muxer import DummyMuxer
from LibPeer.Networks.NARP.Router.AMPP import IndependantAMPP
import uuid
import struct

# TODO not at all even really started
# make your own Muxer for this I think

class NARPRouter:
    def __init__(self, networks):
        self.muxer = DummyMuxer()
        self.networks = {}
        # Dict of a dict
        self.network_addresses = {}
        self.network_discoverers = {}

        for network in networks:
            # Create a unique id for this network
            netid = uuid.uuid4()
            self.networks[netid] = network

            # Subscribe to new data
            network.datagram_received.subscribe(self.datagram_received, netid)

            # Create an AMPP instance for this network
            discoverer = IndependantAMPP(network, netid)
            self.network_discoverers[netid] = discoverer

            # Create the dict for this network
            self.network_addresses[netid] = {}

            # Subscribe to discovered addresses
            discoverer.new_address.subscribe(self.handle_new_address)
            

    def handle_new_address(self, address: BAddress, network_id: bytes):
        # Get the address hash
        address_hash = address.get_hash()

        # Store the address against the hash
        self.network_addresses[network_id][address_hash] = address

        # Create a NARP address
        new_address = BAddress(
            address.protocol,
            # Address is network ID because that is the
            # least specific part of the address
            base64.b64encode(self.network_id),
            # Address hash is Port because that is the
            # most specific part of the address
            base64.b64encode(address_hash),
            address.label,
            "NARP"
        )

        # Advertise this new address
        # TODO, loop over each network and send out the address wrapped in that network's interface's address
        for discoverer in self.network_discoverers.values():
            # Skip if this is the originating network
            if(self.network_discoverers[network_id] == discoverer):
                pass

            # Query peers for our address
            discoverer.get_address().addCallback(self.network_address_determined, discoverer, new_address)


    def network_address_determined(self, addresses, discoverer: IndependantAMPP, narp_address: BAddress):
        # Loop over each address we were given
        for address in addresses:
            # Wrap the address around the routable address
            adv_address = AddressUtil.add_outer_hop(address, narp_address)

            # Advertise this address
            discoverer.advertise(adv_address)


    def propogate_subscription(self, subscription, network_id):
        # Send subscription to all networks
        for netid, network in self.network_addresses.items():
            # Don't send to the network of origin
            if(netid != network_id):
                discoverer: IndependantAMPP = self.network_discoverers[netid]

                # Send the subscription
                discoverer.cross_network_subscription(subscription)

    
    def datagram_received(self, datagram, address: BAddress, netid):
        # New datagram from one of our networks
        # Check if it is a NARP packet
        if(datagram[:4] == "NARP"):
            # Catch any errors
            try:
                # Valid identifier
                data:bytes = datagram[4:]

                # Get address field length
                addrlen = struct.unpack('!Q', data[:8])

                # Catch address parsing errors
                try:
                    # Get the BAddress of this packet
                    narp_address = BAddress.from_serialised(data[8:addrlen+8])
                except:
                    # Send error
                    self.send_pran(router_reply_codes.PRAN_BAD_ADDRESS, None, address, netid)
                    return

                # Note that the BAddress is not wrapped at this point
                # Make sure the network from the address exists
                if(narp_address.net_address not in self.network_addresses):
                    # Send error
                    self.send_pran(router_reply_codes.PRAN_NOT_FOUND, {"Address": str(narp_address)}, address, netid)
                    return

                # Make sure the destination exists
                if(narp_address.port not in self.network_addresses[narp_address.net_address]):
                    # Send error
                    self.send_pran(router_reply_codes.PRAN_NOT_FOUND, {"Address": str(narp_address)}, address, netid)
                    return

                # Get the destination network
                dest_network: Network = self.networks[narp_address.net_address]

                # Get the destination's real address
                dest_address: BAddress = self.network_addresses[narp_address.net_address][narp_address.port]

                # Catch any network errors
                try:
                    # Forward the data to it's destination
                    dest_network.send_datagram # TODO

                


    
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

