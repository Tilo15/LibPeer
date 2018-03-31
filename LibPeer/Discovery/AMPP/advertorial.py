import time
import uuid
from LibPeer.Formats.baddress import BAddress

class Advertorial:
    def __init__(self):
        self.address = None
        self.hops_left = 0
        self.lifespan = 0
        self.time_received = time.time()
        self.id = uuid.uuid4().bytes

    def is_current(self):
        return (time.time() - self.time_received) < self.lifespan

    def to_dict(self):
        return {
            b"address": self.address.get_binary_address(),
            b"ttl": self.hops_left - 1,
            b"expires_in": self.lifespan,
            b"id": self.id
        }
    
    @staticmethod
    def from_dict(data):
        obj = Advertorial()
        obj.address = BAddress.from_serialised(data[b"address"])
        obj.hops_left = data[b"ttl"]
        obj.lifespan = data[b"expires_in"]
        obj.id = data[b"id"]
        return obj