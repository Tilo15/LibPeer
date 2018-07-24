# IRCP - InterRouter Communications Protocol

from LibPeer.Formats.baddress import BAddress
from LibPeer.Formats.umsgpack import packb, unpackb
import uuid

class ICRP:
    def __init__(self):
        # Note in the context of this class, a node is a LibPeer peer,
        # and a peer is an other fellow router
        self.router_id = uuid.uuid4().bytes
        self.node_routes = {}
        self.peer_addresses = {}

    def datagram_received(self, datagram, address: BAddress, netid):
        # Is it a telemetry message?
        if(datagram[:1] == b"T"):
            # Unpack the datagram
            data = unpackb(datagram[1:])

            # Get the message type
            message_type = data["type"]

            # Route declaration message
            if(message_type == "route"):
                # The node's address as seen by it's nearest router
                initial_address = BAddress.from_serialised(data["initial_address"]

                # The node's routing identifier
                node_id = data["node_id"]

                # Get the router id of the router that sent this message
                router_id = data["router_id"]

                # Get the route to the node
                route = data["route"]

                # Check if this router's id features in the route already
                if(self.router_id in route):
                    # Drop
                    return

                # Add the router to our map of peers
                self.peer_addresses[router_id] = address

                # Add the node to our map if it isn't there
                if(node_id not in self.node_routes):
                    self.node_routes[node_id] = []

                # Add the route to the node
                self.node_routes[]




            
