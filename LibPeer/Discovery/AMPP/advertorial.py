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
            "address": self.address.get_binary_address(),
            "ttl": self.hops_left - 1,
            "expires_in": self.lifespan,
            "id": self.id
        }
    
    @staticmethod
    def from_dict(data):
        obj = Advertorial()
        obj.address = BAddress.from_serialised(data["address"])
        obj.hops_left = data["ttl"]
        obj.lifespan = data["expires_in"]
        obj.id = data["id"]
        return obj