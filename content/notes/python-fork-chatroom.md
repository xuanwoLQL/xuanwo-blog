---
title: "fork 理解与群聊聊天室"
slug: "python-fork-chatroom"
date: 2026-10-12T16:44:18+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "用 fork 派生多进程处理客户端，理解进程模型与群聊广播。"
summary: "用 fork 派生多进程处理客户端，理解进程模型与群聊广播。"
tags: ["Python", "fork", "多进程"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 8
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/fork理解和使用/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-fork-chatroom/workflow.svg" alt="监听进程接受连接，子进程处理单个客户端，结果再广播给其他连接。" loading="lazy">
  <figcaption>图 1 · fork 群聊进程模型。监听进程接受连接，子进程处理单个客户端，结果再广播给其他连接。</figcaption>
</figure>

## 需求
- 有人进入聊天室时，其他人会收到姓名，姓名不能重复；
- 有人进入时，其他人收到通知：`xxx进入了聊天室`；
- 一个人发消息，其他人收到 `xxx：xxxxxx`；
- 有人退出，其他人收到 `xxx退出了聊天室`；
- 扩展功能：服务器可以向所有用户发公告：`管理员消息：xxxxxx`。

## 文件
| 文件 | 说明 |
|---|---|
| `chat_server.py` / `chat_client.py` | 聊天室（线程版，Windows/Linux 都能跑，推荐） |
| `chat_server_fork.py` | 聊天室（fork 多进程版，**仅 Linux/Kali**；配同一个 `chat_client.py` 使用） |
| `chatroom_protocol.py` | 服务端/客户端共用的“长度前缀 + JSON”协议，用来解决粘包 |
| `fork_demo.py` | 对照老师截图，演示 `os.fork()` 的返回值、`wait` 回收、父子变量独立 |

## 运行
先在“服务端窗口”运行服务器，再在多个“客户端窗口”运行客户端：

```bash
# 线程版（Windows / Linux 都可以）
python chat_server.py 9000
python chat_client.py 127.0.0.1 9000     # 多开几个，分别输入不同昵称

# fork 多进程版（Kali）
python3 chat_server_fork.py 9000
python3 chat_client.py 127.0.0.1 9000

# 理解 fork
python3 fork_demo.py
```

客户端操作：输入昵称进入 → 回车发消息 → 输入 `quit` 退出。
服务端控制台敲一行字回车 = 以管理员身份给所有人发公告。

## 关于 fork
`os.fork()` 只有 Linux/macOS 有，Windows 没有，所以 Windows 上请用线程版。
fork 版里父进程负责 accept 和全部网络收发，每收到一条消息 fork 一个子进程去判断
（登录判重名 / 聊天转发 / 退出通知），子进程把结论通过管道写回父进程，父进程再广播。
这样避免了“父子进程都持有同一个套接字、谁先 close 谁就破坏对方 fd”的坑。

## 自测结果
- Windows（线程版）：登录、重名被拒、进入通知、聊天转发、管理员公告、退出通知，全部通过。
- Kali 22（fork 版）：进入通知、重名被拒、聊天转发、退出通知，9 项断言全部通过；`fork_demo.py` 正常输出两遍 `fork test over`。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-fork-chatroom 完整源码包](/code/python-fork-chatroom/source.zip)

项目目录：

```text
fork理解和使用/
├─ chat_client.py
├─ chat_server.py
├─ chat_server_fork.py
├─ chatroom_protocol.py
├─ fork_demo.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：fork_demo.py</summary>

```python
# -*- coding: utf-8 -*-
"""
os.fork 理解与使用（对照老师给的截图）

os.fork() 只在 Linux / macOS 等类 Unix 系统可用，Windows 没有这个函数。
它“调用一次，返回两次”：
  - 父进程里返回子进程的 pid（大于 0）
  - 子进程里返回 0
  - 失败返回负数
父进程和子进程各自从 fork 之后继续往下执行。

两个容易踩的坑（下面代码都处理了）：
  1. 子进程如果不 os._exit()，会继续把父进程后面的代码再跑一遍；
  2. fork 会把标准输出缓冲区复制一份，父子各打一遍，所以要及时 flush。

用法（在 Kali / Linux 里跑）： python3 fork_demo.py
"""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)   # 每行立刻写出，避免 fork 复制缓冲区导致重复


