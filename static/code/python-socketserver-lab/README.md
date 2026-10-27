# socketserver 编程实验

## 实验内容与文件对照

| 实验 | 要求 | 文件 |
|---|---|---|
| 1.1 基础 TCPServer | `TCPServer` 回显服务器，自定义类继承 `BaseRequestHandler`，监听 8000 | `01_echo_server.py`、`01_echo_client.py` |
| 1.2 多线程 TCPServer | `ThreadingTCPServer`，记录连接时间/IP，显示当前连接数 | `02_threading_server.py`、`02_threading_client.py` |
| 1.3 UDP 服务器 | `UDPServer`，返回消息长度和接收时间，带数据包统计，监听 8001 | `03_udp_server.py`、`03_udp_client.py` |
| 1.4 混合服务器 | 多线程同时跑 TCP（收文件）和 UDP（时间同步） | `04_hybrid_server.py`、`04_hybrid_client.py` |
| 选做 思考与扩展 | 简单聊天室服务器，支持多客户端同时聊天 | `05_chat_server.py`、`05_chat_client.py` |

每个实验都配了测试客户端，可以单独跑起来验证。

## 运行

四个服务器用的端口不冲突（8000 / 8002 / 8001 / 8003+8004），可以同时开着。

```bash
# 实验 1.1（先开服务端，再开 1~2 个客户端）
python 01_echo_server.py
python 01_echo_client.py

# 实验 1.2（一个服务端 + 一个模拟 5 个客户端的脚本）
python 02_threading_server.py
python 02_threading_client.py 127.0.0.1 8002 5 3

# 实验 1.3
python 03_udp_server.py
python 03_udp_client.py

# 实验 1.4（一个服务器同时提供两个服务）
python 04_hybrid_server.py
python 04_hybrid_client.py time            # UDP 校时
python 04_hybrid_client.py upload 要传的文件.txt   # TCP 传文件

# 选做：聊天室（服务端 + 多个客户端，各开一个终端）
python 05_chat_server.py
python 05_chat_client.py 127.0.0.1 8005 张三
python 05_chat_client.py 127.0.0.1 8005 李四
```

## 各实验实现要点

### 1.1 基础 TCPServer
- socketserver 的固定套路：处理类继承 `BaseRequestHandler` 并重写 `handle()` →
  `Server((地址, 端口), 处理类)` → `serve_forever()`。
- `self.request` 是和客户端通信的套接字，`self.client_address` 是客户端 `(IP, 端口)`。
- **`TCPServer` 是串行的**：一次只服务一个连接。开两个客户端就能看到第二个在排队，
  这是它和 1.2 的 `ThreadingTCPServer` 的本质区别。

### 1.2 多线程 TCPServer
- 类名只差一个 `Threading`，每来一个连接自动新建线程跑 `handle()`。
- 连接时间、IP 记录在 `online` 字典里，当前连接数就是 `len(online)`。
- **共享变量 `online`、`total_conn` 用 `threading.Lock` 加锁**，避免多线程同时改导致数据错乱。
- `daemon_threads = True`：主线程退出时工作线程一起退出。

### 1.3 UDP 服务器
- UDP 的 `self.request` 是 `(数据报, 服务器套接字)` 元组，一个数据报调用一次 `handle()`，
  所以 `handle()` 里不用写 `while True`。
- 回复要用 `sock.sendto(数据, self.client_address)`，UDP 没有连接对象。
- 数据包统计放在 `stats`（按客户端分别统计）+ `total`（总量）里。
- `UDPServer` 是单线程串行处理，`handle()` 不会并发，所以这里没加锁。

### 1.4 混合服务器
- 两个 `serve_forever()` 各占一个线程（UDP 在子线程，TCP 在主线程），
  所以同一个程序同时监听 TCP 8003 和 UDP 8004。
- TCP 上传协议：`b'UPLD'` + 4 字节文件名长度 + 文件名 + 8 字节文件大小 + 文件内容，
  用长度前缀解决粘包；`recv_exact()` 负责“收满 n 个字节”，解决分包。
- 服务端存文件时用 `os.path.basename()` 去掉路径，防止 `../../` 目录穿越。
- 服务端一边写盘一边算 MD5 并回给客户端，客户端拿本地 MD5 比对，验证文件完整性。
- UDP 校时：客户端记下 `t0`（发包前）和 `t3`（收包后），
  服务器回自己的 unix 时间戳，客户端算 `偏移 = 服务器时间 - (t0+t3)/2` 和往返时延。

