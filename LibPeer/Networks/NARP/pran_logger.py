from LibPeer.Logging import log
from LibPeer.Networks.NARP import NARP
from LibPeer.Networks.NARP import router_reply_codes as rc

CODE_MAP = {
    rc.PRAN_SAME_NETWORK: "Same Network",
    rc.PRAN_RATE_LIMITED: "Rate Limited",
    rc.PRAN_WARNING_MESSAGE: "Warning Message",
    rc.PRAN_BAD_ADDRESS: "Bad Address",
    rc.PRAN_NOT_FOUND: "Not Found",
    rc.PRAN_INTERNAL_ERROR: "Internal Error",
    rc.PRAN_NETWORK_UNAVAILABLE: "Network Unavailable",
    rc.PRAN_ORIGIN_BLOCKED: "Origin Blocked",
    rc.PRAN_PAYLOAD_REFUSED: "Payload Refused"
}



class PranLogger:
    def __init__(self, network: NARP):
        self.narp = network
        self.narp.router_reply.subscribe(self.router_reply)

    def router_reply(self, code, message):
        output = "PRAN %i - %s"
        # TODO this should read messages and
        # format them when a standard has been made for them
        log.error(output)
