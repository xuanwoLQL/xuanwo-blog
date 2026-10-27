---
title: "多进程文件下载"
slug: "python-multiprocess-download"
date: 2026-10-12T16:44:18+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "把文件分段交给多个进程下载，再合并校验。"
summary: "把文件分段交给多个进程下载，再合并校验。"
tags: ["Python", "多进程", "下载"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 5
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/多进程文件下载作业/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-multiprocess-download/workflow.svg" alt="服务端提供文件与偏移量，多个进程各自下载分片，最后按顺序合并。" loading="lazy">
  <figcaption>图 1 · 多进程分块下载。服务端提供文件与偏移量，多个进程各自下载分片，最后按顺序合并。</figcaption>
</figure>

## 需求
课本 5.2.1 实例（代码 5-2s）：服务端主进程 accept 客户端连接，
每来一个客户端就用 `multiprocessing.Process` 起一个子进程去发送文件，
从而同时给多个客户端提供文件下载服务。

## 文件
| 文件 | 说明 |
|---|---|
| `download_server.py` | 服务端（父进程 accept，子进程发文件） |
| `download_client.py` | 客户端（请求文件名、接收文件、保存到本地） |

## 运行
```bash
# 服务端：共享目录（要下载的文件放这里），端口默认 9100
python download_server.py [共享目录] [端口]

# 客户端
python download_client.py [服务器IP] [端口] [文件名] [保存名]
```
不带文件名运行客户端会进入循环，可以反复输入文件名下载。

## 实现要点
- 客户端发来“文件名”时用 4 字节长度前缀，服务端先收长度再收文件名，避免粘包。
- 文件存在时先回 `yes` + 8 字节文件大小，客户端按大小收满为止，保证收完整。
- 服务端只允许访问共享目录内的文件（`os.path.basename` 去掉路径），防止目录穿越。
- **注意**：Windows 下 `multiprocessing` 用 spawn 起子进程，子进程会重新导入模块，
  所以共享目录是当参数传给子进程的，不能依赖父进程后来改过的全局变量（这里是实际调试踩到的坑）。

## 自测结果
两个客户端并发下载同一个 20010 字节文件，内容都完全一致；请求不存在的文件时正确提示“没有该文件”。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-multiprocess-download 完整源码包](/code/python-multiprocess-download/source.zip)

项目目录：

