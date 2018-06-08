from LibPeer.Manager.peer import Peer
from LibPeer.Interfaces import Interface
from LibPeer.Events.awaiter import ReceiptAwaiter
from threading import Lock

import queue
import io

class Connection:
    def __init__(self, peer: Peer, interface: Interface):
        self.peer: Peer = peer
        self.open = True
        self._fifo: queue.Queue = queue.Queue()
        self._bytes: bytes = b""
        self._position = 0
        self._send_successes = set()
        self._send_errors = {}
        self._interface: Interface = interface


    def read(self, count, timeout = None):
        result: bytes = b""
        to_read = count
        while(to_read > 0):
            if(len(self._bytes) <= self._position):
                # We have reached the end of the current chunk,
                # prepare another one
                self._prepare_next_chunk(timeout)

            # Read more bytes from our current chunk
            read = self._bytes[self._position:self._position + to_read]
            result += read
            self._position += len(read)
            to_read -= len(result)

        return result


    def _prepare_next_chunk(self, timeout = None):
        self._bytes = self._fifo.get(True, timeout)
        self._position = 0

    def send(self, data):
        '''Send data along the connection'''
        ReceiptAwaiter(self._interface._send_data, data, self.peer)

