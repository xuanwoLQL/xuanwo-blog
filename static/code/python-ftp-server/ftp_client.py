# -*- coding: utf-8 -*-
"""
基于 Socket 编程的 FTP 客户端（tkinter 图形界面）

界面上的东西对照实验要求：
  · 文本框：服务器 IP、端口、用户名、密码（密码用 * 显示）
  · 按钮：连接、断开、刷新列表(LS)、上传(PUT)、下载(GET)、返回上级
  · 列表控件：服务器文件列表（名称 / 大小 / 修改时间 / 类型），双击目录进目录、双击文件下载
  · 进度条 + 日志区：上传下载时实时显示百分比、速度、剩余时间这些状态

线程模型（这是 GUI + 网络编程最容易出错的地方）：
  · 主线程只干一件事：跑 tkinter 的 mainloop()，所有控件操作都在主线程做；
  · 网络操作（连接、登录、列目录、传文件）全都放到 worker 线程里做，
    否则 recv() 一阻塞，窗口就“未响应”了；
  · worker 线程不能直接改控件（tkinter 不是线程安全的），
    所以它把“要显示什么”丢进 queue.Queue，由主线程用 after() 定时取出来更新界面。
    代码里所有界面刷新都走 self.ui_queue，就是这个原因。

用法：
    python ftp_client.py            # 先确保服务端 ftp_server.py 已经启动
"""

import hashlib
import os
import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from ftp_protocol import (CHUNK, TYPE_END, TYPE_FILE, human_size, md5_file,
                          recv_frame, recv_json, send_chunk, send_end, send_json)

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = '2121'
SOCK_TIMEOUT = 15           # 每次收发的超时时间（秒），避免界面无限等待


