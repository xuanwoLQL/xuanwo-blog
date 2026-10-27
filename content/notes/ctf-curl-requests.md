---
title: "用 curl 发送 POST / PUT / GET"
slug: "ctf-curl-requests"
date: 2026-08-30T19:12:07+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "CTF 中常用的 curl 请求写法：参数编码、指定方法、带 Cookie 与文件上传。"
summary: "CTF 中常用的 curl 请求写法：参数编码、指定方法、带 Cookie 与文件上传。"
tags: ["CTF", "curl", "工具"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 5
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/5.使用curl 发POST,PUT,GET等等.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-curl-requests/workflow.svg" alt="把请求方法、Header、Cookie、Body 和文件上传拆成可复现参数。" loading="lazy">
  <figcaption>图 1 · curl 请求构造流程。把请求方法、Header、Cookie、Body 和文件上传拆成可复现参数。</figcaption>
</figure>

## 1. 启动本地回显服务器

完整代码：

<details>
<summary>展开完整代码：echo_server.py</summary>

```python
#!/usr/bin/env python3
"""Small HTTP echo server for practicing curl requests."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        payload = {
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers),
            "body_utf8": body.decode("utf-8", errors="replace"),
            "body_hex": body.hex(),
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
```

</details>

下载：[echo_server.py](/code/ctf-curl-requests/echo_server.py)


运行：

```bash
python3 echo_server.py
```

服务端监听 `127.0.0.1:8080`，返回方法、路径、Header、Body 的 UTF-8 和 Hex。

## 2. GET

```bash
curl -i -sS 'http://127.0.0.1:8080/?name=xuanwo&page=1'
```

`-i` 显示响应头，`-sS` 静默但显示错误。

## 3. POST 表单

```bash
curl -i -sS -X POST 'http://127.0.0.1:8080/login' \
  --data-urlencode 'username=admin' \
  --data-urlencode 'password=a b&c'
```

`--data-urlencode` 会自动处理空格、`&`、中文和等号，避免手工编码错误。

## 4. POST JSON

```bash
curl -i -sS -X POST 'http://127.0.0.1:8080/api' \
  -H 'Content-Type: application/json' \
  --data-binary '{"name":"xuanwo","score":100}'
```

读取文件：

```bash
curl -i -sS -X POST 'http://127.0.0.1:8080/api' \
  -H 'Content-Type: application/json' \
  --data-binary @payload.json
```

## 5. PUT / PATCH / DELETE

```bash
curl -i -sS -X PUT 'http://127.0.0.1:8080/note/1' \
  --data-raw 'new content'

curl -i -sS -X PATCH 'http://127.0.0.1:8080/note/1' \
  -H 'Content-Type: application/json' \
  --data '{"title":"updated"}'

curl -i -sS -X DELETE 'http://127.0.0.1:8080/note/1'
```

## 6. Cookie 与 Header

```bash
curl -i -sS 'http://127.0.0.1:8080/' \
  -H 'X-Forwarded-For: 127.0.0.1' \
  -H 'Referer: http://trusted.example/' \
  -H 'User-Agent: moe browser' \
  -b 'user=admin; role=administrator'
```

保存 Cookie：

```bash
curl -i -sS -c /tmp/cookie.txt \
  -X POST 'http://127.0.0.1:8080/login' \
  --data-urlencode 'username=admin'

curl -sS -b /tmp/cookie.txt 'http://127.0.0.1:8080/profile'
```

## 7. 文件上传

```bash
curl -i -sS -X POST 'http://127.0.0.1:8080/upload' \
  -F 'file=@./test.png;type=image/png' \
  -F 'name=test'
```

## 8. 跟随跳转与超时

```bash
curl -i -sS -L --max-time 10 \
  'http://127.0.0.1:8080/redirect'
```

## 9. 代理

```bash
curl -i -sS -x 'http://127.0.0.1:8081' \
  'http://target.local/'
```

## 10. 保存证据

```bash
curl -sS -D /tmp/headers.txt \
  -o /tmp/body.txt \
  'http://127.0.0.1:8080/'
head -n 30 /tmp/headers.txt
head -n 30 /tmp/body.txt
```

## 11. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| Shell 展开 `&` | 参数未加引号 | URL 用单引号包住 |
| JSON 被转义 | Shell 引号问题 | `--data-binary @file` |
| 302 后看不到最终响应 | 未跟随跳转 | 加 `-L` |
| HTTPS 证书错误 | 测试环境自签 | 只在授权环境用 `-k` |
| 请求被系统代理接管 | 环境变量/代理 | 显式 `-x` 或 `--noproxy` |
