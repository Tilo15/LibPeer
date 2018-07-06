# SODI, Solicited Object and Data Interface

from LibPeer.Logging import log
from LibPeer.Interfaces import Interface
from LibPeer import Transports
from LibPeer.Manager.message import Message
from LibPeer.Formats.butil import sb, ss
from LibPeer.Formats.umsgpack import unpackb, packb
from LibPeer.Events import Event
from LibPeer.Interfaces.SODI.solicitation import Solicitation
from LibPeer.Interfaces.SODI.reply import Reply
from LibPeer.Interfaces.SODI.query import Query

import struct

class SODI(Interface):
    def __init__(self):
        self.name = "SODI"
        self.usable_transports = [Transports.TRANSPORT_DSTP]
        self.solicitations = {}
        self.received_query = Event()


    def _receive_message(self, message: Message):
        addr_hash = message.peer.address.get_hash()
        if(addr_hash in self.solicitations):
            # We have requested something from this peer
            solicitation: Solicitation = self.solicitations[addr_hash]

            if(solicitation.reply != None):
                # We already have a reply going for this one
                # Pass the message to the reply
                solicitation.reply._chunk_received(message.data)

            else:
                # Since the solicitation is valid but there is no reply object
                # this must be the start of a reply. Get the size of the reply
                object_size = struct.unpack("!L", message.data[:4])[0]

                # Get the solicitation token for the reply
                token = message.data[4:20]

                # Make sure the token matches the expected one
                if(solicitation.token == token):
                    # Create the reply object
                    solicitation.reply = Reply(message.peer, object_size, solicitation.token)

                    # Subscribe to the final step of receiving the reply
                    solicitation.reply.data_ready.subscribe(self._reply_finished, solicitation)

                    # Notify the application that we got a response
                    solicitation.response.call(solicitation)

                    # Send the data to the reply object
                    solicitation.reply._chunk_received(message.data[20:])

                else:
                    log.debug("Received reply from valid peer with invalid token")

        else:
            # We aren't expecting a reply from this peer, so it must be a solicitation, get it's size
            sol_size = struct.unpack("!H", message.data[:2])[0]

            # Deserialise
            solicitation = Solicitation.from_dict(unpackb(message.data[2:sol_size + 2]))


            # Create the query object for the application to handle
            query = Query(solicitation, self, message.peer)

            # Notify the application
            self.received_query.call(query)



    def _reply_finished(self, solicitation: Solicitation):
        # Remove the solicitation from the list
        del self.solicitations[solicitation.peer.address.get_hash()]



    def send_solicitation(self, solicitation: Solicitation):
        '''Send the solicitation to it's peer'''

        # Serialise the solicitation
        sol_data = packb(solicitation.to_dict())

        # Frame the solicitation
        frame = struct.pack("!H", len(sol_data))
        frame += sol_data

        # Save the solicitation against the address
        self.solicitations[solicitation.peer.address.get_hash()] = solicitation

        # Send the frame
        self._send_data(frame, solicitation.peer)

        # Return the solicitation
        return solicitation



