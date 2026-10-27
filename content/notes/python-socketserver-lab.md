---
title: "socketserver 编程实验"
slug: "python-socketserver-lab"
date: 2026-10-18T11:31:48+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "用 socketserver 写 TCP / UDP / 多线程 / 混合模式服务器与客户端。"
summary: "用 socketserver 写 TCP / UDP / 多线程 / 混合模式服务器与客户端。"
tags: ["Python", "Socket", "并发"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 1
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/socketserver编程实验/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-socketserver-lab/workflow.svg" alt="请求处理器负责协议逻辑，服务器类负责监听和并发调度，存储层负责文件读写。" loading="lazy">
  <figcaption>图 1 · socketserver 并发模型。请求处理器负责协议逻辑，服务器类负责监听和并发调度，存储层负责文件读写。</figcaption>
</figure>

## 实验内容与文件对照

| 实验 | 要求 | 文件 |
|---|---|---|
| 1.1 基础 TCPServer | `TCPServer` 回显服务器，自定义类继承 `BaseRequestHandler`，监听 8000 | `01_echo_server.py`、`01_echo_client.py` |
| 1.2 多线程 TCPServer | `ThreadingTCPServer`，记录连接时间/IP，显示当前连接数 | `02_threading_server.py`、`02_threading_client.py` |
| 1.3 UDP 服务器 | `UDPServer`，返回消息长度和接收时间，带数据包统计，监听 8001 | `03_udp_server.py`、`03_udp_client.py` |
| 1.4 混合服务器 | 多线程同时跑 TCP（收文件）和 UDP（时间同步） | `04_hybrid_server.py`、`04_hybrid_client.py` |
| 选做 思考与扩展 | 简单聊天室服务器，支持多客户端同时聊天 | `05_chat_server.py`、`05_chat_client.py` |

每个实验都配了测试客户端，可以单独跑起来验证。

## 运行

四个服务器用的端口不冲突（8000 / 8002 / 8001 / 8003+8004），可以同时开着。

```bash
# 实验 1.1（先开服务端，再开 1~2 个客户端）
python 01_echo_server.py
python 01_echo_client.py

# 实验 1.2（一个服务端 + 一个模拟 5 个客户端的脚本）
python 02_threading_server.py
python 02_threading_client.py 127.0.0.1 8002 5 3

# 实验 1.3
python 03_udp_server.py
python 03_udp_client.py

# 实验 1.4（一个服务器同时提供两个服务）
python 04_hybrid_server.py
python 04_hybrid_client.py time            # UDP 校时
python 04_hybrid_client.py upload 要传的文件.txt   # TCP 传文件

# 选做：聊天室（服务端 + 多个客户端，各开一个终端）
python 05_chat_server.py
python 05_chat_client.py 127.0.0.1 8005 张三
python 05_chat_client.py 127.0.0.1 8005 李四
```

## 各实验实现要点

### 1.1 基础 TCPServer
- socketserver 的固定套路：处理类继承 `BaseRequestHandler` 并重写 `handle()` →
  `Server((地址, 端口), 处理类)` → `serve_forever()`。
- `self.request` 是和客户端通信的套接字，`self.client_address` 是客户端 `(IP, 端口)`。
- **`TCPServer` 是串行的**：一次只服务一个连接。开两个客户端就能看到第二个在排队，
  这是它和 1.2 的 `ThreadingTCPServer` 的本质区别。

### 1.2 多线程 TCPServer
- 类名只差一个 `Threading`，每来一个连接自动新建线程跑 `handle()`。
- 连接时间、IP 记录在 `online` 字典里，当前连接数就是 `len(online)`。
- **共享变量 `online`、`total_conn` 用 `threading.Lock` 加锁**，避免多线程同时改导致数据错乱。
- `daemon_threads = True`：主线程退出时工作线程一起退出。

### 1.3 UDP 服务器
- UDP 的 `self.request` 是 `(数据报, 服务器套接字)` 元组，一个数据报调用一次 `handle()`，
  所以 `handle()` 里不用写 `while True`。
- 回复要用 `sock.sendto(数据, self.client_address)`，UDP 没有连接对象。
- 数据包统计放在 `stats`（按客户端分别统计）+ `total`（总量）里。
- `UDPServer` 是单线程串行处理，`handle()` 不会并发，所以这里没加锁。

### 1.4 混合服务器
- 两个 `serve_forever()` 各占一个线程（UDP 在子线程，TCP 在主线程），
  所以同一个程序同时监听 TCP 8003 和 UDP 8004。
- TCP 上传协议：`b'UPLD'` + 4 字节文件名长度 + 文件名 + 8 字节文件大小 + 文件内容，
  用长度前缀解决粘包；`recv_exact()` 负责“收满 n 个字节”，解决分包。
- 服务端存文件时用 `os.path.basename()` 去掉路径，防止 `../../` 目录穿越。
- 服务端一边写盘一边算 MD5 并回给客户端，客户端拿本地 MD5 比对，验证文件完整性。
- UDP 校时：客户端记下 `t0`（发包前）和 `t3`（收包后），
  服务器回自己的 unix 时间戳，客户端算 `偏移 = 服务器时间 - (t0+t3)/2` 和往返时延。

### 选做：聊天室
- 用 `self.rfile.readline()` **按行读取**，一条消息一行（`\n` 结尾），
  这是控制台程序里最简单的“防粘包”办法。
- 支持昵称、上线/下线系统提示、`/list` 在线名单、`/quit` 退出。
- `online` 字典被多个线程读写，广播前先把字典复制一份再遍历（加锁），避免边遍历边修改。
- 客户端是“子线程收消息 + 主线程 input() 发消息”，不然 input() 一阻塞就看不到别人的话了。

## 自测结果

### 1.1 基础 TCPServer（6 项全通过）
- 回显正确：`hello`、`中文测试`、500 字节长内容，发多少回多少，一字不差 ✔
- **串行特点实测**：a 还连着的时候，b 发消息收不到回显（被挡住）；a 一断开，
  b 立刻收到自己的回显 —— 正好证明了 `TCPServer` 一次只服务一个连接 ✔
- 客户端用 `SO_LINGER` 强制发 RST 模拟“拔网线”，服务端打印
  `[异常] 客户端 … 非正常断开：[WinError 10054]` 后继续服务新客户端，不崩溃 ✔

### 1.2 多线程 TCPServer（5 个客户端并发）
服务端日志里的在线数量：`1 → 2 → 3 → 4 → 5`（5 个客户端同时在线），
每个都记录了 `连接时间：2026-10-18 11:10:51` 和自己的 IP；
客户端全部退出后数量 `5 → 4 → 3 → 2 → 1 → 0`。
5 个客户端各发 2 条（每条间隔 0.3 秒），**总耗时 0.61 秒** ——
如果是串行的 1.1，需要 5 倍以上的时间。✔

### 1.3 UDP 服务器（4 个数据包）
```
第 1 条：我发了 28 字节，往返 1.0 毫秒
        服务器回复：收到消息长度：28 字节，接收时间：2026-10-18 11:12:44（这是你的第 1 个包）
第 4 条：我发了 37 字节，往返 0.7 毫秒
        服务器回复：收到消息长度：37 字节，接收时间：2026-10-18 11:12:45（这是你的第 4 个包）
```
长度、时间、按客户端分开的包计数都正确 ✔（按 Ctrl+C 退出时还会打印总的包数/字节数统计）

### 1.4 混合服务器
- **UDP 时间同步**：往返时延 0.0~1.0 毫秒，平均时钟偏差 +0.000 秒 ✔
- **TCP 文件上传**：上传 250000 字节的文件，进度条按 26%/52%/78%/100% 打印，
  服务端算出的 MD5 与本地 **一致**，提示“上传成功，文件完整” ✔

### 选做：聊天室（两个客户端同时在线，6 项全通过）
真开两个客户端进程（张三、李四）同时在线：
- 李四收到 `张三: 大家好，我是张三`；张三收到 `李四: 张三你好，我是李四` ✔
- 张三看到 `系统：李四 加入了聊天室`；李四看到 `系统：张三 离开了聊天室` ✔
- 张三执行 `/list` 返回 `当前在线 2 人：张三（…）、李四（…）` ✔

## 调试中实际踩到的坑（值得记一笔）

1. **`b'…中文…'` 是语法错误**：写 1.4 的 UDP 部分时，我把中文提示写成了
   `sock.sendto(b'ERR|请发送 TIME…'.decode('utf-8'), …)`，结果整个文件
   `SyntaxError: bytes can only contain ASCII literal characters` —— 服务器根本没启动起来，
   客户端还以为是“服务器没开”。
   正确写法是 `'中文'.encode('utf-8')`：**bytes 字面量里只能放 ASCII，中文要先写成 str 再 encode**。
2. **多台服务器一起开时端口要错开**：1.1 用 8000（实验指定）、1.3 用 8001（实验指定），
   1.2 用了 8002、1.4 的 TCP/UDP 用了 8003/8004、聊天室用 8005，
   这样五个程序可以同时开着，方便对照，不会互相抢端口。
3. **服务端重启用 `allow_reuse_address = True`**：不然 Windows 上重启会报
   `Address already in use`（TIME_WAIT 还没释放）。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-socketserver-lab 完整源码包](/code/python-socketserver-lab/source.zip)

