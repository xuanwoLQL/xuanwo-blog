---
title: "基于 Socket 的 FTP 服务器"
slug: "python-ftp-server"
date: 2026-10-18T10:50:01+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "手写 FTP 协议、用户认证、目录浏览与文件传输，配套 tkinter 客户端。"
summary: "手写 FTP 协议、用户认证、目录浏览与文件传输，配套 tkinter 客户端。"
tags: ["Python", "FTP", "Socket"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 2
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/基于Socket编程的FTP服务器/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-ftp-server/workflow.svg" alt="客户端命令走控制连接，文件内容走独立数据连接，服务器最终读写共享目录。" loading="lazy">
  <figcaption>图 1 · FTP 控制面与数据面。客户端命令走控制连接，文件内容走独立数据连接，服务器最终读写共享目录。</figcaption>
</figure>

## 需求与实现对照

| 实验要求 | 在哪实现的 |
|---|---|
| 基于 socketserver 实现并发 TCP 服务器，可同时处理多个客户端 | `ftp_server.py` —— `socketserver.ThreadingTCPServer`，每个连接自动一个线程 |
| 用户账号的加密认证（哈希密码存储与验证） | `ftp_protocol.py` 的 `hash_password/verify_password`（盐 + PBKDF2-HMAC-SHA256，12 万次迭代），`make_users.py` 生成 `users.json` |
| 用户家目录隔离，只能访问自己的专属目录 | `ftp_server.py` 的 `safe_path()`：`normpath` 规范化后必须仍在家目录 `ftp_root/<用户名>` 内 |
| 完整支持文件上传 PUT、下载 GET、查看列表 LS | `ftp_server.py` 的 `do_ls/do_get/do_put` |
| 能处理客户端的正常与异常断开 | QUIT 正常退出；`ConnectionResetError/ConnectionAbortedError/BrokenPipeError` + `socket.timeout` + `finally` 统一清理 |
| 客户端用 Tkinter 做图形界面 | `ftp_client.py` |
| 界面含按钮、文本框、列表控件、进度条 | 连接/断开/刷新/上传/下载/返回上级 6 个按钮；IP/端口/用户名/密码 4 个文本框；`ttk.Treeview` 文件列表；`ttk.Progressbar` |
| 上传下载实时显示进度（百分比）和状态 | 进度条 + 状态标签 + 日志区，都在传完前每 0.1 秒刷新一次 |
| 保证文件传输完整性（哈希校验） | 下载：服务端先给 MD5，客户端边收边算、收完比对；上传：客户端先声明 MD5，服务端落盘后再算一遍比对 |

## 文件说明

| 文件 | 说明 |
|---|---|
| `ftp_protocol.py` | 公共协议模块：帧收发、MD5、口令哈希（服务端和客户端共用，保证两边协议一致） |
| `make_users.py` | 生成/管理账号文件 `users.json`（只存盐和哈希，不存明文口令） |
| `users.json` | 账号文件（由 `make_users.py` 生成） |
| `ftp_server.py` | 服务端 |
| `ftp_client.py` | 客户端（tkinter 图形界面） |
| `ftp_root/` | 数据根目录，每个用户一个子目录（首次登录自动创建） |

## 运行

```bash
# 第 1 步：生成账号（只需一次）
python make_users.py
#   → alice/alice123、bob/bob123、admin/admin@123

# 第 2 步：启动服务端（默认 0.0.0.0:2121）
python ftp_server.py
#   也可以指定：python ftp_server.py 0.0.0.0 2121 ftp_root

# 第 3 步：启动客户端
python ftp_client.py
```
客户端里填 IP `127.0.0.1`、端口 `2121`、用户名 `alice`、密码 `alice123`，点“连接”。

**界面操作**：
- 登录后自动列出家目录；双击目录进去，双击文件下载；“返回上级”回上一级。
- 选中文件点“下载选中文件(GET)”→ 选保存位置 → 进度条实时显示百分比/速度/剩余时间。
- 点“选择本地文件上传(PUT)”→ 选文件 → 上传；如果服务器上已有同名文件会先问你要不要覆盖。
- 日志区会记录每一步（登录握手耗时、传输速度、完整性校验结果）。
- 想验证多用户隔离：开两个客户端分别用 `alice` 和 `bob` 登录，互相看不到对方的文件。

## 应用层协议（`ftp_protocol.py`）

```
每一帧 = 1字节类型 + 8字节负载长度(大端) + 负载
   类型 b'J' —— JSON 控制消息（登录、列目录、命令应答）
   类型 b'F' —— 文件数据块（64KB 一块）
   类型 b'E' —— 传输结束标记
```

- **防粘包/分包**：先读固定 9 字节帧头拿到长度，再精确收满这么多字节（`recv_exact`），
  既不会把两帧粘在一起，也不会把一帧读一半。
- **控制命令**（都是 JSON）：`login` / `ls` / `get` / `put` / `quit`。

命令流程示例（下载）：
```
客户端 → {"cmd":"get","name":"a.bin"}
服务端 → {"ok":true,"size":12345,"md5":"…"}     ← 先告诉大小和 MD5
服务端 → [F]数据块 [F]数据块 … [E]               ← 分块传内容
客户端 → 边收边算 MD5，收完比对大小和 MD5
```

## 实现要点

### 服务端
- **并发**：`ThreadingTCPServer`，每个连接一个线程；`daemon_threads = True`。
- **加密认证**：`users.json` 里每个账号存 `salt` + `PBKDF2-HMAC-SHA256` 摘要（12 万次迭代），
  登录时算一遍再比；用 `secrets.compare_digest` 做定时安全比较，防时序攻击；
  用户名不存在时也走一遍哈希计算，避免用响应快慢探测用户名是否存在；
  连续错 3 次直接断开。
- **家目录隔离**：客户端给的都是**相对自己家目录**的路径；`safe_path()` 先拒绝绝对路径
  （`/etc/passwd`、`D:/...`），再 `normpath` 规范化，最后检查结果是否仍在家目录内，
  越界一律拒绝（`../`、`..\\`、`C:/Windows` 都试过，全部挡住）。
- **上传的原子性**：先写到 `xxx.part`，大小和 MD5 都校验通过后才 `os.replace()` 改名成正式文件，
  中途失败就删掉临时文件 —— 服务器上不会留下半截的坏文件。
- **协议流不错位**（调试中实际踩到的坑）：上传过程中如果服务端出错（比如目标目录不存在），
  **必须把客户端这一轮发来的数据全部收完再报错**，否则剩下的数据留在缓冲区里会被当成下一条命令，
  整个连接的数据流就错位了 —— `recv_file_body()` 就是为此把“收数据”和“判断对错”分开的。

### 客户端（GUI 的线程模型）
- 主线程只跑 tkinter；所有网络操作都在 worker 线程；worker 通过 `queue.Queue` 把
  “要显示什么”交给主线程，主线程用 `after(80ms)` 定时取出来更新控件 —— 这是 tkinter 的标准做法，
  **worker 线程绝对不能直接改控件**。
- 传输中禁止再发别的命令（`busy` 标志 + 按钮置灰），保证同一时刻只有一个线程用这条连接。
- 任务收尾顺序是“先刷新列表、再解除 busy”，反过来的话用户可能在刷新期间又点一次下载，
  两个线程同时用一个套接字就会串包。
- 下载同样先写 `.part` 临时文件，校验通过才改名，MD5 不对就删掉。

## 自测结果

### 服务端协议自测（25 项全通过）
| 测的东西 | 结果 |
|---|---|
| 错误口令 | 连错 3 次被拒，第 3 次后服务器主动断开 ✔ |
| 正确口令登录 | 成功，自动创建家目录并放一个 `欢迎.txt` ✔ |
| LS | 返回文件列表和大小/时间，路径显示为 `/` ✔ |
| PUT（MD5 正确） | 上传成功，服务端返回的 MD5 与本地一致 ✔ |
| PUT（故意给错 MD5） | 被拒绝：“MD5 校验失败（客户端说 000…，服务器算是 5eb6…）”，临时文件已删 ✔ |
| PUT 数据超过声明大小 | 拒绝并丢弃，且不影响后续命令 ✔ |
| GET | 200KB 文件（跨多个 64KB 块）下载回来与上传内容**字节一致** ✔ |
| 目录穿越 5 种写法 | `../bob/欢迎.txt`、`C:/Windows/win.ini`、`../../evil.txt`、绝对路径、`LS ../..` 全部被拒 ✔ |
| 覆盖保护 | 同名文件默认不给覆盖，带 `overwrite` 才能覆盖 ✔ |
| 用户隔离 | bob 登录后看不到 alice 的任何文件 ✔ |
| 异常断开 | 直接关 socket 不发 QUIT，服务端记录“异常断开”后正常回收线程，无异常堆栈 ✔ |
| 并发 | 3 个客户端同时下载同一文件，内容都正确 ✔ |

服务端日志全程 **没有任何未处理的异常（Traceback）**，164 行日志里记录了每次登录、上传、下载、
断开和每一次被拒绝的越权访问。

### 图形界面自测（21 项全通过）
用脚本直接驱动界面的方法（绕过文件选择框）：连接登录 → 列目录 → 错误密码重试 →
下载并比对内容一致（71 字节）→ 进子目录/返回上级 → 上传 300KB 并比对服务端 MD5 一致 →
列表自动刷新 → 断开 → 关窗。全部通过，进度条能正确走到 100%。

> 过程中通过测试发现并修掉了一个真实 bug：任务结束时把进度条清零，
> 导致用户看不到“100% 完成”的状态，改成“新任务开始时才清零”。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-ftp-server 完整源码包](/code/python-ftp-server/source.zip)

