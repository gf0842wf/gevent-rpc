### gevent rpc(tcp) ###

传输方式可以配置,实现 pickle-rpc, json-rpc, msgpack-rpc

传输协议参数:

    客户端请求: [funcname(str), args, kwargs]
    服务端响应: [code, result/error_message] code:0-ok, other-error