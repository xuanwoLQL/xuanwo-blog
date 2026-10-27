# -*- coding: utf-8 -*-
"""
思考与扩展（选做）的聊天室客户端（控制台版）

用法：
    python 05_chat_client.py [服务器IP] [端口] [昵称]
默认：127.0.0.1 8005，昵称用“游客+随机数”。

同样是“一个线程收、主线程发”的结构：主线程 input() 等用户输入会阻塞，
所以收消息必须放在子线程 recv_thread() 里，否则别人发的话看不到。
输入 /list 看在线名单，输入 /quit 退出。
"""

import random
import socket
import sys
import threading

HOST, PORT = '127.0.0.1', 8005
running = True


def recv_thread(s):
    """子线程：一直收服务器发来的消息并打印。"""
    global running
    while running:
        try:
            data = s.recv(4096)
        except OSError:
            break
        if not data:
            print('\n服务器断开了连接')
            running = False
            break
        # 服务器一次可能发来多行，逐行打印
        for line in data.decode('utf-8', 'ignore').split('\r\n'):
            if line:
                print('\r' + line)          # \r 是为了不和 input() 的提示符挤在一起
                print('你（%s）：' % name, end='', flush=True)


if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    name = sys.argv[3] if len(sys.argv) > 3 else '游客%d' % random.randint(100, 999)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        print('连接失败：请先运行 05_chat_server.py')
        sys.exit(1)

    # 第一条消息发昵称
    s.sendall((name + '\r\n').encode('utf-8'))

    t = threading.Thread(target=recv_thread, args=(s,), daemon=True)
    t.start()

    try:
        while running:
            msg = input('你（%s）：' % name)
            if not msg:
                continue
            s.sendall((msg + '\r\n').encode('utf-8'))
            if msg.strip() == '/quit':
                break
    except (KeyboardInterrupt, EOFError):
        print('\n退出')
    finally:
        running = False
        s.close()
        print('客户端退出')
