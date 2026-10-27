---
title: "GUI 聊天室"
slug: "python-gui-chatroom"
date: 2026-10-18T11:31:23+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "基于 Socket 与 tkinter 的图形化聊天室，包含协议设计与消息广播。"
summary: "基于 Socket 与 tkinter 的图形化聊天室，包含协议设计与消息广播。"
tags: ["Python", "tkinter", "聊天室"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 7
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/GUI聊天室实例作业/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-gui-chatroom/workflow.svg" alt="Tkinter 界面负责输入和显示，网络线程负责收发，服务器负责广播。" loading="lazy">
  <figcaption>图 1 · GUI 聊天室组件关系。Tkinter 界面负责输入和显示，网络线程负责收发，服务器负责广播。</figcaption>
</figure>

## 需求
按课本图片里的代码写服务端和客户端：
- 服务端（代码 5-9s `chat_01s.py`）：用 `socketserver.ThreadingTCPServer` 实现多线程聊天室，
  维护 `conns`（连接列表）和 `users`（连接→用户名），把每个客户端的消息广播给所有人。
- 客户端（代码 5-9c `chat_01c.py`）：用 tkinter 做图形界面，一个列表框显示聊天记录，
  一个输入框 + 一个按钮（Logon/Send 切换），另开一个线程 `receive_msg()` 收消息。

## 文件
| 文件 | 说明 |
|---|---|
| `chat_01s.py` | 聊天室服务端（代码 5-9s），默认监听 `127.0.0.1:9988` |
| `chat_01c.py` | 聊天室客户端（代码 5-9c），tkinter 图形界面 |

## 运行
```bash
# 1. 先启动服务端
python chat_01s.py              # 也可以：python chat_01s.py 192.168.1.10 9988

# 2. 再启动两个（或多个）客户端，观察是否互相收到消息
python chat_01c.py
python chat_01c.py
```

界面操作：
1. 在输入框里输入自己的用户名（例如 `张三`），点 **Logon** 按钮 —— 这一步是把用户名发给服务器，
   其他客户端会看到 `Welcome 张三!`，按钮文字变成 **Send**。
2. 输入聊天内容回车/点 **Send**，所有客户端都会收到 `张三: 内容`。
3. 输入 `BYE` 发送，就退出聊天室，其他客户端会看到 `张三 is exited!`。

## 实现要点
- 服务端每来一个客户端，`ThreadingTCPServer` 自动开一个线程执行 `handle()`，互不阻塞。
- `handle()` 用 `conns.count(conn) == 0` 判断是不是新客户端：新客户端的第一条消息当用户名，
  之后的当聊天内容；`users` 字典就是“连接对象 → 用户名”的映射。
- 客户端必须用子线程 `receive_msg()` 收消息，否则 `recv()` 会把 tkinter 主线程卡死。
- 消息前 3 个字符是 `BYE`（不分大小写）表示退出。

## 对课本代码做的少量修正（代码里都标了 `#====[新增]`）
1. 服务端 `recv()` 收到空字节串（客户端被强杀/关窗口）时课本会死循环刷空数据，加了判断并清理连接。
2. 广播时对每个连接单独 `try`，避免一个客户端断线导致这一轮广播整体失败。
3. 异常断开时把连接从 `conns`/`users` 里清理掉，不然会留下“死连接”。
4. 客户端把“启动接收线程”放到“建好控件”之后，避免线程往还没创建的 `chat_list` 里插数据。
5. IP/端口支持命令行参数；课本里的 `192.168.3.201` 是作者机器的地址，本机测试用 `127.0.0.1`。

代码里 `# 第 N 行` 的注释对应课本上的行号，方便和书上的代码对照。

## 自测结果

### 服务端（用 socket 直接模拟客户端，12 项全通过）
| 测的东西 | 结果 |
|---|---|
| 新客户端登录 | 发用户名后收到 `Welcome alice!` ✔ |
| 第二个客户端登录 | bob 自己收到欢迎语，**alice 也收到**（广播生效）✔ |
| 聊天消息 | `alice: 大家好` 同时到达 alice 和 bob ✔ |
| 发 BYE | 服务端打印 `bob is exited!`，并主动关闭 bob 的连接（recv 返回空字节串）✔ |
| BYE 之后 | 剩下的 alice 仍能正常收发 ✔ |
| 异常断开（不发 BYE 直接关 socket） | 服务端打印 `carol 已断开连接`，不崩溃；新客户端照样能进来聊 ✔ |
| 并发 | 5 个客户端同时登录、各发一条，都收到了自己的广播 ✔ |

### 客户端界面（用脚本自动驱动按钮，见下）
把窗口跑起来、自动“输入用户名 → 点 Logon → 输入两条消息 → 发 BYE”，结果：
```
按钮文字：Logon → Send            （第一次点击后正确切换）
列表框：[0] Welcome 自动测试用户!
        [1] 自动测试用户: 大家好，这是自动测试发的消息
        [2] 自动测试用户: 第二条消息
发 BYE 后按钮状态 = disabled      （课本第 16 行的逻辑生效）
```
服务端日志同步可见 `data = Welcome 自动测试用户!`、`data = 自动测试用户: 大家好…`。

> 小提示：如果同时开 5 个以上的客户端猛发消息，服务端控制台的打印会互相插花 ——
> 课本的代码是直接用 `print()` 打印的，没加锁，多线程下输出会交错。不影响功能，只是日志不好看。

## 和课本代码的对应关系
代码里凡是 `# 第 N 行` 的注释，都对应课本（第 147~149 页）上的行号；
标了 `#====[新增]` 的地方是上面第（修正）节里提到的补充。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-gui-chatroom 完整源码包](/code/python-gui-chatroom/source.zip)

项目目录：

```text
GUI聊天室实例作业/
├─ chat_01c.py
├─ chat_01s.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：chat_01s.py</summary>

```python
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
```

</details>

<details>
<summary>打开完整代码：chat_01c.py</summary>

```python
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
```

</details>
