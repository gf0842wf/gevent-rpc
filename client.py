# -*- coding: utf-8 -*-

from endpoint import create_connection
from delay import timeout_partial
from cPickle import dumps, loads
from codec import FixEncoder, FixDecoder
from gevent.event import AsyncResult
from gevent.queue import Queue
import gevent
import sys


class Connection(object):
    """Connection 默认是短连接, 不支持重连"""
    
    reconnect_delay = 5 # 断线重连延时
    timeout = 20 # 调用超时
    
    def __init__(self, address, dumps=None, loads=None):
        self.address = address
        self.conn = create_connection(address)
        self.retry = 0 # 重试次数
        
        self.encode = FixEncoder(dumps).encode
        self.decoder = FixDecoder(loads)

    def reconnect(self):
        while True:
            self.conn.close()
            try:
                print "Trying reconnect.."
                self.conn = create_connection(self.address)
                self.retry = 0
                print "Reconneced."
                break
            except:
                self.retry += 1
                print sys.exc_info()
            if self.retry < 100:
                gevent.sleep(self.reconnect_delay)
            else:
                gevent.sleep(self.retry + self.reconnect_delay)
                
    def _call(self, name, args=(), kw={}):
        try:
            self.conn.sendall(self.encode([name, args, kw]))
        except Exception as e:
            return e
        
        while True:
            data = timeout_partial(self.timeout, self.conn.recv, 128)
            if isinstance(data, BaseException):
                print "timeout..."
                return data
            if not data:
                print "closed..."
                return
            for msg in self.decoder.decode(data):
                return msg
                
    def call(self, name, args=(), kw={}):
        msg = self._call(name, args, kw)
        if isinstance(msg, tuple) and len(msg) >= 2 and msg[0] == "msg":
            if self.timeout is not None:
                self.conn.close()
            return msg[1]
        print "Err msg:", msg
        if self.timeout is None:
            self.reconnect()
            msg = self._call(name, args, kw)
            if isinstance(msg, tuple) and len(msg) >= 2 and msg[0] == "msg":
                return msg[1]
        else:
            self.conn.close()
            
    def __getattr__(self, name, timeout=20):
        return lambda *args, **kw: self.call(name, args, kw)


class Pool(object):
    """连接池:每个连接使用一个gevent队列的连接池
    : Pool 默认是长连接, 支持重连
    """
    
    def __init__(self, args, n):
        # args = (address, dumps, loads)
        assert n > 0, n
        self.conns = []
        self.queues = []
        self.tasks = []

        for _ in xrange(n):
            c = Connection(*args)
            c.timeout = None
            self.conns.append(c)
            q = Queue()
            self.queues.append(q)
            g = gevent.spawn(self.loop, c, q)
            self.tasks.append(g)
    
        assert len(self.conns) == n
    
    def loop(self, conn, q):
        """循环任务
        : 队列格式: ([name, args, kw], result),
        : result是gevent的AsyncResult对象, result为空则非阻塞
        """
        while True:
            [name, args, kw], result = q.peek()
            try:
                rs = conn.call(name, args, kw)
                if result:
                    result.set(rs)
            except:
                print "[LastCall]:", name, args, kw
                if result:
                    result.set_exception(sys.exc_info()[1])
                else:
                    print traceback.format_exc()
            finally:
                q.next()

    def selectq(self, qid=-1):
        """选择第几个队列, 默认返回长度最小的队列"""
        if qid >= 0:
            return self.queues[qid%len(self.queues)]
        minq = min(self.queues, key=lambda qs:qs.qsize())
        return minq

    def call(self, name, args=(), kw={}, block=True):
        q = self.selectq()
        if block:
            result = AsyncResult()
            q.put(([name, args, kw], result))
            return result.get()
        else:
            q.put(([name, args, kw], None))
            
    def __getattr__(self, name):
        if not name.startswith("RPC_"):
            getattr(self, name)
        return lambda *args, **kw: self.call(name, args, kw)

    
if __name__ == "__main__":
    c = Connection(("127.0.0.1", 7000), dumps, loads)
    print c.RPC_echo("abc")
    
    
    args = (("127.0.0.1", 7000), dumps, loads)
    p = Pool(args, 6)
    print p.RPC_echo("efg")
    
    gevent.spawn(gevent.sleep, 10000).join()
#     gevent.wait()
            
                