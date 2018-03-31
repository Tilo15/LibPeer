from twisted.internet import reactor, task
from LibPeer.Logging import log
from LibPeer.Transports.LMTP import chunk
from LibPeer.Formats.butil import *
import LibPeer.Events
import struct
import time
import random
import binascii

class Transaction:
    TIMEOUT_CONNECTION = 30
    TIMEOUT_CHUNK = 2
    LATENCY_CHECK_INTERVAL = 5

    def __init__(self, id, address, channel, send_func, delay_target = 0.1):
        # Shared
        self.id = id
        self.address = address
        self.connected = False
        self.receiving = False
        self.channel = channel
        self.send = send_func
        self.on_cancel = LibPeer.Events.Event()
        self.size = 0
        self.did_connect = False

        # For sending only
        self.delay_target = delay_target
        self.receipt = LibPeer.Events.Receipt()
        self.window_size = 10
        self.max_resends = 10
        self.chunks_to_send = set()
        self.no_more_chunks = False
        self.chunks_in_flight = {}
        self.acknowledgements = 0
        self.additional_acknowledgements = 0
        self.sent_chunks = 0
        self.time_request_time = 0
        self.latency = 0.5
        self.window_sizes = []

        # For receiving only
        self.chunks = {}
        self.on_complete = LibPeer.Events.Event()



    def start(self, data):
        self.chunks_to_send = set(chunk.Chunker.chunkise(data))
        self.size = len(self.chunks_to_send)
        self.connect()

    def data_received(self, data):
        # First byte is the control code
        cc = data[:1]
        if(cc == b"\x05"):
            # Connection message
            self.cb_connection(data[1:])

        elif(cc == b"\x0C"):
            # Chunk
            self.chunk_received(data[1:])

        elif(cc == b"\x06"):
            # Acknowledgement
            self.chunk_acknowledged(data[1:])

        else:
            log.warn("invalid control code (%s) received" % b2s(binascii.hexlify(cc)))



    def chunk_received(self, data):
        # Create chunk object
        _chunk = chunk.Chunk.new_from_string(data)

        log.debug('Got chunk %i' % _chunk.sequence_number)

        # Is it valid?
        if(_chunk.valid):
            # Acknowledge the chunk, and return it's timestamp
            message = b"\x06" + struct.pack("dL", _chunk.timestamp, _chunk.sequence_number)
            self.send(self, message)
            # Add the chunk to our dict
            self.chunks[_chunk.sequence_number] = _chunk


    def on_connected(self):
        # Meature latency
        self.measure_latency()
        # Start sending (and resending) chunks!
        self.send_chunks()
        task.deferLater(reactor, self.delay_target, self.resend_chunks)
        # Every so often check the network latency to keep our calculations accurate
        task.deferLater(reactor, Transaction.LATENCY_CHECK_INTERVAL, self.measure_latency)

    def chunk_acknowledged(self, data):
        timestamp, sequence_number = struct.unpack("dL", data)
        if(sequence_number in self.chunks_in_flight):
            # The chunk has landed!
            self.acknowledgements += 1
            del self.chunks_in_flight[sequence_number]

        else:
            self.additional_acknowledgements += 1


        self.recalculate_window(timestamp)
        # Send more chunks!
        self.send_chunks()
    
    def send_chunks(self):
        if(len(self.chunks_in_flight) < int(self.window_size) and not self.no_more_chunks):
            # Send more chunks!
            count = int(self.window_size) - len(self.chunks_in_flight)
            for i in range(count):
                if(len(self.chunks_to_send) > 0):
                    _chunk = self.chunks_to_send.pop()
                    self.send_chunk(_chunk)
                    self.sent_chunks += 1
                else:
                    self.no_more_chunks = True
                    break

        if(self.no_more_chunks and len(self.chunks_in_flight) == 0):
            # Finished!
            self.send(self, b"\x05\x04")
            # For timing out:
            task.deferLater(reactor, Transaction.TIMEOUT_CONNECTION, self.disconnection_timeout)
            if(not self.receipt.complete):
                self.receipt.success()

    def send_chunk(self, _chunk):
        # put the chunk in flight
        self.chunks_in_flight[_chunk.sequence_number] = _chunk
        # time for take off!
        self.send(self, b"\x0c" + _chunk.serialise())

    def resend_chunks(self):
        if(self.connected and len(self.chunks_in_flight) > 0):
            # Pick a random in flight chunk and resend it
            ifc = self.chunks_in_flight.values()
            # Decide how many resends we should send
            amount = (self.window_size - len(self.chunks_in_flight))
            if(amount < 1):
                amount = 1

            for i in range(int(amount)):
                _chunk = random.choice(ifc)
                self.send_chunk(_chunk)
            # Reschedule
            task.deferLater(reactor, self.latency*2, self.resend_chunks)

    def recalculate_window(self, timestamp):
        delay_factor = (self.delay_target - (time.time() - timestamp - self.latency)) / self.delay_target
        window_factor = len(self.chunks_in_flight) / self.window_size
        gain = delay_factor * window_factor

        self.window_size += gain
        if(self.window_size < 1):
            self.window_size = 1

        log.info("Latency: %.8f\tGain: %.2f\tWindow: %i\tSent: %i\tAcknowledged: %i\tIn Flight: %i\tDelay: %.4fs\tTransfered: %.0f%%" % stf(self.latency, gain, self.window_size, self.sent_chunks, self.acknowledgements, len(self.chunks_in_flight), (time.time() - timestamp), (self.acknowledgements/float(self.size))*100))

    def connect(self):
        # Connect request with size of data
        message = b"\x05\x01" + struct.pack('Q', self.size)
        self.send(self, message)
        # Call the timeout checker
        task.deferLater(reactor, Transaction.TIMEOUT_CONNECTION, self.connection_timeout)

    def measure_latency(self):
        if(self.connected):
            self.time_request_time = time.time()
            self.send(self, b"\x05\x16\x05")
            task.deferLater(reactor, Transaction.LATENCY_CHECK_INTERVAL, self.measure_latency)

    def close(self):
        if(self.connected):
            # Cancel the current transaction
            self.send(self, b"\x05\x30")
            self.send(self, b"\x05\x30")
            self.connected = False
            self.on_cancel.call(self.id)

    def cb_connection(self, data):
        """For handling \\x05 (connection) messages"""
        if(data == b"\x06"): # ACK
            # Receiver acknowledged the transaction and is ready to receive
            self.connected = True
            self.did_connect = True
            self.receiving = False
            self.on_connected()

        elif(data == b"\x30"): # CAN
            # Party is canceling the transaction
            self.connected = False
            log.debug("transaction canceled")
            self.on_cancel.call(self.id)
            self.receipt.failure("transaction canceled by remote party")

        elif(data == b"\x04\x06"): # EOT ACK
            # Receiver acknowledges the end of the transaction
            self.connected = False
            log.info("peer acknowledged end of transaction")

        elif(data[:1] == b"\x01"): # SOH
            # Sender is ready to send
            self.size = struct.unpack("Q", data[1:])
            self.connected = True
            self.did_connect = True
            self.receiving = True
            # Tell sender to start sending
            self.send(self, b"\x05\x06")
            log.debug("accepted request to receive %i chunks" % self.size)

        elif(data == b"\x04"): # EOT
            # Sender has finished sending and wants to stop all communications
            self.send(self, b"\x05\x04\x06")
            self.connected = False
            # Reconstruct the message and pass it along
            self.on_complete.call(self.id, self.address, self.channel,self.dechunk_data())

        elif(data[:2] == b"\x16\x05"): # SYN ENQ
            # Sender wants to know the current time
            self.send(self, b"\x05\x16\x06" + struct.pack("d", time.time()))
            log.debug("sent current time to sender")

        elif(data[:2] == b"\x16\x06"): # SYN ACK
            # Receiver has sent us their current time
            if(self.time_request_time != 0):
                # We were waiting for this
                remote_time = struct.unpack("d", data[2:])[0]
                current_time = time.time()
                clock_difference = remote_time - self.time_request_time
                current_time += clock_difference
                self.latency = current_time - remote_time
                self.time_request_time = 0
                log.debug("a delay of %.3f seconds was measured" % self.latency)
            else:
                log.debug("ignoring time response because it was not requested")



        else:
            log.warn("invalid connection control message received")

    def connection_timeout(self):
        if(not self.did_connect):
            # Connection timed out
            # Cancel the connection in case the receiver is actually there
            self.send(self, b"\x05\x30")
            log.warn("set up of transaction '%s' to %s timed out" % (self.id.encode("hex"), str(self.address)))
            self.on_cancel.call(self.id)
            self.receipt.failure("transaction setup timed out")

    def disconnection_timeout(self):
        if(self.connected):
            log.debug("disconnection of transmission '%s' from %s timed out" % (self.id.encode("hex"), str(self.address)))
            # Disconnection timed out, send packet a few more times then give up
            self.send(self, b"\x05\x04")
            self.send(self, b"\x05\x04")
            self.send(self, b"\x05\x04")
            self.close()


    def dechunk_data(self):
        data = ""
        # Reconstruct data in order
        for key in sorted(self.chunks.keys()):
            data += self.chunks[key].data
        
        return data
            
