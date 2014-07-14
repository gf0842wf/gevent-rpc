# -*- coding: utf-8 -*-

import struct


class FixEncoder(object):
    """固定4bytes长度头编码器"""
    
    def __init__(self, dumps=None):
        self.dumps = dumps or (lambda data: data)
        
    def encode(self, msg):
        trunk = self.dumps(msg)
        length = len(trunk)
        data = struct.pack(">I%ds" % length, length, trunk)
        return data


class FixDecoder(object):
    """固定4bytes长度头解码器"""
        
    _buf = ""
    
    def __init__(self, loads=None):
        self.loads = loads or (lambda data: data)
    
    def decode(self, data):
        buf = self._buf =  self._buf + data
        while True:
            if not buf:
                raise StopIteration
            if len(buf) < 4:
                yield ("short", "header")
                continue
            length, = struct.unpack(">I", buf[:4])
            if len(buf) < length:
                yield ("short", "message")
                continue
            trunk = buf[4:4+length]
            buf = buf[4+length:]
            self._buf = buf
            msg = self.loads(trunk)
            yield ("msg", msg)


if __name__ == "__main__":
    import cPickle as pickle
    # test pickle
    encode = FixEncoder(pickle.dumps).encode
    data = encode({"a":[1,2,3]})
    encoder = FixDecoder(pickle.loads)
    for m in encoder.decode(data):
        print m
        
        