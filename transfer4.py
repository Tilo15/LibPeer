from LibPeer.Logging import log
from LibPeer.Discovery.AMPP import AMPP
from LibPeer.Manager import Manager
from LibPeer.Networks.ipv4 import IPv4
from LibPeer.Transports.DSTP import DSTP
from LibPeer.Interfaces.SODI import SODI
from LibPeer.Interfaces.SODI.query import Query
from LibPeer.Interfaces.SODI.solicitation import Solicitation
from LibPeer.Events.awaiter import EventAwaiter

import time
import threading
import glob
import os
import sys


log.settings(True, 1)

discoverer = AMPP(["badftp4"])
manager = Manager("badftp4", discoverer, "test")
network = manager.add_network(IPv4, local=True)
transpo = manager.add_transport(DSTP)
discoverer.add_network(network)

interface = SODI()
interface.begin(manager)

manager.set_discoverable(True)
manager.run()

download_count = {}

def process_query(query: Query):
    if(query.query == "LIST"):
        # List files
        reply = {
            "files": glob.glob("ftp/*", recursive=True)
        }
        # Reply
        query.reply(reply)

    elif(query.query.startswith("GET ")):
        # Serve a file
        file_name = query.query[4:]

        # Increment the download count
        if(file_name in download_count):
            download_count[file_name] += 1
        else:
            download_count[file_name] = 1
        
        # Get the size of the file
        file_size = os.path.getsize(file_name)

        # Build a reply
        reply = {
            "file": file_name.split("/")[-1],
            "download_count": download_count[file_name]
        }

        # Reply
        query.reply(reply, file_size)

        # Send data
        f = open(file_name, 'rb')
        query.send(f.read())

    else:
        print ("Invalid query '%s'" % query.query)


def handle_query(query: Query):
    threading.Thread(target=process_query, args=(query,)).start()


interface.received_query.subscribe(handle_query)

time.sleep(15)

while True:

    peers = manager.get_peers()

    for peer in peers:
        print("[%i]  %s" % (peers.index(peer), peer))

    peerId = int(input("Query Peer >"))

    # Query the peer for files
    sol = Solicitation("LIST", peers[peerId])
    interface.send_solicitation(sol)

    # Wait for the reply
    listing = sol.wait_for_object()

    # List the options
    for option in listing["files"]:
        print("[%i]  %s" % (listing["files"].index(option), option))

    fileId = int(input("File >"))

    # Request that file from the server
    sol = Solicitation("GET %s" % listing["files"][fileId], peers[peerId])
    interface.send_solicitation(sol)

    # Wait for the reply
    info = sol.wait_for_object()

    # Print info
    print("'%s' has has %i hits" % (info["file"], info["download_count"]))

    # Get the file ready
    f = open(info["file"], 'wb')

    # Start reading
    while not sol.reply.complete:
        f.write(sol.reply.read())
        sys.stdout.write("Downloading file %.2f%% complete (%i/%i)\r" % (((sol.reply.data_received / float(sol.reply.data_size)) * 100), sol.reply.data_received, sol.reply.data_size))

    # Get remaining data in buffer
    f.write(sol.reply.read_all())

    f.close()

    print("\nDone!")


