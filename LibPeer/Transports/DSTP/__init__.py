import LibPeer.Events
from LibPeer.Muxer import parcel
from LibPeer.Transports import Transport
from LibPeer.Transports.LMTP import transaction
from LibPeer.Logging import log
from LibPeer.Transports.DSTP.connection import Connection
from LibPeer.Formats.butil import *
import uuid

# Data Stream Transport Protocol
# id = \x06


class DSTP(Transport):
    def __init__(self, muxer, *modifiers):
        self.muxer = muxer
        self.modifiers = modifiers
        self.id = b'\x06'
        self.muxer.add_transport(self)
        self.data_received = LibPeer.Events.Event()
        self.delay_target = 0.1
        self.channel_connections = {}

    def send(self, data, address, channel=b"\x00" * 16):
        connection = self.get_or_create_connection(address, sb(channel))
        return connection.send_data(sb(data))

    def parcel_received(self, _parcel):
        connection = self.get_or_create_connection(_parcel.address, _parcel.channel)
        connection.process_message(sb(_parcel.message))

    def get_or_create_connection(self, address, channel):
        hash = address.get_hash()
        if(channel not in self.channel_connections):
            self.channel_connections[channel] = {}

        if(hash not in self.channel_connections[channel]):
            connection = Connection(address, channel, self.connection_send)
            connection.new_data.subscribe(self.data_ready)
            self.channel_connections[channel][hash] = connection
        
        return self.channel_connections[channel][hash]

    def connection_send(self, connection, data):
	    _parcel = parcel.Parcel(connection.channel, self.id, data, connection.address)
	    self.muxer.send_parcel(_parcel)

    def data_ready(self, connection, data):
        address = connection.address
        channel = connection.channel

        obj = self.mod_decode(address, data)
        self.data_received.call(self.id, address, channel, obj)
