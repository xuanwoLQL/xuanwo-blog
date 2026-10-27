# -*- coding: utf-8 -*-
"""
思考与扩展（选做）—— 简单聊天室服务器，支持多个客户端同时聊天

和 GUI 版聊天室（课本 5-9s）的区别：
  · 用“按行读取”的方式解决粘包问题 —— 每条消息都以 \\n 结尾，
    服务端用 self.rfile.readline() 一次读一行，天然不会把两条消息粘在一起；
  · 支持昵称、系统提示（谁进来了/谁走了）、/list 查看在线名单、/quit 退出；
  · 客户端是控制台版，不依赖图形界面，方便在实验课上快速验证。

自定义的简单文本协议（每条消息一行，以 \\n 结束）：
    客户端发的第一行：昵称
    之后发的行：聊天内容；以 / 开头的行是命令：/list 看在线名单，/quit 退出
    服务端发的行：直接显示给用户看的文本（聊天内容形如 '张三: 你好'）
"""

import socketserver
import threading
import time

HOST = '0.0.0.0'
PORT = 8005

lock = threading.Lock()          # 保护 online 这个共享字典（多线程服务器必须加锁）
online = {}                      # 连接对象 -> {'name': 昵称, 'addr': 地址, 'time': 上线时间}


def now_str():
    return time.strftime('%H:%M:%S')


def broadcast(text, exclude=None):
    """把一行文本发给所有在线客户端（exclude 用于“不发给某人自己”）。"""
    line = (text + '\r\n').encode('utf-8')
    # 先把字典复制一份再遍历，避免遍历过程中别的线程往字典里加人/删人
    with lock:
        items = list(online.items())
    for conn, info in items:
        if conn is exclude:
            continue
        try:
            conn.sendall(line)
        except OSError:
            # 这个人已经断了，交给它自己的线程去清理，这里不动它
            pass


class ChatHandler(socketserver.StreamRequestHandler):
    def handle(self):
        conn = self.request
        addr = '%s:%s' % self.client_address
        name = None
        try:
            # 第一行是昵称；self.rfile 是 socketserver 帮我们包好的文件对象，
            # 用 readline() 可以一次读一行（读到 \\n 为止），不怕粘包
            line = self.rfile.readline(1024)
            if not line:
                return
            name = line.decode('utf-8').strip() or addr
            with lock:
                online[conn] = {'name': name, 'addr': addr, 'time': time.time()}
                count = len(online)
            print('[上线] %s（%s），当前在线 %d 人' % (name, addr, count))
            conn.sendall(('欢迎 %s 加入聊天室！当前在线 %d 人\r\n'
                          % (name, count)).encode('utf-8'))
            conn.sendall('输入 /list 看在线名单，输入 /quit 退出，其它内容直接聊天\r\n'.encode('utf-8'))
            broadcast('系统：%s 加入了聊天室' % name, exclude=conn)

            # 之后每来一行就是一条聊天内容
            while True:
                line = self.rfile.readline(4096)
                if not line:
                    break                                   # 客户端关闭了连接
                msg = line.decode('utf-8', 'ignore').strip()
                if not msg:
                    continue

                if msg == '/quit':                          # 主动退出
                    conn.sendall('再见了！\r\n'.encode('utf-8'))
                    break
                if msg == '/list':                          # 只看在线名单，只回给请求的人
                    with lock:
                        names = ['%s（%s）' % (v['name'], v['addr']) for v in online.values()]
                    conn.sendall(('当前在线 %d 人：%s\r\n'
                                  % (len(names), '、'.join(names))).encode('utf-8'))
                    continue
                if msg.startswith('/'):
                    conn.sendall(('不认识的命令：%s\r\n' % msg).encode('utf-8'))
                    continue

                print('[%s] %s: %s' % (now_str(), name, msg))
                broadcast('%s: %s' % (name, msg))           # 广播给所有人（包括自己）
        except (ConnectionResetError, ConnectionAbortedError) as e:
            print('[异常] %s（%s）异常断开：%s' % (name or '?', addr, e))
        finally:
            if name:
                with lock:
                    online.pop(conn, None)
                    count = len(online)
                print('[下线] %s（%s），当前在线 %d 人' % (name, addr, count))
                broadcast('系统：%s 离开了聊天室' % name)


class MyChatServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    with MyChatServer((HOST, PORT), ChatHandler) as server:
        print('聊天室服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：多开几个终端运行 python 05_chat_client.py')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n聊天室服务器退出，共 %d 人还在线' % len(online))
