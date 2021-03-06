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

    def serialise(self, md5sum=True):
        # Empty UUID if this is first chunk
        after = b"\x00" * 16
        if(self.after != None):
            after = self.after

        self.time_sent = time.time()

        chunk = b"%s%s%s" % (self.id, after, sb(self.data))

        lite_checksum = zlib.adler32(chunk)

        full_checksum = b"\x00" * 16

        if(md5sum):
            hasher = hashlib.md5()
            hasher.update(chunk)
            full_checksum = hasher.digest()

        frame = b"%s%s%s" % (struct.pack('!dL', self.time_sent, lite_checksum), full_checksum, chunk)

        return frame


    @staticmethod
    def from_string(frame):
        frame = sb(frame)
        chunk = Chunk()
        # Timestamp and lite checksum
        chunk.time_sent, lite_checksum = struct.unpack('!dL', frame[:12])

        # Full checksum
        full_checksum = frame[12:28]

        # Data (the actual chunk part)
        data = frame[28:]

        # Verify chunk data
        chunk.valid = lite_checksum == zlib.adler32(data)

        # A full checksum with all zeros means that only the
        # lite checksum was sent
        if(chunk.valid and full_checksum != b"\x00"*16):
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