项目目录：

```text
基于Socket编程的FTP服务器/
├─ ftp_client.py
├─ ftp_protocol.py
├─ ftp_server.py
├─ make_users.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：ftp_protocol.py</summary>

```python
# -*- coding: utf-8 -*-
"""
FTP 作业公共协议模块 —— 服务端和客户端都用它，保证两边的协议完全一致

自定义应用层协议（解决 TCP 粘包/分包）：
    每一帧 = 1字节类型 + 8字节负载长度(大端) + 负载
      类型 b'J' —— JSON 控制消息（登录、列目录、各种命令应答），负载是 UTF-8 的 JSON
      类型 b'F' —— 文件数据块，负载是文件的一段二进制内容（默认 64KB 一块）
      类型 b'E' —— 传输结束标记，负载为空

为什么这样设计：
  · 每帧前面都有“长度”，接收方先读固定 9 字节的帧头，知道这帧有多少字节，
    再精确地收满这么多字节 —— 所以既不会把两帧粘在一起（粘包），
    也不会把一帧只读了一半（分包）。
  · 控制信息全部用 JSON，以后要加新命令只要加一个 "cmd" 名字，不用改协议本身。

密码存储用的也是这个模块里的函数：盐 + PBKDF2-HMAC-SHA256 迭代哈希，
服务器上只存哈希，不存明文密码。
"""

import hashlib
import json
import os
import secrets
import struct

# ---------------- 协议常量 ----------------
TYPE_JSON = b'J'          # 控制消息
TYPE_FILE = b'F'          # 文件数据块
TYPE_END = b'E'           # 传输结束

HEAD = struct.Struct('!cQ')       # !c = 1 字节字符，!Q = 8 字节无符号大端整数
HEAD_LEN = HEAD.size              # = 9
CHUNK = 64 * 1024                 # 文件分块大小 64KB
MAX_FRAME = 16 * 1024 * 1024      # 单帧最大 16MB，防止对方发个乱码长度把内存吃爆

# ---------------- 口令哈希参数 ----------------
PBKDF2_ITERATIONS = 120000
SALT_BYTES = 16


# ==================== 收发帧 ====================
def send_frame(sock, type_byte, payload=b''):
    """发一帧：帧头（类型 + 长度）+ 负载。用 sendall 保证全部写完。"""
    sock.sendall(HEAD.pack(type_byte, len(payload)) + payload)


def send_json(sock, obj):
    """发一条 JSON 控制消息。ensure_ascii=False 让中文按 UTF-8 发，节省字节。"""
    payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    send_frame(sock, TYPE_JSON, payload)


def send_chunk(sock, data):
    """发一块文件内容。"""
    send_frame(sock, TYPE_FILE, data)


def send_end(sock):
    """发传输结束标记。"""
    send_frame(sock, TYPE_END, b'')


def recv_exact(sock, n):
    """收满 n 个字节；对方提前关闭连接则返回 None。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def recv_frame(sock):
    """收一帧，返回 (类型, 负载)；对方关闭连接时返回 (None, None)。"""
    head = recv_exact(sock, HEAD_LEN)
    if head is None:
        return None, None
    type_byte, length = HEAD.unpack(head)
    if length > MAX_FRAME:
        raise ValueError('收到不合理的帧长度：%d 字节' % length)
    payload = b''
    if length:
        payload = recv_exact(sock, length)
        if payload is None:
            return None, None
    return type_byte, payload


def recv_json(sock):
    """收一条 JSON 控制消息，返回字典；连接结束返回 None。"""
    type_byte, payload = recv_frame(sock)
    if type_byte is None:
        return None
    if type_byte != TYPE_JSON:
        raise ValueError('期待 JSON 控制帧，收到的却是 %r' % type_byte)
    return json.loads(payload.decode('utf-8'))


# ==================== 文件工具 ====================
def md5_file(path, progress=None):
    """分块算文件的 MD5（大文件也不会占满内存）。"""
    md5 = hashlib.md5()
    total = os.path.getsize(path)
    done = 0
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            md5.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    return md5.hexdigest()


def human_size(n):
    """把字节数格式化成人看得懂的形式，例如 1536 -> '1.5 KB'。"""
    if n < 1024:
        return '%d B' % n
    value = float(n)
    for unit in ('KB', 'MB', 'GB', 'TB'):
        value /= 1024.0
        if value < 1024 or unit == 'TB':
            return '%.1f %s' % (value, unit)


# ==================== 口令哈希 ====================
def new_salt():
    """生成随机盐（每个用户一个，防止彩虹表）。"""
    return secrets.token_hex(SALT_BYTES)


def hash_password(password, salt_hex):
    """用 盐 + PBKDF2-HMAC-SHA256 迭代哈希 算出口令摘要，返回十六进制字符串。"""
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                             bytes.fromhex(salt_hex), PBKDF2_ITERATIONS)
    return dk.hex()


def verify_password(password, salt_hex, expect_hash):
    """校验口令：算一遍再和存起来的哈希对比。用 compare_digest 做定时安全比较，防时序攻击。"""
    return secrets.compare_digest(hash_password(password, salt_hex), expect_hash)
```

</details>

<details>
<summary>打开完整代码：make_users.py</summary>

```python
# -*- coding: utf-8 -*-
"""
生成用户账号文件 users.json（服务器只存“盐 + 哈希”，不存明文密码）

