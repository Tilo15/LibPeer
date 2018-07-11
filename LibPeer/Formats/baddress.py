import hashlib
import binascii
from LibPeer.Formats.butil import *


class BAddress:
    HASH_LENGTH = 32

    def __init__(self, protocol, net_address, port, label="", address_type="IPv4"):
        self.protocol = protocol
        self.net_address = net_address
        self.port = port
        self.label = label
        self.address_type = address_type

    def get_binary_address(self):
        data = b"\x01" + sb(self.protocol)
        if (self.label != ""):
            if (len(self.label) == BAddress.HASH_LENGTH):
                data += b"/%s" % sb(self.label)
            else:
                raise ValueError("Invalid label size of %i" % len(self.label))
        else:
            data += b"\x02"

        # Make port a string if it is not
        port = self.port
        if(type(port) is int):
            port = str(self.port)

        data += b"%s\x1F%s\x1F%s\x04" % (sb(self.address_type), sb(self.net_address), sb(port))
        return data

    @staticmethod
    def from_serialised(data):        
        protocol = b""
        label = b""
        body = b""
        headerComplete = False
        headerStarted = False
        hashStarted = False
        hashIndex = 0
        for i in range(len(data)):
            if (not headerStarted):
                if (data[i] == 1):
                    headerStarted = True

            elif(hashStarted):
                hashIndex += 1
                label += data[i]
                if(hashIndex >= BAddress.HASH_LENGTH):
                    headerComplete = True
                    hashStarted = False

            elif (not headerComplete):
                if (data[i] == 2):
                    headerComplete = True
                elif (data[i] == 47): # Ascii '/'
                    hashStarted = True
                else:
                    protocol += bytes([data[i]])

            else:
                if (data[i] == 4):
                    break
                else:
                    body += bytes([data[i]])

        bodyData = body.split(b"\x1F")
        return BAddress(ss(protocol), ss(bodyData[1]), ss(bodyData[2]), ss(label), ss(bodyData[0]))

    @staticmethod
    def array_from_serialised(data, application=""):
        items = set(data.split(b"\x04")[:-1])
        if(application == ""):
            return [BAddress.from_serialised(item) for item in items]
        else:
            addresses = []
            for item in items:
                addr = BAddress.from_serialised(item)
                if(addr.protocol == application):
                    addresses.append(addr)

            return addresses

    def get_hash(self):
        return hashlib.sha256(concatb(self.address_type, self.net_address, str(self.port))).digest()


    def __str__(self):
        string = ""

        # Make port a string if it is not
        port = self.port
        if(type(port) is int):
            port = str(self.port)

        if(self.protocol != None):
            labelHex = binascii.hexlify(sb(self.label))
            string = "%s[%s://%s:%s/%s]" % st(self.address_type, self.protocol, self.net_address, port, labelHex)
        else:
            string = "%s[%s:%s]" % st(self.address_type, self.net_address, port)
        return string


def label_from_text(text):
    return hashlib.sha256(text).digest()
