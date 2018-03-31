
from LibPeer.Discovery import AMPP
from LibPeer.Discovery import LAN
from LibPeer.Transports import DSTP
from LibPeer.Networks import ipv4
from LibPeer.Logging import log
import LibPeer.Manager
import traceback
import time
import os

log.settings(True, 0)

# Create the discoverer
discoverer = AMPP.AMPP(["badftp2"])
#discoverer = LAN.LAN()

# Create the manager
# 	Application Name: badftp2
#	Discoverer      : our discoverer
#	Cache File Path : cachefile
m = LibPeer.Manager.Manager("badftp2", discoverer, "cachefile")

# Register a network and transport with the manager
net = m.add_network(ipv4.IPv4, local=True)
trans = m.add_transport(DSTP.DSTP)

# Also add the network to the AMPP discoverer
discoverer.add_network(net)

incoming = {}

def incoming_message(message_object):
	to_process = message_object.data
	peer = message_object.peer.address.get_hash()

	if(peer not in incoming and to_process[0] == "F"):
		to_process = to_process[1:]

		# Get details
		is_size = False
		size = ""
		name = ""
		while True:
			c = to_process[0]
			to_process = to_process[1:]
			if(c == ":"):
				is_size = True
			elif(c == "\n"):
				break
			elif(is_size):
				size += c
			elif(not is_size):
				name += c

		size = int(size)
		f = open(name, 'w')
		incoming[peer] = [name, size, 0, f]

	if(len(to_process) > 0 and peer in incoming):
		item = incoming[peer]
		item[3].write(to_process)
		item[2] += len(to_process)
		log.info("%s - %i%% (%i/%i)" % (item[0], int((item[2] / float(item[1]) * 100)), item[2], item[1]))
		if(item[1] == item[2]):
			item[3].close()
			del incoming[peer]
			log.info("File downloaded!")

	
outgoing = {}

def fail(message, file, peer, size):
	log.error("%s failed to send: %s" % (file, message))

def continuation(file, peer, size):
	f = outgoing[file]
	data = f.read(1228800)
	if(len(data) == 0):
		f.close()
		log.info("File sent in %.2f seconds" % (time.time() - started))
	else:
		log.info("%s - %i%% (%i/%i)" % (file, int((f.tell() / float(size) * 100)), f.tell(), size))
		peer.send_message(trans, data).subscribe(continuation, fail, args=(filename, peer, size))


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

		outgoing[filename] = f

		size = os.path.getsize(filename)
		peer.send_message(trans, "F%s:%i\n" % (filename.split('/')[-1], size)).subscribe(continuation, fail, args=(filename, peer, size))
		

except Exception:
	print(traceback.format_exc())


m.stop()
