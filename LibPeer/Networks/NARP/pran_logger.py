from LibPeer.Logging import log
from LibPeer.Networks.NARP import NARP
from LibPeer.Networks.NARP import router_reply_codes as rc
from LibPeer.Formats.umsgpack import unpackb

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
        # Init a data dict
        data = {}

        # If there is message data, unpack it
        if(len(message) > 0):
            data = unpackb(message)

        if(code == rc.PRAN_BAD_ADDRESS):
            self.log(code, "The router did not understand the address", True)

        if(code == rc.PRAN_INTERNAL_ERROR):
            self.log(code, "", True)

        if(code == rc.PRAN_NETWORK_UNAVAILABLE):
            self.log(code, "", True)

        if(code == rc.PRAN_NOT_FOUND):
            self.log(code, "The router could not find the address '%s'" % message["Address"], True)

        if(code == rc.PRAN_ORIGIN_BLOCKED):
            self.log(code, message["Reason"], True)

        if(code == rc.PRAN_ORIGIN_BLOCKED):
            self.log(code, "The router dropped your packet because it contains '%s'" % message["Contains"], True)

        if(code == rc.PRAN_RATE_LIMITED):
            self.log(code, message["Reason"])

        if(code == rc.PRAN_SAME_NETWORK):
            self.log(code, "The peer at '%s' is located on your local network at '%s'" %(message["Destination", "LocalAddess"]))

        if(code == rc.PRAN_WARNING_MESSAGE):
            self.log(code, message["Message"])


        

        
        


    def log(self, code, message, error=False):
        # Begin formatting message
        output = "PRAN %i - %s" % (code, CODE_MAP[code])

        # If there is a message, add that too
        if(len(message) > 0):
            output += ": %s" % message

        # Output at the correct level
        if(not error):
            log.warn(output)

        else:
            log.error(output)
