# -*- coding: utf-8 -*-

from server import RPCServer
from client import Connection, Pool
from cPickle import dumps, loads
import gevent


class TestRPCServer(RPCServer):
    dumps = dumps
    loads = loads
    
    def RPC_add(self, a, b):
        return a + b

    def RPC_sleep(self, seconds):
    	gevent.sleep(seconds)
    

if __name__ == "__main__":
    TestRPCServer(7000).start()
    
    c = Connection(("127.0.0.1", 7000), dumps, loads)
    print c.RPC_sleep(3) 
    c.reconnect() # Connection 是短连接,必须主动重连才能继续利用 connection
    print c.RPC_add(2, 3)
    
    args = (("127.0.0.1", 7000), dumps, loads)
    p = Pool(args, 6)
    print p.RPC_echo("123")
    print p.RPC_add(1, 2) # Pool 是长连接,不需要重连
    # [0, 3] 其中 0-表示成功, 3-结果值
    
    gevent.wait()