项目目录：

```text
socketserver编程实验/
├─ 01_echo_client.py
├─ 01_echo_server.py
├─ 02_threading_client.py
├─ 02_threading_server.py
├─ 03_udp_client.py
├─ 03_udp_server.py
├─ 04_hybrid_client.py
├─ 04_hybrid_server.py
├─ 05_chat_client.py
├─ 05_chat_server.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：01_echo_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验 1.1 基础 TCPServer 实现 —— 简单回显服务器

要求对照：
  (1) 创建一个基于 socketserver.TCPServer 的简单回显服务器
  (2) 客户端发送任何消息，服务器原样返回
  (3) 自定义请求处理类继承自 BaseRequestHandler，服务器监听本地 8000 端口

socketserver 的套路（记住这四步）：
    1) 写一个处理类，继承 BaseRequestHandler（或 StreamRequestHandler），重写 handle()；
    2) 用 (地址, 端口) 和处理类实例化 Server 类；
    3) 调 serve_forever() 开始服务；
    4) 结束时 server_close()。

注意：TCPServer 是“串行”的 —— serve_forever() 一次只处理一个连接，
      前一个客户端不断开，后面的客户端只能排队等着（可以开两个 01_echo_client.py 验证），
      所以它不能做并发服务器。并发版本见实验 1.2 的 ThreadingTCPServer。
"""

import socketserver

HOST = '0.0.0.0'      # 0.0.0.0 表示监听本机所有网卡，同网段的机器都能连
PORT = 8000           # 实验要求的端口


class EchoHandler(socketserver.BaseRequestHandler):
    """自定义请求处理类：每来一个客户端连接，socketserver 就调用一次 handle()。"""

    def handle(self):
        # self.request       —— 与客户端通信的套接字（TCP 里就是 conn）
        # self.client_address —— 客户端的 (IP, 端口)
        print('[连接] 客户端 %s:%s 已连接' % self.client_address)
        while True:
            try:
                data = self.request.recv(1024)      # 收数据
            except ConnectionResetError as e:
                # 客户端直接关窗口/被强杀会走这里，服务端不能因此崩溃
                print('[异常] 客户端 %s 非正常断开：%s' % (self.client_address, e))
                break

            if not data:                            # 空字节串 = 客户端正常关闭了连接
                break

            print('[收到] %s:%s 发来 %d 字节：%s'
                  % (self.client_address[0], self.client_address[1],
                     len(data), data.decode('utf-8')))
            # 原样发回去（回显）。用 sendall()：send() 不保证一次把数据全发完，sendall() 保证
            self.request.sendall(data)

        print('[断开] 客户端 %s:%s 已断开' % self.client_address)


class MyTCPServer(socketserver.TCPServer):
    """加两个类属性，让服务端重启时不用等端口释放。"""
    allow_reuse_address = True       # 允许地址复用，否则重启会报 Address already in use


if __name__ == '__main__':
    # with 语句会在退出时自动调用 server_close() 关闭监听套接字
    with MyTCPServer((HOST, PORT), EchoHandler) as server:
        print('回显服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：另开一个终端运行 python 01_echo_client.py')
        try:
            server.serve_forever()       # 一直循环，等客户端连接
        except KeyboardInterrupt:
            print('\n服务器退出')
```

