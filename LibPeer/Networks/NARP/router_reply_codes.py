# PRAN (NARP backwards) reply codes

# 1xx - Warnings

# 100 - Same Network,
#       The route destination is on the same network
#       as the source.
# msg - Destination, LocalAddress
PRAN_SAME_NETWORK = 100

# 101 - Rate Limited,
#       The router has imposed a rate limit on your connection.
# msg - Reason
PRAN_RATE_LIMITED = 101

# 102 - Warning Message,
#       The router wishes to bring to the user's attention a
#       human readable warning message.
# msg - Message
PRAN_WARNING_MESSAGE = 102


# 2xx - Client Errors

# 200 - Bad Address,
#       The address sent by the client could not be decoded.
# msg - None
PRAN_BAD_ADDRESS = 200

# 201 - Not Found,
#       The address sent by the client was not in the router's
#       records and could not be routed.
# msg - Address
PRAN_NOT_FOUND = 201


# 3xx - Router Errors

# 300 - Internal Error,
#       The router suffered an undefined internal error and could not continue.
# msg - None
PRAN_INTERNAL_ERROR = 300

# 301 - Network Unavailable,
#       The router could not forward the datagram because the destination
#       network was unavailable.
# msg - None
PRAN_NETWORK_UNAVAILABLE = 301


# 4xx - Refusals

# 400 - Origin Blocked,
#       The router refused to route the datagram because the sender has been
#       blacklisted.
# msg - Reason
PRAN_ORIGIN_BLOCKED = 400

# 401 - Payload Refused,
#       The router refused to route the datagram because of the contents of
#       the datagram.
# msg - Contains
PRAN_PAYLOAD_REFUSED = 401