def demo_basic():
    """截图 1：根据 fork 的返回值区分父子进程。"""
    print('--- demo 1: 基本 fork ---', flush=True)
    pid = os.fork()
    if pid < 0:
        print('failed', flush=True)
    elif pid == 0:
        # 子进程
        print('new（我是子进程，pid=%d，父进程 pid=%d）' % (os.getpid(), os.getppid()), flush=True)
        print('fork test over（子进程也打印这一行）', flush=True)
        os._exit(0)
    else:
        # 父进程
        print('old（我是父进程，我的子进程 pid=%d）' % pid, flush=True)
        print('fork test over（父进程也打印这一行）', flush=True)
        os.waitpid(pid, 0)      # 回收子进程，避免留下僵尸进程给后面的 demo 误收


def demo_wait():
    """截图 2：父进程 wait 回收子进程，检查退出状态。"""
    print('--- demo 2: fork + wait ---', flush=True)
    pid = os.fork()
    if pid < 0:
        print('create process failed', flush=True)
    elif pid == 0:
        print('child pid:%d，get parent pid:%d' % (os.getpid(), os.getppid()), flush=True)
        os._exit(2)             # 子进程用退出码 2 结束
    else:
        child_pid, status = os.wait()      # 阻塞等待子进程结束
        print('wait 返回：子进程 pid=%d，status=%d，退出码=%d'
              % (child_pid, status, os.waitstatus_to_exitcode(status)), flush=True)


def demo_shared():
    """说明 fork 之后父子进程的变量是各自独立的拷贝（写时复制）。"""
    print('--- demo 3: 父子进程变量互相独立 ---', flush=True)
    value = 100
    pid = os.fork()
    if pid == 0:
        value += 1
        print('子进程里 value = %d（改的是自己的副本）' % value, flush=True)
        os._exit(0)
    else:
        os.wait()               # 等子进程先打印
        print('父进程里 value = %d（不受子进程影响）' % value, flush=True)


if __name__ == '__main__':
    if not hasattr(os, 'fork'):
        print('当前系统（%s）没有 os.fork，请在 Kali / Linux 里运行本程序。' % sys.platform)
        sys.exit(0)
    demo_basic()
    time.sleep(0.1)
    demo_wait()
    demo_shared()
```

</details>

<details>
<summary>打开完整代码：chatroom_protocol.py</summary>

```python
# -*- coding: utf-8 -*-
"""
聊天室公共协议模块（服务端和客户端共用）

作用：把“收发一条完整消息”的细节封装起来，避免 TCP 粘包。

自定义协议（跟课本 4-3c / 6 的“长度前缀 + 消息体”一致）：
    一条消息 = 4 字节长度(网络字节序, struct '!I') + 消息体(UTF-8 的 JSON)
收的时候先读 4 字节拿到长度，再按这个长度把消息体读满，
所以两条消息绝不会粘在一起，也不会只读一半。
"""

import struct
import json

HEAD_LEN = 4                 # 协议头固定 4 字节
MAX_LEN = 1024 * 1024        # 消息体最大 1MB，防止异常长度导致内存爆炸


def send_msg(sock, msg_dict):
    """发送一条消息，msg_dict 会被序列化成 JSON。"""
    body = json.dumps(msg_dict, ensure_ascii=False).encode('utf-8')
    head = struct.pack('!I', len(body))   # '!I' = 大端 4 字节无符号整数
    sock.sendall(head + body)


