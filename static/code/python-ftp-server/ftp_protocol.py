# -*- coding: utf-8 -*-
"""
FTP 作业公共协议模块 —— 服务端和客户端都用它，保证两边的协议完全一致

自定义应用层协议（解决 TCP 粘包/分包）：
    每一帧 = 1字节类型 + 8字节负载长度(大端) + 负载
      类型 b'J' —— JSON 控制消息（登录、列目录、各种命令应答），负载是 UTF-8 的 JSON
      类型 b'F' —— 文件数据块，负载是文件的一段二进制内容（默认 64KB 一块）
      类型 b'E' —— 传输结束标记，负载为空

为什么这样设计：
  · 每帧前面都有“长度”，接收方先读固定 9 字节的帧头，知道这帧有多少字节，
    再精确地收满这么多字节 —— 所以既不会把两帧粘在一起（粘包），
    也不会把一帧只读了一半（分包）。
  · 控制信息全部用 JSON，以后要加新命令只要加一个 "cmd" 名字，不用改协议本身。

密码存储用的也是这个模块里的函数：盐 + PBKDF2-HMAC-SHA256 迭代哈希，
服务器上只存哈希，不存明文密码。
"""

import hashlib
import json
import os
import secrets
import struct

# ---------------- 协议常量 ----------------
TYPE_JSON = b'J'          # 控制消息
TYPE_FILE = b'F'          # 文件数据块
TYPE_END = b'E'           # 传输结束

HEAD = struct.Struct('!cQ')       # !c = 1 字节字符，!Q = 8 字节无符号大端整数
HEAD_LEN = HEAD.size              # = 9
CHUNK = 64 * 1024                 # 文件分块大小 64KB
MAX_FRAME = 16 * 1024 * 1024      # 单帧最大 16MB，防止对方发个乱码长度把内存吃爆

# ---------------- 口令哈希参数 ----------------
PBKDF2_ITERATIONS = 120000
SALT_BYTES = 16


# ==================== 收发帧 ====================
def send_frame(sock, type_byte, payload=b''):
    """发一帧：帧头（类型 + 长度）+ 负载。用 sendall 保证全部写完。"""
    sock.sendall(HEAD.pack(type_byte, len(payload)) + payload)


def send_json(sock, obj):
    """发一条 JSON 控制消息。ensure_ascii=False 让中文按 UTF-8 发，节省字节。"""
    payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    send_frame(sock, TYPE_JSON, payload)


def send_chunk(sock, data):
    """发一块文件内容。"""
    send_frame(sock, TYPE_FILE, data)


def send_end(sock):
    """发传输结束标记。"""
    send_frame(sock, TYPE_END, b'')


def recv_exact(sock, n):
    """收满 n 个字节；对方提前关闭连接则返回 None。"""
    buf = b''
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def recv_frame(sock):
    """收一帧，返回 (类型, 负载)；对方关闭连接时返回 (None, None)。"""
    head = recv_exact(sock, HEAD_LEN)
    if head is None:
        return None, None
    type_byte, length = HEAD.unpack(head)
    if length > MAX_FRAME:
        raise ValueError('收到不合理的帧长度：%d 字节' % length)
    payload = b''
    if length:
        payload = recv_exact(sock, length)
        if payload is None:
            return None, None
    return type_byte, payload


def recv_json(sock):
    """收一条 JSON 控制消息，返回字典；连接结束返回 None。"""
    type_byte, payload = recv_frame(sock)
    if type_byte is None:
        return None
    if type_byte != TYPE_JSON:
        raise ValueError('期待 JSON 控制帧，收到的却是 %r' % type_byte)
    return json.loads(payload.decode('utf-8'))


# ==================== 文件工具 ====================
def md5_file(path, progress=None):
    """分块算文件的 MD5（大文件也不会占满内存）。"""
    md5 = hashlib.md5()
    total = os.path.getsize(path)
    done = 0
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            md5.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    return md5.hexdigest()


def human_size(n):
    """把字节数格式化成人看得懂的形式，例如 1536 -> '1.5 KB'。"""
    if n < 1024:
        return '%d B' % n
    value = float(n)
    for unit in ('KB', 'MB', 'GB', 'TB'):
        value /= 1024.0
        if value < 1024 or unit == 'TB':
            return '%.1f %s' % (value, unit)


# ==================== 口令哈希 ====================
def new_salt():
    """生成随机盐（每个用户一个，防止彩虹表）。"""
    return secrets.token_hex(SALT_BYTES)


def hash_password(password, salt_hex):
    """用 盐 + PBKDF2-HMAC-SHA256 迭代哈希 算出口令摘要，返回十六进制字符串。"""
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                             bytes.fromhex(salt_hex), PBKDF2_ITERATIONS)
    return dk.hex()


def verify_password(password, salt_hex, expect_hash):
    """校验口令：算一遍再和存起来的哈希对比。用 compare_digest 做定时安全比较，防时序攻击。"""
    return secrets.compare_digest(hash_password(password, salt_hex), expect_hash)