用法：
    python make_users.py                  # 生成默认账号
    python make_users.py add 用户名 密码    # 追加/修改一个账号
    python make_users.py list              # 查看现有账号（看不到密码，只能看到盐和哈希）

默认账号：
    alice  / alice123
    bob    / bob123
    admin  / admin@123

users.json 的结构：
    {
      "alice": {"salt": "十六进制随机盐", "hash": "PBKDF2-HMAC-SHA256 摘要", "iterations": 120000},
      ...
    }
即使这个文件被泄露，攻击者也不知道明文口令（要靠暴力破解，代价很高）。
"""

import json
import os
import sys

from ftp_protocol import PBKDF2_ITERATIONS, hash_password, new_salt

HERE = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(HERE, 'users.json')

DEFAULT_USERS = [
    ('alice', 'alice123'),
    ('bob', 'bob123'),
    ('admin', 'admin@123'),
]


def load():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def add_user(users, name, password):
    salt = new_salt()
    users[name] = {
        'salt': salt,
        'hash': hash_password(password, salt),
        'iterations': PBKDF2_ITERATIONS,
    }
    print('已设置账号：%s（口令长度 %d，已加盐哈希后保存）' % (name, len(password)))


def main():
    args = sys.argv[1:]

    if args and args[0] == 'list':
        users = load()
        if not users:
            print('还没有任何账号，先运行 python make_users.py 生成默认账号')
            return
        print('共 %d 个账号（%s）：' % (len(users), USERS_FILE))
        for name, rec in users.items():
            print('  %-10s salt=%s… hash=%s…（%d 次迭代）'
                  % (name, rec['salt'][:8], rec['hash'][:16], rec.get('iterations', 0)))
        return

    if args and args[0] == 'add':
        if len(args) < 3:
            print('用法：python make_users.py add 用户名 密码')
            return
        users = load()
        add_user(users, args[1], args[2])
        save(users)
        print('已写入 %s' % USERS_FILE)
        return

    # 不带参数：生成默认账号（已存在的账号会被重置成默认口令）
    users = {}
    for name, password in DEFAULT_USERS:
        add_user(users, name, password)
    save(users)
    print('\n已写入 %s，可以直接启动服务端：python ftp_server.py' % USERS_FILE)
    print('登录信息：' + '、'.join('%s/%s' % (n, p) for n, p in DEFAULT_USERS))


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：ftp_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
基于 Socket 编程的 FTP 服务器

要求对照：
  · 基于 socketserver 实现并发 TCP 服务器，可同时处理多个客户端连接
      → socketserver.ThreadingTCPServer，每个连接自动一个线程
  · 用户账号的加密认证（哈希密码存储与验证）
      → users.json 存的是“随机盐 + PBKDF2-HMAC-SHA256(12 万次迭代)”的摘要，不存明文；
        用 hmac.compare_digest 做定时安全比较；连续错 3 次直接断开
  · 用户家目录隔离（每个用户只能访问自己的专属目录）
      → 每个用户的家目录是 ftp_root/<用户名>，客户端给的路径先 normpath 规范化，
        再检查是否还在家目录里面，越界（../、绝对路径、软链接绕过）一律拒绝
  · 完整支持 PUT（上传）、GET（下载）、LS（列目录）
  · 能处理客户端的正常与异常断开
      → QUIT 正常退出、直接关窗口/拔网线（ConnectionResetError/ConnectionAborted）都能处理，
        并用 try/except/finally 保证线程退出、连接关闭、日志记录
  · 文件传输完整性
      → 下载：服务端先算好 MD5 告诉客户端，客户端边收边算、收完比对；
        上传：客户端先声明 MD5，服务端落盘后自己算一遍比对，不一致就删掉临时文件并报错

通信协议见 ftp_protocol.py（1 字节类型 + 8 字节长度 + 负载，解决粘包/分包）。

用法：
    python make_users.py          # 第一次先执行，生成账号
    python ftp_server.py [监听地址] [端口] [数据根目录]
    默认 0.0.0.0:2121，数据根目录是脚本旁边的 ftp_root
"""

import hashlib
import json
import os
import socket
import socketserver
import sys
import threading
import time

from ftp_protocol import (CHUNK, TYPE_END, TYPE_FILE, human_size, md5_file,
                          recv_frame, recv_json, send_chunk, send_end, send_json,
                          verify_password)

HERE = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(HERE, 'users.json')
FTP_ROOT = os.path.join(HERE, 'ftp_root')

HOST, PORT = '0.0.0.0', 2121
MAX_LOGIN_TRY = 3                     # 连续输错几次就断开连接
MAX_UPLOAD = 2 * 1024 * 1024 * 1024   # 单个文件最大 2GB，防止把磁盘写满
SOCK_TIMEOUT = 300                    # 客户端 5 分钟没动静就断开，避免线程一直挂着

log_lock = threading.Lock()           # 多线程打印日志，加锁避免输出交错
stat_lock = threading.Lock()
online = {}                           # 用户名 -> 信息（当前在线用户）
total_login = 0                       # 累计成功登录次数


def log(msg):
    with log_lock:
        print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def load_users():
    """读取账号文件。"""
    if not os.path.exists(USERS_FILE):
        print('找不到账号文件：%s' % USERS_FILE)
        print('请先运行：python make_users.py')
        sys.exit(1)
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def safe_path(home, name):
    """把客户端给的路径转换到家目录下的绝对路径。

    返回 None 表示越界（想访问家目录以外的文件），一律拒绝。
    这是家目录隔离的关键：先 normpath 把 ../ 和 // 都规范化掉，再看结果在不在家目录里。
    """
    name = (name or '').replace('\\', '/')
    # 绝对路径（/etc/passwd、D:/Windows/...）直接拒绝：我们只接受相对自己家目录的路径
    if name.startswith('/') or ':' in name:
        return None
    target = os.path.normpath(os.path.join(home, name))
    if target == home or target.startswith(home + os.sep):
        return target
    return None


