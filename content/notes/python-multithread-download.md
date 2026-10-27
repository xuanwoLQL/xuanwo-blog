---
title: "多线程文件下载"
slug: "python-multithread-download"
date: 2026-10-18T09:56:41+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "多线程分块下载、进度显示与并发一致性测试。"
summary: "多线程分块下载、进度显示与并发一致性测试。"
tags: ["Python", "多线程", "下载"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 6
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/实验五-基于多线程的文件下载实验/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-multithread-download/workflow.svg" alt="HTTP Range 让多个线程下载同一文件的不同区间，主线程负责合并与校验。" loading="lazy">
  <figcaption>图 1 · 多线程分段下载。HTTP Range 让多个线程下载同一文件的不同区间，主线程负责合并与校验。</figcaption>
</figure>

## 实验内容与文件对照

| 实验要求 | 文件 |
|---|---|
| (1) 多线程文件服务器：分块回传、每个客户端一个线程 | `download_server.py` |
| (2) 多线程文件下载客户端：多用户并发下载 + 验证完整性（大小/MD5） | `download_client.py` |
| (3) 线程并发控制与性能对比实验 | `concurrency_test.py` |
| 生成下载测试用的大文件（辅助） | `make_test_files.py` |

## 运行步骤

```bash
# 第 0 步：生成测试文件（默认在 ./shared 生成 6 个 8MB 的文件）
python make_test_files.py

# 第 1 步：启动服务端
#   参数：[共享目录] [端口] [每连接限速KB/s] [最大并发线程数]
#   做性能对比实验时建议限速，否则本机回环太快，看不出并发差别
python download_server.py shared 9101 512 16

# 第 2 步：客户端（另开终端）
python download_client.py 127.0.0.1 9101 test1.bin                # 下载一个文件
python download_client.py 127.0.0.1 9101 test1.bin test2.bin --jobs 6   # 模拟 6 个用户同时下载

# 第 3 步：并发控制与性能对比实验（另开终端）
python concurrency_test.py 127.0.0.1 9101 4 1,2,4,8
```

## 自定义传输协议（解决粘包/分包）

```
① 请求帧（客户端 → 服务端）
   b'FDL1'  +  4字节文件名长度(大端)  +  文件名(UTF-8)

② 应答帧（服务端 → 客户端）
   b'1' 找到文件： + 8字节文件大小(大端) + 文件内容(分块发送) + 32字节MD5(十六进制文本)
   b'0' 没找到：   + 4字节错误信息长度(大端) + 错误信息(UTF-8)
```

- **先发长度再发内容**，接收方就知道该收多少字节 —— 这是解决粘包的关键；
- 收数据统一走 `recv_exact()`：循环 `recv` 直到收满 n 个字节 —— 这是解决分包的关键；
- 发数据统一用 `sendall()`，保证一次全部写出；
- 校验：服务端边发边算 MD5 附在最后，客户端边收边算 MD5，收完比对（同时比对字节数），
  两项都对才算下载成功。

## 各要求实现要点

### (1) 多线程文件服务器
- 主线程只负责 `accept()`，每来一个连接就 `threading.Thread(target=serve_client, daemon=True)` 起一个线程，
  主线程立刻回去等下一个人，实现多客户端并发下载。
- 文件按 64KB 分块回传，可以下载任意大小的文件而不会占满内存。
- 只取文件名（`os.path.basename`）拼路径，防止客户端用 `../../` 下载共享目录以外的文件。
- 服务端也打印每个客户端的耗时和速度，方便和客户端对照。

### (2) 线程安全与资源管理
- **共享资源加锁**：`stat_lock` 保护在线表 `active` 和累计统计（连接数、总字节数）；
  `log_lock` 保护日志输出，避免多个线程的打印互相插花；每个线程自己 `open()` 自己的文件句柄，
  不共享文件对象。
- **线程的回收**：工作线程设成 `daemon=True`；主线程按 Ctrl+C 退出时，
  还会对每个线程 `join(timeout=5)` 等它们结束，两者都做了。

### (3) 线程并发控制
- 服务端用 `threading.BoundedSemaphore(max_threads)` 限制**同时传输的线程数**，
  超过上限的客户端在 `sem.acquire()` 处排队等待（最多等 60 秒，超时就回“服务器繁忙”）。
- 支持**每连接限速**（`limit_bps`）：每发一块就按“已发字节数 ÷ 限速”算出应该花的时间，
  比实际快就 sleep 一会儿 —— 用来模拟真实网络带宽受限，并发的效果才看得清楚。

## 自测结果

**测试环境**：Python 3.11，Windows，4 个 2MB 测试文件，服务端每连接限速 512KB/s、最多 16 线程。

1. **并发下载 + 完整性校验**：`--jobs 6` 同时下载 3 个不同文件（有重复），
   6 个任务全部成功，下载下来的文件与源文件 **MD5 完全一致**（`af7cdaef…`、`0a074cd2…` 等）。
   请求不存在的文件返回“服务器上没有文件”，用 `../../../../Windows/win.ini` 做目录穿越被拒绝。
2. **线程并发控制**：服务端限制最多 3 个线程时，6 个客户端并发下载同一文件，
   日志里线程数**始终不超过 3**，前 3 个在 11.75 秒完成、后 3 个排队等到 23.76 秒完成
   （正好一个批次的时间），6 个文件全部校验通过。
3. **性能对比（限速 512KB/s，4 个 2MB 文件）**：

   | 并发线程数 | 总耗时(秒) | 平均每文件(秒) | 加速比 | 成功/总数 |
   |---|---|---|---|---|
   | 1（串行） | 16.008 | 4.002 | 1.00x | 4/4 |
   | 2 | 8.007 | 2.002 | 2.00x | 4/4 |
   | 4 | 4.007 | 1.002 | 3.99x | 4/4 |
   | 8 | 4.006 | 1.002 | 4.00x | 4/4 |

   结论：并发度不超过文件个数时，加速比接近线性（≈ 并发线程数）；
   线程数超过文件个数后不再变快（多出的线程没有文件可分）；
   串行 16 秒 vs 4 线程 4 秒，**4 倍加速**，并发效果明显。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-multithread-download 完整源码包](/code/python-multithread-download/source.zip)

