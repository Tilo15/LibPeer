import struct
import binascii
import time
import uuid

CHUNK_SIZE = 4096


class Chunk:
    def __init__(self):
        self.checksum = 0
        self.id = uuid.uuid4().bytes
        self.after = None
        self.data = ""
        self.time_sent = 0
        self.valid = False

    def serialise(self):
        self.checksum = binascii.crc32(self.data)

        # Empty UUID if this is first chunk
        after = "\x00" * 16
        if(self.after != None):
            after = self.after

        msg = "%s%s%s%s" % (self.id, after, struct.pack('dl', time.time(), self.checksum), self.data)
        return msg

    @staticmethod
    def from_string(data):
        _chunk = Chunk()
        _chunk.id = data[:16]
        _chunk.after = data[16:32]
        _chunk.time_sent, _chunk.checksum = struct.unpack('dl', data[32:48])
        _chunk.data = data[48:]
        _chunk.valid = _chunk.checksum == binascii.crc32(_chunk.data)
        return _chunk

    @staticmethod
    def create_chunk(data, after=None):
        _chunk = Chunk()
        _chunk.after = after
        _chunk.valid = True
        _chunk.data = data
        return _chunk

    @staticmethod
    def create_chunks(data, after=None):
        chunks = []
        while(len(data) != 0):
            cdata = data[:CHUNK_SIZE]
            data = data[CHUNK_SIZE:]
            last = after
            if(len(chunks) > 0):
                last = chunks[-1].id

            _chunk = Chunk.create_chunk(cdata, last)
            chunks.append(_chunk)

        return chunks
