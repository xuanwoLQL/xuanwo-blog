---
slug: "tcp-file-service"
title: "TCP 网盘"
description: "Python 标准库手写应用层协议：多线程并发、SHA-256 密码存储、8KB 分块传输与断点续传。"
date: 2026-10-08T20:00:00+08:00
lastmod: 2026-10-08T20:00:00+08:00
repo: "https://github.com/xuanwoLQL/tcp-file-service"
language: "Python"
tech: ["Socket", "多线程", "断点续传", "协议设计"]
featured: true
ShowToc: false
comments: false
---

## 一句话

一个不依赖任何第三方库的「网盘」：客户端和服务端用自定义协议通信，支持注册、登录、列目录、上传、下载与断点续传。

## 协议设计

控制面用一行 UTF-8 JSON + `\n`，数据面直接跟裸字节流。这样二进制文件不需要塞进 JSON 做转义。

```text
客户端 → 服务端：{"cmd":"upload","filename":"a.bin","size":204800}\n
服务端 → 客户端：{"status":"ok"}\n
客户端 → 服务端：<204800 字节裸数据，每块 8KB>
```

## 功能清单

| 功能 | 实现 |
| --- | --- |
| 用户注册 | 密码 SHA-256 哈希后存储，明文不落盘 |
| 用户登录 | 会话绑定在 TCP 连接上 |
| 查看网盘 | 列出用户一级目录下的文件、子目录与大小 |
| 上传 | 先协商文件名与大小，再按 8KB 分块传输 |
| 下载 | 支持断点续传，从本地已有字节数继续 |
| 并发 | 每个连接一个线程，共享用户表加锁 |

## 我学到的东西

- **协议边界**：控制面和数据面分开，解析逻辑会简单很多。
- **并发一致性**：多线程同时读写用户表时，锁的粒度决定了正确性与吞吐。
- **断点续传**：客户端本地文件大小就是天然的 offset，但服务端必须校验范围。
- **异常路径**：连接中断、半包、文件名冲突，比正常路径更值得写测试。

## 运行

```bash
python server.py     # 监听 0.0.0.0:8888
python client.py     # 默认连接 127.0.0.1:8888
```

## 相关链接

- 仓库：<https://github.com/xuanwoLQL/tcp-file-service>
- 博客内的网络编程笔记：[/notes/python-socketserver-lab/](/notes/python-socketserver-lab/)
