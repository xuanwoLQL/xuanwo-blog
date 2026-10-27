# -*- coding: utf-8 -*-
"""
实验 1.4 混合服务器 —— 同时支持 TCP 和 UDP

要求对照：
  (1) 创建一个同时支持 TCP 和 UDP 的服务器
  (2) TCP 部分：实现简单的文件传输功能（接收客户端上传的文件并保存）
      UDP 部分：实现时间同步功能（响应客户端的时间请求）
  (3) 用多线程分别运行 TCPServer 和 UDPServer

为什么要用两个线程：serve_forever() 是“死循环”，一个线程里只能跑一个服务器，
    所以主线程跑 TCP 的 serve_forever()，另开一个线程跑 UDP 的 serve_forever()，
    两个服务器就在不同端口上同时工作了。

TCP 上传文件的协议（自己定的，用长度前缀解决粘包）：
    客户端 → 服务端：b'UPLD' + 4字节文件名长度(大端) + 文件名(UTF-8)
                     + 8字节文件大小(大端) + 文件内容
    服务端 → 客户端：b'OK' + 4字节MD5长度 + MD5文本(十六进制)     上传成功
                     b'ER' + 4字节原因长度 + 原因文本            上传失败
先发“文件名长度”再发文件名、先发“文件大小”再发内容，接收方就知道该收多少字节，
既不会把两次发送粘在一起，也不会把一条消息读了一半。

UDP 时间同步的协议：
    客户端 → 服务端：b'TIME|<客户端本地时间字符串>'
    服务端 → 客户端：b'TIME|<服务器时间字符串>|<服务器unix时间戳>'
    客户端用 t0(发送前)、t3(收到后) 算出往返时延和时钟偏差，完成“校时”。
"""

import hashlib
import os
import socketserver
import struct
import threading
import time

TCP_HOST, TCP_PORT = '0.0.0.0', 8003
UDP_HOST, UDP_PORT = '0.0.0.0', 8004

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
MAX_FILE = 512 * 1024 * 1024        # 最大 512MB，防止乱传把磁盘写满

log_lock = threading.Lock()         # 两个服务器在不同线程里打印日志，加锁免得输出交错


def log(msg):
    with log_lock:
        print(msg, flush=True)


def time_str(ts=None):
    """把时间戳格式化成 '2026-10-18 10:20:30.123'"""
    ts = time.time() if ts is None else ts
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)) + '.%03d' % int((ts % 1) * 1000)