```text
多进程文件下载作业/
├─ download_client.py
├─ download_server.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：download_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
课本 129 页实例 —— 多进程文件下载服务（服务端）

对应课本 5.2.1 代码 5-2s（process02s.py）：
  主进程只负责 accept 客户端连接，每来一个客户端就用
  multiprocessing.Process 起一个子进程去发送文件，
  这样子进程可以同时给多个客户端提供文件下载服务。

用法：
  python download_server.py [共享目录] [端口]
  共享目录默认是脚本所在目录，端口默认 9100。
  客户端请求的文件名，会到共享目录里去找。
"""

import os
import socket
import sys
from multiprocessing import Process

HOST = '0.0.0.0'
PORT = 9100
CHUNK = 1024 * 4
PREFIX = b'DOWNLOAD'

SHARE_DIR = os.path.dirname(os.path.abspath(__file__))


def recv_file_name(conn):
    """接收客户端发来的文件名（自解释的定长头部 + 文件名，避免粘包）。"""
    head = b''
    while len(head) < len(PREFIX) + 4:
        part = conn.recv(len(PREFIX) + 4 - len(head))
        if not part:
            return None
        head += part
    if head[:len(PREFIX)] != PREFIX:
        return None
    length = int.from_bytes(head[len(PREFIX):], 'big')
    name = b''
    while len(name) < length:
        part = conn.recv(length - len(name))
        if not part:
            return None
        name += part
    return name.decode('utf-8')


def send_all(conn, data):
    """把一段数据完整发出去（send 不保证一次全发完，循环发）。"""
    sent = 0
    while sent < len(data):
        sent += conn.send(data[sent:])


def sendfile(conn, share_dir):
    """子进程的处理函数：接收文件名，把文件发给客户端。

    注意：Windows 下 multiprocessing 用 spawn 方式创建子进程，
    子进程会重新导入本模块，拿不到父进程后来改过的全局变量 SHARE_DIR，
    所以这里必须把共享目录当参数传进来。
    """
    try:
        filename = recv_file_name(conn)
        if not filename:
            return
        print('我是子进程，我的 ID 是', os.getpid())
        print('客户端请求我的文件：', filename)

        # 只允许访问共享目录内的文件，去掉路径部分，防止目录穿越
        safe_name = os.path.basename(filename)
        path = os.path.join(share_dir, safe_name)

        if os.path.isfile(path):
            size = os.path.getsize(path)
            print('我有 %s，开始下载！' % safe_name)
            send_all(conn, b'yes')                       # 告诉客户端：文件存在
            send_all(conn, size.to_bytes(8, 'big'))      # 再发 8 字节文件大小
            with open(path, 'rb') as f:
                while True:
                    data = f.read(CHUNK)
                    if not data:
                        break
                    send_all(conn, data)
            print('%s 下载成功！' % safe_name)
        else:
            print('抱歉，我没有 %s！' % safe_name)
            send_all(conn, b'no')
    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        print('与客户端的连接中断：%s' % e)
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    global SHARE_DIR
    if len(sys.argv) > 1:
        SHARE_DIR = os.path.abspath(sys.argv[1])
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, port))
    s.listen(100)
    print('我是父进程，我的 ID 是', os.getpid())
    print('多进程文件下载服务端已启动，共享目录：%s' % SHARE_DIR)
    print('监听 %s:%d，等待客户端连接……' % (HOST, port))

    try:
        while True:
            conn, addr = s.accept()
            print('等待连接……收到来自 %s 的连接' % (addr,))
            # 课本做法：每来一个客户端，就创建一个子进程去处理
            p = Process(target=sendfile, args=(conn, SHARE_DIR))
            p.start()
            # 父进程不 join，立刻回去 accept 下一个客户端，实现并发
    except KeyboardInterrupt:
        print('\n服务端退出')
    finally:
        s.close()


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：download_client.py</summary>

```python
# -*- coding: utf-8 -*-
"""
课本 129 页实例 —— 多进程文件下载服务（客户端）

用法：
  python download_client.py [服务器IP] [端口] [要下载的文件名] [保存到本地叫什么]
  默认：127.0.0.1 9100，不写文件名时进入循环，可以反复输入文件名下载。

流程：connect -> 发文件名 -> 收 'yes'/'no' -> 收 8 字节大小 -> 按大小收文件
"""

import socket
import sys

PREFIX = b'DOWNLOAD'
CHUNK = 1024 * 4


def recv_all(sock, n):
    """收满 n 个字节，收不满就返回 None。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def request_file(host, port, filename, save_as):
    name_bytes = filename.encode('utf-8')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except ConnectionRefusedError:
        print('连接失败：服务端没有启动，请先运行 download_server.py')
        return False

    try:
        # 发送请求：定长头部 + 文件名
        sock.sendall(PREFIX + len(name_bytes).to_bytes(4, 'big') + name_bytes)
        # 先收服务端的应答：'yes' 有文件 / 'no' 没有
        answer = sock.recv(3)
        if answer != b'yes':
            print('下载失败：服务器上没有 %s' % filename)
            return False
        # 收 8 字节文件大小
        size_bytes = recv_all(sock, 8)
        if size_bytes is None:
            print('下载失败：连接中断')
            return False
        size = int.from_bytes(size_bytes, 'big')
        print('文件大小 %d 字节，开始下载……' % size)

        got = 0
        with open(save_as, 'wb') as f:
            while got < size:
                data = sock.recv(min(CHUNK, size - got))
                if not data:
                    break
                f.write(data)
                got += len(data)
        if got == size:
            print('%s 下载成功，已保存为 %s（%d 字节）' % (filename, save_as, got))
            return True
        print('下载不完整：只收到 %d / %d 字节' % (got, size))
        return False
    except OSError as e:
        print('与服务器的连接出错：%s' % e)
        return False
    finally:
        sock.close()


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9100
    if len(sys.argv) > 3:
        filename = sys.argv[3]
        save_as = sys.argv[4] if len(sys.argv) > 4 else filename
        request_file(host, port, filename, save_as)
        return
    print('多进程文件下载客户端，输入文件名回车下载，直接回车退出')
    while True:
        filename = input('要下载的文件名：').strip()
        if not filename:
            break
        request_file(host, port, filename, filename)
    print('客户端退出')


if __name__ == '__main__':
    main()
```

</details>
