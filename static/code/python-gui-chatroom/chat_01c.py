#!/usr/bin/env python3
# coding: utf-8
"""
课本 5.5.3 聊天室（客户端）—— 代码 5-9c  chat_01c.py

界面：一个聊天记录列表框（带滚动条）+ 一个输入框 + 一个按钮。
按钮文字会在 'Logon' 和 'Send' 之间切换：第一次点击时输入框里填的是用户名，
点 Logon 相当于“登录”，按钮文字变成 Send，之后输入的就是聊天内容。

为什么要用线程：recv() 是阻塞的，如果放在主线程里收消息，界面就会卡住不动，
所以单开一个线程 receive_msg() 专门收消息，主线程专心跑 tkinter 的 mainloop()。

用法：
    python chat_01c.py [服务器IP] [端口]
"""

import socket
import sys
import threading
import tkinter as tk

# 与服务端保持一致：本机测试用 127.0.0.1，跨机器改成服务端的真实 IP
IP = '127.0.0.1'
PORT = 9988


def send_msg():
    """按钮的回调函数：向服务器发送消息（登录时发的是用户名）。"""
    txt = bt_txt.get()
    if txt == 'Logon':                                  # 第 9 行：第一次点击，按钮由 Logon 变 Send
        bt_txt.set('Send')
    msg = et_txt.get()                                  # 第 10 行：取输入框内容
    et_txt.set('')                                      # 第 11 行：清空输入框
    print('msg =', msg)
    msg_b = msg.encode('utf-8')                         # 第 13 行
    s.send(msg_b)                                       # 第 14 行：发给服务器
    if msg.upper()[0:3] == 'BYE':                       # 第 15 行：要退出聊天室
        chat_send.config(state=tk.DISABLED)             # 第 16 行：按钮变成不可点
        s.close()                                       # 第 17 行
        print('已发送 BYE，可以关闭窗口了')


def receive_msg():
    """在子线程里循环接收服务器广播来的消息，并显示到列表框。"""
    while True:
        try:
            data_b = s.recv(1024)                       # 第 21 行
            data_s = data_b.decode('utf-8')             # 第 22 行
            print('data_s =', data_s)

            #====[新增]:收到空字节串说明服务器已经关掉了连接，再循环下去会刷屏====
            if not data_s:
                print('和服务器断开了')
                break

            chat_list.insert(tk.END, data_s)            # 第 24 行：追加到列表末尾
            chat_list.see(tk.END)                       # 第 25 行：自动滚动到最新一条
        except Exception as e:                          # 第 26 行
            print('Error is ', e)
            print('Exit!')
            break


if __name__ == '__main__':
    if len(sys.argv) > 1:
        IP = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])

    # 第 32、33 行：先连服务器（连不上就没必要开窗口了）
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((IP, PORT))
    except ConnectionRefusedError:
        print('连接失败：请先运行 chat_01s.py 启动聊天室服务端')
        sys.exit(1)
    print('已连接到聊天室服务器 %s:%d' % (IP, PORT))

    #====[新增]:课本是“先启动接收线程、再建窗口”，但线程里要往 chat_list 里塞数据，
    #     万一这时控件还没建好就会报 NameError；所以这里把控件建好之后再启动线程====
    root = tk.Tk()                                              # 第 36 行
    root.title('Chatting room')                                 # 第 37 行
    root.geometry('300x350')                                    # 第 38 行
    root.resizable(width=False, height=True)                    # 第 39 行
    fm = tk.Frame(root, width=300, height=300)                  # 第 40 行
    scrl = tk.Scrollbar(fm)                                     # 第 41 行：列表框的滚动条
    chat_list = tk.Listbox(fm, width=300, selectmode=tk.BROWSE)  # 第 42 行：聊天记录
    chat_list.configure(yscrollcommand=scrl.set)                # 第 43 行
    scrl['command'] = chat_list.yview                           # 第 44 行
    bt_txt = tk.StringVar(value='Logon')                        # 第 45 行：按钮上的文字
    et_txt = tk.StringVar(value='')                             # 第 46 行：输入框的内容
    chat_txt = tk.Entry(root, bd=5, width=280, textvariable=et_txt)               # 第 47 行
    chat_send = tk.Button(root, textvariable=bt_txt, command=send_msg)            # 第 48 行
    scrl.pack(side=tk.RIGHT, fill=tk.Y)                         # 第 49 行
    chat_txt.pack()                                             # 第 50 行
    chat_send.pack()                                            # 第 51 行
    chat_list.pack()                                            # 第 52 行
    fm.pack()                                                   # 第 53 行

    # 第 34、35 行：开一个守护线程专门收消息
    t = threading.Thread(target=receive_msg, daemon=True)
    t.start()

    root.mainloop()                                             # 第 54 行
