# -*- coding: utf-8 -*-
"""
群聊聊天室 —— 客户端

用法：
  python chat_client.py [服务器IP] [端口]     # 默认 127.0.0.1 9000

交互：
  - 启动后先输入昵称（昵称不能重复，重名会提示重新输入）
  - 进入聊天室后：回车即发送一条消息，其他人都能看到 "你的昵称：消息内容"
  - 输入 quit 退出聊天室，其他人会收到 "xxx退出了聊天室"

实现：主线程负责读键盘发送，后台线程负责收消息并打印，两者用一把锁避免打印串行。
"""

import socket
import sys
import threading

from chatroom_protocol import send_msg, recv_msg

stop_event = threading.Event()
print_lock = threading.Lock()


def safe_print(text):
    with print_lock:
        print(text)


def recv_loop(sock, name):
    """后台线程：一直收消息并显示。"""
    while not stop_event.is_set():
        try:
            msg = recv_msg(sock)
        except OSError:
            msg = None
        if msg is None:
            safe_print('\n[连接已断开，聊天室关闭]')
            stop_event.set()
            return
        t = msg.get('type')
        if t == 'chat':
            safe_print('%s：%s' % (msg['sender'], msg['content']))
        elif t == 'system':
            safe_print('*** %s ***' % msg['content'])
        elif t == 'announce':
            safe_print('>>> %s' % msg['content'])


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9000

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except ConnectionRefusedError:
        print('连接失败：服务端没有启动，请先运行 chat_server.py')
        sock.close()
        return

    # ---- 登录：输入昵称，直到服务端接受 ----
    while True:
        name = input('请输入昵称：').strip()
        if not name:
            print('昵称不能为空')
            continue
        send_msg(sock, {'type': 'login', 'name': name})
        ack = recv_msg(sock)
        if ack is None:
            print('服务端已关闭连接')
            sock.close()
            return
        if ack.get('ok'):
            break
        print('进入失败：%s，请换一个昵称' % ack.get('reason', '未知原因'))

    print('已进入聊天室，你叫 %s。输入 quit 退出。' % name)
    recv_thread = threading.Thread(target=recv_loop, args=(sock, name), daemon=True)
    recv_thread.start()

    # ---- 主线程：读键盘发送 ----
    try:
        while not stop_event.is_set():
            try:
                text = input()
            except EOFError:
                break
            if stop_event.is_set():
                break
            text = text.strip()
            if not text:
                continue
            if text.lower() == 'quit':
                try:
                    send_msg(sock, {'type': 'quit'})
                except OSError:
                    pass
                break
            try:
                send_msg(sock, {'type': 'chat', 'content': text})
            except OSError:
                safe_print('[发送失败，连接可能已断开]')
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        try:
            sock.close()
        except OSError:
            pass
        print('已退出聊天室')


if __name__ == '__main__':
    main()
