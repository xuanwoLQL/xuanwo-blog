# fork 理解和使用：群聊聊天室

## 需求
- 有人进入聊天室时，其他人会收到姓名，姓名不能重复；
- 有人进入时，其他人收到通知：`xxx进入了聊天室`；
- 一个人发消息，其他人收到 `xxx：xxxxxx`；
- 有人退出，其他人收到 `xxx退出了聊天室`；
- 扩展功能：服务器可以向所有用户发公告：`管理员消息：xxxxxx`。

## 文件
| 文件 | 说明 |
|---|---|
| `chat_server.py` / `chat_client.py` | 聊天室（线程版，Windows/Linux 都能跑，推荐） |
| `chat_server_fork.py` | 聊天室（fork 多进程版，**仅 Linux/Kali**；配同一个 `chat_client.py` 使用） |
| `chatroom_protocol.py` | 服务端/客户端共用的“长度前缀 + JSON”协议，用来解决粘包 |
| `fork_demo.py` | 对照老师截图，演示 `os.fork()` 的返回值、`wait` 回收、父子变量独立 |

## 运行
先在“服务端窗口”运行服务器，再在多个“客户端窗口”运行客户端：

```bash
# 线程版（Windows / Linux 都可以）
python chat_server.py 9000
python chat_client.py 127.0.0.1 9000     # 多开几个，分别输入不同昵称

# fork 多进程版（Kali）
python3 chat_server_fork.py 9000
python3 chat_client.py 127.0.0.1 9000

# 理解 fork
python3 fork_demo.py
```

客户端操作：输入昵称进入 → 回车发消息 → 输入 `quit` 退出。
服务端控制台敲一行字回车 = 以管理员身份给所有人发公告。

## 关于 fork
`os.fork()` 只有 Linux/macOS 有，Windows 没有，所以 Windows 上请用线程版。
fork 版里父进程负责 accept 和全部网络收发，每收到一条消息 fork 一个子进程去判断
（登录判重名 / 聊天转发 / 退出通知），子进程把结论通过管道写回父进程，父进程再广播。
这样避免了“父子进程都持有同一个套接字、谁先 close 谁就破坏对方 fd”的坑。

## 自测结果
- Windows（线程版）：登录、重名被拒、进入通知、聊天转发、管理员公告、退出通知，全部通过。
- Kali 22（fork 版）：进入通知、重名被拒、聊天转发、退出通知，9 项断言全部通过；`fork_demo.py` 正常输出两遍 `fork test over`。