</details>

<details>
<summary>打开完整代码：01_echo_client.py</summary>

```python
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
```

</details>

<details>
<summary>打开完整代码：02_threading_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验 1.2 多线程 TCPServer —— 同时处理多个客户端连接

要求对照：
  (1) 创建一个基于 socketserver.ThreadingTCPServer 的多线程服务器
  (2) 记录每个客户端的连接时间和 IP 地址
  (3) 服务器能够显示当前连接的客户端数量

和实验 1.1 的 TCPServer 相比，只有一个字的区别：
    TCPServer          —— 串行，一次只服务一个连接
    ThreadingTCPServer —— 每 accept 到一个连接就自动新建一个线程去跑 handle()，
                          所以多个客户端可以真正同时在在线、同时收发数据。

多线程带来的新问题：多个线程会同时修改“在线客户端表”这个共享数据，
    所以要用 threading.Lock 加锁保护（一次只让一个线程改），避免竞态条件。
"""

import socketserver
import threading
import time

HOST = '0.0.0.0'
PORT = 8002                     # 1.1 用了 8000，这里换个端口，方便同时开两个实验对比

lock = threading.Lock()         # 保护下面这几个共享变量
online = {}                     # 连接对象 -> {'ip':.., 'port':.., 'connect_time':.., 'time':时间戳}
total_conn = 0                  # 历史累计连接数


def now_str():
    return time.strftime('%Y-%m-%d %H:%M:%S')


class ClientHandler(socketserver.BaseRequestHandler):
    """每个客户端一个线程，这个类的方法会被多个线程同时执行。"""

    def handle(self):
        global total_conn

        # ---- 客户端上线：加锁修改共享数据 ----
        with lock:
            total_conn += 1
            online[self.request] = {
                'ip': self.client_address[0],
                'port': self.client_address[1],
                'connect_time': now_str(),
                'time': time.time(),
            }
            count = len(online)
            total = total_conn

        print('[连接] %s  客户端 %s:%s 已连接'
              % (now_str(), self.client_address[0], self.client_address[1]))
        print('       连接时间：%s' % online[self.request]['connect_time'])
        print('       当前在线客户端数量：%d（累计连接：%d）' % (count, total))
        print('       当前在线列表：%s' % [(v['ip'], v['port']) for v in online.values()])

        try:
            while True:
                data = self.request.recv(1024)
                if not data:
                    break
                msg = data.decode('utf-8')
                with lock:                                   # 读共享字典也要加锁，防止刚好有人正在改
                    info = online[self.request]
                dur = int(time.time() - info['time'])
                print('[消息] %s 发来：%s（在线 %d 秒）' % (info['ip'], msg, dur))
                # 回显：带上客户端地址和在线时长，方便看出是“哪一个客户端”在被服务
                reply = '[%s] %s 你已在线 %d 秒，你说的是：%s' % (now_str(), info['ip'], dur, msg)
                self.request.sendall(reply.encode('utf-8'))
        except ConnectionResetError as e:
            print('[异常] 客户端 %s:%s 非正常断开：%s'
                  % (self.client_address[0], self.client_address[1], e))
        finally:
            # ---- 客户端下线：同样加锁修改共享数据 ----
            with lock:
                info = online.pop(self.request, None)
                count = len(online)
            if info:
                print('[断开] %s  客户端 %s:%s 已断开（本次在线 %d 秒）'
                      % (now_str(), info['ip'], info['port'], int(time.time() - info['time'])))
            print('       当前在线客户端数量：%d' % count)


class MyThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True        # 主线程退出时，工作线程跟着退出，不然 Ctrl+C 后卡住不退出


if __name__ == '__main__':
    with MyThreadingTCPServer((HOST, PORT), ClientHandler) as server:
        print('多线程 TCPServer 已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：python 02_threading_client.py 127.0.0.1 8002 5   （模拟 5 个客户端同时连接）')
        print('提示：01_echo_client.py 也能连这个服务器')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n服务器退出（最终在线数：%d）' % len(online))
```

</details>

<details>
<summary>打开完整代码：02_threading_client.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验 1.2 的测试客户端 —— 模拟多个客户端“同时”连接多线程服务器

用法：
    python 02_threading_client.py [服务器IP] [端口] [并发连接数] [每个连接发几条消息]
默认：127.0.0.1 8002 5 3

每个连接跑在各自的线程里，几个线程一起连、一起发、一起收，
如果服务端是多线程的，就能看到所有客户端几乎同时被服务；
换成实验 1.1 的 TCPServer（串行）再跑这个脚本，就会发现后面的客户端要排队等待。
"""

