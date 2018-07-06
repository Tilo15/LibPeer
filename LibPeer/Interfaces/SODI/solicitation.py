from LibPeer.Manager.peer import Peer
from LibPeer.Interfaces.SODI.reply import Reply
from LibPeer.Events import Event
from LibPeer.Events.awaiter import EventAwaiter

import uuid
import time


class Solicitation:
    def __init__(self, query: str, peer: Peer):
        self.peer = peer
        self.token = uuid.uuid4().bytes
        self.query = query
        self.reply: Reply = None
        self.response = Event()

    def to_dict(self):
        return {
            "token": self.token,
            "query": self.query
        }

    def wait_for_object(self, timeout: int = 20):
        # Wait for the response event
        EventAwaiter(self.response, timeout)

        if(self.reply == None):
            # Wait for the object to be loaded
            EventAwaiter(self.reply.object_ready, timeout)

        # Return the object
        return self.reply.object

        

    @staticmethod
    def from_dict(data: dict):
        solicitation = Solicitation(data["query"], None)
        solicitation.token = data["token"]
        return solicitation