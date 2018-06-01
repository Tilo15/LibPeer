from LibPeer.Logging import log
from LibPeer.Manager import Manager
from LibPeer.Manager.message import Message
from LibPeer.Transports import Transport
from LibPeer.Manager.peer import Peer


class Interface:
    '''An interface is the layber between the modifiers/transport layer, and the application,
    it provides its own API for facilitating communication between peers.
    '''
    def __init__(self):
        self.name = ""
        self.usable_transports = []

    def begin(self, manager: Manager, channel=b'\x00'*16, transport = None):
        ''''''
        # Set channel
        self.channel = channel

        # Initialise transport
        self.transport: Transport  = None

        # Get reference to get peers method
        self.get_peers = manager.get_peers

        # Get reference to manager's call method
        self.safe_call = manager.call

        # If a transport was passed in use that
        if(transport != None):
            self.transport = transport
        
        else:
            for trans in self.usable_transports:
                if(trans in manager.transports):
                    self.transport = manager.transports[trans]
            
            if(self.transport == None):
                log.error("Unable to find suitable transport in supplied manager")
                return False

        manager.subscribe(self._receive_message, self.channel)

        # Set ready to true
        self.ready = True

        return True


    def is_ready(self):
        '''Determines if the interface has been initialised'''
        if(hasattr(self, 'ready')):
            if(self.ready):
                return True

        return False

    def _begin(self):
        pass

    def _receive_message(self, message: Message):
        raise NotImplementedError

    def _send_data(self, data, peer: Peer):
        return peer.send_message(self.transport, data, self.channel)