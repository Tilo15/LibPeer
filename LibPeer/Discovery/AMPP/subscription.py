from LibPeer.Formats.baddress import BAddress
import uuid

class Subscription:
    def __init__(self):
        self.applications = []
        self.address = None
        self.renewing = False
        self.id = uuid.uuid4().bytes

    def to_dict(self):
        return {
            b"subscriptions": self.applications,
            b"id": self.id,
            b"renewing": self.renewing
        }

    @staticmethod
    def from_dict(data):
        s = Subscription()
        s.applications = data[b"subscriptions"]
        s.id = data[b"id"]
        s.renewing = data[b"renewing"]
        return s