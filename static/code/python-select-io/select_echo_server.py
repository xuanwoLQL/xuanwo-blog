# -*- coding: utf-8 -*-
"""
基于 select 的并发（多路复用）回声服务器

需求：
  (1) 一个基于 select 的 TCP 服务器，可同时接受多个客户端的连接请求；
  (2) 把收到的客户端数据原样返回（回声功能）；
  (3) 客户端断开时，正确关闭连接并清理资源；
  (4) 单进程内用 select 管理所有连接，维护连接列表，
      监视这些连接上的可读、可写、异常事件。

设计要点：
  - 用一个 select 同时监视“监听套接字 + 所有已连接套接字”；
  - 用三个集合区分三类事件：
        inputs  —— 关心“可读”：监听套接字（有新连接）+ 各客户端（有数据/断开）
        outputs —— 关心“可写”：有待发数据的连接（回声还没发完时挂上）
        excepts —— 关心“异常”：出现带外数据等异常时处理
  - 所有客户端套接字设为非阻塞，send 发不完就放进 pending 缓存，
    下次它可写时再补发，主线程绝不被某个慢客户端卡住。

用法：
  python select_echo_server.py [端口]     # 默认 9300
"""

import select
import socket
import sys

HOST = '0.0.0.0'
PORT = 9300
BUFFER = 4096


class SelectEchoServer:
    def __init__(self, port):
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((HOST, port))
        self.server.listen(100)
        self.server.setblocking(False)

        self.inputs = [self.server]     # 关心可读
        self.outputs = []               # 关心可写（有待发数据）
        self.conns = {}                 # 套接字 -> {'addr':..., 'sendbuf':..., 'recvbuf':...}
        print('select 回声服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, port))

    # ---- 接受一个新连接 ----
    def accept(self):
        while True:
            try:
                conn, addr = self.server.accept()
            except BlockingIOError:
                return              # 没有更多新连接了
            except OSError as e:
                print('accept 出错：%s' % e)
                return
            conn.setblocking(False)
            self.inputs.append(conn)
            self.conns[conn] = {'addr': addr, 'sendbuf': b'', 'recvbuf': b''}
            print('新连接 %s，当前连接数 %d' % (addr, len(self.conns)))

    # ---- 关闭一条连接并清理资源 ----
    def close_conn(self, conn):
        info = self.conns.pop(conn, None)
        if conn in self.inputs:
            self.inputs.remove(conn)
        if conn in self.outputs:
            self.outputs.remove(conn)
        try:
            conn.close()
        except OSError:
            pass
        if info:
            print('连接 %s 断开，清理资源。当前连接数 %d' % (info['addr'], len(self.conns)))

    # ---- 处理可读：有数据就读，读到 EOF 表示对方关闭 ----
    def readable(self, conn):
        try:
            data = conn.recv(BUFFER)
        except BlockingIOError:
            return
        except (ConnectionResetError, OSError) as e:
            print('recv 出错 %s：%s' % (self.conns[conn]['addr'], e))
            self.close_conn(conn)
            return
        if not data:                # 空字节串 = 对端关闭连接
            self.close_conn(conn)
            return
        text = data.decode('utf-8', 'replace')
        print('收到 %s 的数据：%r' % (self.conns[conn]['addr'], text))
        # 回声：把收到的数据原样写进待发缓存，并把这个连接加入“可写”集合
        self.conns[conn]['sendbuf'] += data
        if conn not in self.outputs:
            self.outputs.append(conn)

    # ---- 处理可写：把待发数据尽量发出去 ----
    def writable(self, conn):
        info = self.conns.get(conn)
        if not info:
            return
        buf = info['sendbuf']
        if not buf:
            self.outputs.remove(conn)
            return
        try:
            sent = conn.send(buf)
        except BlockingIOError:
            return                  # 发送缓冲区满了，下次再发
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print('send 出错 %s：%s' % (info['addr'], e))
            self.close_conn(conn)
            return
        info['sendbuf'] = buf[sent:]
        if not info['sendbuf']:
            self.outputs.remove(conn)   # 发完了就不用再关心可写

    # ---- 处理异常 ----
    def exceptional(self, conn):
        print('连接 %s 出现异常事件，关闭它' % (self.conns.get(conn, {}).get('addr')))
        self.close_conn(conn)

    def run(self):
        try:
            while True:
                # select 阻塞等待，直到有事件发生（可读/可写/异常）
                readable, writable, exceptional = select.select(
                    self.inputs, self.outputs, self.inputs)
                for conn in readable:
                    if conn is self.server:
                        self.accept()
                    else:
                        self.readable(conn)
                for conn in writable:
                    self.writable(conn)
                for conn in exceptional:
                    if conn in self.conns:
                        self.exceptional(conn)
        except KeyboardInterrupt:
            print('\n服务器退出，正在关闭所有连接……')
        finally:
            for conn in list(self.conns):
                self.close_conn(conn)
            self.server.close()
            print('服务器已关闭')


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    SelectEchoServer(port).run()


if __name__ == '__main__':
    main()
