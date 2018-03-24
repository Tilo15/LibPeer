from LibPeer.Formats.baddress import BAddress


class Subscription:
    def __init__(self):
        self.applications = []
        self.address = None

    def to_dict(self):
        return {
            "subscriptions": self.applications
        }

    @staticmethod
    def from_dict(data):
        self.applications = data["subscriptions"]