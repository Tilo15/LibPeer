from LibPeer.Formats.baddress import BAddress
import uuid

class Subscription:
    def __init__(self):
        self.applications = []
        self.address = None
        self.id = uuid.uuid4().bytes

    def to_dict(self):
        return {
            "subscriptions": self.applications,
            "id": self.id
        }

    @staticmethod
    def from_dict(data):
        s = Subscription()
        s.applications = data["subscriptions"]
        s.id = data["id"]
        return s