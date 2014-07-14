# -*- coding: utf-8 -*-

from gevent.queue import Queue
from gevent import socket
import struct
import gevent

from codec import FixEncoder, FixDecoder


class EndPoint(gevent.Greenlet):
    """可以用在服务端/客户端"""
    
    def __init__(self, transport, address, dumps=None, loads=None):
        self.transport = transport
        self.address = address
        self.inbox = Queue()
        self.jobs = []
        
        self.encode = FixEncoder(dumps).encode
        self.decoder = FixDecoder(loads)

        gevent.Greenlet.__init__(self)
        
    def __str__(self):
        return "[EndPoint:%r]" % (self.address, )
    
    def close(self):
        self.transport.close()
        
    def put_data(self, data, async_result):
        self.inbox.put((data, async_result))
    
    def recv_data(self):
        while True:
            try:
                data = self.transport.recv(128)
                if not data:
                    self.on_connection_closed()
                    break
                for msg in self.decoder.decode(data):
                    flag, message = msg
                    if flag == "msg":
                        self.on_data(message)
            except Exception as e:
                self.on_connection_lost(e)
                break


    def send_data(self):
        while True:
            msg, async_result = self.inbox.get()
            try:
                data = self.encode(msg)
                self.transport.sendall(data)
                print "send:", repr(data)
                result = "ok"
            except Exception as e:
                result = e
            async_result.set(result)

    def on_data(self, msg):
        """called when data received. (stripped the 4 bytes header)"""
        raise NotImplementedError()

    def on_connection_closed(self):
        """called when peer closed the connect"""
        raise NotImplementedError()

    def on_connection_lost(self, reason):
        """called when lost peer"""
        raise NotImplementedError()

    def terminate(self):
        gevent.killall(self.jobs)
        self.transport.close()
        self.kill()

    def _run(self):
        job_recv = gevent.spawn(self.recv_data)
        job_send = gevent.spawn(self.send_data)

        def _exit(glet):
            job_recv.unlink(_exit)
            job_send.unlink(_exit)
            self.terminate()

        job_recv.link(_exit)
        job_send.link(_exit)

        self.jobs.append(job_recv)
        self.jobs.append(job_send)
        

def create_connection(address, timeout=None, **ssl_args):
    """客户端创建连接,返回sock
    :自带有一个 from gevent.socket import create_connection, 不过没有ssl参数
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
    
    if timeout:
        sock.settimeout(timeout)
    if ssl_args:
        from gevent.ssl import wrap_socket
        sock = wrap_socket(sock, **ssl_args)
        
    host = address[0]
    port = int(address[1]) 
    sock.connect((host, port))
    
    return sock


if __name__ == "__main__":
    import struct
    sock = create_connection(("127.0.0.1", 7000))
    sock.sendall(struct.pack(">I5s", 5, "hello"))
    while True:
        print repr(sock.recv(10))
