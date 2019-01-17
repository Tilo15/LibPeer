import time
from LibPeer.Logging import log

class Metric:
    def __init__(self, address):
        self.hash = address.get_hash()
        self.dropped_packets = 0
        self.acknowledged_packets = 0
        self.negative_acknowledged_packets = 0
        self.sent_packets = 0
        self.latency = 0
        self.in_flight = 0
        self.last_packet_delay = 0
        self.last_packet_sent = 0
        self.last_window_size = 16

    def packet_sent(self):
        self.last_packet_sent = time.time()
        self.in_flight += 1
        self.sent_packets += 1
        self.dropped_packets += 1

    def packet_acknowledged(self, time_sent):
        self.dropped_packets -= 1
        self.acknowledged_packets += 1
        self.in_flight -= 1
        self.last_packet_delay = time.time() - time_sent

    def packet_negative_acknowledged(self):
        self.negative_acknowledged_packets += 1


    def get_window_size(self):
        delay_factor = (1 - self.last_packet_delay*10)
        window_factor = self.in_flight / self.last_window_size
        gain = delay_factor * window_factor
        self.last_window_size += gain
        if(self.last_window_size < 5):
            self.last_window_size = 5

        time.sleep(0.006) # Look, I don't even know why this is helping.
                          # I had a log statement here, and when I took it out everything fell apart
                          # So... TODO I guess.

        return self.last_window_size

    

    

