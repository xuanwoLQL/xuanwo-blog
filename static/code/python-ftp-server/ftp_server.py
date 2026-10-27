# -*- coding: utf-8 -*-
"""
基于 Socket 编程的 FTP 服务器

要求对照：
  · 基于 socketserver 实现并发 TCP 服务器，可同时处理多个客户端连接
      → socketserver.ThreadingTCPServer，每个连接自动一个线程
  · 用户账号的加密认证（哈希密码存储与验证）
      → users.json 存的是“随机盐 + PBKDF2-HMAC-SHA256(12 万次迭代)”的摘要，不存明文；
        用 hmac.compare_digest 做定时安全比较；连续错 3 次直接断开
  · 用户家目录隔离（每个用户只能访问自己的专属目录）
      → 每个用户的家目录是 ftp_root/<用户名>，客户端给的路径先 normpath 规范化，
        再检查是否还在家目录里面，越界（../、绝对路径、软链接绕过）一律拒绝
  · 完整支持 PUT（上传）、GET（下载）、LS（列目录）
  · 能处理客户端的正常与异常断开
      → QUIT 正常退出、直接关窗口/拔网线（ConnectionResetError/ConnectionAborted）都能处理，
        并用 try/except/finally 保证线程退出、连接关闭、日志记录
  · 文件传输完整性
      → 下载：服务端先算好 MD5 告诉客户端，客户端边收边算、收完比对；
        上传：客户端先声明 MD5，服务端落盘后自己算一遍比对，不一致就删掉临时文件并报错

通信协议见 ftp_protocol.py（1 字节类型 + 8 字节长度 + 负载，解决粘包/分包）。

用法：
    python make_users.py          # 第一次先执行，生成账号
    python ftp_server.py [监听地址] [端口] [数据根目录]
    默认 0.0.0.0:2121，数据根目录是脚本旁边的 ftp_root
"""

import hashlib
import json
import os
import socket
import socketserver
import sys
import threading
import time

from ftp_protocol import (CHUNK, TYPE_END, TYPE_FILE, human_size, md5_file,
                          recv_frame, recv_json, send_chunk, send_end, send_json,
                          verify_password)

HERE = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(HERE, 'users.json')
FTP_ROOT = os.path.join(HERE, 'ftp_root')

HOST, PORT = '0.0.0.0', 2121
MAX_LOGIN_TRY = 3                     # 连续输错几次就断开连接
MAX_UPLOAD = 2 * 1024 * 1024 * 1024   # 单个文件最大 2GB，防止把磁盘写满
SOCK_TIMEOUT = 300                    # 客户端 5 分钟没动静就断开，避免线程一直挂着

log_lock = threading.Lock()           # 多线程打印日志，加锁避免输出交错
stat_lock = threading.Lock()
online = {}                           # 用户名 -> 信息（当前在线用户）
total_login = 0                       # 累计成功登录次数


def log(msg):
    with log_lock:
        print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def load_users():
    """读取账号文件。"""
    if not os.path.exists(USERS_FILE):
        print('找不到账号文件：%s' % USERS_FILE)
        print('请先运行：python make_users.py')
        sys.exit(1)
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def safe_path(home, name):
    """把客户端给的路径转换到家目录下的绝对路径。

    返回 None 表示越界（想访问家目录以外的文件），一律拒绝。
    这是家目录隔离的关键：先 normpath 把 ../ 和 // 都规范化掉，再看结果在不在家目录里。
    """
    name = (name or '').replace('\\', '/')
    # 绝对路径（/etc/passwd、D:/Windows/...）直接拒绝：我们只接受相对自己家目录的路径
    if name.startswith('/') or ':' in name:
        return None
    target = os.path.normpath(os.path.join(home, name))
    if target == home or target.startswith(home + os.sep):
        return target
    return None


