from LibPeer.Logging import log
from LibPeer.Discovery.AMPP import AMPP
from LibPeer.Manager import Manager
from LibPeer.Networks.ipv4 import IPv4
from LibPeer.Transports.DSTP import DSTP
from LibPeer.Interfaces.DSI import DSI
from LibPeer.Interfaces.DSI.connection import Connection


log.settings(True, 0)

discoverer = AMPP(["ifaceTest"])
manager = Manager("ifaceTest", discoverer
network = manager.add_network(IPv4, local=True)
transpo = manager.add_transport(DSTP)
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

interface.new_connection.subscribe(new_connection)

while True:
    line = sys.stdin.readline()

    if(line == '#\n'):
        break

    print("FINDING NEW PEERS")
    for peer in manager.get_peers():
        print("FOUND %s" % peer)
        try:
            connection = interface.connect(peer)
            connections.add(connection)
            threading.Thread(target=listen_to_peer, args=(connection,)).start()
        except:
            print ("FAILED TO CONNECT TO PEER %s" % peer)

    for connection in connections:
        print("SENDING TO %s" % connection.peer.address)
        try:
            connection.send(line)
        except:
            print("UNABLE TO SEND TO %s" % connection.peer)

    print ("DONE")

for connection in connections:
    connection.close()

manager.stop()

print("EXIT")
exit()