
class Modifier:
    
    def decode(self, data, address):
        raise NotImplementedError

    def encode(self, data, address):
        raise NotImplementedError