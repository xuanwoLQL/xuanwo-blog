# -*- coding: utf-8 -*-
"""
实验 1.1 基础 TCPServer 实现 —— 简单回显服务器

要求对照：
  (1) 创建一个基于 socketserver.TCPServer 的简单回显服务器
  (2) 客户端发送任何消息，服务器原样返回
  (3) 自定义请求处理类继承自 BaseRequestHandler，服务器监听本地 8000 端口

socketserver 的套路（记住这四步）：
    1) 写一个处理类，继承 BaseRequestHandler（或 StreamRequestHandler），重写 handle()；
    2) 用 (地址, 端口) 和处理类实例化 Server 类；
    3) 调 serve_forever() 开始服务；
    4) 结束时 server_close()。

注意：TCPServer 是“串行”的 —— serve_forever() 一次只处理一个连接，
      前一个客户端不断开，后面的客户端只能排队等着（可以开两个 01_echo_client.py 验证），
      所以它不能做并发服务器。并发版本见实验 1.2 的 ThreadingTCPServer。
"""

import socketserver

HOST = '0.0.0.0'      # 0.0.0.0 表示监听本机所有网卡，同网段的机器都能连
PORT = 8000           # 实验要求的端口


class EchoHandler(socketserver.BaseRequestHandler):
    """自定义请求处理类：每来一个客户端连接，socketserver 就调用一次 handle()。"""

    def handle(self):
        # self.request       —— 与客户端通信的套接字（TCP 里就是 conn）
        # self.client_address —— 客户端的 (IP, 端口)
        print('[连接] 客户端 %s:%s 已连接' % self.client_address)
        while True:
            try:
                data = self.request.recv(1024)      # 收数据
            except ConnectionResetError as e:
                # 客户端直接关窗口/被强杀会走这里，服务端不能因此崩溃
                print('[异常] 客户端 %s 非正常断开：%s' % (self.client_address, e))
                break

            if not data:                            # 空字节串 = 客户端正常关闭了连接
                break

            print('[收到] %s:%s 发来 %d 字节：%s'
                  % (self.client_address[0], self.client_address[1],
                     len(data), data.decode('utf-8')))
            # 原样发回去（回显）。用 sendall()：send() 不保证一次把数据全发完，sendall() 保证
            self.request.sendall(data)

        print('[断开] 客户端 %s:%s 已断开' % self.client_address)


class MyTCPServer(socketserver.TCPServer):
    """加两个类属性，让服务端重启时不用等端口释放。"""
    allow_reuse_address = True       # 允许地址复用，否则重启会报 Address already in use


if __name__ == '__main__':
    # with 语句会在退出时自动调用 server_close() 关闭监听套接字
    with MyTCPServer((HOST, PORT), EchoHandler) as server:
        print('回显服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：另开一个终端运行 python 01_echo_client.py')
        try:
            server.serve_forever()       # 一直循环，等客户端连接
        except KeyboardInterrupt:
            print('\n服务器退出')
