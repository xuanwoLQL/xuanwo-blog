# -*- coding: utf-8 -*-
"""
聊天室公共协议模块（服务端和客户端共用）

作用：把“收发一条完整消息”的细节封装起来，避免 TCP 粘包。

自定义协议（跟课本 4-3c / 6 的“长度前缀 + 消息体”一致）：
    一条消息 = 4 字节长度(网络字节序, struct '!I') + 消息体(UTF-8 的 JSON)
收的时候先读 4 字节拿到长度，再按这个长度把消息体读满，
所以两条消息绝不会粘在一起，也不会只读一半。
"""

import struct
import json

HEAD_LEN = 4                 # 协议头固定 4 字节
MAX_LEN = 1024 * 1024        # 消息体最大 1MB，防止异常长度导致内存爆炸


def send_msg(sock, msg_dict):
    """发送一条消息，msg_dict 会被序列化成 JSON。"""
    body = json.dumps(msg_dict, ensure_ascii=False).encode('utf-8')
    head = struct.pack('!I', len(body))   # '!I' = 大端 4 字节无符号整数
    sock.sendall(head + body)


def recv_all(sock, n):
    """一次 recv 不一定收满 n 字节，循环收，收满为止；对端关闭时返回 None。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def recv_msg(sock):
    """接收一条完整的消息，返回字典；对端正常关闭时返回 None。"""
    head = recv_all(sock, HEAD_LEN)
    if head is None:
        return None
    length = struct.unpack('!I', head)[0]
    if length > MAX_LEN:
        return None
    body = recv_all(sock, length)
    if body is None:
        return None
    return json.loads(body.decode('utf-8'))
