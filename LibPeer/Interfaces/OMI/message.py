from LibPeer.Formats.umsgpack import unpackb, packb

import uuid
import struct

class Message:
    def __init__(self, obj: dict, ttl: int = 30):
        self.id = uuid.uuid4().bytes
        self.object = obj
        self.ttl = ttl

        self._data_size = 0
        self._received_data = b""

    def _new_data(self, data: bytes):
        self._received_data += data

        if(len(self._received_data) >= self._data_size):
            self.object = unpackb(self._received_data)
            return True
            
        return False

    def serialise(self):
        # Serialise the dict
        obj_data = packb(self.object)

        # Frame it
        frame = struct.pack("!LB", len(obj_data), self.ttl)
        frame += self.id
        frame += obj_data

        # Return the framed object
        return frame




    @staticmethod
    def new_for_incoming(objId: bytes, ttl: int, size: int):
        msg = Message({}, ttl - 1)
        msg._data_size = size
        msg.id = objId
        return msg