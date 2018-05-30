import hashlib
import uuid

from LibPeer.Logging import log
from LibPeer.Muxer import parcel
from LibPeer.Formats import baddress
from LibPeer.Formats.butil import *


class Muxer:

    def __init__(self):
        self.receivedMessages = []
        self.transports = {}
        self.networks = {}
    
    def add_transport(self, transport):
        self.transports[transport.id] = transport

    def add_network(self, network):
        self.networks[network.type] = network


    def datagram_received(self, message, address):
        if len(message) < 37:
            # Ignore messages smaller than the min length
            return

        if message[:3] == b'MXR':
            messageId = message[3:19]
            messageChannel = message[19:35]
            messageTransportProtocol = message[35:36]
            messageApplicationProtocol = message[36:message[36:].find(b"\x02") + 36]
            address.protocol = messageApplicationProtocol
            message = message[message[36:].find(b"\x02") + 37:]

            if(messageId not in self.receivedMessages):
                self.receivedMessages.append(messageId)
                _parcel = parcel.Parcel(messageChannel, messageTransportProtocol, message, address)
                if(messageTransportProtocol == b'\xFF'):
                    log.warn("protocol 255 is reserved; dropping")
                elif(messageTransportProtocol in self.transports):
                    self.transports[messageTransportProtocol].parcel_received(_parcel)
                else:
                    log.error("protocol not registered")
            else:
                log.debug("dropping duplicate parcel")


    def send_parcel(self, parcel):
        message = b'MXR' + uuid.uuid4().bytes + parcel.channel + parcel.protocol + sb(parcel.address.protocol) + b'\x02' + parcel.message
        return self.networks[parcel.address.address_type].send_datagram(message, parcel.address)
        
            