import socket
import sys
import threading
import time

lock = threading.Lock()          # 让多个客户端线程打印日志时不互相打断


def log(msg):
    with lock:
        print(msg)


def one_client(host, port, idx, rounds):
    """模拟一个客户端：连接 -> 发几条消息 -> 关掉"""
    name = '客户端%d' % idx
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        log('%s 连接失败：服务器没启动' % name)
        return False

    try:
        for i in range(1, rounds + 1):
            msg = '%s 的第 %d 条消息' % (name, i)
            s.sendall(msg.encode('utf-8'))
            reply = s.recv(1024)
            if not reply:
                log('%s 服务器关闭了连接' % name)
                return False
            log('  %s 收到回显：%s' % (name, reply.decode('utf-8')))
            time.sleep(0.3)
        return True
    except OSError as e:
        log('%s 出错：%s' % (name, e))
        return False
    finally:
        s.close()
        log('%s 已断开' % name)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8002
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    print('模拟 %d 个客户端同时连接 %s:%d，每个发 %d 条消息' % (n, host, port, rounds))
    begin = time.time()
    threads = []
    for i in range(1, n + 1):
        t = threading.Thread(target=one_client, args=(host, port, i, rounds))
        threads.append(t)
        t.start()

    # 主线程 join 所有子线程，等它们全部结束再统计总耗时
    for t in threads:
        t.join()

    print('全部客户端结束，总耗时：%.2f 秒' % (time.time() - begin))
    print('（如果每个客户端各发 %d 条、每条间隔 0.3 秒，串行服务器需要 %d 倍以上时间）'
          % (rounds, n))


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：03_udp_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验 1.3 UDP 服务器 —— 返回消息长度和接收时间

要求对照：
  (1) 创建一个基于 socketserver.UDPServer 的简单服务器
  (2) 实现简单的数据包统计功能
  (3) 服务器监听本地 8001 端口

UDP 和 TCP 在 socketserver 里的区别：
    · TCP（StreamRequestHandler）：handle() 在一次连接里会被“持续调用”，
      我们要自己写 while 循环反复 recv；
    · UDP（DatagramRequestHandler/BaseRequestHandler）：没有连接，
      self.request 是一个 (数据报内容, 服务器套接字) 的二元组，
      一个数据报调用一次 handle()，所以 handle() 里不用写循环。
回复用 sock.sendto(数据, self.client_address)，因为 UDP 没有连接对象，要指定发给谁。
"""

import socketserver
import time

HOST = '0.0.0.0'
PORT = 8001

# 数据包统计：UDPServer 是单线程串行处理的，handle() 不会并发执行，所以这里不用加锁
stats = {}        # 客户端地址 (ip, port) -> {'packets': 包数, 'bytes': 字节数}
total = {'packets': 0, 'bytes': 0}


class UdpHandler(socketserver.BaseRequestHandler):
    """每收到一个 UDP 数据报，就被调用一次。"""

    def handle(self):
        # UDP 里 self.request 是 (收到的数据 bytes, 服务器端的套接字) 二元组
        data, sock = self.request
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = repr(data)                      # 不是 utf-8 就按十六进制原样显示

        recv_time = time.strftime('%Y-%m-%d %H:%M:%S')

        # ---- 数据包统计 ----
        st = stats.setdefault(self.client_address, {'packets': 0, 'bytes': 0})
        st['packets'] += 1
        st['bytes'] += len(data)
        total['packets'] += 1
        total['bytes'] += len(data)

        print('[收到] %s:%s 的第 %d 个数据包，%d 字节，内容：%s'
              % (self.client_address[0], self.client_address[1],
                 st['packets'], len(data), text))
        print('       统计：本客户端共 %d 包/%d 字节；服务器共 %d 包/%d 字节，来自 %d 个客户端'
              % (st['packets'], st['bytes'], total['packets'],
                 total['bytes'], len(stats)))

        # ---- 按要求回复：消息长度 + 接收时间 ----
        reply = ('收到消息长度：%d 字节，接收时间：%s（这是你的第 %d 个包）'
                 % (len(data), recv_time, st['packets']))
        sock.sendto(reply.encode('utf-8'), self.client_address)     # UDP 要用 sendto 并指定地址


class MyUDPServer(socketserver.UDPServer):
    allow_reuse_address = True


if __name__ == '__main__':
    with MyUDPServer((HOST, PORT), UdpHandler) as server:
        print('UDP 服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：python 03_udp_client.py 127.0.0.1 8001')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n服务器退出')
            print('最终统计：共收到 %d 个数据包，%d 字节，来自 %d 个客户端'
                  % (total['packets'], total['bytes'], len(stats)))
            for addr, st in stats.items():
                print('   %s:%s —— %d 包，%d 字节' % (addr[0], addr[1], st['packets'], st['bytes']))
```

</details>

<details>
<summary>打开完整代码：03_udp_client.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验 1.3 的测试客户端 —— 向 UDP 服务器发消息，打印服务器返回的长度与时间

用法：
    python 03_udp_client.py [服务器IP] [端口] [发送条数]
默认：127.0.0.1 8001 5，每条消息长度递减（用来观察服务器统计的字节数变化）。

UDP 客户端不需要 connect() 也能发（connect 只是绑定默认目标地址，方便用 send/recv），
这里仍然 connect 一下，这样就能直接用 s.send() 和 s.recv()。
"""

