from LibPeer.Discovery.AMPP.bootstrapers import Bootstrapper
from LibPeer.Events import Event
from LibPeer.Logging import log
from twisted.internet import protocol
from twisted.protocols import basic
from twisted.internet import reactor
from twisted.internet import defer
import binascii
import uuid

class IPv4_IRC(Bootstrapper):
    def __init__(self):
        self.network_type = "IPv4"
        self.recommended_advertise_interval = 10

        self.helper: IRC_Helper = None
        self.factory = IRC_Helper_Factory()
        self.factory.ready.subscribe(self.connection_succeeded)
        self.factory.connection_failed.subscribe(self.connection_failed)

        self.irc_server = ("irc.freenode.net", 6667)
        self.irc_quit_message = "AMPP bootstrapper cancel called"

        self.test_defer = None
    
    def get_ampp_peers(self):
        '''Returns a deffered result of a list of BAddresses'''
        raise NotImplemented()

    def advertise(self, network):
        '''Returns a deffered result when the AMPP peer has been advertised'''
        raise NotImplemented()

    def test_availability(self, network):
        # Deferred
        self.test_defer = defer.Deferred()
        
        # Attempt to connect to server
        log.debug("Attempting to connect to the IRC server at %s:%i..." % self.irc_server)
        reactor.connectTCP(self.irc_server[0], self.irc_server[1], self.factory)

    def cancel(self):
        if(self.helper_ready()):
            self.log("Stopping IRC client")
            self.helper.quit(self.irc_quit_message)


    def helper_ready(self):
        return self.helper != None

    def connection_failed(self):
        # If we were testing, give back negative result
        if(self.test_defer != None):
            self.test_defer.callback(False)
            self.test_defer = None
        else:
            # Otherwise give error
            log.error("IRC server connection failed")

    def connection_succeeded(self, helper):
        # If we were testing, give back positive result
        if(self.test_defer != None):
            self.test_defer.callback(True)
            self.test_defer = None
        
        # Save reference to the IRC_Helper class
        self.helper = helper
            


class IRC_Helper(basic.LineReceiver):
    def __init__(self, ready_event):
        basic.LineReceiver.__init__(self)

        self.ready = ready_event
        self.channel = "#"
        self.nickname = binascii.hexlify(uuid.uuid4().bytes)

    def lineReceived(self, data):
        '''Received IRC data'''
        response_parts = data.split(b':')
        metadata = response_parts[1].split(b' ')
        message = response_parts[0]


    def send_message(self, message):


    def connectionMade(self):
        log.debug("Connection to IRC server made")
        self.sendLine("PASS none")
        self.sendLine("NICK %s" % self.nickname)
        self.ready.call(self)

    def receivedMOTD(self, motd):
        log.info("The IRC server sent us the message of the day:")
        for line in motd:
            log.info(line)

        log.info(" --")


class IRC_Helper_Factory(protocol.ClientFactory):
    def __init__():
        self.connection_failed = Event()
        self.ready = Event()

    def buildProtocol(self, addr):
        helper = IRC_Helper()
        return IRC_Helper()

    def clientConnectionLost(self, connector, reason):
        log.info("Got disconnected from IRC server, reconnecting")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log.warn("Failed to connect to IRC server: %s" % reason)
        self.connection_failed.call(reason)