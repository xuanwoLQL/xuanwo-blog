---
title: "dirsearch 目录扫描"
slug: "dirsearch-usage"
date: 2026-08-29T10:04:31+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "目录与接口发现的基本参数、字典选择与结果判读。"
summary: "目录与接口发现的基本参数、字典选择与结果判读。"
tags: ["dirsearch", "信息收集", "工具"]
categories: ["安全工具"]
series: ["安全工具箱"]
weight: 2
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/7.dirsearch的使用.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/dirsearch-usage/workflow.svg" alt="从授权目标、字典和线程设置开始，最终把扫描命中变成手工证据。" loading="lazy">
  <figcaption>图 1 · 目录扫描验证流程。从授权目标、字典和线程设置开始，最终把扫描命中变成手工证据。</figcaption>
</figure>

## 1. 安装

```bash
python3 -m pip install dirsearch
dirsearch --version
```

如果系统 Python 缺少依赖，建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install dirsearch
```

## 2. 最小扫描

```bash
dirsearch -u 'http://127.0.0.1:8080/' \
  -w /path/to/SecLists/Discovery/Web-Content/common.txt \
  -t 10 \
  --timeout=8 \
  --exclude-status=404
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| `-u` | 目标 URL |
| `-w` | 字典 |
| `-t` | 并发线程 |
| `--timeout` | 请求超时 |
| `--exclude-status` | 排除无意义状态码 |

## 3. 带扩展名扫描

```bash
dirsearch -u 'http://127.0.0.1:8080/' \
  -w /path/to/SecLists/Discovery/Web-Content/raft-small-files.txt \
  -e php,html,js,txt,bak,zip \
  -t 8
```

## 4. 从结果到证据

扫描完成后，对每个候选手工复核：

```bash
curl -i -sS 'http://127.0.0.1:8080/<candidate>' -o /tmp/dirsearch-check.txt
head -n 30 /tmp/dirsearch-check.txt
```

判断：

- 200 且内容不同于首页：优先；
- 301/302：记录 Location；
- 403：可能仍存在；
- 200 但返回统一错误页：比较 `Content-Length`、title 和 body hash。

## 5. 一个完整示例

```bash
mkdir -p /tmp/dirsearch-run
dirsearch -u 'http://127.0.0.1:8080/' \
  -w /path/to/SecLists/Discovery/Web-Content/common.txt \
  -e php,txt,zip \
  -t 10 \
  -o /tmp/dirsearch-run/report.txt \
  --format=plain

grep -E '200|301|302|403' /tmp/dirsearch-run/report.txt
```

## 6. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ModuleNotFoundError` | Python 依赖缺失 | 用虚拟环境 |
| 请求全部超时 | 网络/代理/限流 | 降线程、加超时 |
| 全部 200 | 目标返回 SPA fallback | 比较 body 长度/hash |
| 429 | 触发限流 | 降低并发，遵守授权 |

## 7. 修复建议

- 移除 `.git`、备份、源码和数据库文件；
- 统一 404，避免目录存在性泄漏；
- 对敏感路径限流；
- 对静态资源做清单化管理。
