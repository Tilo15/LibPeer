from LibPeer.Networks.NARP.Router import NARPRouter
from LibPeer.Networks.NARP.Router.dummy_muxer import DummyMuxer
from LibPeer.Networks.ipv4 import IPv4
from LibPeer.Networks.NARP import NARP
from LibPeer.Logging import log
from twisted.internet import reactor

# TODO make configurable

log.settings(True, 1)

muxer = DummyMuxer()

networks = [
    IPv4(muxer, True, 8000, "192.168.1.5"),
    IPv4(muxer, True, 8000, "192.168.2.5")
    ]

router = NARPRouter(networks)

reactor.run(installSignalHandlers=False)