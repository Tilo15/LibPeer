from twisted.internet import reactor, task
from LibPeer.Events import Receipt
from LibPeer.Transports.DSTP.metric import Metric
from LibPeer.Transports.DSTP.chunk import Chunk
from LibPeer.Events import Event
from LibPeer.Logging import log
from LibPeer.Formats.butil import *
import time
import struct


class Connection:
    RETRY_DELAY = 0.5
    CONNECT_TIMEOUT = 30
    PING_TIMEOUT = 5
    SEND_RETRY_TIMEOUT = 5
    PING_MAX_RETRIES = 10

    def __init__(self, address, channel, send_func):
        log.debug("new connection with %s instanciated" % address)
        self.address = address
        self.channel = channel
        self.metric = Metric(address)
        self.connected = False
        self.connecting = True
        self.last_touch = 0
        self.send = send_func
        self.last_ping = 0
        self.last_pong = 0
        self.ping_retries = 0
        # TX
        self.to_send = []
        self.in_flight = {}
        self.receipts = {}
        self.last_chunk = b"\x00" * 16
        self.last_send = 0
        # RX
        self.received = {}
        self.forgotten = set()
        self.forgotten.add(b"\x00" * 16)
        self.assembling = False
        self.assemble_queue = []

        self.new_data = Event()

    MESSAGE_CONNECT_REQUEST = b"\x05"
    MESSAGE_CONNECT_ACCEPT = b"\x0D"
    MESSAGE_DISCONNECT = b"\x18"
    MESSAGE_RESET = b"\x10"
    MESSAGE_PING = b"\x50"
    MESSAGE_PONG = b"\x70"
    MESSAGE_CHUNK = b"\x02"
    MESSAGE_CHUNK_ACKNOWLEDGE = b"\x06"
    MESSAGE_CHUNK_NEGATIVE_ACKNOWLEDGE = b"\x15"

    def process_message(self, data):
        ident = data[:1]
        if(ident == Connection.MESSAGE_CONNECT_REQUEST):
            if(self.connected == False):
                self.send_message(Connection.MESSAGE_CONNECT_ACCEPT)
                self.connected = True
                self.connecting = False
                self.schedule_check_alive()
                self.do_send()
            else:
                self.send_message(Connection.MESSAGE_RESET)

        elif(ident == Connection.MESSAGE_CONNECT_ACCEPT):
            if(self.connecting):
                self.connected = True
                self.connecting = False
                self.schedule_check_alive()
                self.do_send()

            else:
                log.debug("Got connection accept message while already connected, ignoring")

        elif(ident == Connection.MESSAGE_DISCONNECT):
            self.connected = False
            log.info("Connection closed by remote peer")
            self.fail_all_remaining("Connection ended by remote peer")

        elif(ident == Connection.MESSAGE_RESET):
            self.connected = False
            self.fail_all_remaining("The connection was reset")
            self.connect()

        elif(ident == Connection.MESSAGE_PING):
            if(self.connected):
                self.send_message(Connection.MESSAGE_PONG)
            else:
                log.debug("Dorment connection issued ping")
                self.send_message(Connection.MESSAGE_DISCONNECT)

        elif(ident == Connection.MESSAGE_PONG):
            self.last_pong = time.time()
            self.ping_retries = 0
            if(self.last_send < time.time() - Connection.SEND_RETRY_TIMEOUT):
                self.do_send()

        elif(ident == Connection.MESSAGE_CHUNK):
            self.process_chunk(data[1:])

        elif(ident == Connection.MESSAGE_CHUNK_NEGATIVE_ACKNOWLEDGE):
            self.metric.packet_negative_acknowledged()
            log.debug("Got negative acknowledge")
            if(data[1:] in self.in_flight):
                self.send_chunk(self.in_flight[data[1:]])

        elif(ident == Connection.MESSAGE_CHUNK_ACKNOWLEDGE):
            if(data[1:17] in self.in_flight):
                del self.in_flight[data[1:17]]
                self.metric.packet_acknowledged(struct.unpack('!d', data[17:])[0])
                # End of a message!
                if(data[1:17] in self.receipts):
                    self.receipts[data[1:17]].success()
                    del self.receipts[data[1:17]]

                self.do_send()

    def send_message(self, type, data = ""):
        self.send(self, concatb(type, data))

    def process_chunk(self, data=""):
        # Create the chunk object
        chunk = Chunk.from_string(data)
        if(chunk.valid):
            self.send_message(Connection.MESSAGE_CHUNK_ACKNOWLEDGE, chunk.id + struct.pack('!d', chunk.time_sent))

            if(chunk.id in self.forgotten) or (chunk.id in self.received):
                log.debug("Duplicate chunk")

            else:
                self.received[chunk.id] = chunk

                assembleable, culprit = self.assembleable(chunk)
                if(assembleable):
                    self.assemble_and_forget(chunk)

        else:
            self.send_message(Connection.MESSAGE_CHUNK_NEGATIVE_ACKNOWLEDGE, chunk.id)

    def send_chunk(self, chunk):
        self.in_flight[chunk.id] = chunk
        #try:
        self.send_message(Connection.MESSAGE_CHUNK, chunk.serialise())
        #except:
        #log.warn("Packet dropped")

    def assembleable(self, chunk):
        while True:
            if(chunk.after in self.forgotten):
                return (True, chunk.after)
            elif(chunk.after in self.received):
                chunk = self.received[chunk.after]
            else:
                return (False, chunk.after)

    def assemble_and_forget(self, chunk):
        if(self.assembling):
            self.assemble_queue.append(chunk)
        else:
            self.assembling = True
            data = b""
            while True:
                if(chunk.id not in self.received):
                    # Chunk already processed, line up another
                    if(len(self.assemble_queue) > 0):
                        chunk = self.assemble_queue.pop()
                    else:
                        self.assembling = False
                        break
                
                else:
                    del self.received[chunk.id]
                    self.forgotten.add(chunk.id)

                    # Prepend data from the current chunk
                    data = chunk.data + data

                    if(chunk.after in self.forgotten):
                        # Last chunk in this line of assembly
                        # Pass along assembled data
                        self.new_data.call(self, data)
                        # Reset and line up next assembly (if any)
                        data = ""
                        if(len(self.assemble_queue) > 0):
                            chunk = self.assemble_queue.pop()
                        else:
                            self.assembling = False
                            break
                    
                    # Line up the next chunk
                    else:
                        chunk = self.received[chunk.after]


    def do_send(self):
        if(self.connected):
            self.last_send = time.time()
            size = int(self.metric.get_window_size())
            in_flight = self.in_flight.values()

            size -= len(self.in_flight)

            resend_count = 0
            for chunk in set(in_flight):
                if(chunk.time_sent < time.time() - (self.metric.last_packet_delay + Connection.RETRY_DELAY)):
                    # Timeout: Resend
                    self.send_chunk(chunk)
                    resend_count += 1
                if(resend_count > size):
                    break

            size -= resend_count

            if(size < 1):
                size = 0

            for i in range(size):
                if(len(self.to_send) > 0):
                    chunk = self.to_send.pop(0)
                    self.metric.packet_sent()
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
            failed = self.last_ping > self.last_pong
            if(failed):
                self.ping_retries += 1
                if(self.ping_retries > Connection.PING_MAX_RETRIES):
                    self.connected = False
                    self.fail_all_remaining("Connection with peer expired")
                    log.info("Connection with peer %s expired" % str(self.address))
                else:
                    self.check_alive()

            else:
                self.schedule_check_alive()
            

    def fail_all_remaining(self, reason):
        for i in self.receipts.values():
            i.failure(reason)
        self.receipts = {}

        if(not self.connected):
            # Tidy up
            self.to_send = []
            self.in_flight = {}
            self.receipts = {}
            self.last_chunk = b"\x00" * 16
            self.last_send = 0
            # RX
            self.received = {}
            self.forgotten = set()
            self.forgotten.add(b"\x00" * 16)
            self.assembling = False
            self.assemble_queue = []