def recv_exact(sock, n):
    """收满 n 个字节。TCP 是字节流，一次 recv 可能只收到一部分，所以要循环收。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None              # 对方关闭了连接
        buf += part
    return buf


# ====================== TCP 部分：文件上传 ======================
class UploadHandler(socketserver.BaseRequestHandler):
    """TCP 处理类：收一个文件，保存到 uploads 目录。"""

    def handle(self):
        sock = self.request
        addr = '%s:%s' % self.client_address
        log('[TCP] %s 已连接' % addr)
        try:
            head = recv_exact(sock, 4)
            if head is None:
                return
            if head != b'UPLD':                          # 校验“魔数”，确认发的确实是上传请求
                log('[TCP] %s 发的不是上传请求，断开' % addr)
                return

            name_len_b = recv_exact(sock, 4)
            name_len = struct.unpack('!I', name_len_b)[0]
            if name_len > 255:
                return
            name = recv_exact(sock, name_len).decode('utf-8')
            size = struct.unpack('!Q', recv_exact(sock, 8))[0]

            # 只管文件名，去掉路径部分，防止客户端用 ../../ 写到别的目录（目录穿越）
            safe_name = os.path.basename(name.replace('\\', '/'))
            if not safe_name or size > MAX_FILE:
                reply = b'ER' + struct.pack('!I', 12) + '文件名或大小不合法'.encode('utf-8')
                sock.sendall(reply)
                return

            save_path = os.path.join(SAVE_DIR, safe_name)
            log('[TCP] %s 要上传 %s（%d 字节），开始接收……' % (addr, safe_name, size))

            # 按大小收文件，一边收一边算 MD5
            md5 = hashlib.md5()
            got = 0
            with open(save_path, 'wb') as f:
                while got < size:
                    chunk = sock.recv(min(64 * 1024, size - got))
                    if not chunk:
                        log('[TCP] %s 上传中途断开，已收到 %d/%d 字节' % (addr, got, size))
                        return
                    f.write(chunk)
                    md5.update(chunk)
                    got += len(chunk)

            digest = md5.hexdigest()
            log('[TCP] %s 上传完成：%s，%d 字节，MD5=%s' % (addr, safe_name, got, digest))
            # 告诉客户端“收到了、存好了、这是校验值”，客户端可以拿去比对
            sock.sendall(b'OK' + struct.pack('!I', len(digest)) + digest.encode('utf-8'))

        except (ConnectionResetError, ConnectionAbortedError) as e:
            log('[TCP] %s 异常断开：%s' % (addr, e))
        except OSError as e:
            log('[TCP] %s 出错：%s' % (addr, e))
        finally:
            log('[TCP] %s 的连接已关闭' % addr)


# ====================== UDP 部分：时间同步 ======================
class TimeHandler(socketserver.BaseRequestHandler):
    """UDP 处理类：收到时间请求就回服务器时间。"""

    def handle(self):
        data, sock = self.request                     # UDP 的 self.request 是 (数据, 套接字)
        text = data.decode('utf-8', 'ignore')
        client_addr = '%s:%s' % self.client_address

        if not text.startswith('TIME'):
            # 注意：中文要写成 str 再 encode('utf-8')，不能直接写 b'…中文…'，
            # bytes 字面量里只能放 ASCII 字符，否则整个文件语法错误
            hint = 'ERR|请发送 TIME|<你的时间> 这样的请求'
            sock.sendto(hint.encode('utf-8'), self.client_address)
            return

        client_time = text.split('|', 1)[1] if '|' in text else '（未提供）'
        now = time.time()
        log('[UDP] 收到 %s 的时间请求（它说现在 %s），回复服务器时间 %s'
            % (client_addr, client_time, time_str(now)))
        reply = 'TIME|%s|%.6f' % (time_str(now), now)
        sock.sendto(reply.encode('utf-8'), self.client_address)


# ====================== 启动：两个服务器各跑一个线程 ======================
class MyTCPServer(socketserver.ThreadingTCPServer):
    """文件上传可能有多个客户端同时传，所以 TCP 这边用多线程版本。"""
    allow_reuse_address = True
    daemon_threads = True


class MyUDPServer(socketserver.UDPServer):
    allow_reuse_address = True


def run_udp():
    with MyUDPServer((UDP_HOST, UDP_PORT), TimeHandler) as server:
        log('UDP 时间同步服务器已启动，监听 %s:%d' % (UDP_HOST, UDP_PORT))
        server.serve_forever()


def run_tcp():
    with MyTCPServer((TCP_HOST, TCP_PORT), UploadHandler) as server:
        log('TCP 文件上传服务器已启动，监听 %s:%d，文件保存到：%s'
            % (TCP_HOST, TCP_PORT, SAVE_DIR))
        server.serve_forever()


if __name__ == '__main__':
    os.makedirs(SAVE_DIR, exist_ok=True)

    # 用多线程分别运行 TCPServer 和 UDPServer：UDP 跑在子线程，TCP 跑在主线程
    udp_thread = threading.Thread(target=run_udp, daemon=True)
    udp_thread.start()

    print('测试：')
    print('  python 04_hybrid_client.py time                 # UDP 部分：时间同步')
    print('  python 04_hybrid_client.py upload 文件名         # TCP 部分：上传文件')
    try:
        run_tcp()
    except KeyboardInterrupt:
        print('\n混合服务器退出')
