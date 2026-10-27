#!/usr/bin/env python3
# coding: utf-8
"""
课本 5.5.2 聊天室（服务端）—— 代码 5-9s  chat_01s.py

聊天室要同时管理多个客户端，接收一个客户端的消息再转发给其它客户端，
所以用 socketserver.ThreadingTCPServer：每来一个客户端连接，socketserver
就自动开一个线程去执行 Chat_server.handle()，多个客户端互不干扰。

通信约定（跟课本一样，很朴素）：
    1) 客户端连上后发的第一条消息是“自己的用户名”，服务器回 'Welcome 用户名!'；
    2) 之后客户端发的都是聊天内容，服务器在前面加上用户名再广播给所有人；
    3) 消息前 3 个字符是 BYE（不分大小写）就表示要退出聊天室。

两个全局变量：
    conns —— 列表，存放所有客户端的连接对象（用列表才能按顺序广播）
    users —— 字典，键是连接对象，值是用户名
"""

import socketserver
import sys

# 课本里写的是 IP = '192.168.3.201'，那是作者机器的局域网地址；
# 本机测试用 127.0.0.1，要和别的机器联调就改成运行服务端那台机器的真实 IP。
IP = '127.0.0.1'
PORT = 9988


class Chat_server(socketserver.StreamRequestHandler):
    """自定义请求处理类，继承 StreamRequestHandler。

    StreamRequestHandler 把和客户端通信的套接字放在 self.request 里，
    并重写了 handle() 方法，所以我们只要重写 handle() 就行。
    """

    def handle(self):
        conn = self.request          # 第 7 行：取出和这个客户端通信的套接字
        try:
            while True:                                      # 第 9 行：无限循环处理这个客户端
                data_b = conn.recv(1024)                     # 第 10 行：收数据（bytes）
                print('data_b =', data_b)                    # 第 11 行

                #====[新增]:recv 收到空字节串说明客户端已经断开了。
                #     课本没判断这一点，客户端被强杀时会陷入死循环疯狂收空数据，这里补上====
                if not data_b:
                    print('%s 已断开连接' % users.get(conn, conn))
                    remove_conn(conn)
                    break

                if conns.count(conn) == 0:                   # 第 11 行：列表里没有它 = 新客户端
                    conns.append(conn)                       # 第 12 行：先加进列表
                    name_s = data_b.decode('utf-8')          # 第 13 行：新客户端的第一条消息是用户名
                    users.setdefault(conn, name_s)           # 第 14 行：记下“这个连接叫什么”
                    data_s = ''                              # 第 15 行
                    data = 'Welcome ' + name_s + '!'         # 第 16 行：欢迎语
                else:                                        # 老客户端，发的是聊天内容
                    name_s = users.get(conn)                 # 第 18 行：查到用户名
                    data_s = data_b.decode('utf-8')          # 第 19 行：聊天内容
                    data = name_s + ': ' + data_s            # 第 20 行：拼成“用户名: 内容”

                print('data =', data)                        # 第 22 行
                data_b = data.encode('utf-8')                # 第 23 行：转回 bytes 再发

                # 第 24、25 行：把这条消息广播给列表里的所有客户端
                for cn in list(conns):
                    #====[新增]:某个客户端已经断线时，别让它把这一轮广播搞崩，
                    #     所以每次 send 单独 try，失败了就把它清掉====
                    try:
                        cn.send(data_b)
                    except OSError as e:
                        print('给某个客户端发送失败：', e)
                        remove_conn(cn)

                if data_s.upper()[0:3] == 'BYE':             # 第 26 行：客户端要退出聊天室
                    print('%s is exited!' % name_s)          # 第 27 行
                    remove_conn(conn)                        # 第 28、29 行：从列表和字典里删掉
                    break                                    # 第 30 行：跳出循环，本线程结束
        except Exception as e:                               # 第 31、32 行
            print('Error is', e)
            #====[新增]:异常断开也要清理，不然 conns 里会留下“死连接”====
            remove_conn(conn)


def remove_conn(conn):
    """把连接从全局的列表和字典里删掉（本来就不在里面也不会报错）。"""
    if conns.count(conn) > 0:
        conns.remove(conn)
    users.pop(conn, None)


conns = []      # 第 33 行
users = {}      # 第 34 行

if __name__ == '__main__':
    # 课本是把 IP、端口写死在代码里的，这里允许用命令行参数覆盖，方便换机器测试：
    #   python chat_01s.py [IP] [端口]
    if len(sys.argv) > 1:
        IP = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])

    server = socketserver.ThreadingTCPServer((IP, PORT), Chat_server)   # 第 36 行
    #====[新增]:工作线程都设成守护线程，主线程 Ctrl+C 退出时它们一起退出====
    server.daemon_threads = True
    server.allow_reuse_address = True
    print('Wait for TCP connecting...')                                 # 第 37 行
    print('聊天室服务端已启动：%s:%d，可以同时开多个 chat_01c.py 来聊天' % (IP, PORT))
    try:
        server.serve_forever()                                          # 第 38 行
    except KeyboardInterrupt:
        print('\n服务端退出')
    finally:
        server.server_close()
