from twisted.names.client import getResolver
import twisted.names.dns as dns
from LibPeer.Discovery.AMPP.bootstrapers.DNS.dns_seeds import SEEDS
from twisted.internet import reactor, defer
from LibPeer.Logging import log
from LibPeer.Formats.butil import ss
import ipaddress

class DNSHelper:
    def __init__(self):
        self.resolver = getResolver()
        self.tasks = 0
        self.addresses = []

    def get_seed_addresses(self):
        deferred = defer.Deferred()
        self.addresses = []
        
        self.tasks = len(SEEDS)

        for seed in SEEDS:
            callback = self.resolver.lookupText(seed)
            callback.addErrback(self.lookup_failure, seed, deferred)
            callback.addCallback(self.dns_txt_lookup_complete, deferred)

        return deferred


    def dns_txt_lookup_complete(self, results, deferred):
        if(results):
            self.tasks += len(results[0])
            for result in results[0]:
                # Find txtx records
                if(result.type == dns.TXT):
                    # Is is an LibPeer record?
                    data = ss(b"".join(result.payload.data))
                    data.replace("::", ":")
                    if(data.startswith("LP:")):
                        parts = data.split(":")
                        entry_type = parts[1]
                        if(entry_type == "MOTD"):
                            # Message of the Day entry
                            message = ":".join(parts[2:])
                            log.info("MOTD %s: %s" % (result.name, message))
                            self.decrement_tasks(deferred, "MOTD entry")
                    
                        elif(entry_type == "NAME"):
                            # DNS Address entry
                            name = parts[2]
                            port = parts[3]
                            callback = self.lookup_name(name)
                            callback.addCallback(self.name_lookup_complete, port, deferred)
                            callback.addErrback(self.name_lookup_failed, deferred)
                        
                        elif(entry_type == "ADDR"):
                            # IPv4 Address entry
                            address = parts[2]
                            port = parts[3]
                            self.add_address((address, port), deferred)

                        else:
                            self.decrement_tasks(deferred, "Invalid LibPeer TXT record")

                else:
                    # Not a valid record for this purpose
                    self.decrement_tasks(deferred, "Entry was not a TXT entry")

            # Finish the task
            self.decrement_tasks(deferred, "A seed lookup completed" )


    def name_lookup_complete(self, address, port, deferred):
        # Looked up "NAME" entry and resolved to IPv4 address
        self.add_address((address, port), deferred)

    def name_lookup_failed(self, error, deferred):
        self.decrement_tasks(deferred, "NAME lookup failed")
                

    def lookup_name(self, address, effort=20, deferred = defer.Deferred(), history = []):
        history.append(ss(address))
        # If the effort is 0 or less, give up
        if(effort <= 0):
            log.debug("Gave up resolving NAME entry")
            deferred.errback(Exception("Exceeded effort"))
            return

        self.resolver.lookupAllRecords(address).addCallback(self.name_lookup_dns_result, deferred, effort, history)
        return deferred

    def name_lookup_dns_result(self, results, deferred, effort, history):
        if(results):
            for result in results[0]:
                # Find A records
                if(result.type == dns.A):
                    address = ipaddress.ip_address(result.payload.address)
                    log.debug("Resolved NAME entry: %s -> %s" % (" -> ".join(history), address))
                    deferred.callback(str(address))

                # Find CNAME records
                if(result.type == dns.CNAME):
                    self.lookup_name(result.payload.name.name, effort - 1, deferred, history)



    def lookup_failure(self, data, seed, deferred):
        self.decrement_tasks(deferred, "Couldn't look up seed %s" % seed)
        # Don't warn for the localresolver
        if(seed != "libpeer.localresolver"):
            log.warn("DNS lookup for seed name %s failed" % seed)

    def add_address(self, address, deferred):
        self.addresses.append(address)
        self.decrement_tasks(deferred, "Address was added")


    def decrement_tasks(self, deferred, reason):
        log.debug("Tasks decremented, reason: %s" % reason)
        self.tasks -= 1
        if(self.tasks == 0):
            deferred.callback(self.addresses)