def recv_all(sock, n):
    """一次 recv 不一定收满 n 字节，循环收，收满为止；对端关闭时返回 None。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def recv_msg(sock):
    """接收一条完整的消息，返回字典；对端正常关闭时返回 None。"""
    head = recv_all(sock, HEAD_LEN)
    if head is None:
        return None
    length = struct.unpack('!I', head)[0]
    if length > MAX_LEN:
        return None
    body = recv_all(sock, length)
    if body is None:
        return None
    return json.loads(body.decode('utf-8'))
```

</details>

<details>
<summary>打开完整代码：chat_server.py</summary>

```python
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
```

</details>

<details>
<summary>打开完整代码：chat_server_fork.py</summary>

```python
# -*- coding: utf-8 -*-
"""
群聊聊天室 —— 服务端（fork 多进程版，Linux / Kali 专用）

对照老师给的示意图：父进程 accept 客户端请求，再交给子进程去处理“进入 / 退出 / 聊天”。

职责划分（关键点）：
  - 父进程：拥有监听套接字和所有客户端套接字，用 select 负责全部网络收发，并维护在线名单。
  - 子进程：只处理“刚收到的那一条消息”，根据这条消息 + 当前在线名单做判断，
            再把结论通过管道写回父进程，然后立刻退出。
  - 父进程：读子进程写回的结论，更新在线名单并广播。

为什么不让子进程长期持有客户端套接字？
  fork 之后，如果子进程关掉套接字，父进程那份 fd 就失效了（反之亦然），
  父进程再去广播就会失败——这是调试时踩到的真实坑（表现为“日志说已广播，客户端却收不到”）。
  所以让父进程独占套接字读写，子进程只做“无状态判断 + 写管道”，最稳。

Windows 上没有 os.fork，请用同目录的 chat_server.py（线程版，功能一样）。