class FtpHandler(socketserver.StreamRequestHandler):
    """一个客户端连接 = 一个线程。"""

    timeout = SOCK_TIMEOUT          # socketserver 会把这个值设到连接套接字上

    def handle(self):
        global total_login
        ip = self.client_address[0]
        user = None
        try:
            user = self.do_login()
            if user is None:
                return                              # 没登录成功（超次数/断开），直接结束
            home = self.home
            log('%s@%s 登录成功，家目录：%s' % (user, ip, home))
            self.command_loop(user, home)
        except socket.timeout:
            log('%s 长时间没有操作，服务器主动断开' % (user or ip))
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            # 客户端直接关窗口/拔网线会走到这里，服务器不能因此崩溃
            log('%s（%s）异常断开：%s' % (user or '未登录客户端', ip, e))
        except ValueError as e:
            log('%s（%s）发来的数据不符合协议：%s' % (user or '未登录客户端', ip, e))
        except Exception as e:
            log('%s（%s）处理出错：%r' % (user or '未登录客户端', ip, e))
        finally:
            # 不管怎么退出，都要把在线状态清掉、把连接关掉
            if user:
                with stat_lock:
                    online.pop(user, None)
                    n = len(online)
                log('%s@%s 已下线（当前在线用户：%s）'
                    % (user, ip, '、'.join(online) if online else '无'))
            else:
                log('%s 的连接已关闭' % ip)
            try:
                self.request.close()
            except OSError:
                pass

    # ---------------- 登录 ----------------
    def do_login(self):
        """处理登录：最多 3 次机会，密码用哈希校验。"""
        global total_login
        ip = self.client_address[0]
        for attempt in range(1, MAX_LOGIN_TRY + 1):
            msg = recv_json(self.request)
            if msg is None:
                log('%s 还没登录就断开连接了' % ip)
                return None
            if msg.get('cmd') != 'login':
                send_json(self.request, {'ok': False, 'msg': '请先登录'})
                continue

            user = (msg.get('user') or '').strip()
            password = msg.get('pass') or ''
            rec = USERS.get(user)
            # 用户名不存在时也要走一遍哈希计算，避免用“响应快慢”探测哪些用户名存在
            ok = False
            if rec:
                ok = verify_password(password, rec['salt'], rec['hash'])
            else:
                verify_password(password, '00' * 16, '00' * 32)

            if ok:
                home = os.path.join(FTP_ROOT, user)
                os.makedirs(home, exist_ok=True)
                welcome = os.path.join(home, '欢迎.txt')
                if not os.path.exists(welcome):        # 第一次登录给个欢迎文件，免得目录是空的
                    with open(welcome, 'w', encoding='utf-8') as f:
                        f.write('%s 你好，这是你的专属目录，只有你自己能看到。\n' % user)
                with stat_lock:
                    total_login += 1
                    online[user] = {'ip': ip, 'time': time.time()}
                    n = len(online)
                self.home = home
                send_json(self.request, {
                    'ok': True,
                    'msg': '登录成功，欢迎 %s！' % user,
                    'user': user,
                    'online': n,
                })
                log('收到 %s@%s 的登录请求，口令校验通过（当前在线 %d 人）' % (user, ip, n))
                return user

            log('收到 %s@%s 的登录请求，口令校验失败（第 %d/%d 次）'
                % (user or '空用户名', ip, attempt, MAX_LOGIN_TRY))
            if attempt == MAX_LOGIN_TRY:
                send_json(self.request, {'ok': False,
                                         'msg': '用户名或密码错误，尝试次数过多，断开连接'})
                return None
            send_json(self.request, {'ok': False,
                                     'msg': '用户名或密码错误（第 %d/%d 次，共 %d 次机会）'
                                            % (attempt, MAX_LOGIN_TRY, MAX_LOGIN_TRY)})
        return None

    # ---------------- 命令循环 ----------------
    def command_loop(self, user, home):
        while True:
            msg = recv_json(self.request)
            if msg is None:
                log('%s 断开了连接（没有发 QUIT，属于异常断开）' % user)
                return
            cmd = msg.get('cmd')
            if cmd == 'ls':
                self.do_ls(user, home, msg)
            elif cmd == 'get':
                self.do_get(user, home, msg)
            elif cmd == 'put':
                self.do_put(user, home, msg)
            elif cmd == 'quit':
                send_json(self.request, {'ok': True, 'msg': '再见！'})
                log('%s 正常退出（QUIT）' % user)
                return
            else:
                send_json(self.request, {'ok': False, 'msg': '不支持的命令：%s' % cmd})

    # ---------------- LS 列目录 ----------------
    def do_ls(self, user, home, msg):
        rel = msg.get('path', '') or ''
        path = safe_path(home, rel)
        if path is None or not os.path.isdir(path):
            log('%s 请求列目录 %r —— 越界或不存在，已拒绝' % (user, rel))
            send_json(self.request, {'ok': False, 'msg': '目录不存在或无权访问'})
            return

        items = []
        try:
            for entry in os.scandir(path):
                try:
                    st = entry.stat()
                except OSError:
                    continue
                items.append({
                    'name': entry.name,
                    'is_dir': entry.is_dir(),
                    'size': 0 if entry.is_dir() else st.st_size,
                    'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime)),
                })
        except OSError as e:
            send_json(self.request, {'ok': False, 'msg': '读取目录失败：%s' % e})
            return

        # 目录排前面，然后按名字排序，好看
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        # 客户端传上来的是相对家目录的路径，回显时统一用 '/' 开头
        show_path = '/' + rel.replace('\\', '/').strip('/')
        send_json(self.request, {'ok': True, 'path': show_path, 'files': items})
        log('%s 列目录 %s，共 %d 项' % (user, show_path, len(items)))

    # ---------------- GET 下载 ----------------
    def do_get(self, user, home, msg):
        name = msg.get('name', '')
        path = safe_path(home, name)
        if path is None or not os.path.isfile(path):
            log('%s 请求下载 %r —— 越界或不存在，已拒绝' % (user, name))
            send_json(self.request, {'ok': False, 'msg': '文件不存在或无权访问'})
            return

        size = os.path.getsize(path)
        digest = md5_file(path)          # 先把 MD5 算好，客户端一拿到就能知道该校验成什么值
        send_json(self.request, {'ok': True, 'name': os.path.basename(path),
                                 'size': size, 'md5': digest})
        log('%s 开始下载 %s（%s），MD5=%s' % (user, name, human_size(size), digest))

        t0 = time.time()
        sent = 0
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                send_chunk(self.request, chunk)      # 分块发送，多大文件都不占内存
                sent += len(chunk)
        send_end(self.request)                       # 结束标记
        cost = time.time() - t0
        log('%s 下载完成 %s：%s，耗时 %.3f 秒（%.1f KB/s）'
            % (user, name, human_size(sent), cost, sent / 1024 / (cost or 1e-6)))

    # ---------------- PUT 上传 ----------------
    def recv_file_body(self, tmp_path, size):
        """接收客户端上传的文件内容，一直收到结束标记为止。

        重要：不管中途出了什么错（比如服务器磁盘写不进去），都要把客户端这一轮
        发来的数据全部收完再返回 —— 否则剩下的数据会留在缓冲区里被当成下一条命令，
        整个连接的数据流就“错位”了（这就是粘包问题的另一种体现）。
        返回 (失败原因, 收到字节数, MD5)；失败原因为空表示收的过程正常。
        """
        f = None
        fail_reason = None
        try:
            try:
                f = open(tmp_path, 'wb')
            except OSError as e:
                fail_reason = '服务器无法创建文件：%s' % e
                log('打开临时文件失败：%s（继续把这一轮数据收完再报错）' % e)

            got = 0
            md5 = hashlib.md5()
            while True:
                type_byte, payload = recv_frame(self.request)
                if type_byte is None:                 # 客户端断开，没法继续收了
                    return fail_reason or '上传途中客户端断开', got, md5.hexdigest()
                if type_byte == TYPE_FILE:
                    got += len(payload)
                    md5.update(payload)               # 校验用的哈希一定要算，写不写盘都要算
                    if got > size:
                        if fail_reason is None:
                            fail_reason = '客户端发送的数据(%d 字节)超过了声明的大小(%d 字节)' % (got, size)
                            if f:
                                f.close()
                                f = None
                    elif f is not None:
                        f.write(payload)
                elif type_byte == TYPE_END:
                    break
            return fail_reason, got, md5.hexdigest()
        finally:
            if f is not None:
                f.close()

    def do_put(self, user, home, msg):
        name = msg.get('name', '')
        size = int(msg.get('size') or 0)
        client_md5 = (msg.get('md5') or '').lower()
        overwrite = bool(msg.get('overwrite'))

        path = safe_path(home, name)
        if path is None:
            log('%s 试图上传到越界路径 %r，已拒绝' % (user, name))
            send_json(self.request, {'ok': False, 'msg': '路径不合法（只能用相对自己家目录的路径）'})
            return
        if size <= 0 or size > MAX_UPLOAD:
            send_json(self.request, {'ok': False,
                                     'msg': '文件大小不合法（单个文件不能超过 %s）'
                                            % human_size(MAX_UPLOAD)})
            return
        if not os.path.isdir(os.path.dirname(path)):
            send_json(self.request, {'ok': False, 'msg': '目标目录不存在'})
            return
        if os.path.isdir(path):
            send_json(self.request, {'ok': False, 'msg': '同名目录已存在，不能覆盖'})
            return
        if os.path.exists(path) and not overwrite:
            send_json(self.request, {'ok': False, 'need_confirm': True,
                                     'msg': '服务器上已有同名文件 %s' % os.path.basename(path)})
            return

        # 先收到临时文件，全部校验通过再改名成正式文件 —— 中途失败不会留下半截文件
        tmp_path = path + '.part'
        send_json(self.request, {'ok': True, 'msg': '可以上传'})
        log('%s 开始上传 %s（%s），声明的 MD5=%s'
            % (user, name, human_size(size), client_md5 or '（未提供）'))

        t0 = time.time()
        fail_reason, got, local_md5 = self.recv_file_body(tmp_path, size)
        cost = time.time() - t0

        def discard(reason):
            """删除临时文件并把这个失败原因告诉客户端。"""
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            log('%s 上传 %s 失败：%s（临时文件已删除）' % (user, name, reason))
            send_json(self.request, {'ok': False, 'msg': '上传失败：%s' % reason})

        if fail_reason:
            discard(fail_reason)
            return
        if got != size:                       # 完整性校验 1：字节数
            discard('文件大小校验失败（收到 %d 字节，声明 %d 字节）' % (got, size))
            return
        if client_md5 and local_md5 != client_md5:   # 完整性校验 2：MD5
            discard('MD5 校验失败（客户端说 %s，服务器算是 %s）' % (client_md5, local_md5))
            return

        os.replace(tmp_path, path)            # 校验通过，原子改名成正式文件
        log('%s 上传完成 %s：%s，耗时 %.3f 秒（%.1f KB/s），MD5=%s（校验通过）'
            % (user, name, human_size(got), cost, got / 1024 / (cost or 1e-6), local_md5))
        send_json(self.request, {'ok': True, 'msg': '上传成功，文件完整',
                                 'name': os.path.basename(path),
                                 'size': got, 'md5': local_md5})


class FtpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True               # 主线程退出时工作线程一起退出


if __name__ == '__main__':
    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])
    if len(sys.argv) > 3:
        FTP_ROOT = os.path.abspath(sys.argv[3])

    USERS = load_users()
    os.makedirs(FTP_ROOT, exist_ok=True)

    print('=' * 66)
    print('FTP 服务器已启动')
    print('  监听地址：%s:%d' % (HOST, PORT))
    print('  数据根目录：%s（每个用户一个子目录，互相隔离）' % FTP_ROOT)
    print('  账号：%s（密码以“盐+哈希”形式存在 users.json，日志里不会出现明文）'
          % '、'.join(USERS))
    print('  客户端：python ftp_client.py')
    print('=' * 66)

    try:
        with FtpServer((HOST, PORT), FtpHandler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务器退出')
        with stat_lock:
            print('本次运行共成功登录 %d 次' % total_login)
