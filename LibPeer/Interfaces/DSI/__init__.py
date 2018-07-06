# DSI, Data Streaming Interface

from LibPeer.Logging import log
from LibPeer.Interfaces import Interface
from LibPeer import Transports
from LibPeer.Manager.message import Message
from LibPeer.Interfaces.DSI.connection import Connection
from LibPeer.Formats.butil import sb, ss
from LibPeer.Events import Event

class DSI(Interface):
    def __init__(self):
        self.name = "DSI"
        self.usable_transports = [Transports.TRANSPORT_DSTP, Transports.TRANSPORT_EDP]
        self.connections = {}
        self.new_connection = Event()

    def _receive_message(self, message: Message):
        if(message.peer in self.connections):
            connection: Connection = self.connections[message.peer]
            connection._chunk_received(sb(message.data))
        
        else:
            connection = Connection(message.peer, self)
            connection._chunk_received(sb(message.data))
            self.connections[message.peer] = connection
            self.new_connection.call(connection)

    def connect(self, peer, timeout = 20):
        '''Connect to a peer'''
        if(peer in self.connections):
            log.warn("Already connected to peer %s" % peer)
            conn = self.connections[peer]
            conn.wait_for_connection(timeout)
            return conn
        else:
            conn = Connection(peer, self, True)
            self.connections[peer] = conn
            conn.wait_for_connection(timeout)
            return conn

