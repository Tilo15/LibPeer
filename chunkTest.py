import sys
from LibPeer.Transports.DSTP.chunk import Chunk

f = open(sys.argv[1])
o = open('out', 'w')

print("Chunking...")
chunks = Chunk.create_chunks(f.read())

print("Serialising...")
frames = []
for chunk in chunks:
    frames.append(chunk.serialise())

print("Deserialising...")
chunks = []
for frame in frames:
    chunks.append(Chunk.from_string(frame))

print("Saving...")
for chunk in chunks:
    o.write(chunk.data)

f.close()
o.close()