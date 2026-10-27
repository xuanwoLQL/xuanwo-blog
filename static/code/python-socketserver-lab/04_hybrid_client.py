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