import socket
import sys
import time

HOST = '127.0.0.1'
PORT = 8001


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)      # SOCK_DGRAM = UDP
    s.settimeout(3)                                           # UDP 不可靠，设超时免得一直等
    s.connect((host, port))
    print('UDP 客户端，目标 %s:%d，连发 %d 个数据包' % (host, port, count))

    for i in range(1, count + 1):
        msg = 'UDP 测试消息第 %d 条%s' % (i, '啊' * i)         # 每条长度不一样
        t0 = time.time()
        s.send(msg.encode('utf-8'))
        try:
            reply = s.recv(1024)
        except socket.timeout:
            print('第 %d 条：超时，没收到回复（UDP 不保证送达）' % i)
            continue
        rtt = (time.time() - t0) * 1000
        print('第 %d 条：我发了 %d 字节，往返 %.1f 毫秒' % (i, len(msg.encode('utf-8')), rtt))
        print('        服务器回复：%s' % reply.decode('utf-8'))
        time.sleep(0.3)

    s.close()
    print('客户端退出')


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：04_hybrid_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验 1.4 混合服务器 —— 同时支持 TCP 和 UDP

要求对照：
  (1) 创建一个同时支持 TCP 和 UDP 的服务器
  (2) TCP 部分：实现简单的文件传输功能（接收客户端上传的文件并保存）
      UDP 部分：实现时间同步功能（响应客户端的时间请求）
  (3) 用多线程分别运行 TCPServer 和 UDPServer

为什么要用两个线程：serve_forever() 是“死循环”，一个线程里只能跑一个服务器，
    所以主线程跑 TCP 的 serve_forever()，另开一个线程跑 UDP 的 serve_forever()，
    两个服务器就在不同端口上同时工作了。

TCP 上传文件的协议（自己定的，用长度前缀解决粘包）：
    客户端 → 服务端：b'UPLD' + 4字节文件名长度(大端) + 文件名(UTF-8)
                     + 8字节文件大小(大端) + 文件内容
    服务端 → 客户端：b'OK' + 4字节MD5长度 + MD5文本(十六进制)     上传成功
                     b'ER' + 4字节原因长度 + 原因文本            上传失败
先发“文件名长度”再发文件名、先发“文件大小”再发内容，接收方就知道该收多少字节，
既不会把两次发送粘在一起，也不会把一条消息读了一半。

UDP 时间同步的协议：
    客户端 → 服务端：b'TIME|<客户端本地时间字符串>'
    服务端 → 客户端：b'TIME|<服务器时间字符串>|<服务器unix时间戳>'
    客户端用 t0(发送前)、t3(收到后) 算出往返时延和时钟偏差，完成“校时”。
"""

import hashlib
import os
import socketserver
import struct
import threading
import time

TCP_HOST, TCP_PORT = '0.0.0.0', 8003
UDP_HOST, UDP_PORT = '0.0.0.0', 8004

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
MAX_FILE = 512 * 1024 * 1024        # 最大 512MB，防止乱传把磁盘写满

log_lock = threading.Lock()         # 两个服务器在不同线程里打印日志，加锁免得输出交错


def log(msg):
    with log_lock:
        print(msg, flush=True)


def time_str(ts=None):
    """把时间戳格式化成 '2026-10-18 10:20:30.123'"""
    ts = time.time() if ts is None else ts
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)) + '.%03d' % int((ts % 1) * 1000)


def recv_exact(sock, n):
    """收满 n 个字节。TCP 是字节流，一次 recv 可能只收到一部分，所以要循环收。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None              # 对方关闭了连接
        buf += part
    return buf


