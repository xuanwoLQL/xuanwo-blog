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
