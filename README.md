# LibPeer Prototype Implementation
This repository hosts the original **prototype** implementation of LibPeer. This document will be updated to list the development of other implementations. This repsoitory is kept up for historical purposes, but it **should not but used as a reference impementation for developing a LibPeer Standard Protocols compliant library**.

The [LibPeer Standard Protocols document](https://saltlamp.pcthingz.com/utdata/LibPeer/LibPeer_Standard_Protocols_v1.pdf) should be used when developing an implementation to meet the specification.

Work is underway to build a reference implementation in Python3, you can [visit its repo](https://github.com/Tilo15/LibPeer-Python) to check on the progress. Presumably when it is done I will update this readme to make it read as if it is complete.

# Original Readme
A Python 3 library for finding and connecting with peers on the internet and other networks.

This isn't really designed for use yet, it is very much still in development, and will have some proper documentation in due course.
it has the following python dependancies:
 * twisted
 * miniupnpc
 * netifaces
 * psutil

Some other open source projects have been incoporated into this one, these are:
 * [umsgpack](https://github.com/vsergeev/u-msgpack-python)
 
The aim of this library is to make peer to peer application creation simple and quick, to the point where no one in the development process has to even care about what an IP address is.
