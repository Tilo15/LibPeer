from LibPeer.Logging import log
from LibPeer.Discovery.AMPP import AMPP
from LibPeer.Manager import Manager
from LibPeer.Manager.peer import Peer
from LibPeer.Networks.ipv4 import IPv4
from LibPeer.Transports.DSTP import DSTP
from LibPeer.Interfaces.OMI import OMI
from LibPeer.Interfaces.OMI.message import Message
from LibPeer.Events.awaiter import ReceiptAwaiter

import time
import threading
import glob
import os
import sys


log.settings(True, 0)

discoverer = AMPP(["omitest"])
manager = Manager("omitest", discoverer)
network = manager.add_network(IPv4, local=True)
transpo = manager.add_transport(DSTP, full_checksum=False)
discoverer.add_network(network)

interface = OMI()
interface.begin(manager)

def new_message(message: Message, peer: Peer):
    print("\nNEW MESSAGE FROM %s" % peer)
    print("SUBJECT: %s" % message.object["subject"])
    print("MESSAGE: %s\n" % message.object["body"])

interface.new_message.subscribe(new_message)

manager.set_discoverable(True)
manager.run()

while True:
    # Get user data
    subject = input("Subject > ")
    body = input("Message > ")

    # Create message object
    msg = Message({"subject": subject, "body": body})
    
    # Find peers
    peers = manager.get_peers()

    # Send to the peers
    sent = 0
    for peer in peers:
        #try:
            ReceiptAwaiter(interface.send, msg, peer)
            sent += 1
        #except:
        #    print("Failed to send to peer %s" % peer)

    print("Sent message to %i peers" % sent)

