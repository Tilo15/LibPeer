

import miniupnpc
import psutil
from LibPeer.Logging import log

class PublicPort:

    def __init__(self):
        self.port = None
        self.open = False
        self.net_address = None
        self.lan_address = None

        self.upnp = miniupnpc.UPnP()
        self.upnp.discoverdelay = 2000
        log.info("searching for UPnP devices")
        ndevices = self.upnp.discover()
        log.debug("%i UPnP devices found" % ndevices)

        self.upnp.selectigd()
        self.net_address = self.upnp.externalipaddress()
        self.lan_address = self.upnp.lanaddr

        log.info("IGD selected: our local IP is %s, our public IP is %s, and we are connected to the IGD on port %i" %
                    (str(self.lan_address), str(self.net_address), self.upnp.statusinfo()[1]))

        port = 7564 # We start one higher at 7565
        res = True
        while(res != None and port < 65536):
            port = port + 1
            # Skip port if it isn't free locally
            while(not PublicPort.is_local_port_free(port)):
		        port = port + 1
            res = self.upnp.getspecificportmapping(port, 'UDP')

        success = self.upnp.addportmapping(port, 'UDP', self.lan_address, port, 'LibPeer. by Billy Barrow (www.pcthingz.com) operating on port %u' % port, '')

        if(success):
            log.info("port %i is now forwarded to this machine by the IGD" % port)
            self.port = port
            self.open = True

        else:
            log.warn("failed to forward port %i on the IGD" % port)


    def close(self):
        if(self.open):
            success = self.upnp.deleteportmapping(self.port, 'UDP')
            self.open = not success
            if(self.open):
                log.warn("failed to close port %i on the IGD" % self.port)
            else:
                log.info("closed port %i on the IGD" % self.port)
            return success
        
        else:
            log.warn("attempt to close already closed port ignored")


    @staticmethod
    def is_local_port_free(port):
        connections = psutil.net_connections()
        for connection in connections:
            if (connection.laddr[1] == port):
                return False
        return True
        