# -*- coding: utf-8 -*-
"""
实验 1.3 UDP 服务器 —— 返回消息长度和接收时间

要求对照：
  (1) 创建一个基于 socketserver.UDPServer 的简单服务器
  (2) 实现简单的数据包统计功能
  (3) 服务器监听本地 8001 端口

UDP 和 TCP 在 socketserver 里的区别：
    · TCP（StreamRequestHandler）：handle() 在一次连接里会被“持续调用”，
      我们要自己写 while 循环反复 recv；
    · UDP（DatagramRequestHandler/BaseRequestHandler）：没有连接，
      self.request 是一个 (数据报内容, 服务器套接字) 的二元组，
      一个数据报调用一次 handle()，所以 handle() 里不用写循环。
回复用 sock.sendto(数据, self.client_address)，因为 UDP 没有连接对象，要指定发给谁。
"""

import socketserver
import time

HOST = '0.0.0.0'
PORT = 8001

# 数据包统计：UDPServer 是单线程串行处理的，handle() 不会并发执行，所以这里不用加锁
stats = {}        # 客户端地址 (ip, port) -> {'packets': 包数, 'bytes': 字节数}
total = {'packets': 0, 'bytes': 0}


class UdpHandler(socketserver.BaseRequestHandler):
    """每收到一个 UDP 数据报，就被调用一次。"""

    def handle(self):
        # UDP 里 self.request 是 (收到的数据 bytes, 服务器端的套接字) 二元组
        data, sock = self.request
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = repr(data)                      # 不是 utf-8 就按十六进制原样显示

        recv_time = time.strftime('%Y-%m-%d %H:%M:%S')

        # ---- 数据包统计 ----
        st = stats.setdefault(self.client_address, {'packets': 0, 'bytes': 0})
        st['packets'] += 1
        st['bytes'] += len(data)
        total['packets'] += 1
        total['bytes'] += len(data)

        print('[收到] %s:%s 的第 %d 个数据包，%d 字节，内容：%s'
              % (self.client_address[0], self.client_address[1],
                 st['packets'], len(data), text))
        print('       统计：本客户端共 %d 包/%d 字节；服务器共 %d 包/%d 字节，来自 %d 个客户端'
              % (st['packets'], st['bytes'], total['packets'],
                 total['bytes'], len(stats)))

        # ---- 按要求回复：消息长度 + 接收时间 ----
        reply = ('收到消息长度：%d 字节，接收时间：%s（这是你的第 %d 个包）'
                 % (len(data), recv_time, st['packets']))
        sock.sendto(reply.encode('utf-8'), self.client_address)     # UDP 要用 sendto 并指定地址


class MyUDPServer(socketserver.UDPServer):
    allow_reuse_address = True


if __name__ == '__main__':
    with MyUDPServer((HOST, PORT), UdpHandler) as server:
        print('UDP 服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：python 03_udp_client.py 127.0.0.1 8001')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n服务器退出')
            print('最终统计：共收到 %d 个数据包，%d 字节，来自 %d 个客户端'
                  % (total['packets'], total['bytes'], len(stats)))
            for addr, st in stats.items():
                print('   %s:%s —— %d 包，%d 字节' % (addr[0], addr[1], st['packets'], st['bytes']))
