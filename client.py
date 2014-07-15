# -*- coding: utf-8 -*-

from endpoint import create_connection
from delay import timeout_partial
from cPickle import dumps, loads
from codec import FixEncoder, FixDecoder
from gevent.event import AsyncResult
from gevent.queue import Queue
from functools import partial
import gevent
import sys


class Connection(object):
    reconnect_delay = 5 # 断线重连延时
    retry = 0 # 重试次数
    
    def __init__(self, address, dumps=None, loads=None):
        self.address = address
        self.conn = create_connection(address)
        
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
                
    def call(self, name, args=(), kw={}, timeout=20):
        try:
            self.conn.sendall(self.encode([name, args, kw]))
            while True:
                data = timeout_partial(timeout, self.conn.recv, 128)
                if isinstance(data, BaseException):
                    print "timeout..."
                    self.conn.close()
                    return
                if not data:
                    print "closed..."
                    self.conn.close()
                    return
                for msg in self.decoder.decode(data):
                    flag, message = msg
                    if flag == "msg":
                        if timeout is not None: self.conn.close()
                        return message
        except Exception as e:
            print "Exception:", e
            
    def __getattr__(self, name, timeout=20):
        return lambda *args, **kw: self.call(name, args, kw, timeout=timeout)


class Pool(object):
    """连接池:每个连接使用一个gevent队列的连接池
    """
    
    def __init__(self, args, n):
        # args = (address, dumps, loads)
        assert n > 0, n
        self.conns = []
        self.queues = []
        self.tasks = []

        for _ in xrange(n):
            c = Connection(*args)
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
                rs = conn.call(name, args, kw, timeout=None)
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
            
    def __getattr__(self, name, block=True):
        return lambda *args, **kw: self.call(name, args, kw, block=block)

    
if __name__ == "__main__":
    c = Connection(("127.0.0.1", 7000), dumps, loads)
    print c.RPC_echo("abc")
    
    
    args = (("127.0.0.1", 7000), dumps, loads)
    p = Pool(args, 6)
    print p.call("RPC_echo", ("abc", ), {})
    
    print p.RPC_echo("abc")
    
    gevent.spawn(gevent.sleep, 10000).join()
#     gevent.wait()
            
                