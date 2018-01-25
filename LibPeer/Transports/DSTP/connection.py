from twisted.internet import reactor, task
from LibPeer.Events import Receipt
from LibPeer.Transports.DSTP.metric import Metric
from LibPeer.Transports.DSTP.chunk import Chunk
from LibPeer.Events import Event
from LibPeer.Logging import log
import time
import struct


class Connection:
    RETRY_DELAY = 5
    CONNECT_TIMEOUT = 30
    PING_TIMEOUT = 5

    def __init__(self, address, channel, send_func):
        self.address = address
        self.channel = channel
        self.metric = Metric(address)
        self.connected = False
        self.connecting = True
        self.last_touch = 0
        self.send = send_func
        self.last_ping = 0
        self.last_pong = 0
        # TX
        self.to_send = []
        self.in_flight = {}
        self.receipts = {}
        self.last_chunk = "\x00" * 16
        # RX
        self.received = {}
        self.forgotten = set()
        # Null UUID represents start of connection
        self.forgotten.add("\x00" * 16)

        self.new_data = Event()

    MESSAGE_CONNECT_REQUEST = "\x05"
    MESSAGE_CONNECT_ACCEPT = "\x0D"
    MESSAGE_DISCONNECT = "\x18"
    MESSAGE_PING = "\x50"
    MESSAGE_PONG = "\x70"
    MESSAGE_CHUNK = "\x02"
    MESSAGE_CHUNK_ACKNOWLEDGE = "\x06"
    MESSAGE_CHUNK_NEGATIVE_ACKNOWLEDGE = "\x15"

    def process_message(self, data):
        ident = data[:1]
        if(ident == Connection.MESSAGE_CONNECT_REQUEST):
            if(self.connected == False):
                self.send_message(Connection.MESSAGE_CONNECT_ACCEPT)
                self.connected = True
                self.connecting = False
                self.schedule_check_alive()

        elif(ident == Connection.MESSAGE_CONNECT_ACCEPT):
            if(self.connecting):
                self.connected = True
                self.connecting = False
                self.schedule_check_alive()

            else:
                log.debug("Got connection accept message while already connected, ignoring")

        elif(ident == Connection.MESSAGE_DISCONNECT):
            self.connected = False

        elif(ident == Connection.MESSAGE_PING):
            if(self.connected):
                self.send_message(Connection.MESSAGE_PONG)
            else:
                log.debug("Dorment connection issued ping, ignoring")

        elif(ident == Connection.MESSAGE_PONG):
            self.last_pong = time.time()

        elif(ident == Connection.MESSAGE_CHUNK):
            self.process_chunk(data[1:])

        elif(ident == Connection.MESSAGE_CHUNK_NEGATIVE_ACKNOWLEDGE):
            log.debug("Got negative acknowledge")
            if(data[1:] in self.in_flight):
                self.send_chunk(self.in_flight[data[1:]])

        elif(ident == Connection.MESSAGE_CHUNK_ACKNOWLEDGE):
            if(data[1:17] in self.in_flight):
                del self.in_flight[data[1:17]]
                self.metric.packet_acknowledged(struct.unpack('d', data[17:])[0])
                # End of a message!
                if(data[1:17] in self.receipts):
                    self.receipts[data[1:17]].success()
                    del self.receipts[data[1:17]]

        self.do_send()

    def send_message(self, type, data = ""):
        self.send(self, "%s%s" % (type, data))

    def process_chunk(self, data=""):
        # Create the chunk object
        chunk = Chunk.from_string(data)
        if(chunk.valid):
            self.send_message(Connection.MESSAGE_CHUNK_ACKNOWLEDGE, chunk.id + struct.pack('d', chunk.time_sent))

            if(chunk.id in self.forgotten or chunk.id in self.received):
                log.debug("Duplicate chunk")

            else:
                self.received[chunk.id] = chunk

                if(self.assembleable(chunk)):
                    message = self.assemble_and_forget(chunk)
                    self.new_data.call(self, message)

        else:
            self.send_message(Connection.MESSAGE_CHUNK_NEGATIVE_ACKNOWLEDGE, chunk.id)

    def send_chunk(self, chunk):
        self.in_flight[chunk.id] = chunk
        self.send_message(Connection.MESSAGE_CHUNK, chunk.serialise())
        self.metric.packet_sent()

    def assembleable(self, chunk):
        if(chunk.after in self.forgotten):
            return True
        elif(chunk.after in self.received):
            return self.assembleable(self.received[chunk.after])
        else:
            return False

    def assemble_and_forget(self, chunk):
        # Forget chunk
        del self.received[chunk.id]
        self.forgotten.add(chunk.id)

        # Assemble data
        if(chunk.after in self.forgotten):
            return chunk.data
        else:
            return self.assemble_and_forget(self.received[chunk.after]) + chunk.data

    def do_send(self):
        if(self.connected):
            size = int(self.metric.get_window_size())
            in_flight = self.in_flight.itervalues()

            resend_count = 0
            for chunk in set(in_flight):
                if(chunk.time_sent < time.time() - Connection.RETRY_DELAY):
                    # Timeout: Resend
                    self.send_chunk(chunk)
                    resend_count += 1

            size -= resend_count

            if(size < 1):
                size = 1

            for i in range(size):
                if(len(self.to_send) > 0):
                    chunk = self.to_send.pop(0)
                    self.send_chunk(chunk)
                
    def send_data(self, data):
        chunks = Chunk.create_chunks(data, self.last_chunk)
        receipt = Receipt()
        self.receipts[chunks[-1].id] = receipt
        self.last_chunk = chunks[-1].id

        self.to_send += chunks

        if(not self.connected):
            self.connect()

        else:
            self.do_send()

        return receipt


    def connect(self):
        self.connecting = True
        self.send_message(Connection.MESSAGE_CONNECT_REQUEST)
        task.deferLater(reactor, Connection.CONNECT_TIMEOUT, self.connect_timeout)

    def connect_timeout(self):
        if(self.connected):
            return

        self.connecting = False
        self.fail_all_remaining("Connection timed out")

    def schedule_check_alive(self):
        task.deferLater(reactor, Connection.PING_TIMEOUT, self.check_alive)

    def check_alive(self):
        if(self.connected):
            self.last_ping = time.time()
            self.send_message(Connection.MESSAGE_PING)
            task.deferLater(reactor, Connection.PING_TIMEOUT, self.check_alive_timeout)

    def check_alive_timeout(self):
        if(self.connected):
            self.connected = self.last_ping < self.last_pong

            if(not self.connected):
                self.fail_all_remaining("Connection with peer expired")
                log.info("Connection with peer %s expired" % str(self.address))
            else:
                self.schedule_check_alive()

    def fail_all_remaining(self, reason):
        for i in self.receipts.itervalues():
            i.failure(reason)