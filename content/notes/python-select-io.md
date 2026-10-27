---
title: "select 非阻塞 IO 并发实验"
slug: "python-select-io"
date: 2026-10-12T16:44:27+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "用 select 多路复用同时处理多个客户端连接。"
summary: "用 select 多路复用同时处理多个客户端连接。"
tags: ["Python", "select", "IO多路复用"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 3
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/基于非阻塞IO模型(select)的并发实验/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-select-io/workflow.svg" alt="单线程用 select 监听多个 socket，只对就绪描述符执行 read/write。" loading="lazy">
  <figcaption>图 1 · select 非阻塞 IO 模型。单线程用 select 监听多个 socket，只对就绪描述符执行 read/write。</figcaption>
</figure>

## 需求
1. 写一个基于 select 的 TCP 服务器，可同时接受多个客户端连接；
2. 把收到的数据原样返回（回声）；
3. 客户端断开时正确关闭连接、清理资源；
4. 单进程内用 select 管理所有连接，维护连接列表，监视可读/可写/异常事件；
5. 写一个测试客户端：连接后发消息、显示回声，并有基本错误处理。

## 文件
| 文件 | 说明 |
|---|---|
| `select_echo_server.py` | select 并发回声服务器（单进程） |
| `select_echo_client.py` | 测试客户端 |

## 运行
```bash
python select_echo_server.py [端口]        # 默认 9300
python select_echo_client.py 127.0.0.1 9300
```
可以多开几个客户端，观察服务器同时给所有人回声。

## 实现要点
- 三个集合：
  - `inputs`（可读）：监听套接字 + 所有客户端；有新连接或新数据时被唤醒。
  - `outputs`（可写）：暂时发不完的连接；都发完了就移出去。
  - `excepts`（异常）：出现异常事件时关闭该连接。
- 所有客户端套接字设为非阻塞；`send` 发不完就把剩余数据留在 `sendbuf`，下次可写时再补发，
  主循环不会因为某个慢客户端被卡住。

## 自测结果
3 个客户端同时连接并发回声全部正确；断开一个客户端后服务器继续服务其他客户端；中文字符串回声正常。

## 常见问题 / 分析
- **为什么用 select 而不是多线程/多进程？** select 在单进程里管理成百上千个连接，
  没有线程切换和锁的开销；但每个连接都要自己维护收发缓冲，逻辑比“一个连接一个线程”复杂。
- **select 的局限**：一是可监视的 fd 数量有限（通常 1024）；二是每次都要把整个 fd 集合
  从用户态复制到内核态并线性扫描，连接很多时效率下降。连接数非常大的场景更适合 epoll（Linux）。
- **本实验要不要在虚拟机里做？** 不需要，Windows 也能跑；用你的 Kali 当然更贴近课本环境：
  把两个 `.py` 拷进 Kali，`python3 select_echo_server.py` 和 `python3 select_echo_client.py` 即可。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-select-io 完整源码包](/code/python-select-io/source.zip)

项目目录：

