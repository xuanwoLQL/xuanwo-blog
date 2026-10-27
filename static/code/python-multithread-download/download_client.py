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