项目目录：

```text
实验五-基于多线程的文件下载实验/
├─ concurrency_test.py
├─ download_client.py
├─ download_server.py
├─ make_test_files.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：make_test_files.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验五 辅助脚本 —— 生成下载测试用的大文件

用法：
  python make_test_files.py [目录] [文件个数] [每个文件多少MB]
  默认：脚本目录下的 shared 目录（和服务端默认共享目录一致）、6 个文件、每个 8MB。

文件内容用固定随机种子生成，所以每次生成的内容都一样、MD5 也可复现，
方便在实验报告里写明校验值。
"""

import hashlib
import os
import random
import sys
import time

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared')


def make_one(path, size, seed):
    """写一个随机内容的大文件，返回它的 MD5。"""
    rnd = random.Random(seed)                      # 每个文件用自己的种子，内容才是不同的
    md5 = hashlib.md5()
    remain = size
    with open(path, 'wb') as f:
        while remain > 0:
            n = min(1024 * 1024, remain)           # 一次生成 1MB，避免一次申请太大内存
            data = rnd.randbytes(n)
            f.write(data)
            md5.update(data)
            remain -= n
    return md5.hexdigest()


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    size_mb = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    os.makedirs(target, exist_ok=True)
    size = size_mb * 1024 * 1024
    print('在 %s 生成 %d 个测试文件，每个 %.0f MB' % (target, count, size_mb))

    t0 = time.time()
    for i in range(1, count + 1):
        name = 'test%d.bin' % i
        path = os.path.join(target, name)
        digest = make_one(path, size, 20261018 + i)     # 种子不同 → 内容不同 → MD5 不同
        print('  %-12s %10d 字节  MD5=%s' % (name, size, digest))
    print('生成完毕，用时 %.2f 秒' % (time.time() - t0))
    print('现在可以运行：python download_server.py  （共享目录就是 %s）' % target)


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：download_server.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验五 基于多线程的文件下载 —— 服务端（多线程文件服务器）

要求对照：
  (1) 多线程文件服务器：监听指定端口，接收客户端发来的文件名请求，在本地目录
      查找文件并分块回传；每 accept 到一个客户端连接，就创建一个独立线程处理它，
      实现多客户端并发下载。
  (2) 线程安全与资源管理：共享资源（客户端计数、在线表、日志输出）都用
      threading.Lock 保护，避免竞态条件；工作线程统一设为 daemon 线程，
      主线程退出前还会 join() 等待它们结束。
  (3) 线程并发控制：用 threading.BoundedSemaphore 限制“同时传输的线程数”，
      超过上限的客户端先排队等待（用于实验 3 的并发控制与性能对比）。

自定义协议（用来解决 TCP 粘包/分包问题）：
  ① 请求帧（客户端 → 服务端）：b'FDL1' + 4字节文件名长度(大端) + 文件名(UTF-8)
  ② 应答帧（服务端 → 客户端）：
       b'1' 找到文件：+ 8字节文件大小(大端) + 文件内容(分块发送) + 32字节MD5(十六进制文本)
       b'0' 没找到：  + 4字节错误信息长度(大端) + 错误信息(UTF-8)
  先发长度再发内容，接收方就知道该收多少字节，不会把两条数据粘在一起，
  也不会把一条数据读一半（分包）；发送统一用 sendall() 保证全部写完。

用法：
  python download_server.py [共享目录] [端口] [每连接限速KB/s] [最大并发线程数]
  默认：脚本目录下的 shared 目录、端口 9101、不限速、最多 16 个并发线程。
  做性能对比实验时建议限速，比如每个连接限速 512KB/s（模拟真实网络带宽受限）：
      python download_server.py shared 9101 512 16
"""

import hashlib
import os
import socket
import struct
import sys
import threading
import time

HOST = '0.0.0.0'
PORT = 9101
CHUNK = 64 * 1024               # 每块 64KB
MAGIC = b'FDL1'                 # 协议魔数，用来确认对方发的确实是本协议的请求
HEAD = struct.Struct('!4sI')    # 4字节魔数 + 4字节文件名长度

# ---------- 全局共享数据，全部用锁保护 ----------
stat_lock = threading.Lock()    # 保护 active / 累计统计
log_lock = threading.Lock()     # 保护日志输出，避免多个线程的打印互相插花
active = {}                     # 线程名 -> '客户端地址:文件名'，当前正在传输的连接
total_conn = 0                  # 累计服务过的连接数
total_bytes = 0                 # 累计发出的文件字节数


def log(msg):
    """带时间戳打印日志，加锁保证多线程下输出不交错。"""
    with log_lock:
        print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def recv_exact(sock, n):
    """收满 n 个字节；对方提前关闭则返回 None（TCP 分包问题就靠它解决）。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def recv_request(sock):
    """按协议收一个请求帧，返回要下载的文件名；协议不对或对方断开则返回 None。"""
    head = recv_exact(sock, HEAD.size)
    if head is None:
        return None
    magic, name_len = HEAD.unpack(head)
    if magic != MAGIC:
        log('对方发的不是本协议的请求（魔数=%r），忽略' % magic)
        return None
    if name_len == 0 or name_len > 1024:
        log('文件名长度不合法：%d' % name_len)
        return None
    name_b = recv_exact(sock, name_len)
    if name_b is None:
        return None
    return name_b.decode('utf-8')


def send_error(sock, text):
    """按协议回一个“失败”应答。"""
    msg = text.encode('utf-8')
    sock.sendall(b'0' + struct.pack('!I', len(msg)) + msg)


def serve_client(conn, addr, share_dir, limit_bps, sem):
    """一个客户端一个线程：收文件名 → 查文件 → 分块回传 → 校验用 MD5。"""
    global total_conn, total_bytes
    who = '%s:%s' % addr
    me = threading.current_thread().name
    got_slot = False
    filename = '（还没收到请求）'
    try:
        # ---- 线程并发控制：拿不到“传输名额”就在这里排队，最多同时跑 max_threads 个 ----
        if sem.acquire(timeout=60):
            got_slot = True
            with stat_lock:
                active[me] = '%s 正在下载 %s' % (who, filename)
                n_active = len(active)
            log('%s 已连接（%s）—— 正在传输的线程数：%d' % (who, me, n_active))
        else:
            log('%s 等待空闲线程超时，拒绝服务' % who)
            send_error(conn, '服务器繁忙，请稍后再试')
            return

        filename = recv_request(conn)
        if filename is None:
            log('%s 没有发来合法的文件名请求' % who)
            return

        # 只取文件名部分，去掉路径，防止客户端用 ../../ 下载共享目录以外的文件
        safe_name = os.path.basename(filename.replace('\\', '/'))
        path = os.path.join(share_dir, safe_name)

        if not safe_name or not os.path.isfile(path):
            log('%s 请求的文件不存在：%s' % (who, filename))
            send_error(conn, '服务器上没有文件：%s' % filename)
            return

        size = os.path.getsize(path)
        with stat_lock:
            total_conn += 1
            active[me] = '%s 正在下载 %s' % (who, safe_name)
        log('%s 开始下载 %s（%d 字节，限速：%s）'
            % (who, safe_name, size,
               '%.0f KB/s' % (limit_bps / 1024) if limit_bps else '不限速'))

        # ---- 分块回传：先发应答头（状态+大小），再发内容，最后发 MD5 ----
        t0 = time.time()
        md5 = hashlib.md5()
        sent = 0
        conn.sendall(b'1' + struct.pack('!Q', size))
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                conn.sendall(chunk)         # sendall 保证这一块全部写完
                md5.update(chunk)
                sent += len(chunk)
                if limit_bps:
                    # 限速：按“已经发了多少字节”算出应该花的时间，比实际快就睡一会儿
                    should_take = sent / limit_bps
                    actual = time.time() - t0
                    if should_take > actual:
                        time.sleep(should_take - actual)
        conn.sendall(md5.hexdigest().encode('ascii'))       # 32 字节十六进制文本
        cost = time.time() - t0

        with stat_lock:
            total_bytes += sent
            n = total_conn
        log('%s 下载完成：%s，%d 字节，耗时 %.3f 秒（%.0f KB/s），MD5=%s，累计服务 %d 个请求'
            % (who, safe_name, sent, cost, sent / 1024 / (cost or 1e-6), md5.hexdigest(), n))

    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
        log('%s 传输中断（客户端异常断开）：%s' % (who, e))
    except OSError as e:
        log('%s 出错：%s' % (who, e))
    finally:
        if got_slot:
            sem.release()
        with stat_lock:
            active.pop(me, None)
            n_active = len(active)
        try:
            conn.close()
        except OSError:
            pass
        log('%s 的连接已关闭 —— 正在传输的线程数：%d' % (who, n_active))


def main():
    share_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared')
    port = PORT
    limit_kbps = 0          # 0 = 不限速
    max_threads = 16

    if len(sys.argv) > 1:
        share_dir = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    if len(sys.argv) > 3:
        limit_kbps = int(sys.argv[3])
    if len(sys.argv) > 4:
        max_threads = int(sys.argv[4])

    limit_bps = limit_kbps * 1024 if limit_kbps > 0 else 0
    os.makedirs(share_dir, exist_ok=True)

    sem = threading.BoundedSemaphore(max_threads)           # 限制并发传输的线程数
    workers = []                                            # 记录所有工作线程，退出时 join

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, port))
    s.listen(128)                                           # 排队等待连接的队列长度

    log('多线程文件下载服务端已启动')
    log('共享目录：%s' % share_dir)
    log('监听端口：%d，每连接限速：%s，最大并发线程数：%d'
        % (port, '%.0f KB/s' % (limit_bps / 1024) if limit_bps else '不限速', max_threads))
    log('想加测试文件可以运行：python make_test_files.py')
    log('等待客户端连接……（Ctrl+C 退出）')

    try:
        while True:
            conn, addr = s.accept()
            # 每来一个客户端就创建一个独立线程，主线程立刻回去 accept 下一个
            t = threading.Thread(target=serve_client,
                                 args=(conn, addr, share_dir, limit_bps, sem),
                                 daemon=True)               # 设为守护线程
            t.name = 'worker-%d' % (len(workers) + 1)
            workers.append(t)
            t.start()
    except KeyboardInterrupt:
        log('收到 Ctrl+C，停止接受新的连接，等待 %d 个工作线程结束……' % len(workers))
    finally:
        s.close()
        # 主动 join() 每个工作线程（daemon 线程也可以 join），最多等 5 秒
        alive = 0
        for t in workers:
            if t.is_alive():
                t.join(timeout=5)
            if t.is_alive():
                alive += 1
        log('服务端退出。累计服务 %d 个请求，共发出 %.2f MB 数据；仍有 %d 个线程未结束'
            % (total_conn, total_bytes / 1024 / 1024, alive))


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：download_client.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验五 基于多线程的文件下载 —— 客户端

功能对照：
  (2) 多线程文件下载客户端：向服务端请求指定文件，接收并保存；
      可以用 --jobs N 模拟多个用户“同时”下载（同一文件或不同文件），
      观察并发下载效果，下载完成后对比文件大小和 MD5 验证完整性。

用法：
  python download_client.py [服务器IP] [端口] [文件名]            # 单次下载
  python download_client.py 127.0.0.1 9101 1.txt --jobs 5        # 模拟 5 个用户同时下载 1.txt
  python download_client.py 127.0.0.1 9101 1.txt 2.mp4 --jobs 3  # 3 个用户逐个领不同文件（轮着分）
  默认服务器 127.0.0.1:9101；不带文件名则进入交互模式，输入文件名下载。

每个“模拟用户”就是一个线程：多个线程同时 connect、同时收数据，
这就是并发下载；服务端可以清楚看到多个客户端同时在线。
"""

import hashlib
import os
import socket
import struct
import sys
import threading
import time

CHUNK = 64 * 1024
HEAD = struct.Struct('!4sI')
MAGIC = b'FDL1'

log_lock = threading.Lock()        # 多个线程往屏幕打印，加锁免得输出交错
ok_count = 0                       # 记录成功次数（多线程共享，用锁保护）
fail_count = 0


def log(msg):
    with log_lock:
        print(msg, flush=True)


def recv_exact(sock, n):
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def download_one(host, port, filename, thread_tag=''):
    """下载一个文件：发送请求 → 收应答头 → 按大小收内容 → 校验大小和 MD5。"""
    global ok_count, fail_count
    who = '%s[%s]' % (thread_tag, filename)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        t0 = time.time()
        sock.connect((host, port))
        name_b = filename.encode('utf-8')
        # ① 请求帧：魔数 + 4字节文件名长度 + 文件名
        sock.sendall(HEAD.pack(MAGIC, len(name_b)) + name_b)

        # ② 应答帧：首字节 '1'=找到 / '0'=没找到
        status = recv_exact(sock, 1)
        if status is None:
            log('%s 服务器连接中断' % who)
            return False
        if status == b'0':
            err_len_b = recv_exact(sock, 4)
            if err_len_b is None:
                log('%s 服务器应答不完整' % who)
                return False
            err_len = struct.unpack('!I', err_len_b)[0]
            err = recv_exact(sock, err_len)
            log('%s 下载失败：%s' % (who, err.decode('utf-8') if err else '未知错误'))
            return False
        if status != b'1':
            log('%s 服务器应答异常：%r' % (who, status))
            return False

        # ③ 拿到 8 字节文件大小，按大小收内容（收满为止，保证完整）
        size_b = recv_exact(sock, 8)
        if size_b is None:
            log('%s 服务器应答不完整' % who)
            return False
        size = struct.unpack('!Q', size_b)[0]

        md5 = hashlib.md5()
        got = 0
        save_name = ('%s_%s' % (thread_tag.replace('用户', 'from_'), filename)
                     if thread_tag else filename)
        with open(save_name, 'wb') as f:
            while got < size:
                chunk = sock.recv(min(CHUNK, size - got))
                if not chunk:                       # 中途断开：收到的数据不完整
                    break
                f.write(chunk)
                md5.update(chunk)
                got += len(chunk)
        elapsed = time.time() - t0

        # ④ 收服务端算好的 MD5（32 字节十六进制），与本地比对
        server_md5_b = recv_exact(sock, 32)
        server_md5 = server_md5_b.decode('ascii') if server_md5_b else '（未收到）'
        local_md5 = md5.hexdigest()

        # 验证完整性：文件大小一致 && MD5 一致
        if got == size and server_md5 == local_md5:
            speed = got / 1024 / (elapsed or 1e-6)
            log('%s 下载成功 %d 字节，耗时 %.3f 秒（%.0f KB/s），大小✔ MD5✔'
                % (who, got, elapsed, speed))
            with log_lock:
                ok_count += 1
            return True
        log('%s 校验失败！收到 %d/%d 字节，服务器MD5=%s，本地MD5=%s'
            % (who, got, size, server_md5, local_md5))
        return False
    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, socket.timeout) as e:
        log('%s 网络错误：%s' % (who, e))
        return False
    except OSError as e:
        log('%s 出错：%s' % (who, e))
        return False
    finally:
        try:
            sock.close()
        except OSError:
            pass


def run_concurrent(host, port, filenames, jobs):
    """模拟 jobs 个用户同时下载：每个用户从文件列表里轮流领一个文件任务。"""
    global ok_count, fail_count
    ok_count = 0                     # 每次并发测试前清零，方便统计本次结果
    fail_count = 0

    tasks = []
    for i in range(1, jobs + 1):
        filename = filenames[(i - 1) % len(filenames)]       # 轮流分配，保证“同文件+不同文件”都有
        tasks.append((filename, '用户%d' % i))

    log('=== 模拟 %d 个用户同时下载，任务分配：%s ==='
        % (jobs, ', '.join('%s→%s' % (u, f) for u, f in tasks)))
    begin = time.time()
    threads = []
    for filename, tag in tasks:
        t = threading.Thread(target=download_one, args=(host, port, filename, tag))
        threads.append(t)
        t.start()
    for t in threads:                                        # 主线程 join 所有子线程
        t.join()
    fail_count = jobs - ok_count                             # 没成功的都算失败
    log('=== 全部结束，总耗时 %.3f 秒：成功 %d 个，失败 %d 个 ==='
        % (time.time() - begin, ok_count, fail_count))


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9101
    rest = sys.argv[3:]
    jobs = 1

    # --jobs N：模拟 N 个用户同时下载
    if '--jobs' in rest:
        i = rest.index('--jobs')
        if i + 1 < len(rest):
            try:
                jobs = max(1, int(rest[i + 1]))
            except ValueError:
                print('--jobs 的参数必须是数字')
                sys.exit(1)
            rest = rest[:i] + rest[i + 2:]

    if rest:
        run_concurrent(host, port, rest, jobs)
        return

    # 交互模式：输入文件名下载，输入空行退出
    print('多线程文件下载客户端，目标 %s:%d' % (host, port))
    print('输入文件名回车下载（例如 1.txt），带 --jobs 的并发模式请看文件头的用法说明')
    print('直接回车退出')
    while True:
        try:
            filename = input('要下载的文件名：').strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not filename:
            break
        download_one(host, port, filename)
    print('客户端退出')


if __name__ == '__main__':
    main()
```

