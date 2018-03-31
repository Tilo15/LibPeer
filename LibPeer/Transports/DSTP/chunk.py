import struct
import hashlib
import time
import uuid
import zlib
from LibPeer.Formats.butil import *

CHUNK_SIZE = 4096

class Chunk:
    def __init__(self):
        self.id = uuid.uuid4().bytes
        self.after = None
        self.data = b""
        self.time_sent = 0
        self.valid = False

    def serialise(self):
        # Empty UUID if this is first chunk
        after = b"\x00" * 16
        if(self.after != None):
            after = self.after

        self.time_sent = time.time()

        chunk = b"%s%s%s" % (self.id, after, self.data)

        lite_checksum = zlib.adler32(chunk)
        hasher = hashlib.md5()
        hasher.update(chunk)
        full_checksum = hasher.digest()

        frame = b"%s%s%s" % (struct.pack('dl', self.time_sent, lite_checksum), full_checksum, chunk)

        return frame


    @staticmethod
    def from_string(frame):
        chunk = Chunk()
        # Timestamp and lite checksum
        chunk.time_sent, lite_checksum = struct.unpack('dl', frame[:16])

        # Full checksum
        full_checksum = frame[16:32]

        # Data (the actual chunk part)
        data = frame[32:]

        # Verify chunk data
        chunk.valid = lite_checksum == zlib.adler32(data)

        if(chunk.valid):
            hasher = hashlib.md5()
            hasher.update(data)
            chunk.valid = full_checksum == hasher.digest()

        # Chunk ID
        chunk.id = data[:16]

        # Prior chunk ID
        chunk.after = data[16:32]

        # Chunk message
        chunk.data = data[32:]

        return chunk


    @staticmethod
    def create_chunk(data, after=None):
        chunk = Chunk()
        chunk.after = after
        chunk.valid = True
        chunk.data = data
        return chunk

    @staticmethod
    def create_chunks(data, after=None):
        chunks = []
        c = 0
        
        while True:
            chunk = Chunk.create_chunk(data[CHUNK_SIZE*c : CHUNK_SIZE*(c+1)], after)
            after = chunk.id

            c += 1

            if(len(chunk.data) == 0):
                break
            else:
                chunks.append(chunk)

        return chunks