```text
基于非阻塞IO模型(select)的并发实验/
├─ select_echo_client.py
├─ select_echo_server.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：select_echo_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
基于 select 的并发（多路复用）回声服务器

需求：
  (1) 一个基于 select 的 TCP 服务器，可同时接受多个客户端的连接请求；
  (2) 把收到的客户端数据原样返回（回声功能）；
  (3) 客户端断开时，正确关闭连接并清理资源；
  (4) 单进程内用 select 管理所有连接，维护连接列表，
      监视这些连接上的可读、可写、异常事件。

设计要点：
  - 用一个 select 同时监视“监听套接字 + 所有已连接套接字”；
  - 用三个集合区分三类事件：
        inputs  —— 关心“可读”：监听套接字（有新连接）+ 各客户端（有数据/断开）
        outputs —— 关心“可写”：有待发数据的连接（回声还没发完时挂上）
        excepts —— 关心“异常”：出现带外数据等异常时处理
  - 所有客户端套接字设为非阻塞，send 发不完就放进 pending 缓存，
    下次它可写时再补发，主线程绝不被某个慢客户端卡住。

用法：
  python select_echo_server.py [端口]     # 默认 9300
"""

import select
import socket
import sys

HOST = '0.0.0.0'
PORT = 9300
BUFFER = 4096


class SelectEchoServer:
    def __init__(self, port):
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((HOST, port))
        self.server.listen(100)
        self.server.setblocking(False)

        self.inputs = [self.server]     # 关心可读
        self.outputs = []               # 关心可写（有待发数据）
        self.conns = {}                 # 套接字 -> {'addr':..., 'sendbuf':..., 'recvbuf':...}
        print('select 回声服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, port))

    # ---- 接受一个新连接 ----
    def accept(self):
        while True:
            try:
                conn, addr = self.server.accept()
            except BlockingIOError:
                return              # 没有更多新连接了
            except OSError as e:
                print('accept 出错：%s' % e)
                return
            conn.setblocking(False)
            self.inputs.append(conn)
            self.conns[conn] = {'addr': addr, 'sendbuf': b'', 'recvbuf': b''}
            print('新连接 %s，当前连接数 %d' % (addr, len(self.conns)))

    # ---- 关闭一条连接并清理资源 ----
    def close_conn(self, conn):
        info = self.conns.pop(conn, None)
        if conn in self.inputs:
            self.inputs.remove(conn)
        if conn in self.outputs:
            self.outputs.remove(conn)
        try:
            conn.close()
        except OSError:
            pass
        if info:
            print('连接 %s 断开，清理资源。当前连接数 %d' % (info['addr'], len(self.conns)))

    # ---- 处理可读：有数据就读，读到 EOF 表示对方关闭 ----
    def readable(self, conn):
        try:
            data = conn.recv(BUFFER)
        except BlockingIOError:
            return
        except (ConnectionResetError, OSError) as e:
            print('recv 出错 %s：%s' % (self.conns[conn]['addr'], e))
            self.close_conn(conn)
            return
        if not data:                # 空字节串 = 对端关闭连接
            self.close_conn(conn)
            return
        text = data.decode('utf-8', 'replace')
        print('收到 %s 的数据：%r' % (self.conns[conn]['addr'], text))
        # 回声：把收到的数据原样写进待发缓存，并把这个连接加入“可写”集合
        self.conns[conn]['sendbuf'] += data
        if conn not in self.outputs:
            self.outputs.append(conn)

    # ---- 处理可写：把待发数据尽量发出去 ----
    def writable(self, conn):
        info = self.conns.get(conn)
        if not info:
            return
        buf = info['sendbuf']
        if not buf:
            self.outputs.remove(conn)
            return
        try:
            sent = conn.send(buf)
        except BlockingIOError:
            return                  # 发送缓冲区满了，下次再发
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print('send 出错 %s：%s' % (info['addr'], e))
            self.close_conn(conn)
            return
        info['sendbuf'] = buf[sent:]
        if not info['sendbuf']:
            self.outputs.remove(conn)   # 发完了就不用再关心可写

    # ---- 处理异常 ----
    def exceptional(self, conn):
        print('连接 %s 出现异常事件，关闭它' % (self.conns.get(conn, {}).get('addr')))
        self.close_conn(conn)

    def run(self):
        try:
            while True:
                # select 阻塞等待，直到有事件发生（可读/可写/异常）
                readable, writable, exceptional = select.select(
                    self.inputs, self.outputs, self.inputs)
                for conn in readable:
                    if conn is self.server:
                        self.accept()
                    else:
                        self.readable(conn)
                for conn in writable:
                    self.writable(conn)
                for conn in exceptional:
                    if conn in self.conns:
                        self.exceptional(conn)
        except KeyboardInterrupt:
            print('\n服务器退出，正在关闭所有连接……')
        finally:
            for conn in list(self.conns):
                self.close_conn(conn)
            self.server.close()
            print('服务器已关闭')


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    SelectEchoServer(port).run()


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：select_echo_client.py</summary>

```python
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
```

</details>
