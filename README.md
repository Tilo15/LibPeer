# LibPeer
A python 2 (and soon to be ported to python 3) library for finding and connecting with peers on the internet and other networks.

This isn't really designed for use yet, it is very much still in development, and will have some proper documentation in due course.
it has the following python dependancies:
 * twisted
 * miniupnpc
 * netifaces
 * psutil
 * future

Some other open source projects have been incoporated into this one, these are:
 * [umsgpack](https://github.com/vsergeev/u-msgpack-python)
 * [rpcudp](https://github.com/bmuller/rpcudp)
 * [kademlia](https://github.com/bmuller/kademlia) - this one got modded a bit
 
The aim of this library is to make peer to peer application creation simple and quick, to the point where no one in the development process has to even care about what an IP address is.
