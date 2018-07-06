from LibPeer.Manager.peer import Peer
from LibPeer.Interfaces.SODI.reply import Reply
from LibPeer.Events import Event
import uuid



class Solicitation:
    def __init__(self, query: str, peer: Peer):
        self.peer = peer
        self.token = uuid.uuid4()
        self.query = query
        self.reply: Reply = None
        self.response = Event()

    def to_dict(self):
        return {
            "token": self.token,
            "query": self.query
        }

    @staticmethod
    def from_dict(data: dict):
        solicitation = Solicitation(data["query"], None)
        solicitation.token = data["token"]
        return solicitation