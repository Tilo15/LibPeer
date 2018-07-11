# NARP - Network Agnostic Routing Protocol

from LibPeer.Networks import Network
from LibPeer.Logging import log
from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats import umsgpack
from LibPeer.Networks.NARP.address_util import AddressUtil
from LibPeer.Events import Event
from LibPeer.Muxer import Muxer
import struct

class NARP(Network):
    def __init__(self, muxer: Muxer):
        self.datagram_received = Event()
        self.router_reply = Event()
        self.muxer: Muxer = muxer
        self.type = "NARP"
        
        for network in self.muxer.networks.values():
            network.datagram_received.subscribe(self.network_received_data, network)

        self.muxer.add_network(self)

        
    def network_received_data(self, datagram: bytes, address: BAddress, network: Network):
        # New datagram from underlying network
        # Check if it is for us
        if(datagram[:5] == "NARPU"):
            # Valid identifier
            data:bytes = datagram[5:]

            # Get address field length
            addrlen = struct.unpack('!Q', data[:8])

            # Get the BAddress of this packet
            inner_narp_address = BAddress.from_serialised(data[8:addrlen+8])

            # Add the next hop address to the address we ultimately return
            narp_address = AddressUtil.add_outer_hop(address, inner_narp_address)

            # Get the encapsulated datagram
            encap_datagram = data[addrlen+8:]
            
            # If the encapsulated datagram is another NARP packet
            # unwrap that before sending to the muxer
            if(encap_datagram[:5] == "NARPU"):
                # If we got here from unwrapping another NARP packet
                # keep the original NARP address instead of using the new one
                if(network == "NARP"):
                    narp_address = address

                # Unwrap the child NARP packet
                return self.network_received_data(encap_datagram, narp_address, "NARP")

            elif(encap_datagram[:4] == "AMPP"):
                # AMPP should never transported over NARP,
                # instead, the NARP router should pass along AMPP messages
                # over the network that NARP is runing atop of.
                # That way, the router can translate addresses from different networks
                # to a NARP address that can be routed through the node.
                log.info("Dropping AMPP message sent over NARP")

            else:
                # Send the datagram up the chain
                self.datagram_received.call(encap_datagram, narp_address)

        # Router reply message
        elif(datagram[:4] == "PRAN"):
            # Get message code
            code = struct.unpack("!H", datagram[4:6])

            # Return the code and message object
            self.router_reply.call(code, umsgpack.unpackb(datagram[6:]))




    def send_datagram(self, message, address: BAddress):
        # Unwrap the two needed addresses from the NARP address
        next_hop = AddressUtil.get_next_hop_address(address)
        narp_address = AddressUtil.remove_outer_hop(address)

        # Serialise the NARP BAddress
        bnarp_address = narp_address.get_binary_address()

        # Construct the NARP datagram
        datagram = b"NARPR"

        # Add the address information
        datagram += struct.pack("!Q", len(bnarp_address))
        datagram += bnarp_address

        # Add the message
        datagram += message

        # Find the appropriate network to send the datagram to
        network: Network = self.muxer.networks[next_hop.address_type]

        # Send the datagram to the next hop address
        return network.send_datagram(datagram, next_hop)


    def get_address(self, peer_suggestion):
        # We can have many NARP addresses, but we should never know them.
        # The suggestion from the peer is probably wrong and even if it
        # is right, it's probably only be right for the machines sharing a network
        # with it. There is zero point in actually using a suggestion from
        # a peer for a NARP address, so let's just say that whatever
        # random information this peer thinks it posesses to reach a correct
        # concolusion about what our address is will in fact be misguided,
        # wrong, and detremential to the network and be over with it, okay?
        return None
        
                
                


            
