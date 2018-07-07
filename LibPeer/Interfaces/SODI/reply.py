from LibPeer.Manager.peer import Peer
from LibPeer.Formats.umsgpack import unpackb, packb
from LibPeer.Events import Event
from LibPeer.Logging import log

import queue
import struct

class Reply:
    def __init__(self, peer: Peer, object_size: int, token: bytes):
        self.peer = peer
        self.object_size = object_size
        self.object = {}
        self.data_size = 0
        self.object_ready = Event()
        self.data_ready = Event()
        self.complete = False
        self.token = token
        self.data_received = 0

        self._received_object_bytes = b""
        self._remaining = object_size
        self._receiving_data = False
        self._read_data = 0
        self._fifo: queue.Queue = queue.Queue()

    def _chunk_received(self, data: bytes):
        if(self.complete):
            log.warn("Peer attempted to send data using a completed solicitation")
            return
        
        if(not self._receiving_data):
            # Get remaining object data
            objdata = data[:self._remaining]

            # Keep log of remaining data
            self._remaining = self.object_size - len(objdata)

            # Add to the buffer
            self._received_object_bytes += objdata

            if(self._remaining == 0):
                # Finished getting object data
                self._object_received()

            # Process any following data
            if(len(objdata) != len(data)):
                self._chunk_received(data[len(objdata):])

        else:
            # Receiving data
            if(self.data_size == 0):
                # Start of data, get size of data
                self.data_size = struct.unpack("!Q", data[:8])[0]

                # We just started, that is also how much data remains
                self._remaining = self.data_size

                # Remove the size from the data we are working with
                data = data[8:]

            # Get data
            bindata = data[:self._remaining]

            # Keep log of remaining data
            self._remaining -= len(bindata)


            # Add to the fifo
            self._fifo.put(bindata)

            # Keep log of how much data we have received
            self.data_received += len(bindata)

            if(self._remaining == 0):
                # End of data
                self.complete = True
                self._receiving_data = False

                # Call anyone who may be interested
                self.data_ready.call()



    def _object_received(self):
        # Switch to receiving data
        self._receiving_data = True

        # Unpack the object
        self.object = unpackb(self._received_object_bytes)

        # No need to hold it in memory
        self._received_object_bytes = b""

        # Notify any event listeners
        self.object_ready.call(self.object)


    def read(self):
        '''Returns all buffered data received so far'''
        data = b""

        while self._fifo.qsize() != 0:
            # Get data from fifo (exception if no data)
            chunk = self._fifo.get_nowait()
            # Buffer data
            data += chunk

        # Keep track of how much data has been read
        self._read_data += len(data)

        # Return requested data
        return data

    def read_all(self):
        '''Reads all remaining data from the data part of the reply'''
        data = b""

        # Calculate the amount of data that has to be read before we are done reading
        expected_size = self.data_size - self._read_data

        while len(data) != expected_size:
            # Read more data
            data += self._fifo.get()

        # Keep track of how much data has been read
        self._read_data += len(data)

        # Hand over the goods
        return data
        



    

    