# ====================== TCP 部分：文件上传 ======================
class UploadHandler(socketserver.BaseRequestHandler):
    """TCP 处理类：收一个文件，保存到 uploads 目录。"""

    def handle(self):
        sock = self.request
        addr = '%s:%s' % self.client_address
        log('[TCP] %s 已连接' % addr)
        try:
            head = recv_exact(sock, 4)
            if head is None:
                return
            if head != b'UPLD':                          # 校验“魔数”，确认发的确实是上传请求
                log('[TCP] %s 发的不是上传请求，断开' % addr)
                return

            name_len_b = recv_exact(sock, 4)
            name_len = struct.unpack('!I', name_len_b)[0]
            if name_len > 255:
                return
            name = recv_exact(sock, name_len).decode('utf-8')
            size = struct.unpack('!Q', recv_exact(sock, 8))[0]

            # 只管文件名，去掉路径部分，防止客户端用 ../../ 写到别的目录（目录穿越）
            safe_name = os.path.basename(name.replace('\\', '/'))
            if not safe_name or size > MAX_FILE:
                reply = b'ER' + struct.pack('!I', 12) + '文件名或大小不合法'.encode('utf-8')
                sock.sendall(reply)
                return

            save_path = os.path.join(SAVE_DIR, safe_name)
            log('[TCP] %s 要上传 %s（%d 字节），开始接收……' % (addr, safe_name, size))

            # 按大小收文件，一边收一边算 MD5
            md5 = hashlib.md5()
            got = 0
            with open(save_path, 'wb') as f:
                while got < size:
                    chunk = sock.recv(min(64 * 1024, size - got))
                    if not chunk:
                        log('[TCP] %s 上传中途断开，已收到 %d/%d 字节' % (addr, got, size))
                        return
                    f.write(chunk)
                    md5.update(chunk)
                    got += len(chunk)

            digest = md5.hexdigest()
            log('[TCP] %s 上传完成：%s，%d 字节，MD5=%s' % (addr, safe_name, got, digest))
            # 告诉客户端“收到了、存好了、这是校验值”，客户端可以拿去比对
            sock.sendall(b'OK' + struct.pack('!I', len(digest)) + digest.encode('utf-8'))

        except (ConnectionResetError, ConnectionAbortedError) as e:
            log('[TCP] %s 异常断开：%s' % (addr, e))
        except OSError as e:
            log('[TCP] %s 出错：%s' % (addr, e))
        finally:
            log('[TCP] %s 的连接已关闭' % addr)


# ====================== UDP 部分：时间同步 ======================
class TimeHandler(socketserver.BaseRequestHandler):
    """UDP 处理类：收到时间请求就回服务器时间。"""

    def handle(self):
        data, sock = self.request                     # UDP 的 self.request 是 (数据, 套接字)
        text = data.decode('utf-8', 'ignore')
        client_addr = '%s:%s' % self.client_address

        if not text.startswith('TIME'):
            # 注意：中文要写成 str 再 encode('utf-8')，不能直接写 b'…中文…'，
            # bytes 字面量里只能放 ASCII 字符，否则整个文件语法错误
            hint = 'ERR|请发送 TIME|<你的时间> 这样的请求'
            sock.sendto(hint.encode('utf-8'), self.client_address)
            return

        client_time = text.split('|', 1)[1] if '|' in text else '（未提供）'
        now = time.time()
        log('[UDP] 收到 %s 的时间请求（它说现在 %s），回复服务器时间 %s'
            % (client_addr, client_time, time_str(now)))
        reply = 'TIME|%s|%.6f' % (time_str(now), now)
        sock.sendto(reply.encode('utf-8'), self.client_address)


# ====================== 启动：两个服务器各跑一个线程 ======================
class MyTCPServer(socketserver.ThreadingTCPServer):
    """文件上传可能有多个客户端同时传，所以 TCP 这边用多线程版本。"""
    allow_reuse_address = True
    daemon_threads = True


class MyUDPServer(socketserver.UDPServer):
    allow_reuse_address = True


def run_udp():
    with MyUDPServer((UDP_HOST, UDP_PORT), TimeHandler) as server:
        log('UDP 时间同步服务器已启动，监听 %s:%d' % (UDP_HOST, UDP_PORT))
        server.serve_forever()


def run_tcp():
    with MyTCPServer((TCP_HOST, TCP_PORT), UploadHandler) as server:
        log('TCP 文件上传服务器已启动，监听 %s:%d，文件保存到：%s'
            % (TCP_HOST, TCP_PORT, SAVE_DIR))
        server.serve_forever()


if __name__ == '__main__':
    os.makedirs(SAVE_DIR, exist_ok=True)

    # 用多线程分别运行 TCPServer 和 UDPServer：UDP 跑在子线程，TCP 跑在主线程
    udp_thread = threading.Thread(target=run_udp, daemon=True)
    udp_thread.start()

    print('测试：')
    print('  python 04_hybrid_client.py time                 # UDP 部分：时间同步')
    print('  python 04_hybrid_client.py upload 文件名         # TCP 部分：上传文件')
    try:
        run_tcp()
    except KeyboardInterrupt:
        print('\n混合服务器退出')
