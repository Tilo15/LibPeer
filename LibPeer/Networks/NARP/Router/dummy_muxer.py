from LibPeer.Muxer import Muxer

class DummyMuxer(Muxer):
    def datagram_received(self, message, address):
        # Ignore
        pass

    def send_parcel(self, parcel):
        raise NotImplementedError("Dummy muxer cannot send parcels")