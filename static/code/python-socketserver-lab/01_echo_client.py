# -*- coding: utf-8 -*-
"""
实验 1.1 的测试客户端 —— 连接回显服务器，发什么就显示服务器返回什么

用法：
    python 01_echo_client.py [服务器IP] [端口]
不加参数默认连 127.0.0.1:8000。

可以同时开两个本客户端来验证 TCPServer 的“串行”特点：
第一个客户端登录后会一直占着服务器，第二个客户端要等第一个退出才会被处理。
"""

import socket
import sys


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        print('连接失败：请先运行 01_echo_server.py 启动服务器')
        return
    print('已连接到回显服务器 %s:%d，输入内容回车发送，直接回车退出' % (host, port))

    try:
        while True:
            msg = input('请输入要发送的内容：')
            if not msg:
                break
            s.sendall(msg.encode('utf-8'))      # 发消息
            echo = s.recv(1024)                 # 收回显
            if not echo:
                print('服务器已关闭连接')
                break
            print('服务器回显：%s' % echo.decode('utf-8'))
    except KeyboardInterrupt:
        print('\n用户中断')
    finally:
        s.close()
        print('客户端退出')


if __name__ == '__main__':
    main()