```

</details>

<details>
<summary>打开完整代码：04_hybrid_client.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验 1.4 的测试客户端 —— 一个脚本两个功能

用法：
    python 04_hybrid_client.py time                          # UDP：向服务器校时
    python 04_hybrid_client.py upload <文件路径>              # TCP：把文件上传到服务器
    python 04_hybrid_client.py                              # 不加参数：两个都测一遍

可选的第 3、4 个参数是服务器 IP 和端口：
    python 04_hybrid_client.py time 192.168.1.10 8004
    python 04_hybrid_client.py upload a.zip 192.168.1.10 8003
"""

import hashlib
import os
import socket
import struct
import sys
import time

SERVER = '127.0.0.1'
TCP_PORT = 8003
UDP_PORT = 8004


def time_str(ts=None):
    ts = time.time() if ts is None else ts
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)) + '.%03d' % int((ts % 1) * 1000)


def recv_exact(sock, n):
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


# ---------------- UDP：时间同步 ----------------
def sync_time(host=SERVER, port=UDP_PORT, times=3):
    """向服务器发几次时间请求，算出往返时延和本机与服务器的时钟偏差。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    print('=== UDP 时间同步：%s:%d ===' % (host, port))
    offsets = []
    try:
        for i in range(1, times + 1):
            t0 = time.time()                                   # t0：本机发请求的时刻
            s.sendto(('TIME|%s' % time_str(t0)).encode('utf-8'), (host, port))
            try:
                data, _ = s.recvfrom(1024)
            except socket.timeout:
                print('第 %d 次：超时，服务器没响应' % i)
                continue
            t3 = time.time()                                   # t3：本机收到响应的时刻

            parts = data.decode('utf-8').split('|')
            if len(parts) != 3 or parts[0] != 'TIME':
                print('第 %d 次：返回的内容看不懂：%s' % (i, data))
                continue

            server_ts = float(parts[2])
            rtt = (t3 - t0) * 1000
            # 假设来回时延差不多，服务器时间对应的本机时刻就是 (t0+t3)/2，
            # 两者之差就是本机表快/慢了多久
            offset = server_ts - (t0 + t3) / 2
            offsets.append(offset)
            print('第 %d 次：服务器时间 %s' % (i, parts[1]))
            print('        往返时延 %.1f 毫秒，时钟偏差 %+.3f 秒（正数=本机慢，负数=本机快）'
                  % (rtt, offset))
            time.sleep(0.3)
    finally:
        s.close()

    if offsets:
        avg = sum(offsets) / len(offsets)
        print('平均时钟偏差 %+.3f 秒 —— 把本机时钟加上这个值就和服务器同步了' % avg)
    print()


# ---------------- TCP：文件上传 ----------------
def upload(file_path, host=SERVER, port=TCP_PORT):
    if not os.path.isfile(file_path):
        print('文件不存在：%s' % file_path)
        return False
    name = os.path.basename(file_path)
    size = os.path.getsize(file_path)

    # 先算好本地文件的 MD5，一会儿和服务器返回的比对，验证上传的文件没坏
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(64 * 1024)
            if not chunk:
                break
            md5.update(chunk)
    local_md5 = md5.hexdigest()

    print('=== TCP 文件上传：%s:%d ===' % (host, port))
    print('本地文件：%s（%d 字节），本地 MD5=%s' % (name, size, local_md5))

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        print('连接失败：请先运行 04_hybrid_server.py')
        return False

    try:
        name_b = name.encode('utf-8')
        # 按照协议拼头部：魔数 + 文件名长度 + 文件名 + 文件大小
        head = b'UPLD' + struct.pack('!I', len(name_b)) + name_b + struct.pack('!Q', size)
        s.sendall(head)

        sent = 0
        t0 = time.time()
        next_report = 25                       # 每过一个 25% 打印一次进度
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                s.sendall(chunk)               # sendall 保证这一段全部发出去
                sent += len(chunk)
                pct = int(sent * 100 / size) if size else 100
                if pct >= next_report:
                    print('上传进度：%d%%（%d/%d 字节）' % (pct, sent, size))
                    next_report += 25
        cost = time.time() - t0
        print('发送完成：%d 字节，用时 %.3f 秒（%.1f KB/s）'
              % (sent, cost, sent / 1024 / (cost or 1e-6)))

        # 收服务器的回复：'OK'+长度+MD5 或 'ER'+长度+原因
        resp = recv_exact(s, 2)
        if resp is None:
            print('服务器没有回复就断开了')
            return False
        msg_len = struct.unpack('!I', recv_exact(s, 4))[0]
        msg = recv_exact(s, msg_len).decode('utf-8')

        if resp == b'OK':
            print('服务器收到的 MD5=%s' % msg)
            if msg == local_md5:
                print('校验结果：一致 ✔ 上传成功，文件完整')
                return True
            print('校验结果：不一致 ✘ 文件可能在传输中损坏了')
            return False
        else:
            print('服务器拒绝：%s' % msg)
            return False
    except OSError as e:
        print('上传出错：%s' % e)
        return False
    finally:
        s.close()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # 不给参数就两个功能都演示一遍
        host = SERVER
        sync_time(host, UDP_PORT)
        demo = os.path.join(os.path.dirname(os.path.abspath(__file__)), '04_hybrid_client.py')
        upload(demo, host, TCP_PORT)
    elif sys.argv[1] == 'time':
        host = sys.argv[2] if len(sys.argv) > 2 else SERVER
        port = int(sys.argv[3]) if len(sys.argv) > 3 else UDP_PORT
        sync_time(host, port)
    elif sys.argv[1] == 'upload':
        if len(sys.argv) < 3:
            print('用法：python 04_hybrid_client.py upload <文件路径> [服务器IP] [端口]')
            sys.exit(1)
        path = sys.argv[2]
        host = sys.argv[3] if len(sys.argv) > 3 else SERVER
        port = int(sys.argv[4]) if len(sys.argv) > 4 else TCP_PORT
        upload(path, host, port)
    else:
        print('不认识的功能：%s' % sys.argv[1])
        print('用法：python 04_hybrid_client.py [time|upload <文件>]')
```

