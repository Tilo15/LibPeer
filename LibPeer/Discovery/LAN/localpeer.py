import time

from LibPeer.Formats.baddress import BAddress


class LocalPeer:
    def __init__(self, peer_data):
        self.address = BAddress.from_serialised(peer_data)
        self.timestamp = time.time()
