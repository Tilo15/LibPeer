
from LibPeer.Discovery import DHT
from LibPeer.Transports import LMTP
from LibPeer.Networks import ipv4
from LibPeer.Logging import log
import LibPeer.Manager
import traceback
import time

log.settings(True, 0)

# Create the discoverer
discoverer = DHT.DHT()

# Create the manager
# 	Application Name: helloworld
#	Discoverer      : our discoverer
#	Cache File Path : cachefile
m = LibPeer.Manager.Manager("badftp", discoverer, "cachefile")

# Register a network and transport with the manager
net = m.add_network(ipv4.IPv4, local=False)
trans = m.add_transport(LMTP.LMTP)

def incoming_message(message_object):
	print("New message from %s:" % str(message_object.peer.address))
	f = open("incoming", 'w')
	f.write(message_object.data)
	f.close()
	print("Saved to 'incoming'")


def send_fail(message):
	print("A file failed to send: %s" % message)

def send_success():
	print("File sent in %s seconds!" % (time.time() - started))

# Make this peer discoverable
m.set_discoverable(True)

# Subscribe to incoming data
m.subscribe(incoming_message)

# Start up the manager
m.run()

time.sleep(10)

started = 0

try:
	while(True):
		filename = raw_input("File Name >")
		if(filename == "#"):
			break

		if(filename[0] == "'" and filename[-1] == "'"):
			filename = filename[1:-1]

		peers = m.get_peers()
		for i in range(len(peers)):
			print("%i:  %s" % (i, str(peers[i].address)))

		peer = peers[int(raw_input("Send to Peer No. >"))]
		
		f = open(filename, 'r')
		started = time.time()
		peer.send_message(trans, f.read()).subscribe(send_success, send_fail)
		f.close()

except Exception:
	print(traceback.format_exc())


m.stop()