class FtpHandler(socketserver.StreamRequestHandler):
    """一个客户端连接 = 一个线程。"""

    timeout = SOCK_TIMEOUT          # socketserver 会把这个值设到连接套接字上

    def handle(self):
        global total_login
        ip = self.client_address[0]
        user = None
        try:
            user = self.do_login()
            if user is None:
                return                              # 没登录成功（超次数/断开），直接结束
            home = self.home
            log('%s@%s 登录成功，家目录：%s' % (user, ip, home))
            self.command_loop(user, home)
        except socket.timeout:
            log('%s 长时间没有操作，服务器主动断开' % (user or ip))
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            # 客户端直接关窗口/拔网线会走到这里，服务器不能因此崩溃
            log('%s（%s）异常断开：%s' % (user or '未登录客户端', ip, e))
        except ValueError as e:
            log('%s（%s）发来的数据不符合协议：%s' % (user or '未登录客户端', ip, e))
        except Exception as e:
            log('%s（%s）处理出错：%r' % (user or '未登录客户端', ip, e))
        finally:
            # 不管怎么退出，都要把在线状态清掉、把连接关掉
            if user:
                with stat_lock:
                    online.pop(user, None)
                    n = len(online)
                log('%s@%s 已下线（当前在线用户：%s）'
                    % (user, ip, '、'.join(online) if online else '无'))
            else:
                log('%s 的连接已关闭' % ip)
            try:
                self.request.close()
            except OSError:
                pass

    # ---------------- 登录 ----------------
    def do_login(self):
        """处理登录：最多 3 次机会，密码用哈希校验。"""
        global total_login
        ip = self.client_address[0]
        for attempt in range(1, MAX_LOGIN_TRY + 1):
            msg = recv_json(self.request)
            if msg is None:
                log('%s 还没登录就断开连接了' % ip)
                return None
            if msg.get('cmd') != 'login':
                send_json(self.request, {'ok': False, 'msg': '请先登录'})
                continue

            user = (msg.get('user') or '').strip()
            password = msg.get('pass') or ''
            rec = USERS.get(user)
            # 用户名不存在时也要走一遍哈希计算，避免用“响应快慢”探测哪些用户名存在
            ok = False
            if rec:
                ok = verify_password(password, rec['salt'], rec['hash'])
            else:
                verify_password(password, '00' * 16, '00' * 32)

            if ok:
                home = os.path.join(FTP_ROOT, user)
                os.makedirs(home, exist_ok=True)
                welcome = os.path.join(home, '欢迎.txt')
                if not os.path.exists(welcome):        # 第一次登录给个欢迎文件，免得目录是空的
                    with open(welcome, 'w', encoding='utf-8') as f:
                        f.write('%s 你好，这是你的专属目录，只有你自己能看到。\n' % user)
                with stat_lock:
                    total_login += 1
                    online[user] = {'ip': ip, 'time': time.time()}
                    n = len(online)
                self.home = home
                send_json(self.request, {
                    'ok': True,
                    'msg': '登录成功，欢迎 %s！' % user,
                    'user': user,
                    'online': n,
                })
                log('收到 %s@%s 的登录请求，口令校验通过（当前在线 %d 人）' % (user, ip, n))
                return user

            log('收到 %s@%s 的登录请求，口令校验失败（第 %d/%d 次）'
                % (user or '空用户名', ip, attempt, MAX_LOGIN_TRY))
            if attempt == MAX_LOGIN_TRY:
                send_json(self.request, {'ok': False,
                                         'msg': '用户名或密码错误，尝试次数过多，断开连接'})
                return None
            send_json(self.request, {'ok': False,
                                     'msg': '用户名或密码错误（第 %d/%d 次，共 %d 次机会）'
                                            % (attempt, MAX_LOGIN_TRY, MAX_LOGIN_TRY)})
        return None

    # ---------------- 命令循环 ----------------
    def command_loop(self, user, home):
        while True:
            msg = recv_json(self.request)
            if msg is None:
                log('%s 断开了连接（没有发 QUIT，属于异常断开）' % user)
                return
            cmd = msg.get('cmd')
            if cmd == 'ls':
                self.do_ls(user, home, msg)
            elif cmd == 'get':
                self.do_get(user, home, msg)
            elif cmd == 'put':
                self.do_put(user, home, msg)
            elif cmd == 'quit':
                send_json(self.request, {'ok': True, 'msg': '再见！'})
                log('%s 正常退出（QUIT）' % user)
                return
            else:
                send_json(self.request, {'ok': False, 'msg': '不支持的命令：%s' % cmd})

    # ---------------- LS 列目录 ----------------
    def do_ls(self, user, home, msg):
        rel = msg.get('path', '') or ''
        path = safe_path(home, rel)
        if path is None or not os.path.isdir(path):
            log('%s 请求列目录 %r —— 越界或不存在，已拒绝' % (user, rel))
            send_json(self.request, {'ok': False, 'msg': '目录不存在或无权访问'})
            return

        items = []
        try:
            for entry in os.scandir(path):
                try:
                    st = entry.stat()
                except OSError:
                    continue
                items.append({
                    'name': entry.name,
                    'is_dir': entry.is_dir(),
                    'size': 0 if entry.is_dir() else st.st_size,
                    'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime)),
                })
        except OSError as e:
            send_json(self.request, {'ok': False, 'msg': '读取目录失败：%s' % e})
            return

        # 目录排前面，然后按名字排序，好看
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        # 客户端传上来的是相对家目录的路径，回显时统一用 '/' 开头
        show_path = '/' + rel.replace('\\', '/').strip('/')
        send_json(self.request, {'ok': True, 'path': show_path, 'files': items})
        log('%s 列目录 %s，共 %d 项' % (user, show_path, len(items)))

    # ---------------- GET 下载 ----------------
    def do_get(self, user, home, msg):
        name = msg.get('name', '')
        path = safe_path(home, name)
        if path is None or not os.path.isfile(path):
            log('%s 请求下载 %r —— 越界或不存在，已拒绝' % (user, name))
            send_json(self.request, {'ok': False, 'msg': '文件不存在或无权访问'})
            return

        size = os.path.getsize(path)
        digest = md5_file(path)          # 先把 MD5 算好，客户端一拿到就能知道该校验成什么值
        send_json(self.request, {'ok': True, 'name': os.path.basename(path),
                                 'size': size, 'md5': digest})
        log('%s 开始下载 %s（%s），MD5=%s' % (user, name, human_size(size), digest))

        t0 = time.time()
        sent = 0
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                send_chunk(self.request, chunk)      # 分块发送，多大文件都不占内存
                sent += len(chunk)
        send_end(self.request)                       # 结束标记
        cost = time.time() - t0
        log('%s 下载完成 %s：%s，耗时 %.3f 秒（%.1f KB/s）'
            % (user, name, human_size(sent), cost, sent / 1024 / (cost or 1e-6)))

    # ---------------- PUT 上传 ----------------
    def recv_file_body(self, tmp_path, size):
        """接收客户端上传的文件内容，一直收到结束标记为止。

        重要：不管中途出了什么错（比如服务器磁盘写不进去），都要把客户端这一轮
        发来的数据全部收完再返回 —— 否则剩下的数据会留在缓冲区里被当成下一条命令，
        整个连接的数据流就“错位”了（这就是粘包问题的另一种体现）。
        返回 (失败原因, 收到字节数, MD5)；失败原因为空表示收的过程正常。
        """
        f = None
        fail_reason = None
        try:
            try:
                f = open(tmp_path, 'wb')
            except OSError as e:
                fail_reason = '服务器无法创建文件：%s' % e
                log('打开临时文件失败：%s（继续把这一轮数据收完再报错）' % e)

            got = 0
            md5 = hashlib.md5()
            while True:
                type_byte, payload = recv_frame(self.request)
                if type_byte is None:                 # 客户端断开，没法继续收了
                    return fail_reason or '上传途中客户端断开', got, md5.hexdigest()
                if type_byte == TYPE_FILE:
                    got += len(payload)
                    md5.update(payload)               # 校验用的哈希一定要算，写不写盘都要算
                    if got > size:
                        if fail_reason is None:
                            fail_reason = '客户端发送的数据(%d 字节)超过了声明的大小(%d 字节)' % (got, size)
                            if f:
                                f.close()
                                f = None
                    elif f is not None:
                        f.write(payload)
                elif type_byte == TYPE_END:
                    break
            return fail_reason, got, md5.hexdigest()
        finally:
            if f is not None:
                f.close()

    def do_put(self, user, home, msg):
        name = msg.get('name', '')
        size = int(msg.get('size') or 0)
        client_md5 = (msg.get('md5') or '').lower()
        overwrite = bool(msg.get('overwrite'))

        path = safe_path(home, name)
        if path is None:
            log('%s 试图上传到越界路径 %r，已拒绝' % (user, name))
            send_json(self.request, {'ok': False, 'msg': '路径不合法（只能用相对自己家目录的路径）'})
            return
        if size <= 0 or size > MAX_UPLOAD:
            send_json(self.request, {'ok': False,
                                     'msg': '文件大小不合法（单个文件不能超过 %s）'
                                            % human_size(MAX_UPLOAD)})
            return
        if not os.path.isdir(os.path.dirname(path)):
            send_json(self.request, {'ok': False, 'msg': '目标目录不存在'})
            return
        if os.path.isdir(path):
            send_json(self.request, {'ok': False, 'msg': '同名目录已存在，不能覆盖'})
            return
        if os.path.exists(path) and not overwrite:
            send_json(self.request, {'ok': False, 'need_confirm': True,
                                     'msg': '服务器上已有同名文件 %s' % os.path.basename(path)})
            return

        # 先收到临时文件，全部校验通过再改名成正式文件 —— 中途失败不会留下半截文件
        tmp_path = path + '.part'
        send_json(self.request, {'ok': True, 'msg': '可以上传'})
        log('%s 开始上传 %s（%s），声明的 MD5=%s'
            % (user, name, human_size(size), client_md5 or '（未提供）'))

        t0 = time.time()
        fail_reason, got, local_md5 = self.recv_file_body(tmp_path, size)
        cost = time.time() - t0

        def discard(reason):
            """删除临时文件并把这个失败原因告诉客户端。"""
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            log('%s 上传 %s 失败：%s（临时文件已删除）' % (user, name, reason))
            send_json(self.request, {'ok': False, 'msg': '上传失败：%s' % reason})

        if fail_reason:
            discard(fail_reason)
            return
        if got != size:                       # 完整性校验 1：字节数
            discard('文件大小校验失败（收到 %d 字节，声明 %d 字节）' % (got, size))
            return
        if client_md5 and local_md5 != client_md5:   # 完整性校验 2：MD5
            discard('MD5 校验失败（客户端说 %s，服务器算是 %s）' % (client_md5, local_md5))
            return

        os.replace(tmp_path, path)            # 校验通过，原子改名成正式文件
        log('%s 上传完成 %s：%s，耗时 %.3f 秒（%.1f KB/s），MD5=%s（校验通过）'
            % (user, name, human_size(got), cost, got / 1024 / (cost or 1e-6), local_md5))
        send_json(self.request, {'ok': True, 'msg': '上传成功，文件完整',
                                 'name': os.path.basename(path),
                                 'size': got, 'md5': local_md5})


class FtpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True               # 主线程退出时工作线程一起退出


if __name__ == '__main__':
    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])
    if len(sys.argv) > 3:
        FTP_ROOT = os.path.abspath(sys.argv[3])

    USERS = load_users()
    os.makedirs(FTP_ROOT, exist_ok=True)

    print('=' * 66)
    print('FTP 服务器已启动')
    print('  监听地址：%s:%d' % (HOST, PORT))
    print('  数据根目录：%s（每个用户一个子目录，互相隔离）' % FTP_ROOT)
    print('  账号：%s（密码以“盐+哈希”形式存在 users.json，日志里不会出现明文）'
          % '、'.join(USERS))
    print('  客户端：python ftp_client.py')
    print('=' * 66)

    try:
        with FtpServer((HOST, PORT), FtpHandler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务器退出')
        with stat_lock:
            print('本次运行共成功登录 %d 次' % total_login)
```

</details>

<details>
<summary>打开完整代码：ftp_client.py</summary>

```python
# -*- coding: utf-8 -*-
"""
基于 Socket 编程的 FTP 客户端（tkinter 图形界面）

界面上的东西对照实验要求：
  · 文本框：服务器 IP、端口、用户名、密码（密码用 * 显示）
  · 按钮：连接、断开、刷新列表(LS)、上传(PUT)、下载(GET)、返回上级
  · 列表控件：服务器文件列表（名称 / 大小 / 修改时间 / 类型），双击目录进目录、双击文件下载
  · 进度条 + 日志区：上传下载时实时显示百分比、速度、剩余时间这些状态

线程模型（这是 GUI + 网络编程最容易出错的地方）：
  · 主线程只干一件事：跑 tkinter 的 mainloop()，所有控件操作都在主线程做；
  · 网络操作（连接、登录、列目录、传文件）全都放到 worker 线程里做，
    否则 recv() 一阻塞，窗口就“未响应”了；
  · worker 线程不能直接改控件（tkinter 不是线程安全的），
    所以它把“要显示什么”丢进 queue.Queue，由主线程用 after() 定时取出来更新界面。
    代码里所有界面刷新都走 self.ui_queue，就是这个原因。

用法：
    python ftp_client.py            # 先确保服务端 ftp_server.py 已经启动
"""

import hashlib
import os
import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from ftp_protocol import (CHUNK, TYPE_END, TYPE_FILE, human_size, md5_file,
                          recv_frame, recv_json, send_chunk, send_end, send_json)

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = '2121'
SOCK_TIMEOUT = 15           # 每次收发的超时时间（秒），避免界面无限等待


class FtpClientGUI:
    def __init__(self, root):
        self.root = root
        self.sock = None
        self.connected = False
        self.busy = False              # 有传输在跑的时候，禁止再发别的命令
        self.cwd = ''                  # 服务器上当前目录（相对自己家目录，'' 表示家目录）
        self.items = []                # 当前目录下的文件列表
        self.user = ''
        self.ui_queue = queue.Queue()  # worker 线程 → 主线程 的“信箱”

        root.title('FTP 客户端 —— 基于 Socket 编程')
        root.geometry('900x640')
        root.minsize(820, 560)

        self.build_ui()
        self.update_buttons()
        self.log('欢迎使用 FTP 客户端。请填写服务器地址和账号后点击“连接”。')
        self.log('提示：服务端第一次运行前要先执行 python make_users.py 生成账号。')
        self.root.after(80, self.pump_ui_queue)     # 定时把 worker 的消息搬到界面上
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    # ==================== 界面 ====================
    def build_ui(self):
        pad = {'padx': 4, 'pady': 4}

        # ---------- 顶部：连接区 ----------
        top = tk.LabelFrame(self.root, text='服务器连接', padx=6, pady=6)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))

        tk.Label(top, text='服务器IP：').grid(row=0, column=0, **pad)
        self.ent_host = tk.Entry(top, width=14)
        self.ent_host.insert(0, DEFAULT_HOST)
        self.ent_host.grid(row=0, column=1, **pad)

        tk.Label(top, text='端口：').grid(row=0, column=2, **pad)
        self.ent_port = tk.Entry(top, width=7)
        self.ent_port.insert(0, DEFAULT_PORT)
        self.ent_port.grid(row=0, column=3, **pad)

        tk.Label(top, text='用户名：').grid(row=0, column=4, **pad)
        self.ent_user = tk.Entry(top, width=12)
        self.ent_user.grid(row=0, column=5, **pad)

        tk.Label(top, text='密码：').grid(row=0, column=6, **pad)
        self.ent_pwd = tk.Entry(top, width=12, show='*')       # 密码框用 * 遮起来
        self.ent_pwd.grid(row=0, column=7, **pad)
        self.ent_pwd.bind('<Return>', lambda e: self.on_connect())   # 输完密码直接回车就能连

        self.btn_connect = tk.Button(top, text='连接', width=8, command=self.on_connect)
        self.btn_connect.grid(row=0, column=8, **pad)
        self.btn_disconnect = tk.Button(top, text='断开', width=8, command=self.on_disconnect)
        self.btn_disconnect.grid(row=0, column=9, **pad)

        # ---------- 中部：服务器文件列表 ----------
        mid = tk.LabelFrame(self.root, text='服务器文件列表（我的家目录）', padx=6, pady=6)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        bar = tk.Frame(mid)
        bar.pack(fill=tk.X)
        self.lbl_path = tk.Label(bar, text='当前目录：/（未连接）', anchor='w', fg='#333')
        self.lbl_path.pack(side=tk.LEFT)
        self.btn_up = tk.Button(bar, text='返回上级', width=9, command=self.on_up)
        self.btn_up.pack(side=tk.RIGHT, padx=2)
        self.btn_refresh = tk.Button(bar, text='刷新列表(LS)', width=13, command=self.on_refresh)
        self.btn_refresh.pack(side=tk.RIGHT, padx=2)

        cols = ('name', 'size', 'mtime', 'type')
        self.tree = ttk.Treeview(mid, columns=cols, show='headings', height=12)
        self.tree.heading('name', text='名称')
        self.tree.heading('size', text='大小')
        self.tree.heading('mtime', text='修改时间')
        self.tree.heading('type', text='类型')
        self.tree.column('name', width=380, anchor='w')
        self.tree.column('size', width=110, anchor='e')
        self.tree.column('mtime', width=150, anchor='center')
        self.tree.column('type', width=80, anchor='center')
        vsb = ttk.Scrollbar(mid, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', self.on_double_click)      # 双击进目录 / 下载

        # ---------- 传输区 ----------
        tra = tk.LabelFrame(self.root, text='文件传输', padx=6, pady=6)
        tra.pack(fill=tk.X, padx=8, pady=4)

        self.btn_download = tk.Button(tra, text='下载选中文件(GET)', width=18,
                                      command=self.on_download)
        self.btn_download.grid(row=0, column=0, padx=4, pady=2)
        self.btn_upload = tk.Button(tra, text='选择本地文件上传(PUT)', width=20,
                                    command=self.on_upload)
        self.btn_upload.grid(row=0, column=1, padx=4, pady=2)

        self.lbl_progress = tk.Label(tra, text='就绪', anchor='w')
        self.lbl_progress.grid(row=1, column=0, columnspan=2, sticky='w', padx=4)
        self.progress = ttk.Progressbar(tra, orient='horizontal', length=800,
                                        mode='determinate', maximum=100)
        self.progress.grid(row=2, column=0, columnspan=2, sticky='we', padx=4, pady=4)
        tra.columnconfigure(0, weight=1)
        tra.columnconfigure(1, weight=1)

        # ---------- 底部：日志区 ----------
        bot = tk.LabelFrame(self.root, text='日志（传输状态、百分比、速度都会打在这里）', padx=6, pady=6)
        bot.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        self.txt_log = scrolledtext.ScrolledText(bot, height=9, state=tk.DISABLED)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    # ==================== 界面刷新（只在主线程里跑） ====================
    def log(self, msg):
        """往日志区追加一行（带时间戳）。"""
        line = '[%s] %s\n' % (time.strftime('%H:%M:%S'), msg)
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, line)
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def pump_ui_queue(self):
        """主线程定时把 worker 线程放进队列的消息取出来，更新界面。"""
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                kind = msg[0]
                if kind == 'log':
                    self.log(msg[1])
                elif kind == 'progress':                     # (百分比, 状态文字)
                    self.progress['value'] = msg[1]
                    self.lbl_progress.config(text=msg[2])
                elif kind == 'files':                        # (路径, 文件列表)
                    self.cwd, self.items = msg[1], msg[2]
                    self.show_files()
                elif kind == 'connected':                    # (是否连接, 用户名)
                    self.connected = msg[1]
                    self.user = msg[2] or ''
                    if not self.connected:
                        self.items = []
                        self.cwd = ''
                        self.show_files()
                        self.lbl_path.config(text='当前目录：/（未连接）')
                    self.update_buttons()
                elif kind == 'busy':                         # 传输开始/结束
                    self.busy = msg[1]
                    if msg[1]:
                        # 新任务开始：进度条清零，准备显示这一次的进度
                        # （注意：任务结束时不能清零，否则用户看不到“100% 完成”那一瞬间）
                        self.progress['value'] = 0
                        self.lbl_progress.config(text='处理中……')
                    self.update_buttons()
        except queue.Empty:
            pass
        self.root.after(80, self.pump_ui_queue)

    def show_files(self):
        self.tree.delete(*self.tree.get_children())
        for it in self.items:
            self.tree.insert('', tk.END, values=(
                it['name'],
                '—' if it['is_dir'] else human_size(it['size']),
                it['mtime'],
                '目录' if it['is_dir'] else '文件',
            ))
        if self.connected:
            self.lbl_path.config(text='当前目录：/%s   （共 %d 项）' % (self.cwd, len(self.items)))
        else:
            self.lbl_path.config(text='当前目录：/（未连接）')

    def update_buttons(self):
        state = tk.NORMAL if (self.connected and not self.busy) else tk.DISABLED
        for btn in (self.btn_refresh, self.btn_download, self.btn_upload, self.btn_up):
            btn.config(state=state)
        self.btn_connect.config(
            state=tk.DISABLED if (self.connected or self.busy) else tk.NORMAL)
        self.btn_disconnect.config(state=tk.NORMAL if self.connected else tk.DISABLED)

    def set_progress(self, percent, text):
        """worker 线程调用：把进度丢进队列（真正更新控件的是主线程）。"""
        self.ui_queue.put(('progress', percent, text))

    # ==================== 按钮事件（主线程） ====================
    def on_connect(self):
        if self.busy:
            return
        host = self.ent_host.get().strip() or DEFAULT_HOST
        port = self.ent_port.get().strip() or DEFAULT_PORT
        user = self.ent_user.get().strip()
        pwd = self.ent_pwd.get()
        if not user:
            messagebox.showwarning('提示', '请填写用户名')
            return
        if not port.isdigit():
            messagebox.showwarning('提示', '端口必须是数字')
            return
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_connect,
                         args=(host, int(port), user, pwd), daemon=True).start()

    def on_disconnect(self):
        """断开连接：能优雅就优雅（发 QUIT），不行就直接关掉 socket。"""
        if not self.connected:
            return
        if self.busy:
            # 正在传输，直接把套接字关掉，worker 线程会立刻收到异常并结束
            self.close_socket()
            self.log('已强制断开连接（传输被中断）')
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))
            return
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_quit, daemon=True).start()

    def on_refresh(self):
        if self.connected and not self.busy:
            self.ui_queue.put(('busy', True))
            threading.Thread(target=self.worker_ls, args=(self.cwd,), daemon=True).start()

    def on_up(self):
        if not self.connected or self.busy or not self.cwd:
            return
        parent = '/'.join(self.cwd.split('/')[:-1])       # 去掉最后一级
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_ls, args=(parent,), daemon=True).start()

    def on_double_click(self, event):
        """双击：目录就进去，文件就下载。"""
        sel = self.tree.selection()
        if not sel or self.busy or not self.connected:
            return
        name = self.tree.item(sel[0], 'values')[0]
        item = next((i for i in self.items if i['name'] == name), None)
        if item is None:
            return
        if item['is_dir']:
            path = '%s/%s' % (self.cwd, name) if self.cwd else name
            self.ui_queue.put(('busy', True))
            threading.Thread(target=self.worker_ls, args=(path,), daemon=True).start()
        else:
            self.start_download(name)

    def on_download(self):
        """下载列表里选中的文件。"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先在列表里选中一个文件')
            return
        name = self.tree.item(sel[0], 'values')[0]
        item = next((i for i in self.items if i['name'] == name), None)
        if item and item['is_dir']:
            messagebox.showinfo('提示', '这是一个目录，双击进去再选文件')
            return
        self.start_download(name)

    def start_download(self, name):
        if not (self.connected and not self.busy):
            return
        # 先问用户存到哪儿（这个对话框必须在主线程里弹）
        local_path = filedialog.asksaveasfilename(
            title='保存到本地', initialfile=name, initialdir=os.getcwd())
        if not local_path:
            self.log('已取消下载 %s' % name)
            return
        remote = '%s/%s' % (self.cwd, name) if self.cwd else name
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_get, args=(remote, local_path), daemon=True).start()

    def on_upload(self):
        if not (self.connected and not self.busy):
            return
        local_path = filedialog.askopenfilename(title='选择要上传的文件',
                                                initialdir=os.getcwd())
        if not local_path:
            return
        name = os.path.basename(local_path)
        # 目标位置：服务器上当前目录
        overwrite = False
        exist = next((i for i in self.items if i['name'] == name and not i['is_dir']), None)
        if exist:
            # 服务器上已有同名文件，先问用户要不要覆盖（服务端也会再拦一道）
            if not messagebox.askyesno('文件已存在',
                                       '服务器上已有 %s（%s），要覆盖它吗？'
                                       % (name, human_size(exist['size']))):
                self.log('已取消上传 %s' % name)
                return
            overwrite = True
        remote = '%s/%s' % (self.cwd, name) if self.cwd else name
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_put,
                         args=(local_path, remote, overwrite), daemon=True).start()

    def on_close(self):
        if self.connected:
            try:
                self.sock.settimeout(2)
                send_json(self.sock, {'cmd': 'quit'})
            except OSError:
                pass
            self.close_socket()
        self.root.destroy()

    # ==================== 网络操作（worker 线程里跑） ====================
    def close_socket(self):
        self.connected = False
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def worker_connect(self, host, port, user, pwd):
        self.ui_queue.put(('log', '正在连接 %s:%d ……' % (host, port)))
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCK_TIMEOUT)
            sock.connect((host, port))
            self.sock = sock

            t0 = time.time()
            # 登录：密码在网络上传的是明文（这是本实验的简化，真实 FTP 还有 FTPS/SSH 加密），
            # 但服务器端保存的是“盐+哈希”，不保存明文
            send_json(sock, {'cmd': 'login', 'user': user, 'pass': pwd})
            reply = recv_json(sock)
            if reply is None:
                self.ui_queue.put(('log', '服务端没有应答就断开了连接'))
                self.close_socket()
                self.ui_queue.put(('connected', False, ''))
                self.ui_queue.put(('busy', False))
                return
            if not reply.get('ok'):
                self.ui_queue.put(('log', '登录失败：%s' % reply.get('msg')))
                self.close_socket()
                self.ui_queue.put(('connected', False, ''))
                self.ui_queue.put(('busy', False))
                return

            self.ui_queue.put(('log', '登录成功：%s（握手耗时 %.0f 毫秒）'
                                      % (reply.get('msg'), (time.time() - t0) * 1000)))
            self.ui_queue.put(('connected', True, reply.get('user')))
            self.do_ls('')                      # 登录后自动列一次目录
            self.ui_queue.put(('busy', False))  # 列完目录再解除“忙碌”，避免用户抢在刷新中间操作
        except socket.timeout:
            self.ui_queue.put(('log', '连接超时：服务器没有响应'))
            self.close_socket()
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))
        except OSError as e:
            self.ui_queue.put(('log', '连接失败：%s' % e))
            self.close_socket()
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))

    def worker_quit(self):
        try:
            send_json(self.sock, {'cmd': 'quit'})
            recv_json(self.sock)
        except OSError:
            pass
        finally:
            self.close_socket()
            self.ui_queue.put(('log', '已断开与服务器的连接'))
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))

    def worker_ls(self, path):
        self.do_ls(path)
        self.ui_queue.put(('busy', False))

    def do_ls(self, path):
        """列目录。注意这里自己不 put busy=False，因为登录后也会调用它。"""
        try:
            send_json(self.sock, {'cmd': 'ls', 'path': path})
            reply = recv_json(self.sock)
            if reply is None:
                raise ConnectionResetError('服务器关闭了连接')
            if not reply.get('ok'):
                self.ui_queue.put(('log', '列目录失败：%s' % reply.get('msg')))
                return
            files = reply.get('files', [])
            self.ui_queue.put(('files', path, files))
            self.ui_queue.put(('log', '列目录 %s：共 %d 项（目录 %d 个，文件 %d 个）'
                                      % (reply.get('path', '/'), len(files),
                                         sum(1 for f in files if f['is_dir']),
                                         sum(1 for f in files if not f['is_dir']))))
        except (socket.timeout, ConnectionResetError, ConnectionAbortedError,
                AttributeError, ValueError, OSError) as e:
            self.ui_queue.put(('log', '列目录出错：%s' % e))
            self.handle_link_error()

    def worker_get(self, remote_name, local_path):
        """下载文件：服务端先告诉大小和 MD5，客户端边收边算 MD5，收完校验。"""
        name = remote_name.split('/')[-1]
        try:
            send_json(self.sock, {'cmd': 'get', 'name': remote_name})
            head = recv_json(self.sock)
            if head is None:
                raise ConnectionResetError('服务器关闭了连接')
            if not head.get('ok'):
                self.ui_queue.put(('log', '下载失败：%s' % head.get('msg')))
                return

            size = head['size']
            expect_md5 = head['md5']
            self.ui_queue.put(('log', '开始下载 %s（%s），服务端 MD5=%s'
                                      % (name, human_size(size), expect_md5)))

            md5 = hashlib.md5()
            got = 0
            t0 = time.time()
            last_update = 0.0
            tmp_path = local_path + '.part'      # 先写临时文件，校验通过再改名
            with open(tmp_path, 'wb') as f:
                while True:
                    type_byte, payload = recv_frame(self.sock)
                    if type_byte is None:
                        raise ConnectionResetError('下载途中连接断开')
                    if type_byte == TYPE_FILE:
                        f.write(payload)
                        md5.update(payload)
                        got += len(payload)
                        # 进度最多每 0.1 秒刷新一次，刷太勤界面反而不流畅
                        now = time.time()
                        if now - last_update > 0.1 or got >= size:
                            last_update = now
                            elapsed = now - t0
                            speed = got / elapsed if elapsed > 0 else 0
                            percent = got * 100.0 / size if size else 100.0
                            eta = (size - got) / speed if speed > 0 else 0
                            self.set_progress(percent,
                                              '下载 %s：%.1f%%（%s / %s）  %.1f KB/s  剩余 %.0f 秒'
                                              % (name, percent, human_size(got),
                                                 human_size(size), speed / 1024, eta))
                    elif type_byte == TYPE_END:
                        break

            cost = time.time() - t0
            local_md5 = md5.hexdigest()
            # 完整性校验：大小 + MD5
            if got != size:
                os.remove(tmp_path)
                self.ui_queue.put(('log', '下载失败：只收到 %d 字节，应该收到 %d 字节'
                                          % (got, size)))
                self.set_progress(0, '下载失败')
                return
            if local_md5 != expect_md5:
                os.remove(tmp_path)
                self.ui_queue.put(('log', '下载失败：MD5 校验不通过（本地 %s，服务端 %s）'
                                          % (local_md5, expect_md5)))
                self.set_progress(0, 'MD5 校验失败')
                return

            os.replace(tmp_path, local_path)
            self.set_progress(100, '下载完成：%s' % name)
            self.ui_queue.put(('log', '下载完成 %s：%s，耗时 %.2f 秒（%.1f KB/s），'
                                      '大小✔ MD5✔（%s）'
                                      % (name, human_size(got), cost,
                                         got / 1024 / (cost or 1e-6), local_md5)))
        except (socket.timeout, ConnectionResetError, ConnectionAbortedError,
                AttributeError, ValueError, OSError) as e:
            self.ui_queue.put(('log', '下载出错：%s' % e))
            self.set_progress(0, '下载中断')
            self.handle_link_error()
        finally:
            # 先刷新列表（还要用套接字），最后才解除“忙碌”——
            # 反过来的话，用户可能在刷新期间又点一个下载，两个线程同时用一个套接字会串包
            self.refresh_quietly()
            self.ui_queue.put(('busy', False))

    def worker_put(self, local_path, remote_name, overwrite):
        """上传文件：先把本地 MD5 算好告诉服务端，服务端落盘后再算一遍比对。"""
        name = os.path.basename(local_path)
        try:
            size = os.path.getsize(local_path)
            self.set_progress(0, '正在计算本地 MD5 ……')
            t_md5 = time.time()
            local_md5 = md5_file(local_path)
            self.ui_queue.put(('log', '本地文件 %s（%s），本地 MD5=%s（计算用了 %.2f 秒）'
                                      % (name, human_size(size), local_md5,
                                         time.time() - t_md5)))

            send_json(self.sock, {'cmd': 'put', 'name': remote_name, 'size': size,
                                  'md5': local_md5, 'overwrite': overwrite})
            head = recv_json(self.sock)
            if head is None:
                raise ConnectionResetError('服务器关闭了连接')
            if not head.get('ok'):
                self.ui_queue.put(('log', '上传被拒绝：%s' % head.get('msg')))
                self.set_progress(0, '上传被拒绝')
                return

            self.ui_queue.put(('log', '开始上传 %s（%s）……' % (name, human_size(size))))
            t0 = time.time()
            sent = 0
            last_update = 0.0
            with open(local_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK)
                    if not chunk:
                        break
                    send_chunk(self.sock, chunk)       # 按协议分块发送
                    sent += len(chunk)
                    now = time.time()
                    if now - last_update > 0.1 or sent >= size:
                        last_update = now
                        elapsed = now - t0
                        speed = sent / elapsed if elapsed > 0 else 0
                        percent = sent * 100.0 / size if size else 100.0
                        eta = (size - sent) / speed if speed > 0 else 0
                        self.set_progress(percent,
                                          '上传 %s：%.1f%%（%s / %s）  %.1f KB/s  剩余 %.0f 秒'
                                          % (name, percent, human_size(sent),
                                             human_size(size), speed / 1024, eta))
            send_end(self.sock)                        # 发结束标记
            cost = time.time() - t0

            reply = recv_json(self.sock)               # 等服务端的校验结果
            if reply is None:
                raise ConnectionResetError('服务器关闭了连接')
            if reply.get('ok'):
                self.set_progress(100, '上传完成：%s' % name)
                self.ui_queue.put(('log', '上传完成 %s：%s，耗时 %.2f 秒（%.1f KB/s），'
                                          '服务端校验通过，MD5=%s'
                                          % (name, human_size(sent), cost,
                                             sent / 1024 / (cost or 1e-6), reply.get('md5'))))
            else:
                self.set_progress(0, '上传失败')
                self.ui_queue.put(('log', '上传失败：%s' % reply.get('msg')))
        except (socket.timeout, ConnectionResetError, ConnectionAbortedError,
                AttributeError, ValueError, OSError) as e:
            self.ui_queue.put(('log', '上传出错：%s' % e))
            self.set_progress(0, '上传中断')
            self.handle_link_error()
        finally:
            self.refresh_quietly()
            self.ui_queue.put(('busy', False))

    def refresh_quietly(self):
        """传完文件后悄悄刷新一下列表，让用户马上看到结果。"""
        if self.connected and self.sock is not None:
            try:
                send_json(self.sock, {'cmd': 'ls', 'path': self.cwd})
                reply = recv_json(self.sock)
                if reply and reply.get('ok'):
                    self.ui_queue.put(('files', self.cwd, reply.get('files', [])))
            except OSError:
                self.handle_link_error()

    def handle_link_error(self):
        """连接出问题时统一处理：标记断开、提示用户。"""
        if self.connected:
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('log', '与服务器的连接已断开，请重新连接'))
        self.close_socket()


if __name__ == '__main__':
    root = tk.Tk()
    app = FtpClientGUI(root)
    root.mainloop()
```

</details>
