import struct
import binascii
import time

CHUNK_SIZE = 256

class Chunk:
    def __init__(self):
        self.sequence_number = 0
        self.timestamp = 0
        self.data = ""
        self.checksum = 0
        self.valid = False

    def set_data(self, data):
        self.data = data
        self.checksum = binascii.crc32(data)
        self.valid = True

    @staticmethod
    def new_from_string(chunk):
        obj = Chunk()
        obj.sequence_number, obj.timestamp, obj.checksum = struct.unpack("Ldl", chunk[:16])
        obj.data = chunk[16:]
        obj.valid = binascii.crc32(obj.data) == obj.checksum
        return obj

    def serialise(self):
        selt.timestamp = time.time()
        chunk = struct.pack("Ldl", self.sequence_number, self.timestamp, self.checksum)
        chunk += self.data
        return chunk


class Chunker:
    @staticmethod
    def chunkise(data):
        chunks = []
        
        while(len(data) != 0):
            chunk = Chunk()
            chunk.set_data(data[:CHUNK_SIZE])
            chunks.append(chunk)
            data = data[CHUNK_SIZE:]

        return chunks