### 选做：聊天室
- 用 `self.rfile.readline()` **按行读取**，一条消息一行（`\n` 结尾），
  这是控制台程序里最简单的“防粘包”办法。
- 支持昵称、上线/下线系统提示、`/list` 在线名单、`/quit` 退出。
- `online` 字典被多个线程读写，广播前先把字典复制一份再遍历（加锁），避免边遍历边修改。
- 客户端是“子线程收消息 + 主线程 input() 发消息”，不然 input() 一阻塞就看不到别人的话了。

## 自测结果

### 1.1 基础 TCPServer（6 项全通过）
- 回显正确：`hello`、`中文测试`、500 字节长内容，发多少回多少，一字不差 ✔
- **串行特点实测**：a 还连着的时候，b 发消息收不到回显（被挡住）；a 一断开，
  b 立刻收到自己的回显 —— 正好证明了 `TCPServer` 一次只服务一个连接 ✔
- 客户端用 `SO_LINGER` 强制发 RST 模拟“拔网线”，服务端打印
  `[异常] 客户端 … 非正常断开：[WinError 10054]` 后继续服务新客户端，不崩溃 ✔

### 1.2 多线程 TCPServer（5 个客户端并发）
服务端日志里的在线数量：`1 → 2 → 3 → 4 → 5`（5 个客户端同时在线），
每个都记录了 `连接时间：2026-10-18 11:10:51` 和自己的 IP；
客户端全部退出后数量 `5 → 4 → 3 → 2 → 1 → 0`。
5 个客户端各发 2 条（每条间隔 0.3 秒），**总耗时 0.61 秒** ——
如果是串行的 1.1，需要 5 倍以上的时间。✔

### 1.3 UDP 服务器（4 个数据包）
```
第 1 条：我发了 28 字节，往返 1.0 毫秒
        服务器回复：收到消息长度：28 字节，接收时间：2026-10-18 11:12:44（这是你的第 1 个包）
第 4 条：我发了 37 字节，往返 0.7 毫秒
        服务器回复：收到消息长度：37 字节，接收时间：2026-10-18 11:12:45（这是你的第 4 个包）
```
长度、时间、按客户端分开的包计数都正确 ✔（按 Ctrl+C 退出时还会打印总的包数/字节数统计）

### 1.4 混合服务器
- **UDP 时间同步**：往返时延 0.0~1.0 毫秒，平均时钟偏差 +0.000 秒 ✔
- **TCP 文件上传**：上传 250000 字节的文件，进度条按 26%/52%/78%/100% 打印，
  服务端算出的 MD5 与本地 **一致**，提示“上传成功，文件完整” ✔

### 选做：聊天室（两个客户端同时在线，6 项全通过）
真开两个客户端进程（张三、李四）同时在线：
- 李四收到 `张三: 大家好，我是张三`；张三收到 `李四: 张三你好，我是李四` ✔
- 张三看到 `系统：李四 加入了聊天室`；李四看到 `系统：张三 离开了聊天室` ✔
- 张三执行 `/list` 返回 `当前在线 2 人：张三（…）、李四（…）` ✔

## 调试中实际踩到的坑（值得记一笔）

1. **`b'…中文…'` 是语法错误**：写 1.4 的 UDP 部分时，我把中文提示写成了
   `sock.sendto(b'ERR|请发送 TIME…'.decode('utf-8'), …)`，结果整个文件
   `SyntaxError: bytes can only contain ASCII literal characters` —— 服务器根本没启动起来，
   客户端还以为是“服务器没开”。
   正确写法是 `'中文'.encode('utf-8')`：**bytes 字面量里只能放 ASCII，中文要先写成 str 再 encode**。
2. **多台服务器一起开时端口要错开**：1.1 用 8000（实验指定）、1.3 用 8001（实验指定），
   1.2 用了 8002、1.4 的 TCP/UDP 用了 8003/8004、聊天室用 8005，
   这样五个程序可以同时开着，方便对照，不会互相抢端口。
3. **服务端重启用 `allow_reuse_address = True`**：不然 Windows 上重启会报
   `Address already in use`（TIME_WAIT 还没释放）。
