# -*- coding: utf-8 -*-
"""
课本 129 页实例 —— 多进程文件下载服务（服务端）

对应课本 5.2.1 代码 5-2s（process02s.py）：
  主进程只负责 accept 客户端连接，每来一个客户端就用
  multiprocessing.Process 起一个子进程去发送文件，
  这样子进程可以同时给多个客户端提供文件下载服务。

用法：
  python download_server.py [共享目录] [端口]
  共享目录默认是脚本所在目录，端口默认 9100。
  客户端请求的文件名，会到共享目录里去找。
"""

import os
import socket
import sys
from multiprocessing import Process

HOST = '0.0.0.0'
PORT = 9100
CHUNK = 1024 * 4
PREFIX = b'DOWNLOAD'

SHARE_DIR = os.path.dirname(os.path.abspath(__file__))


def recv_file_name(conn):
    """接收客户端发来的文件名（自解释的定长头部 + 文件名，避免粘包）。"""
    head = b''
    while len(head) < len(PREFIX) + 4:
        part = conn.recv(len(PREFIX) + 4 - len(head))
        if not part:
            return None
        head += part
    if head[:len(PREFIX)] != PREFIX:
        return None
    length = int.from_bytes(head[len(PREFIX):], 'big')
    name = b''
    while len(name) < length:
        part = conn.recv(length - len(name))
        if not part:
            return None
        name += part
    return name.decode('utf-8')


def send_all(conn, data):
    """把一段数据完整发出去（send 不保证一次全发完，循环发）。"""
    sent = 0
    while sent < len(data):
        sent += conn.send(data[sent:])


def sendfile(conn, share_dir):
    """子进程的处理函数：接收文件名，把文件发给客户端。

    注意：Windows 下 multiprocessing 用 spawn 方式创建子进程，
    子进程会重新导入本模块，拿不到父进程后来改过的全局变量 SHARE_DIR，
    所以这里必须把共享目录当参数传进来。
    """
    try:
        filename = recv_file_name(conn)
        if not filename:
            return
        print('我是子进程，我的 ID 是', os.getpid())
        print('客户端请求我的文件：', filename)

        # 只允许访问共享目录内的文件，去掉路径部分，防止目录穿越
        safe_name = os.path.basename(filename)
        path = os.path.join(share_dir, safe_name)

        if os.path.isfile(path):
            size = os.path.getsize(path)
            print('我有 %s，开始下载！' % safe_name)
            send_all(conn, b'yes')                       # 告诉客户端：文件存在
            send_all(conn, size.to_bytes(8, 'big'))      # 再发 8 字节文件大小
            with open(path, 'rb') as f:
                while True:
                    data = f.read(CHUNK)
                    if not data:
                        break
                    send_all(conn, data)
            print('%s 下载成功！' % safe_name)
        else:
            print('抱歉，我没有 %s！' % safe_name)
            send_all(conn, b'no')
    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        print('与客户端的连接中断：%s' % e)
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    global SHARE_DIR
    if len(sys.argv) > 1:
        SHARE_DIR = os.path.abspath(sys.argv[1])
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, port))
    s.listen(100)
    print('我是父进程，我的 ID 是', os.getpid())
    print('多进程文件下载服务端已启动，共享目录：%s' % SHARE_DIR)
    print('监听 %s:%d，等待客户端连接……' % (HOST, port))

    try:
        while True:
            conn, addr = s.accept()
            print('等待连接……收到来自 %s 的连接' % (addr,))
            # 课本做法：每来一个客户端，就创建一个子进程去处理
            p = Process(target=sendfile, args=(conn, SHARE_DIR))
            p.start()
            # 父进程不 join，立刻回去 accept 下一个客户端，实现并发
    except KeyboardInterrupt:
        print('\n服务端退出')
    finally:
        s.close()


if __name__ == '__main__':
    main()
