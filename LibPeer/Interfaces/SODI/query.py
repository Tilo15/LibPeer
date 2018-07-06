from LibPeer.Interfaces import Interface
from LibPeer.Interfaces.SODI.solicitation import Solicitation
from LibPeer.Formats.umsgpack import packb
from LibPeer.Manager.peer import Peer

import struct

class Query:
    def __init__(self, solicitation: Solicitation, interface: Interface, peer: Peer):
        self.solicitation = solicitation
        self.interface = interface
        self.peer = peer

        self.query = solicitation.query
        self.data_size = 0

        self._data_remaining = 0
        self._replying = False

    def reply(self, obj: dict, data_size: int = 0):
        '''Reply to a query request,
        object is the object to be sent in the reply, and
        data_size (optional, default = 0) is the length of the binary data that will be sent'''

        if(self._replying):
            raise Exception("Cannot reply to a solicitation twice")

        # Set the data size and remaining data
        self._data_remaining = data_size
        self.data_size = data_size

        # Serialise the object
        obj_data = packb(obj)

        # Create the frame
        frame = struct.pack("!L", len(obj_data))
        frame += self.solicitation.token
        frame += obj_data
        frame += struct.pack("!Q", data_size)

        # Send the frame
        self.interface._send_data(frame, self.peer)

        # Set replying status
        self._replying = True

    def send(self, data: bytes):
        '''Send the data section of the reply to the query. Must have called reply first'''

        if(not self._replying):
            raise Exception("Cannot send data before a reply has been made")

        if(self._data_remaining < len(data)):
            raise IOError("Data to send exceeds remaining data size limit")

        # Subtract the count
        self._data_remaining -= len(data)

        # Send the data
        self.interface._send_data(data, self.peer)


