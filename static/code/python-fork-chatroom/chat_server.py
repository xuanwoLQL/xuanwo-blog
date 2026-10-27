# -*- coding: utf-8 -*-
"""
群聊聊天室 —— 服务端

需求（见同目录 需求文档.txt）：
  1. 有人进入聊天室时，其他人会收到姓名，姓名不能重复
  2. 有人进入聊天室时，其他人会收到通知：xxx进入了聊天室
  3. 一个人发消息，其他人会收到 xxx：xxxxxx
  4. 有人退出聊天室，其他人会收到通知 xxx退出了聊天室
  5. 扩展功能：服务器可以向所有用户发送公告：管理员消息：xxxxxx

说明：
  - 用 TCP + 线程实现（课本 4-3c 的“长度前缀协议”解决粘包，见 chatroom_protocol.py）。
    每个客户端一个线程，可以同时服务很多人；一轮广播时加锁，保证消息不会串行错乱。
  - 这里不直接用 os.fork 是因为本机是 Windows，os.fork 只在 Linux 下可用；
    线程模型在本实验里能表达同样的“每个连接独立处理”的效果。
  - 服务端自己也可以在控制台敲字，回车后以“管理员消息”广播给所有用户（扩展功能）。

用法：
  python chat_server.py [端口]      # 默认端口 9000
"""

import socket
import sys
import threading

from chatroom_protocol import send_msg, recv_msg

HOST = '0.0.0.0'
PORT = 9000

clients = {}          # 昵称 -> {'conn': 套接字, 'send_lock': 该连接的发锁}
clients_lock = threading.Lock()


def broadcast(msg, exclude=None):
    """把消息发给所有在线用户，exclude 可排除某个昵称（比如发消息的人自己）。"""
    with clients_lock:
        targets = [(name, info) for name, info in clients.items() if name != exclude]
    dead = []
    for name, info in targets:
        try:
            with info['send_lock']:
                send_msg(info['conn'], msg)
        except OSError:
            dead.append(name)     # 发送失败说明这个用户已经掉线，稍后清理
    for name in dead:
        with clients_lock:
            info = clients.pop(name, None)
        if info:
            try:
                info['conn'].close()
            except OSError:
                pass


def handle_client(conn, addr):
    """一个客户端一个线程：先登录，再循环收消息并转发。"""
    name = None
    send_lock = threading.Lock()
    try:
        # ---- 登录：反复要求昵称，直到不重复 ----
        while True:
            msg = recv_msg(conn)
            if msg is None:
                return
            if msg.get('type') != 'login':
                continue
            want = str(msg.get('name', '')).strip()
            if not want:
                with send_lock:
                    send_msg(conn, {'type': 'login_ack', 'ok': False, 'reason': '昵称不能为空'})
                continue
            with clients_lock:
                if want in clients:
                    exists = True
                else:
                    exists = False
                    clients[want] = {'conn': conn, 'send_lock': send_lock}
            if exists:
                # 需求1：姓名不能重复
                with send_lock:
                    send_msg(conn, {'type': 'login_ack', 'ok': False, 'reason': '昵称已被占用'})
                continue
            name = want
            with send_lock:
                send_msg(conn, {'type': 'login_ack', 'ok': True, 'name': name})
            print('%s 登录成功 %s' % (addr, name))
            break

        # 需求2：通知其他人 xxx进入了聊天室（并带上姓名，满足“其他人会收到姓名”）
        broadcast({'type': 'system', 'content': '%s进入了聊天室' % name}, exclude=name)

        # ---- 循环收消息并转发给其他人 ----
        while True:
            msg = recv_msg(conn)
            if msg is None:       # 客户端关闭连接
                break
            if msg.get('type') == 'chat':
                content = str(msg.get('content', ''))
                print('[%s] %s' % (name, content))
                # 需求3：其他人会收到 xxx：xxxxxx
                broadcast({'type': 'chat', 'sender': name, 'content': content}, exclude=name)
            elif msg.get('type') == 'quit':
                break
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        # 需求4：有人退出聊天室，其他人收到通知
        if name:
            with clients_lock:
                info = clients.pop(name, None)
            if info:
                broadcast({'type': 'system', 'content': '%s退出了聊天室' % name})
                print('%s 退出了聊天室' % name)
        try:
            conn.close()
        except OSError:
            pass


def admin_console():
    """扩展功能：服务端控制台敲一行字，就向所有用户广播“管理员消息：xxxxxx”。"""
    while True:
        try:
            text = input()
        except EOFError:
            return
        text = text.strip()
        if not text:
            continue
        if text == '/quit':
            print('（服务端控制台结束，服务器仍继续运行）')
            return
        broadcast({'type': 'announce', 'content': '管理员消息：%s' % text})
        print('（已广播）管理员消息：%s' % text)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 端口释放后可以马上重新绑定，避免调试时“地址已被占用”
    sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sk.bind((HOST, port))
    sk.listen(100)     # 课本：listen 参数 100，表示最多同时接受 100 个客户端
    print('聊天室服务端已启动，监听 %s:%d' % (HOST, port))
    print('（在控制台敲字并回车 = 以管理员身份向所有人发公告；Ctrl+C 退出）')

    # 后台线程读管理员公告
    threading.Thread(target=admin_console, daemon=True).start()

    try:
        while True:
            conn, addr = sk.accept()
            print('新连接来自 %s' % (addr,))
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print('\n服务端退出')
    finally:
        sk.close()


if __name__ == '__main__':
    main()
