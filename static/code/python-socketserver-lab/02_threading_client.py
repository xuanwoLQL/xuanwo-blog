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