</details>

<details>
<summary>打开完整代码：05_chat_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
思考与扩展（选做）—— 简单聊天室服务器，支持多个客户端同时聊天

和 GUI 版聊天室（课本 5-9s）的区别：
  · 用“按行读取”的方式解决粘包问题 —— 每条消息都以 \\n 结尾，
    服务端用 self.rfile.readline() 一次读一行，天然不会把两条消息粘在一起；
  · 支持昵称、系统提示（谁进来了/谁走了）、/list 查看在线名单、/quit 退出；
  · 客户端是控制台版，不依赖图形界面，方便在实验课上快速验证。

自定义的简单文本协议（每条消息一行，以 \\n 结束）：
    客户端发的第一行：昵称
    之后发的行：聊天内容；以 / 开头的行是命令：/list 看在线名单，/quit 退出
    服务端发的行：直接显示给用户看的文本（聊天内容形如 '张三: 你好'）
"""

import socketserver
import threading
import time

HOST = '0.0.0.0'
PORT = 8005

lock = threading.Lock()          # 保护 online 这个共享字典（多线程服务器必须加锁）
online = {}                      # 连接对象 -> {'name': 昵称, 'addr': 地址, 'time': 上线时间}


def now_str():
    return time.strftime('%H:%M:%S')


def broadcast(text, exclude=None):
    """把一行文本发给所有在线客户端（exclude 用于“不发给某人自己”）。"""
    line = (text + '\r\n').encode('utf-8')
    # 先把字典复制一份再遍历，避免遍历过程中别的线程往字典里加人/删人
    with lock:
        items = list(online.items())
    for conn, info in items:
        if conn is exclude:
            continue
        try:
            conn.sendall(line)
        except OSError:
            # 这个人已经断了，交给它自己的线程去清理，这里不动它
            pass


class ChatHandler(socketserver.StreamRequestHandler):
    def handle(self):
        conn = self.request
        addr = '%s:%s' % self.client_address
        name = None
        try:
            # 第一行是昵称；self.rfile 是 socketserver 帮我们包好的文件对象，
            # 用 readline() 可以一次读一行（读到 \\n 为止），不怕粘包
            line = self.rfile.readline(1024)
            if not line:
                return
            name = line.decode('utf-8').strip() or addr
            with lock:
                online[conn] = {'name': name, 'addr': addr, 'time': time.time()}
                count = len(online)
            print('[上线] %s（%s），当前在线 %d 人' % (name, addr, count))
            conn.sendall(('欢迎 %s 加入聊天室！当前在线 %d 人\r\n'
                          % (name, count)).encode('utf-8'))
            conn.sendall('输入 /list 看在线名单，输入 /quit 退出，其它内容直接聊天\r\n'.encode('utf-8'))
            broadcast('系统：%s 加入了聊天室' % name, exclude=conn)

            # 之后每来一行就是一条聊天内容
            while True:
                line = self.rfile.readline(4096)
                if not line:
                    break                                   # 客户端关闭了连接
                msg = line.decode('utf-8', 'ignore').strip()
                if not msg:
                    continue

                if msg == '/quit':                          # 主动退出
                    conn.sendall('再见了！\r\n'.encode('utf-8'))
                    break
                if msg == '/list':                          # 只看在线名单，只回给请求的人
                    with lock:
                        names = ['%s（%s）' % (v['name'], v['addr']) for v in online.values()]
                    conn.sendall(('当前在线 %d 人：%s\r\n'
                                  % (len(names), '、'.join(names))).encode('utf-8'))
                    continue
                if msg.startswith('/'):
                    conn.sendall(('不认识的命令：%s\r\n' % msg).encode('utf-8'))
                    continue

                print('[%s] %s: %s' % (now_str(), name, msg))
                broadcast('%s: %s' % (name, msg))           # 广播给所有人（包括自己）
        except (ConnectionResetError, ConnectionAbortedError) as e:
            print('[异常] %s（%s）异常断开：%s' % (name or '?', addr, e))
        finally:
            if name:
                with lock:
                    online.pop(conn, None)
                    count = len(online)
                print('[下线] %s（%s），当前在线 %d 人' % (name, addr, count))
                broadcast('系统：%s 离开了聊天室' % name)


class MyChatServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    with MyChatServer((HOST, PORT), ChatHandler) as server:
        print('聊天室服务器已启动，监听 %s:%d（Ctrl+C 退出）' % (HOST, PORT))
        print('测试：多开几个终端运行 python 05_chat_client.py')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n聊天室服务器退出，共 %d 人还在线' % len(online))
```

</details>

<details>
<summary>打开完整代码：05_chat_client.py</summary>

```python
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
```

</details>
