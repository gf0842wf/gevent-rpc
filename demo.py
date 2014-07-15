# -*- coding: utf-8 -*-

from server import RPCServer
from client import Pool
from cPickle import dumps, loads
import gevent


class TestRPCServer(RPCServer):
    dumps = dumps
    loads = loads
    
    def RPC_add(self, a, b):
        return a + b
    

if __name__ == "__main__":
    TestRPCServer(7000).start()
    
    args = (("127.0.0.1", 7000), dumps, loads)
    p = Pool(args, 6)
    print p.RPC_add(2, 3)
    # [0, 3] 其中 0-表示成功, 3-结果值
    
    gevent.wait()