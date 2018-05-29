class Discoverer:
    def __init__(self):
        self.recommended_rebroadcast_interval = 40

    def start_discoverer(self, cachePath):
        raise NotImplementedError

    def get_address(self):
        raise NotImplementedError

    def advertise(self, peer_address):
        raise NotImplementedError

    def get_peers(self, application, label=""):
        raise NotImplementedError

    def stop_discoverer(self):
        raise NotImplementedError