</details>

<details>
<summary>打开完整代码：concurrency_test.py</summary>

```python
# -*- coding: utf-8 -*-
"""
实验五(3) 线程并发控制与性能对比实验

这个脚本做四组对照实验，把结果打成表格，可直接抄进实验报告：

  实验 A  串行下载：1 个线程，一个个文件挨着下载（对照基准）
  实验 B  多线程并发下载不同文件：N 个文件各开一个线程同时下
  实验 C  多线程并发下载同一个文件：N 个线程抢同一个文件（服务端要能同时供多个客户端读同一文件）
  实验 D  不同并发度对比：分别用 1、2、4、8 个线程下同一批文件，看耗时和加速比

每个下载任务都校验文件大小和 MD5，只有两项都对才算成功。

用法：
  python concurrency_test.py [服务器IP] [端口] [文件个数] [并发度列表]
  默认：127.0.0.1 9101 4 1,2,4,8

做这个实验时服务端最好加上“每连接限速”，否则本机回环太快（几百 MB/s），
几毫秒就传完，看不出并发的差别。推荐：
  python download_server.py shared 9101 512 16      # 每个连接限速 512KB/s
预期结果：限速下并发下载的总耗时约等于“单个文件耗时”，串行则是“文件数 × 单个耗时”。
"""

import hashlib
import os
import socket
import struct
import sys
import threading
import time

# 直接复用客户端里定好的协议，不用再抄一遍（协议头、魔数、块大小）
from download_client import CHUNK, HEAD, MAGIC, recv_exact

HERE = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(HERE, '_并发测试下载')      # 下载下来的文件放这里，校验完就删掉

print_lock = threading.Lock()


def log(msg):
    with print_lock:
        print(msg, flush=True)


def fetch(host, port, filename, tag=''):
    """下载一个文件并校验完整性，返回结果字典（不打印，交给调用方汇总）。"""
    result = {'file': filename, 'tag': tag, 'ok': False, 'size': 0,
              'seconds': 0.0, 'error': '', 'md5_ok': False}
    save_path = os.path.join(DOWNLOAD_DIR, '%s_%s' % (tag or 'x', filename))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        begin = time.perf_counter()
        sock.connect((host, port))
        name_b = filename.encode('utf-8')
        sock.sendall(HEAD.pack(MAGIC, len(name_b)) + name_b)      # 发请求帧

        status = recv_exact(sock, 1)
        if status is None:
            result['error'] = '服务器无应答'
            return result
        if status == b'0':                                        # 应答 '0'：服务器上没有这个文件
            n_b = recv_exact(sock, 4)
            msg = recv_exact(sock, struct.unpack('!I', n_b)[0]) if n_b else b''
            result['error'] = msg.decode('utf-8', 'ignore') or '下载失败'
            return result

        size = struct.unpack('!Q', recv_exact(sock, 8))[0]        # 8 字节文件大小
        md5 = hashlib.md5()
        got = 0
        with open(save_path, 'wb') as f:
            while got < size:                                     # 按大小收满为止
                chunk = sock.recv(min(CHUNK, size - got))
                if not chunk:
                    break
                f.write(chunk)
                md5.update(chunk)
                got += len(chunk)
        result['seconds'] = time.perf_counter() - begin
        result['size'] = got

        server_md5_b = recv_exact(sock, 32)                       # 服务端发来的 MD5
        server_md5 = server_md5_b.decode('ascii') if server_md5_b else ''
        result['md5_ok'] = (server_md5 == md5.hexdigest())
        # 完整性校验：大小对 + MD5 对
        if got == size and result['md5_ok']:
            result['ok'] = True
        else:
            result['error'] = '大小或MD5不一致（收到 %d/%d 字节）' % (got, size)
        return result
    except OSError as e:
        result['error'] = str(e)
        return result
    finally:
        sock.close()
        # 校验完就把文件删掉，避免测试文件越堆越多（只删本脚本自己下的文件）
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
        except OSError:
            pass


def run_serial(host, port, filenames):
    """实验 A：单线程串行下载。"""
    log('\n===== 实验 A：串行下载（1 个线程，一个个下）=====')
    begin = time.perf_counter()
    oks = 0
    for fn in filenames:
        r = fetch(host, port, fn, 'A串行')
        log('  %-12s %s  %.3f 秒  %s' % (fn, '✔' if r['ok'] else '✘',
                                         r['seconds'], r['error']))
        oks += 1 if r['ok'] else 0
    total = time.perf_counter() - begin
    log('  合计：%d 个文件，总耗时 %.3f 秒，成功 %d/%d'
        % (len(filenames), total, oks, len(filenames)))
    return total, oks


def run_concurrent(host, port, filenames, jobs, title):
    """实验 B/C：jobs 个线程同时下载（文件按轮转分配，可以同一个也可以不同）。"""
    log('\n===== %s =====' % title)
    jobs = max(1, jobs)
    tasks = [filenames[i % len(filenames)] for i in range(jobs)]
    # 用“事件”让所有线程尽量同时开跑，这样测出来的才是真正的并发效果
    start_flag = threading.Event()
    results = [None] * jobs

    def worker(idx, fn):
        start_flag.wait()                       # 等发令枪
        results[idx] = fetch(host, port, fn, '线程%d' % (idx + 1))

    threads = [threading.Thread(target=worker, args=(i, fn)) for i, fn in enumerate(tasks)]
    begin = time.perf_counter()
    for t in threads:
        t.start()
    start_flag.set()                            # 发令：所有线程一起冲
    for t in threads:
        t.join()
    total = time.perf_counter() - begin

    for r in results:
        log('  %-8s %-12s %s  %.3f 秒  %s'
            % (r['tag'], r['file'], '✔' if r['ok'] else '✘', r['seconds'], r['error']))
    oks = sum(1 for r in results if r['ok'])
    speeds = [r['size'] / r['seconds'] / 1024 for r in results if r['ok'] and r['seconds']]
    log('  合计：%d 个并发任务，总耗时 %.3f 秒，成功 %d/%d'
        % (jobs, total, oks, jobs))
    if speeds:
        log('  单个任务平均速度：%.0f KB/s（并发时每个连接的速度）' % (sum(speeds) / len(speeds)))
    return total, oks


def run_jobs_compare(host, port, filenames, levels):
    """实验 D：不同并发度下载同一批文件，做耗时/加速比对照表。"""
    log('\n===== 实验 D：不同并发度对比（每组都下载同样这 %d 个文件）=====' % len(filenames))
    base = None
    table = []
    for jobs in levels:
        # 任务数固定 = 文件个数，只改变“同时干活的线程数”：
        # 线程数比文件数还多时，多出来的线程分不到文件，正好说明并发度受任务数限制
        start_flag = threading.Event()
        results = [0] * jobs

        def worker(idx, limit):
            # 第 idx 个线程负责 files[idx]、files[idx+limit]、… 这些文件
            start_flag.wait()
            oks = 0
            for j in range(idx, len(filenames), limit):
                r = fetch(host, port, filenames[j], 'D%d' % limit)
                oks += 1 if r['ok'] else 0
            results[idx] = oks

        workers = [threading.Thread(target=worker, args=(i, jobs)) for i in range(jobs)]
        begin = time.perf_counter()
        for t in workers:
            t.start()
        start_flag.set()                        # 所有线程一起开跑
        for t in workers:
            t.join()
        total = time.perf_counter() - begin
        ok = sum(results)
        if base is None:
            base = total                        # 1 个线程（串行）的耗时作为基准
        table.append((jobs, total, total / len(filenames), base / total, ok))

    log('  %-12s %-13s %-16s %-10s %s'
        % ('并发线程数', '总耗时(秒)', '平均每文件(秒)', '加速比', '成功/总数'))
    log('  ' + '-' * 64)
    for jobs, total, avg, speedup, ok in table:
        log('  %-14d %-13.3f %-16.3f %-10s %d/%d'
            % (jobs, total, avg, '%.2fx' % speedup, ok, len(filenames)))
    log('  说明：加速比 = 串行(1 线程)耗时 ÷ 当前并发度耗时。')
    log('        并发度没超过文件个数时，加速比 ≈ 并发线程数（4 线程约 4 倍）；')
    log('        线程数超过文件个数后就不会再快了，因为多出来的线程没有文件可分。')
    log('        同时也要受服务端“最大并发线程数”和“每连接限速”的限制。')


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9101
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    levels = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else [1, 2, 4, 8]

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    filenames = ['test%d.bin' % i for i in range(1, count + 1)]

    print('=' * 70)
    print('实验五(3) 线程并发控制与性能对比实验')
    print('服务端：%s:%d   测试文件：%s' % (host, port, ', '.join(filenames)))
    print('=' * 70)

    # 先探一下服务器有没有测试文件，没有就直接给出解决办法，别浪费时间
    probe = fetch(host, port, filenames[0], 'probe')
    if not probe['ok']:
        print('\n无法下载 %s：%s' % (filenames[0], probe['error']))
        print('请检查：')
        print('  1) 服务端已经启动：python download_server.py')
        print('  2) 服务端共享目录里有测试文件：python make_test_files.py')
        print('  3) IP / 端口没写错（当前 %s:%d）' % (host, port))
        sys.exit(1)
    print('\n连通性正常：%s 下载成功，%.3f 秒（%.0f KB/s）—— 这个速度就是“单个文件”的基准'
          % (filenames[0], probe['seconds'], probe['size'] / probe['seconds'] / 1024))

    run_serial(host, port, filenames)
    run_concurrent(host, port, filenames, count,
                   '实验 B：%d 个线程并发下载 %d 个不同文件' % (count, count))
    run_concurrent(host, port, filenames[:1], count,
                   '实验 C：%d 个线程并发下载同一个文件（%s）' % (count, filenames[0]))
    run_jobs_compare(host, port, filenames, levels)

    print('\n提示：如果并发加速不明显，说明瓶颈不在并发数上。')
    print('     可以在服务端加“每连接限速”再看一次，效果会非常直观：')
    print('     python download_server.py shared 9101 512 16')
    print('完成，测试下载目录 %s 里校验后的文件已自动删除。' % DOWNLOAD_DIR)


if __name__ == '__main__':
    main()
```

</details>
