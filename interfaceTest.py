from LibPeer.Logging import log
from LibPeer.Discovery.AMPP import AMPP
from LibPeer.Manager import Manager
from LibPeer.Networks.ipv4 import IPv4
from LibPeer.Transports.DSTP import DSTP
from LibPeer.Transports.EDP import EDP
from LibPeer.Interfaces.DSI import DSI
from LibPeer.Interfaces.DSI.connection import Connection


log.settings(True, 0)

discoverer = AMPP(["ifaceTest"])
manager = Manager("ifaceTest", discoverer, "test")
network = manager.add_network(IPv4, local=True)
transpo = manager.add_transport(EDP)
discoverer.add_network(network)

interface = DSI()
interface.begin(manager)

manager.set_discoverable(True)
manager.run()




import sys
import threading


connections = set()

def new_connection(connection: Connection):
    connections.add(connection)
    threading.Thread(target=listen_to_peer, args=(connection,)).start()

def listen_to_peer(connection: Connection):
    while True:
        print("%s: %s" %  (connection.peer.address, connection.read(10)))

while True:
    line = sys.stdin.readline()

    print("FINDING NEW PEERS")
    for peer in manager.get_peers():
        print("FOUND %s" % peer)
        connection = interface.connect(peer)
        connections.add(connection)
        threading.Thread(target=listen_to_peer, args=(connection,)).start()

    for connection in connections:
        print("SENDING TO %s" % connection.peer.address)
        try:
            connection.send(line)
        except:
            print("UNABLE TO SEND TO %s" % connection.peer)

    print ("DONE")
