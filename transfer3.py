from LibPeer.Logging import log
from LibPeer.Discovery.AMPP import AMPP
from LibPeer.Manager import Manager
from LibPeer.Networks.ipv4 import IPv4
from LibPeer.Transports.DSTP import DSTP
from LibPeer.Interfaces.DSI import DSI
from LibPeer.Interfaces.DSI.connection import Connection

import struct
import time
import threading


log.settings(True, 1)

discoverer = AMPP(["badftp3"])
manager = Manager("badftp3", discoverer)
network = manager.add_network(IPv4, local=True)
transpo = manager.add_transport(DSTP)
discoverer.add_network(network)

interface = DSI()
interface.begin(manager)

manager.set_discoverable(True)
manager.run()

def download_file(connection: Connection):
    size = struct.unpack("!Q", connection.read(8))[0]

    print("Receiving file... (%i bytes)" % size)

    f = open("download", 'wb')

    data = connection.read(size)

    print("Got %i bytes" % len(data))

    f.write(data)

    f.flush()

    f.close()

    print("Saved!")

    connection.close()

    print("Connection closed")

def new_connection(connection: Connection):
    threading.Thread(target=download_file, args=(connection,)).start()
    

interface.new_connection.subscribe(new_connection)

time.sleep(5)

while True:
    fileName = input("File >")

    if(fileName == ""):
        break

    peers = manager.get_peers()

    for peer in peers:
        print("[%i]  %s" % (peers.index(peer), peer))

    peerId = int(input("Peer >"))

    print("Loading File")

    f = open(fileName, 'rb')

    data = f.read()

    f.close()

    print("Sending File... (%i bytes)" % len(data))

    peer = peers[peerId]

    connection = interface.connect(peer)

    connection.send(struct.pack("!Q", len(data)))

    connection.send(data)

    print("File Sent!")



