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
