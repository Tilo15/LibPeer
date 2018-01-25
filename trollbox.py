
from LibPeer.Discovery import LAN
from LibPeer.Transports import DSTP
from LibPeer.Networks import ipv4
from LibPeer.Logging import log
import LibPeer.Manager
import traceback

log.settings(True, 0)

# Create the discoverer
discoverer = LAN.LAN()

# Create the manager
# 	Application Name: helloworld
#	Discoverer      : our discoverer
#	Cache File Path : cachefile
m = LibPeer.Manager.Manager("helloworld", discoverer, "cachefile")

# Register a network and transport with the manager
net = m.add_network(ipv4.IPv4, local=True)
trans = m.add_transport(DSTP.DSTP)

def incoming_message(message_object):
	print
	print("New message from %s:" % str(message_object.peer.address))
	print("    %s" % message_object.data)
	print

def send_fail(message):
	print("A message failed to send: %s" % message)

def send_success():
	print("Message sent!")

# Make this peer discoverable
m.set_discoverable(True)

# Subscribe to incoming data
m.subscribe(incoming_message)

# Start up the manager
m.run()

try:
	while(True):
		print
		print("Type a message:")
		message = raw_input()
		if(message == "#"):
			break

		if(message == "ping"):
			for peer in m.get_peers():
				peer.ping()

		else:
			for peer in m.get_peers():
				peer.send_message(trans, message).subscribe(send_success, send_fail)
				#print("Sent your message to %s" % str(peer.address))

except Exception:
	print(traceback.format_exc())


m.stop()
