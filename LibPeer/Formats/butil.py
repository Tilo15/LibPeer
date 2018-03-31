# Utilities for handling bytes

def b2s(b: bytes) -> str:
    '''Convert bytes object (b) to a string'''
    return b.decode("utf-8")

def s2b(s: str) -> bytes:
    '''Convert str object (s) to bytes'''
    return s.encode("utf-8")

def ss(o) -> str:
    '''Safely convert object to string'''
    if(type(o) is bytes):
        return b2s(o)
    elif(type(o) is str):
        return o
    else:
        raise TypeError("%s object is neither str or bytes" % type(o))

def sb(o) -> bytes:
    '''Safely convert object to bytes'''
    if(type(o) is str):
        return s2b(o)
    elif(type(o) is bytes):
        return o
    else:
        raise TypeError("%s object is neither bytes or string" % type(o)) 

def concats(*args) -> str:
    '''Returns a single string object containing the joined arguments'''
    result = ""
    for arg in args:
        result += ss(arg)

    return result

def concatb(*args) -> bytes:
    '''Returns a single bytes object containing the joined arguments'''
    result = b""
    for arg in args:
        result += sb(arg)

    return result

def st(*args):
    '''Returns a tuple of strings, converting bytes objects where needed'''
    items = ()
    for arg in args:
        items += (ss(arg),)

    return items
