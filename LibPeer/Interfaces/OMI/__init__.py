from LibPeer.Interfaces import Interface
from LibPeer import Transports
from LibPeer.Manager.message import Message as ManagerMessage
from LibPeer.Manager.peer import Peer
from LibPeer.Formats.umsgpack import packb, unpackb
from LibPeer.Interfaces.OMI.message import Message
from LibPeer.Events import Event

import struct

class OMI(Interface):
    def __init__(self):
        self.usable_transports = [Transports.TRANSPORT_DSTP, Transports.TRANSPORT_EDP]
        self.messages = {}
        self.new_message = Event()
        self.used_message_ids = set()

    def _receive_message(self, message: ManagerMessage):
        # Get list of peers
        peers = self.get_peers()

        peer_hash = message.peer.address.get_hash()

        if(peer_hash in self.messages):
            # Handle the message
            self._handle_message(message.data, message.peer, self.messages[peer_hash])

        else:
            # New message
            # Get the TTL and size of the message
            size, ttl = struct.unpack("!LB", message.data[:5])

            # Get the ID of the message
            msgId = message.data[5:21]

            # Ignore duplicate messages
            if(msgId in self.used_message_ids):
                return

            # Add to message set
            self.used_message_ids.add(msgId)

            # Create message object
            msg = Message.new_for_incoming(msgId, ttl, size)

            # Add message to map
            self.messages[peer_hash] = msg

            # Handle the message data
            self._handle_message(message.data[21:], message.peer, msg)


    def _handle_message(self, data: bytes, peer: Peer, message: Message):
        # Add data to the message
        complete = message._new_data(data)

        # If the message has been received fully
        if(complete):
            # Remove from messages map
            del self.messages[peer.address.get_hash()]

            # Notify application
            self.new_message.call(message, peer)


    def send(self, message: Message, peer: Peer):
        # Serialise
        data = message.serialise()

        # Send it
        return self._send_data(data, peer)

            


