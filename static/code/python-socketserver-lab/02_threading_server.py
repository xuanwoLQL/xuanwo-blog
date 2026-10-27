# -*- coding: utf-8 -*-
"""
实验 1.2 多线程 TCPServer —— 同时处理多个客户端连接

要求对照：
  (1) 创建一个基于 socketserver.ThreadingTCPServer 的多线程服务器
  (2) 记录每个客户端的连接时间和 IP 地址
  (3) 服务器能够显示当前连接的客户端数量

和实验 1.1 的 TCPServer 相比，只有一个字的区别：
    TCPServer          —— 串行，一次只服务一个连接
    ThreadingTCPServer —— 每 accept 到一个连接就自动新建一个线程去跑 handle()，
                          所以多个客户端可以真正同时在在线、同时收发数据。

多线程带来的新问题：多个线程会同时修改“在线客户端表”这个共享数据，
    所以要用 threading.Lock 加锁保护（一次只让一个线程改），避免竞态条件。
"""

import socketserver
import threading
import time

HOST = '0.0.0.0'
PORT = 8002                     # 1.1 用了 8000，这里换个端口，方便同时开两个实验对比

lock = threading.Lock()         # 保护下面这几个共享变量
online = {}                     # 连接对象 -> {'ip':.., 'port':.., 'connect_time':.., 'time':时间戳}
total_conn = 0                  # 历史累计连接数


def now_str():
    return time.strftime('%Y-%m-%d %H:%M:%S')


class ClientHandler(socketserver.BaseRequestHandler):
    """每个客户端一个线程，这个类的方法会被多个线程同时执行。"""

    def handle(self):
        global total_conn

        # ---- 客户端上线：加锁修改共享数据 ----
        with lock:
            total_conn += 1
            online[self.request] = {
                'ip': self.client_address[0],
                'port': self.client_address[1],
                'connect_time': now_str(),
                'time': time.time(),
            }
            count = len(online)
            total = total_conn

        print('[连接] %s  客户端 %s:%s 已连接'
              % (now_str(), self.client_address[0], self.client_address[1]))
        print('       连接时间：%s' % online[self.request]['connect_time'])
        print('       当前在线客户端数量：%d（累计连接：%d）' % (count, total))
        print('       当前在线列表：%s' % [(v['ip'], v['port']) for v in online.values()])

        try:
            while True:
                data = self.request.recv(1024)
                if not data:
                    break
                msg = data.decode('utf-8')
                with lock:                                   # 读共享字典也要加锁，防止刚好有人正在改
                    info = online[self.request]
                dur = int(time.time() - info['time'])
                print('[消息] %s 发来：%s（在线 %d 秒）' % (info['ip'], msg, dur))
                # 回显：带上客户端地址和在线时长，方便看出是“哪一个客户端”在被服务
                reply = '[%s] %s 你已在线 %d 秒，你说的是：%s' % (now_str(), info['ip'], dur, msg)
                self.request.sendall(reply.encode('utf-8'))
        except ConnectionResetError as e:
            print('[异常] 客户端 %s:%s 非正常断开：%s'
                  % (self.client_address[0], self.client_address[1], e))
        finally:
            # ---- 客户端下线：同样加锁修改共享数据 ----
            with lock:
                info = online.pop(self.request, None)
                count = len(online)
            if info:
                print('[断开] %s  客户端 %s:%s 已断开（本次在线 %d 秒）'
                      % (now_str(), info['ip'], info['port'], int(time.time() - info['time'])))
            print('       当前在线客户端数量：%d' % count)


class MyThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True        # 主线程退出时，工作线程跟着退出，不然 Ctrl+C 后卡住不退出


if __name__ == '__main__':
    with MyThreadingTCPServer((HOST, PORT), ClientHandler) as server:
        print('多线程 TCPServer 已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：python 02_threading_client.py 127.0.0.1 8002 5   （模拟 5 个客户端同时连接）')
        print('提示：01_echo_client.py 也能连这个服务器')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n服务器退出（最终在线数：%d）' % len(online))
