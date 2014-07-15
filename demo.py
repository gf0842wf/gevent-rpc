# -*- coding: utf-8 -*-

from server import RPCServer
from client import Pool
from cPickle import dumps, loads
import gevent


class TestRPCServer(RPCServer):
    
    def RPC_add(self, l, r):
        return l + r
    

if __name__ == "__main__":
    TestRPCServer(7000).start()
    
    args = (("127.0.0.1", 7000), dumps, loads)
    p = Pool(args, 6)
    print p.RPC_add(1, 2)
    # [0, 3] 其中 0-表示成功, 3-结果值
    
    gevent.wait()