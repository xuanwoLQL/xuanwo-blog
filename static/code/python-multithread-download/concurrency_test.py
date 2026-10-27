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
