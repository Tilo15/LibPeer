
from LibPeer.Formats.baddress import BAddress
import base64

class AddressUtil:
    @staticmethod
    def add_outer_hop(hop_address: BAddress, narp_address: BAddress, label = ""):
        return BAddress(
            "NARP",
            base64.b64encode(hop_address.get_binary_address()),
            base64.b64encode(narp_address.get_binary_address()),
            label
        )

    @staticmethod
    def get_next_hop_address(address: BAddress):
        baddr = base64.b64decode(address.net_address)
        return BAddress.from_serialised(baddr)

    @staticmethod
    def remove_outer_hop(address: BAddress):
        baddr = base64.b64decode(address.port)
        return BAddress.from_serialised(baddr)