class FtpClientGUI:
    def __init__(self, root):
        self.root = root
        self.sock = None
        self.connected = False
        self.busy = False              # 有传输在跑的时候，禁止再发别的命令
        self.cwd = ''                  # 服务器上当前目录（相对自己家目录，'' 表示家目录）
        self.items = []                # 当前目录下的文件列表
        self.user = ''
        self.ui_queue = queue.Queue()  # worker 线程 → 主线程 的“信箱”

        root.title('FTP 客户端 —— 基于 Socket 编程')
        root.geometry('900x640')
        root.minsize(820, 560)

        self.build_ui()
        self.update_buttons()
        self.log('欢迎使用 FTP 客户端。请填写服务器地址和账号后点击“连接”。')
        self.log('提示：服务端第一次运行前要先执行 python make_users.py 生成账号。')
        self.root.after(80, self.pump_ui_queue)     # 定时把 worker 的消息搬到界面上
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    # ==================== 界面 ====================
    def build_ui(self):
        pad = {'padx': 4, 'pady': 4}

        # ---------- 顶部：连接区 ----------
        top = tk.LabelFrame(self.root, text='服务器连接', padx=6, pady=6)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))

        tk.Label(top, text='服务器IP：').grid(row=0, column=0, **pad)
        self.ent_host = tk.Entry(top, width=14)
        self.ent_host.insert(0, DEFAULT_HOST)
        self.ent_host.grid(row=0, column=1, **pad)

        tk.Label(top, text='端口：').grid(row=0, column=2, **pad)
        self.ent_port = tk.Entry(top, width=7)
        self.ent_port.insert(0, DEFAULT_PORT)
        self.ent_port.grid(row=0, column=3, **pad)

        tk.Label(top, text='用户名：').grid(row=0, column=4, **pad)
        self.ent_user = tk.Entry(top, width=12)
        self.ent_user.grid(row=0, column=5, **pad)

        tk.Label(top, text='密码：').grid(row=0, column=6, **pad)
        self.ent_pwd = tk.Entry(top, width=12, show='*')       # 密码框用 * 遮起来
        self.ent_pwd.grid(row=0, column=7, **pad)
        self.ent_pwd.bind('<Return>', lambda e: self.on_connect())   # 输完密码直接回车就能连

        self.btn_connect = tk.Button(top, text='连接', width=8, command=self.on_connect)
        self.btn_connect.grid(row=0, column=8, **pad)
        self.btn_disconnect = tk.Button(top, text='断开', width=8, command=self.on_disconnect)
        self.btn_disconnect.grid(row=0, column=9, **pad)

        # ---------- 中部：服务器文件列表 ----------
        mid = tk.LabelFrame(self.root, text='服务器文件列表（我的家目录）', padx=6, pady=6)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        bar = tk.Frame(mid)
        bar.pack(fill=tk.X)
        self.lbl_path = tk.Label(bar, text='当前目录：/（未连接）', anchor='w', fg='#333')
        self.lbl_path.pack(side=tk.LEFT)
        self.btn_up = tk.Button(bar, text='返回上级', width=9, command=self.on_up)
        self.btn_up.pack(side=tk.RIGHT, padx=2)
        self.btn_refresh = tk.Button(bar, text='刷新列表(LS)', width=13, command=self.on_refresh)
        self.btn_refresh.pack(side=tk.RIGHT, padx=2)

        cols = ('name', 'size', 'mtime', 'type')
        self.tree = ttk.Treeview(mid, columns=cols, show='headings', height=12)
        self.tree.heading('name', text='名称')
        self.tree.heading('size', text='大小')
        self.tree.heading('mtime', text='修改时间')
        self.tree.heading('type', text='类型')
        self.tree.column('name', width=380, anchor='w')
        self.tree.column('size', width=110, anchor='e')
        self.tree.column('mtime', width=150, anchor='center')
        self.tree.column('type', width=80, anchor='center')
        vsb = ttk.Scrollbar(mid, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', self.on_double_click)      # 双击进目录 / 下载

        # ---------- 传输区 ----------
        tra = tk.LabelFrame(self.root, text='文件传输', padx=6, pady=6)
        tra.pack(fill=tk.X, padx=8, pady=4)

        self.btn_download = tk.Button(tra, text='下载选中文件(GET)', width=18,
                                      command=self.on_download)
        self.btn_download.grid(row=0, column=0, padx=4, pady=2)
        self.btn_upload = tk.Button(tra, text='选择本地文件上传(PUT)', width=20,
                                    command=self.on_upload)
        self.btn_upload.grid(row=0, column=1, padx=4, pady=2)

        self.lbl_progress = tk.Label(tra, text='就绪', anchor='w')
        self.lbl_progress.grid(row=1, column=0, columnspan=2, sticky='w', padx=4)
        self.progress = ttk.Progressbar(tra, orient='horizontal', length=800,
                                        mode='determinate', maximum=100)
        self.progress.grid(row=2, column=0, columnspan=2, sticky='we', padx=4, pady=4)
        tra.columnconfigure(0, weight=1)
        tra.columnconfigure(1, weight=1)

        # ---------- 底部：日志区 ----------
        bot = tk.LabelFrame(self.root, text='日志（传输状态、百分比、速度都会打在这里）', padx=6, pady=6)
        bot.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        self.txt_log = scrolledtext.ScrolledText(bot, height=9, state=tk.DISABLED)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    # ==================== 界面刷新（只在主线程里跑） ====================
    def log(self, msg):
        """往日志区追加一行（带时间戳）。"""
        line = '[%s] %s\n' % (time.strftime('%H:%M:%S'), msg)
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, line)
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def pump_ui_queue(self):
        """主线程定时把 worker 线程放进队列的消息取出来，更新界面。"""
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                kind = msg[0]
                if kind == 'log':
                    self.log(msg[1])
                elif kind == 'progress':                     # (百分比, 状态文字)
                    self.progress['value'] = msg[1]
                    self.lbl_progress.config(text=msg[2])
                elif kind == 'files':                        # (路径, 文件列表)
                    self.cwd, self.items = msg[1], msg[2]
                    self.show_files()
                elif kind == 'connected':                    # (是否连接, 用户名)
                    self.connected = msg[1]
                    self.user = msg[2] or ''
                    if not self.connected:
                        self.items = []
                        self.cwd = ''
                        self.show_files()
                        self.lbl_path.config(text='当前目录：/（未连接）')
                    self.update_buttons()
                elif kind == 'busy':                         # 传输开始/结束
                    self.busy = msg[1]
                    if msg[1]:
                        # 新任务开始：进度条清零，准备显示这一次的进度
                        # （注意：任务结束时不能清零，否则用户看不到“100% 完成”那一瞬间）
                        self.progress['value'] = 0
                        self.lbl_progress.config(text='处理中……')
                    self.update_buttons()
        except queue.Empty:
            pass
        self.root.after(80, self.pump_ui_queue)

    def show_files(self):
        self.tree.delete(*self.tree.get_children())
        for it in self.items:
            self.tree.insert('', tk.END, values=(
                it['name'],
                '—' if it['is_dir'] else human_size(it['size']),
                it['mtime'],
                '目录' if it['is_dir'] else '文件',
            ))
        if self.connected:
            self.lbl_path.config(text='当前目录：/%s   （共 %d 项）' % (self.cwd, len(self.items)))
        else:
            self.lbl_path.config(text='当前目录：/（未连接）')

    def update_buttons(self):
        state = tk.NORMAL if (self.connected and not self.busy) else tk.DISABLED
        for btn in (self.btn_refresh, self.btn_download, self.btn_upload, self.btn_up):
            btn.config(state=state)
        self.btn_connect.config(
            state=tk.DISABLED if (self.connected or self.busy) else tk.NORMAL)
        self.btn_disconnect.config(state=tk.NORMAL if self.connected else tk.DISABLED)

    def set_progress(self, percent, text):
        """worker 线程调用：把进度丢进队列（真正更新控件的是主线程）。"""
        self.ui_queue.put(('progress', percent, text))

    # ==================== 按钮事件（主线程） ====================
    def on_connect(self):
        if self.busy:
            return
        host = self.ent_host.get().strip() or DEFAULT_HOST
        port = self.ent_port.get().strip() or DEFAULT_PORT
        user = self.ent_user.get().strip()
        pwd = self.ent_pwd.get()
        if not user:
            messagebox.showwarning('提示', '请填写用户名')
            return
        if not port.isdigit():
            messagebox.showwarning('提示', '端口必须是数字')
            return
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_connect,
                         args=(host, int(port), user, pwd), daemon=True).start()

    def on_disconnect(self):
        """断开连接：能优雅就优雅（发 QUIT），不行就直接关掉 socket。"""
        if not self.connected:
            return
        if self.busy:
            # 正在传输，直接把套接字关掉，worker 线程会立刻收到异常并结束
            self.close_socket()
            self.log('已强制断开连接（传输被中断）')
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))
            return
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_quit, daemon=True).start()

    def on_refresh(self):
        if self.connected and not self.busy:
            self.ui_queue.put(('busy', True))
            threading.Thread(target=self.worker_ls, args=(self.cwd,), daemon=True).start()

    def on_up(self):
        if not self.connected or self.busy or not self.cwd:
            return
        parent = '/'.join(self.cwd.split('/')[:-1])       # 去掉最后一级
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_ls, args=(parent,), daemon=True).start()

    def on_double_click(self, event):
        """双击：目录就进去，文件就下载。"""
        sel = self.tree.selection()
        if not sel or self.busy or not self.connected:
            return
        name = self.tree.item(sel[0], 'values')[0]
        item = next((i for i in self.items if i['name'] == name), None)
        if item is None:
            return
        if item['is_dir']:
            path = '%s/%s' % (self.cwd, name) if self.cwd else name
            self.ui_queue.put(('busy', True))
            threading.Thread(target=self.worker_ls, args=(path,), daemon=True).start()
        else:
            self.start_download(name)

    def on_download(self):
        """下载列表里选中的文件。"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先在列表里选中一个文件')
            return
        name = self.tree.item(sel[0], 'values')[0]
        item = next((i for i in self.items if i['name'] == name), None)
        if item and item['is_dir']:
            messagebox.showinfo('提示', '这是一个目录，双击进去再选文件')
            return
        self.start_download(name)

    def start_download(self, name):
        if not (self.connected and not self.busy):
            return
        # 先问用户存到哪儿（这个对话框必须在主线程里弹）
        local_path = filedialog.asksaveasfilename(
            title='保存到本地', initialfile=name, initialdir=os.getcwd())
        if not local_path:
            self.log('已取消下载 %s' % name)
            return
        remote = '%s/%s' % (self.cwd, name) if self.cwd else name
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_get, args=(remote, local_path), daemon=True).start()

    def on_upload(self):
        if not (self.connected and not self.busy):
            return
        local_path = filedialog.askopenfilename(title='选择要上传的文件',
                                                initialdir=os.getcwd())
        if not local_path:
            return
        name = os.path.basename(local_path)
        # 目标位置：服务器上当前目录
        overwrite = False
        exist = next((i for i in self.items if i['name'] == name and not i['is_dir']), None)
        if exist:
            # 服务器上已有同名文件，先问用户要不要覆盖（服务端也会再拦一道）
            if not messagebox.askyesno('文件已存在',
                                       '服务器上已有 %s（%s），要覆盖它吗？'
                                       % (name, human_size(exist['size']))):
                self.log('已取消上传 %s' % name)
                return
            overwrite = True
        remote = '%s/%s' % (self.cwd, name) if self.cwd else name
        self.ui_queue.put(('busy', True))
        threading.Thread(target=self.worker_put,
                         args=(local_path, remote, overwrite), daemon=True).start()

    def on_close(self):
        if self.connected:
            try:
                self.sock.settimeout(2)
                send_json(self.sock, {'cmd': 'quit'})
            except OSError:
                pass
            self.close_socket()
        self.root.destroy()

    # ==================== 网络操作（worker 线程里跑） ====================
    def close_socket(self):
        self.connected = False
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def worker_connect(self, host, port, user, pwd):
        self.ui_queue.put(('log', '正在连接 %s:%d ……' % (host, port)))
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCK_TIMEOUT)
            sock.connect((host, port))
            self.sock = sock

            t0 = time.time()
            # 登录：密码在网络上传的是明文（这是本实验的简化，真实 FTP 还有 FTPS/SSH 加密），
            # 但服务器端保存的是“盐+哈希”，不保存明文
            send_json(sock, {'cmd': 'login', 'user': user, 'pass': pwd})
            reply = recv_json(sock)
            if reply is None:
                self.ui_queue.put(('log', '服务端没有应答就断开了连接'))
                self.close_socket()
                self.ui_queue.put(('connected', False, ''))
                self.ui_queue.put(('busy', False))
                return
            if not reply.get('ok'):
                self.ui_queue.put(('log', '登录失败：%s' % reply.get('msg')))
                self.close_socket()
                self.ui_queue.put(('connected', False, ''))
                self.ui_queue.put(('busy', False))
                return

            self.ui_queue.put(('log', '登录成功：%s（握手耗时 %.0f 毫秒）'
                                      % (reply.get('msg'), (time.time() - t0) * 1000)))
            self.ui_queue.put(('connected', True, reply.get('user')))
            self.do_ls('')                      # 登录后自动列一次目录
            self.ui_queue.put(('busy', False))  # 列完目录再解除“忙碌”，避免用户抢在刷新中间操作
        except socket.timeout:
            self.ui_queue.put(('log', '连接超时：服务器没有响应'))
            self.close_socket()
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))
        except OSError as e:
            self.ui_queue.put(('log', '连接失败：%s' % e))
            self.close_socket()
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))

    def worker_quit(self):
        try:
            send_json(self.sock, {'cmd': 'quit'})
            recv_json(self.sock)
        except OSError:
            pass
        finally:
            self.close_socket()
            self.ui_queue.put(('log', '已断开与服务器的连接'))
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('busy', False))

    def worker_ls(self, path):
        self.do_ls(path)
        self.ui_queue.put(('busy', False))

    def do_ls(self, path):
        """列目录。注意这里自己不 put busy=False，因为登录后也会调用它。"""
        try:
            send_json(self.sock, {'cmd': 'ls', 'path': path})
            reply = recv_json(self.sock)
            if reply is None:
                raise ConnectionResetError('服务器关闭了连接')
            if not reply.get('ok'):
                self.ui_queue.put(('log', '列目录失败：%s' % reply.get('msg')))
                return
            files = reply.get('files', [])
            self.ui_queue.put(('files', path, files))
            self.ui_queue.put(('log', '列目录 %s：共 %d 项（目录 %d 个，文件 %d 个）'
                                      % (reply.get('path', '/'), len(files),
                                         sum(1 for f in files if f['is_dir']),
                                         sum(1 for f in files if not f['is_dir']))))
        except (socket.timeout, ConnectionResetError, ConnectionAbortedError,
                AttributeError, ValueError, OSError) as e:
            self.ui_queue.put(('log', '列目录出错：%s' % e))
            self.handle_link_error()

    def worker_get(self, remote_name, local_path):
        """下载文件：服务端先告诉大小和 MD5，客户端边收边算 MD5，收完校验。"""
        name = remote_name.split('/')[-1]
        try:
            send_json(self.sock, {'cmd': 'get', 'name': remote_name})
            head = recv_json(self.sock)
            if head is None:
                raise ConnectionResetError('服务器关闭了连接')
            if not head.get('ok'):
                self.ui_queue.put(('log', '下载失败：%s' % head.get('msg')))
                return

            size = head['size']
            expect_md5 = head['md5']
            self.ui_queue.put(('log', '开始下载 %s（%s），服务端 MD5=%s'
                                      % (name, human_size(size), expect_md5)))

            md5 = hashlib.md5()
            got = 0
            t0 = time.time()
            last_update = 0.0
            tmp_path = local_path + '.part'      # 先写临时文件，校验通过再改名
            with open(tmp_path, 'wb') as f:
                while True:
                    type_byte, payload = recv_frame(self.sock)
                    if type_byte is None:
                        raise ConnectionResetError('下载途中连接断开')
                    if type_byte == TYPE_FILE:
                        f.write(payload)
                        md5.update(payload)
                        got += len(payload)
                        # 进度最多每 0.1 秒刷新一次，刷太勤界面反而不流畅
                        now = time.time()
                        if now - last_update > 0.1 or got >= size:
                            last_update = now
                            elapsed = now - t0
                            speed = got / elapsed if elapsed > 0 else 0
                            percent = got * 100.0 / size if size else 100.0
                            eta = (size - got) / speed if speed > 0 else 0
                            self.set_progress(percent,
                                              '下载 %s：%.1f%%（%s / %s）  %.1f KB/s  剩余 %.0f 秒'
                                              % (name, percent, human_size(got),
                                                 human_size(size), speed / 1024, eta))
                    elif type_byte == TYPE_END:
                        break

            cost = time.time() - t0
            local_md5 = md5.hexdigest()
            # 完整性校验：大小 + MD5
            if got != size:
                os.remove(tmp_path)
                self.ui_queue.put(('log', '下载失败：只收到 %d 字节，应该收到 %d 字节'
                                          % (got, size)))
                self.set_progress(0, '下载失败')
                return
            if local_md5 != expect_md5:
                os.remove(tmp_path)
                self.ui_queue.put(('log', '下载失败：MD5 校验不通过（本地 %s，服务端 %s）'
                                          % (local_md5, expect_md5)))
                self.set_progress(0, 'MD5 校验失败')
                return

            os.replace(tmp_path, local_path)
            self.set_progress(100, '下载完成：%s' % name)
            self.ui_queue.put(('log', '下载完成 %s：%s，耗时 %.2f 秒（%.1f KB/s），'
                                      '大小✔ MD5✔（%s）'
                                      % (name, human_size(got), cost,
                                         got / 1024 / (cost or 1e-6), local_md5)))
        except (socket.timeout, ConnectionResetError, ConnectionAbortedError,
                AttributeError, ValueError, OSError) as e:
            self.ui_queue.put(('log', '下载出错：%s' % e))
            self.set_progress(0, '下载中断')
            self.handle_link_error()
        finally:
            # 先刷新列表（还要用套接字），最后才解除“忙碌”——
            # 反过来的话，用户可能在刷新期间又点一个下载，两个线程同时用一个套接字会串包
            self.refresh_quietly()
            self.ui_queue.put(('busy', False))

    def worker_put(self, local_path, remote_name, overwrite):
        """上传文件：先把本地 MD5 算好告诉服务端，服务端落盘后再算一遍比对。"""
        name = os.path.basename(local_path)
        try:
            size = os.path.getsize(local_path)
            self.set_progress(0, '正在计算本地 MD5 ……')
            t_md5 = time.time()
            local_md5 = md5_file(local_path)
            self.ui_queue.put(('log', '本地文件 %s（%s），本地 MD5=%s（计算用了 %.2f 秒）'
                                      % (name, human_size(size), local_md5,
                                         time.time() - t_md5)))

            send_json(self.sock, {'cmd': 'put', 'name': remote_name, 'size': size,
                                  'md5': local_md5, 'overwrite': overwrite})
            head = recv_json(self.sock)
            if head is None:
                raise ConnectionResetError('服务器关闭了连接')
            if not head.get('ok'):
                self.ui_queue.put(('log', '上传被拒绝：%s' % head.get('msg')))
                self.set_progress(0, '上传被拒绝')
                return

            self.ui_queue.put(('log', '开始上传 %s（%s）……' % (name, human_size(size))))
            t0 = time.time()
            sent = 0
            last_update = 0.0
            with open(local_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK)
                    if not chunk:
                        break
                    send_chunk(self.sock, chunk)       # 按协议分块发送
                    sent += len(chunk)
                    now = time.time()
                    if now - last_update > 0.1 or sent >= size:
                        last_update = now
                        elapsed = now - t0
                        speed = sent / elapsed if elapsed > 0 else 0
                        percent = sent * 100.0 / size if size else 100.0
                        eta = (size - sent) / speed if speed > 0 else 0
                        self.set_progress(percent,
                                          '上传 %s：%.1f%%（%s / %s）  %.1f KB/s  剩余 %.0f 秒'
                                          % (name, percent, human_size(sent),
                                             human_size(size), speed / 1024, eta))
            send_end(self.sock)                        # 发结束标记
            cost = time.time() - t0

            reply = recv_json(self.sock)               # 等服务端的校验结果
            if reply is None:
                raise ConnectionResetError('服务器关闭了连接')
            if reply.get('ok'):
                self.set_progress(100, '上传完成：%s' % name)
                self.ui_queue.put(('log', '上传完成 %s：%s，耗时 %.2f 秒（%.1f KB/s），'
                                          '服务端校验通过，MD5=%s'
                                          % (name, human_size(sent), cost,
                                             sent / 1024 / (cost or 1e-6), reply.get('md5'))))
            else:
                self.set_progress(0, '上传失败')
                self.ui_queue.put(('log', '上传失败：%s' % reply.get('msg')))
        except (socket.timeout, ConnectionResetError, ConnectionAbortedError,
                AttributeError, ValueError, OSError) as e:
            self.ui_queue.put(('log', '上传出错：%s' % e))
            self.set_progress(0, '上传中断')
            self.handle_link_error()
        finally:
            self.refresh_quietly()
            self.ui_queue.put(('busy', False))

    def refresh_quietly(self):
        """传完文件后悄悄刷新一下列表，让用户马上看到结果。"""
        if self.connected and self.sock is not None:
            try:
                send_json(self.sock, {'cmd': 'ls', 'path': self.cwd})
                reply = recv_json(self.sock)
                if reply and reply.get('ok'):
                    self.ui_queue.put(('files', self.cwd, reply.get('files', [])))
            except OSError:
                self.handle_link_error()

    def handle_link_error(self):
        """连接出问题时统一处理：标记断开、提示用户。"""
        if self.connected:
            self.ui_queue.put(('connected', False, ''))
            self.ui_queue.put(('log', '与服务器的连接已断开，请重新连接'))
        self.close_socket()


if __name__ == '__main__':
    root = tk.Tk()
    app = FtpClientGUI(root)
    root.mainloop()
