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
