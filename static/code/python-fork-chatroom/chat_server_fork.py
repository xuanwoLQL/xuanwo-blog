# -*- coding: utf-8 -*-
"""
群聊聊天室 —— 服务端（fork 多进程版，Linux / Kali 专用）

对照老师给的示意图：父进程 accept 客户端请求，再交给子进程去处理“进入 / 退出 / 聊天”。

职责划分（关键点）：
  - 父进程：拥有监听套接字和所有客户端套接字，用 select 负责全部网络收发，并维护在线名单。
  - 子进程：只处理“刚收到的那一条消息”，根据这条消息 + 当前在线名单做判断，
            再把结论通过管道写回父进程，然后立刻退出。
  - 父进程：读子进程写回的结论，更新在线名单并广播。

为什么不让子进程长期持有客户端套接字？
  fork 之后，如果子进程关掉套接字，父进程那份 fd 就失效了（反之亦然），
  父进程再去广播就会失败——这是调试时踩到的真实坑（表现为“日志说已广播，客户端却收不到”）。
  所以让父进程独占套接字读写，子进程只做“无状态判断 + 写管道”，最稳。

Windows 上没有 os.fork，请用同目录的 chat_server.py（线程版，功能一样）。

用法（Kali）： python3 chat_server_fork.py [端口]     # 默认 9000
"""

import json
import os
import select
import socket
import struct
import sys

HOST = '0.0.0.0'
PORT = 9000
HEAD_LEN = 4
MAX_LEN = 1024 * 1024
HEAD = struct.Struct('!I')

clients = {}       # 昵称 -> 客户端套接字（仅父进程使用）
sockets = []       # 所有已连接套接字（父进程 select 监视）


# ---------------- 套接字协议：4 字节长度 + JSON ----------------
def recv_exact(conn, n):
    buf = b''
    while len(buf) < n:
        part = conn.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def recv_sock_msg(conn):
    head = recv_exact(conn, HEAD_LEN)
    if head is None:
        return None
    length = HEAD.unpack(head)[0]
    if length > MAX_LEN:
        return None
    body = recv_exact(conn, length)
    if body is None:
        return None
    return json.loads(body.decode('utf-8'))


def send_sock_msg(conn, obj):
    body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    conn.sendall(HEAD.pack(len(body)) + body)


# ---------------- 子进程 -> 父进程 的结果管道：4 字节长度 + JSON ----------------
def pipe_write(fd, obj):
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    os.write(fd, HEAD.pack(len(data)) + data)


def pipe_read_one(fd):
    buf = b''
    while len(buf) < HEAD_LEN:
        part = os.read(fd, HEAD_LEN - len(buf))
        if not part:
            return None
        buf += part
    length = HEAD.unpack(buf)[0]
    body = b''
    while len(body) < length:
        part = os.read(fd, length - len(body))
        if not part:
            break
        body += part
    return json.loads(body.decode('utf-8'))


def broadcast(msg, exclude=None):
    for name, conn in list(clients.items()):
        if name == exclude:
            continue
        try:
            send_sock_msg(conn, msg)
        except OSError:
            pass
    print('[服务端广播] %s' % msg.get('content', msg), flush=True)


def child_decide(conn, msg, cur_name, online_names):
    """子进程里执行：判断这条消息，必要时直接回 ack，然后把结论写进管道。"""
    mtype = msg.get('type')
    if cur_name is None:
        # 还没登录，只接受 login
        if mtype != 'login':
            pipe_write(_req_fd, {'type': 'ignore'})
            return
        name = str(msg.get('name', '')).strip()
        if not name:
            send_sock_msg(conn, {'type': 'login_ack', 'ok': False, 'reason': '昵称不能为空'})
            pipe_write(_req_fd, {'type': 'ignore'})
            return
        if name in online_names:
            send_sock_msg(conn, {'type': 'login_ack', 'ok': False, 'reason': '昵称已被占用'})
            pipe_write(_req_fd, {'type': 'ignore'})
            return
        send_sock_msg(conn, {'type': 'login_ack', 'ok': True, 'name': name})
        pipe_write(_req_fd, {'type': 'login', 'name': name})
        return
    # 已登录
    if mtype == 'quit':
        pipe_write(_req_fd, {'type': 'quit', 'name': cur_name})
        return
    if mtype == 'chat':
        pipe_write(_req_fd, {'type': 'chat', 'sender': cur_name,
                             'content': msg.get('content', '')})
        return
    pipe_write(_req_fd, {'type': 'ignore'})


_req_fd = None       # 子进程里使用的管道写端（fork 前设置好）


def handle_conn_data(conn):
    """父进程收到某个客户端的一条消息：fork 子进程判断，再读回结论并更新名单。"""
    global _req_fd
    msg = recv_sock_msg(conn)
    if msg is None:
        # 连接断开 / 数据非法
        old = _name_of.pop(conn, None)
        if conn in sockets:
            sockets.remove(conn)
        if old:
            clients.pop(old, None)
            broadcast({'type': 'system', 'content': '%s退出了聊天室' % old}, old)
        try:
            conn.close()
        except OSError:
            pass
        return

    rr, rw = os.pipe()          # 子进程 -> 父进程 传递结论
    _req_fd = rw
    cur_name = _name_of.get(conn)
    online_names = list(clients.keys())
    pid = os.fork()
    if pid == 0:
        # ---- 子进程 ----
        os.close(rr)
        sk.close()
        try:
            child_decide(conn, msg, cur_name, online_names)
        finally:
            os.close(rw)
        os._exit(0)
    # ---- 父进程 ----
    os.close(rw)
    info = pipe_read_one(rr)
    os.close(rr)
    os.waitpid(pid, 0)
    if info is None:
        return
    t = info.get('type')
    if t == 'login':
        _name_of[conn] = info['name']
        clients[info['name']] = conn
        broadcast({'type': 'system', 'content': '%s进入了聊天室' % info['name']},
                  info['name'])
    elif t == 'chat':
        broadcast({'type': 'chat', 'sender': info['sender'], 'content': info['content']},
                  info['sender'])
    elif t == 'quit':
        _name_of[conn] = None
        clients.pop(info['name'], None)
        broadcast({'type': 'system', 'content': '%s退出了聊天室' % info['name']},
                  info['name'])


_name_of = {}      # 连接 -> 昵称


def main():
    global sk, _name_of
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sk.bind((HOST, port))
    sk.listen(100)
    print('聊天室服务端(fork版)已启动，监听 %s:%d，父进程 pid=%d' % (HOST, port, os.getpid()), flush=True)
    try:
        while True:
            ready, _, _ = select.select([sk] + sockets, [], [])
            for r in ready:
                if r is sk:
                    conn, addr = sk.accept()
                    sockets.append(conn)
                    _name_of[conn] = None
                    print('新连接 %s' % (addr,), flush=True)
                else:
                    handle_conn_data(r)
    except KeyboardInterrupt:
        print('\n父进程退出')
    finally:
        sk.close()


if __name__ == '__main__':
    if not hasattr(os, 'fork'):
        print('当前系统（%s）没有 os.fork，请用 chat_server.py（线程版），或在 Kali 里运行本文件。' % sys.platform)
        sys.exit(0)
    main()
