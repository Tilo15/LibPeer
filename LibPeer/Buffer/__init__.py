from LibPeer.Logging import log
import threading

class Buffer:
    def __init__(self, transport, address, channel="\x00"*16, max_length=1073741824):
        self.bufferstring = ""
        self.transport = transport
        self.address = address
        self.channel = channel
        self.max_length = max_length
        self.new_data = threading.Event()
        self.transport.data_received.subscribe(self.data_received)

        self.not_sending = threading.Event()
        self.not_sending.set()
        self.error = False
        self.error_message = ""
        self.send_complete = threading.Event()

    def data_received(self, protoId, address, channel, obj):
        if(self.address.get_hash() == address.get_hash() and channel == self.channel):
            if(isinstance(obj, basestring)):
                self.bufferstring += obj
                clip = len(self.bufferstring) - self.max_length
                if(clip > 0):
                    self.bufferstring = self.bufferstring[clip:]

                self.new_data.set()

            else:
                log.warn("Buffer object cannot buffer non-string data, incoming message dropped")

    def read(self, count=0):
        if(count == 0):
            count = len(self.bufferstring)

        while(len(self.bufferstring) != count):
            self.new_data.wait()
            self.new_data.clear()

        data = self.bufferstring[:count]
        self.bufferstring = self.bufferstring[count:]

        return data

    def write(self, data):
        # Wait for any in process send operation
        self.not_sending.wait()
        self.not_sending.clear()

        threading.Thread(target=self.threded_write, args=(data,)).start()

        self.send_complete.wait()
        self.send_complete.clear()

        if(self.error):
            message = self.error_message
            self.error_message = ""
            self.error = False
            self.not_sending.set()
            raise IOError(message)
            
        else:
            self.not_sending.set()
            return


    def threded_write(self, data):
        receipt = self.transport.send(data, self.address, self.channel)
        receipt.subscribe(self.write_success, self.write_error)

    def write_success(self):
        self.error = False
        self.send_complete.set()

    def write_error(self, message):
        self.error_message = message
        self.error = True
        self.send_complete.set()