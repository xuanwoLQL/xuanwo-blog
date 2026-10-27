# -*- coding: utf-8 -*-
"""
基于 select 的回声客户端（用于测试服务器）

需求：连接服务器、发送消息、显示收到的回声；
      允许用户输入字符串发送给服务器；有良好的错误处理（连接失败/传输错误）。

用法：
  python select_echo_client.py [服务器IP] [端口]
  默认 127.0.0.1 9300。
  交互：输入一行回车即发送；输入 quit 退出。
"""

import select
import socket
import sys

BUFFER = 4096


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9300

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except ConnectionRefusedError:
        print('连接失败：服务器没有启动，请先运行 select_echo_server.py')
        sock.close()
        return
    except OSError as e:
        print('连接出错：%s' % e)
        sock.close()
        return

    print('已连接 %s:%d。输入一行回车发送，输入 quit 退出。' % (host, port))
    sock.setblocking(False)
    running = True
    try:
        while running:
            try:
                line = input('你：').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line.lower() == 'quit':
                break
            try:
                sock.sendall(line.encode('utf-8'))
            except OSError as e:
                print('发送失败：%s' % e)
                break
            # 用 select 等服务器回声（带超时，避免一直卡住）
            try:
                r, _, _ = select.select([sock], [], [], 5)
            except OSError as e:
                print('select 出错：%s' % e)
                break
            if not r:
                print('等待回声超时（5 秒），服务器可能没有响应')
                continue
            try:
                data = sock.recv(BUFFER)
            except OSError as e:
                print('接收失败：%s' % e)
                break
            if not data:
                print('服务器已关闭连接')
                break
            print('服务器回声：%s' % data.decode('utf-8', 'replace'))
    finally:
        sock.close()
        print('客户端退出')


if __name__ == '__main__':
    main()