用法（Kali）： python3 chat_server_fork.py [端口]     # 默认 9000
"""

import json
import os
import select
import socket
import struct
import sys

HOST = '0.0.0.0'
PORT = 9000
HEAD_LEN = 4
MAX_LEN = 1024 * 1024
HEAD = struct.Struct('!I')

clients = {}       # 昵称 -> 客户端套接字（仅父进程使用）
sockets = []       # 所有已连接套接字（父进程 select 监视）


# ---------------- 套接字协议：4 字节长度 + JSON ----------------
def recv_exact(conn, n):
    buf = b''
    while len(buf) < n:
        part = conn.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def recv_sock_msg(conn):
    head = recv_exact(conn, HEAD_LEN)
    if head is None:
        return None
    length = HEAD.unpack(head)[0]
    if length > MAX_LEN:
        return None
    body = recv_exact(conn, length)
    if body is None:
        return None
    return json.loads(body.decode('utf-8'))


def send_sock_msg(conn, obj):
    body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    conn.sendall(HEAD.pack(len(body)) + body)


# ---------------- 子进程 -> 父进程 的结果管道：4 字节长度 + JSON ----------------
def pipe_write(fd, obj):
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    os.write(fd, HEAD.pack(len(data)) + data)


def pipe_read_one(fd):
    buf = b''
    while len(buf) < HEAD_LEN:
        part = os.read(fd, HEAD_LEN - len(buf))
        if not part:
            return None
        buf += part
    length = HEAD.unpack(buf)[0]
    body = b''
    while len(body) < length:
        part = os.read(fd, length - len(body))
        if not part:
            break
        body += part
    return json.loads(body.decode('utf-8'))


def broadcast(msg, exclude=None):
    for name, conn in list(clients.items()):
        if name == exclude:
            continue
        try:
            send_sock_msg(conn, msg)
        except OSError:
            pass
    print('[服务端广播] %s' % msg.get('content', msg), flush=True)


def child_decide(conn, msg, cur_name, online_names):
    """子进程里执行：判断这条消息，必要时直接回 ack，然后把结论写进管道。"""
    mtype = msg.get('type')
    if cur_name is None:
        # 还没登录，只接受 login
        if mtype != 'login':
            pipe_write(_req_fd, {'type': 'ignore'})
            return
        name = str(msg.get('name', '')).strip()
        if not name:
            send_sock_msg(conn, {'type': 'login_ack', 'ok': False, 'reason': '昵称不能为空'})
            pipe_write(_req_fd, {'type': 'ignore'})
            return
        if name in online_names:
            send_sock_msg(conn, {'type': 'login_ack', 'ok': False, 'reason': '昵称已被占用'})
            pipe_write(_req_fd, {'type': 'ignore'})
            return
        send_sock_msg(conn, {'type': 'login_ack', 'ok': True, 'name': name})
        pipe_write(_req_fd, {'type': 'login', 'name': name})
        return
    # 已登录
    if mtype == 'quit':
        pipe_write(_req_fd, {'type': 'quit', 'name': cur_name})
        return
    if mtype == 'chat':
        pipe_write(_req_fd, {'type': 'chat', 'sender': cur_name,
                             'content': msg.get('content', '')})
        return
    pipe_write(_req_fd, {'type': 'ignore'})


_req_fd = None       # 子进程里使用的管道写端（fork 前设置好）


def handle_conn_data(conn):
    """父进程收到某个客户端的一条消息：fork 子进程判断，再读回结论并更新名单。"""
    global _req_fd
    msg = recv_sock_msg(conn)
    if msg is None:
        # 连接断开 / 数据非法
        old = _name_of.pop(conn, None)
        if conn in sockets:
            sockets.remove(conn)
        if old:
            clients.pop(old, None)
            broadcast({'type': 'system', 'content': '%s退出了聊天室' % old}, old)
        try:
            conn.close()
        except OSError:
            pass
        return

    rr, rw = os.pipe()          # 子进程 -> 父进程 传递结论
    _req_fd = rw
    cur_name = _name_of.get(conn)
    online_names = list(clients.keys())
    pid = os.fork()
    if pid == 0:
        # ---- 子进程 ----
        os.close(rr)
        sk.close()
        try:
            child_decide(conn, msg, cur_name, online_names)
        finally:
            os.close(rw)
        os._exit(0)
    # ---- 父进程 ----
    os.close(rw)
    info = pipe_read_one(rr)
    os.close(rr)
    os.waitpid(pid, 0)
    if info is None:
        return
    t = info.get('type')
    if t == 'login':
        _name_of[conn] = info['name']
        clients[info['name']] = conn
        broadcast({'type': 'system', 'content': '%s进入了聊天室' % info['name']},
                  info['name'])
    elif t == 'chat':
        broadcast({'type': 'chat', 'sender': info['sender'], 'content': info['content']},
                  info['sender'])
    elif t == 'quit':
        _name_of[conn] = None
        clients.pop(info['name'], None)
        broadcast({'type': 'system', 'content': '%s退出了聊天室' % info['name']},
                  info['name'])


_name_of = {}      # 连接 -> 昵称


def main():
    global sk, _name_of
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sk.bind((HOST, port))
    sk.listen(100)
    print('聊天室服务端(fork版)已启动，监听 %s:%d，父进程 pid=%d' % (HOST, port, os.getpid()), flush=True)
    try:
        while True:
            ready, _, _ = select.select([sk] + sockets, [], [])
            for r in ready:
                if r is sk:
                    conn, addr = sk.accept()
                    sockets.append(conn)
                    _name_of[conn] = None
                    print('新连接 %s' % (addr,), flush=True)
                else:
                    handle_conn_data(r)
    except KeyboardInterrupt:
        print('\n父进程退出')
    finally:
        sk.close()


if __name__ == '__main__':
    if not hasattr(os, 'fork'):
        print('当前系统（%s）没有 os.fork，请用 chat_server.py（线程版），或在 Kali 里运行本文件。' % sys.platform)
        sys.exit(0)
    main()
```

</details>

<details>
<summary>打开完整代码：chat_client.py</summary>

```python
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
```

</details>
