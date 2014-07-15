# -*- coding: utf-8 -*-

from endpoint import EndPoint
from gevent.event import AsyncResult
from gevent.server import StreamServer
import gevent


class RPCBot(EndPoint):
        
    def on_connection_closed(self):
        print("RPCBot {0} closed the connecton".format(self))

    def on_connection_lost(self, reason):
        print("RPCBot {0} lost:{1}".format(self, reason))
        
    def rpcable(self, msg):
        """数据检测"""
        if not isinstance(msg, list):
            return [1, "call param type error"]
        if len(msg) != 3:
            return [2, "call param count error"]
        name, args, kw = msg
        if not isinstance(name, str):
            return [3, "call func name error"]
        if not name.startswith("RPC_"):
            return [4, "call func name not start with RPC_"]
        if not isinstance(args, tuple):
            return [5, "call func args error"]
        if not isinstance(kw, dict):
            return [6, "call func kw error"]
        func = getattr(self.server, name, None)
        if not callable(func):
            return [7, "not the remote call"]
        
        return [func, args, kw]

    def on_data(self, msg):
        rpc_param = self.rpcable(msg)
        print "P:", rpc_param
        async_result = AsyncResult()
        
        if len(rpc_param) != 3:
            self.put_data(rpc_param, result)
        else:
            func, args, kw = rpc_param
            try:
                data = [0, func(*args, **kw)]
            except Exception as e:
                data = [8, str(e)]
            self.put_data(data, async_result)
        result = async_result.get()
        
#         self.close() # 长连接rpc应该由客户端关闭?
                
        print("RPCBot {0} result: {1}".format(self, result)) 


class RPCServer(gevent.Greenlet):
    
    def __init__(self, port):
        self.port = port
        gevent.Greenlet.__init__(self)

    def _connection_handler(self, trans, address):
        print("New Connection From {0}".format(address))
        bot = RPCBot(trans, address, self.dumps, self.loads)
        bot.server = self
        bot.start()
        
    def RPC_echo(self, data):
        return data
    
    def _run(self):
        print("TCP server Listen at port {0}".format(self.port))
        server = StreamServer(("0.0.0.0", self.port), self._connection_handler)
        server.serve_forever()


if __name__ == "__main__":
    from cPickle import dumps, loads

    s = RPCServer(7000)
    s.dumps = dumps
    s.loads = loads
    s.start()
    
    gevent.wait()