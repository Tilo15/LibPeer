from LibPeer.Manager.peer import Peer
from LibPeer.Interfaces import Interface
from LibPeer.Events.awaiter import ReceiptAwaiter
from LibPeer.Formats.butil import sb
from LibPeer.Logging import log
from threading import Lock

import queue
import io
import struct
import time

class Connection:
    def __init__(self, peer: Peer, interface: Interface, initiate: bool = False):
        self.peer: Peer = peer
        self.open = False
        self._fifo: queue.Queue = queue.Queue()
        self._bytes: bytes = b""
        self._position = 0
        self._send_successes = set()
        self._send_errors = {}
        self._interface: Interface = interface
        self._data_left = 0
        self._is_client = initiate
        self.closed = False

        if(initiate):
            # Initiate the connection with the 'server'
            self._interface._send_data(b"DSIC", self.peer)


    def read(self, count, timeout = None):
        result: bytes = b""
        to_read = count
        while(to_read > 0):
            if(len(self._bytes) <= self._position):
                # We have reached the end of the current chunk,
                # prepare another one
                if(self.open):
                    self._prepare_next_chunk(timeout)
                else:
                    raise ConnectionResetError("Connection to the remote peer is not open yet or was closed")

            # Read more bytes from our current chunk
            read = self._bytes[self._position:self._position + to_read]
            result += read
            self._position += len(read)
            to_read = count - len(result)

        return result


    def _prepare_next_chunk(self, timeout = None):
        self._bytes = self._fifo.get(True, timeout)
        self._position = 0

    def send(self, data):
        '''Send data along the connection'''
        if(not self.open):
            raise ConnectionError("Connection is not yet open or has been closed")

        elif(len(data) > 18446744073709551615):
            raise OverflowError("Cannot send a message larger than 18446744073709551615 bytes")

        else:
            frame = b"DSIS"
            frame += struct.pack("!Q", len(data))
            frame += sb(data)
            ReceiptAwaiter(self._interface._send_data, frame, self.peer)

    def wait_for_connection(self, timeout = 10):
        '''Wait for the connection to the remote peer to be open'''
        start = time.time()
        while(not self.open):
            if(time.time() - start > timeout):
                raise TimeoutError("The peer did not respond")

    def close(self):
        '''Close the connection'''
        if(self.open):
            ReceiptAwaiter(self._interface._send_data, b"DSID", self.peer)
            self.open = False
            self.closed = True
        else:
            log.warn("Connection to peer %s already closed" % self.peer)
            

    def _chunk_received(self, data):
        while(len(data) > 0):
            if(self._data_left > 0):
                # Get no more than what is left
                data_to_use = data[:self._data_left]

                # Subtract that from the counter
                self._data_left -= len(data_to_use)

                # Add to the queue
                self._fifo.put(data_to_use)

                # If there is data left over from our chunk, process that
                data = data[len(data_to_use):]

            elif(data[:4] == b"DSIC" and not self._is_client):
                # We are being connected to
                self._interface._send_data(b"DSIA", self.peer)
                self.open = True
                
                # Process leftovers
                data = data[4:]

            elif(data[:4] == b"DSIA" and self._is_client):
                # Our connection request was acknowledged
                self.open = True

                # Process leftovers
                data = data[4:]

            elif(data[:4] == b"DSID"):
                # Disconnect request
                self.open = False
                self.closed = True

                # Process leftovers
                data = data[4:]
            
            elif(data[:4] == b"DSIS"):
                # New data to stream
                length = struct.unpack("!Q", data[4:12])[0]

                # To get to here, this must be zero so we can overwrite
                self._data_left = length

                # Process leftovers (in this case, the actual data)
                data = data[12:]

            else:
                # Invalid data detected, strip a char to see if it was in error...
                data = data[1:]






