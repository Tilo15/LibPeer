import time
from LibPeer.Formats.baddress import BAddress

class Advertorial:
    def __init__(self):
        self.address = None
        self.application = ""
        self.tags = []
        self.hops_left = 0
        self.lifespan = 0
        self.time_received = time.time()

    def is_current(self):
        return (time.time() - self.time_received) < self.lifespan

    def to_dict(self):
        return {
            "address": self.address.get_binary_address(),
            "tags": self.tags,
            "ttl": self.hops_left - 1,
            "expires_in": self.lifespan
        }
    
    @staticmethod
    def from_dict(data):
        obj = Advertorial()
        obj.address = BAddress.from_serialised(data["address"])
        obj.tags = data["tags"]
        obj.hops_left = data["ttl"]
        obj.lifespan = data["expires_in"]
        return obj