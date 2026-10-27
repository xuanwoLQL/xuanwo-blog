---
title: "压缩包解密：zip2john / rar2john / 7z2john"
slug: "archive-cracking-john"
date: 2026-08-29T13:54:41+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "先从压缩包提取可破解哈希，再交给 John 跑字典。"
summary: "先从压缩包提取可破解哈希，再交给 John 跑字典。"
tags: ["John", "压缩包", "密码破解"]
categories: ["安全工具"]
series: ["安全工具箱"]
weight: 4
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/9.压缩包的解密.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/archive-cracking-john/workflow.svg" alt="从加密压缩包中提取可验证哈希，再用字典或规则恢复密码。" loading="lazy">
  <figcaption>图 1 · 压缩包密码恢复流程。从加密压缩包中提取可验证哈希，再用字典或规则恢复密码。</figcaption>
</figure>

## 1. 准备环境

Linux：

```bash
sudo apt install john hashcat
```

Windows 本机可以使用 hashcat 和 John 的 Windows 版本。

## 2. ZIP

提取哈希：

```bash
zip2john secret.zip > zip.hash
cat zip.hash
```

查看 hash 类型：

```bash
hashcat --identify zip.hash
```

常见 ZIP 模式：

```text
PKZIP (Compressed Multi-File) -> -m 17200
```

运行：

```bash
hashcat -m 17200 -a 0 \
  zip.hash \
  /path/to/rockyou.txt \
  -o cracked.txt \
  --force
```

## 3. RAR

```bash
rar2john secret.rar > rar.hash
hashcat --identify rar.hash
hashcat -m 13000 -a 0 rar.hash /path/to/rockyou.txt --force
```

## 4. 7z

```bash
7z2john secret.7z > 7z.hash
hashcat --identify 7z.hash
hashcat -m 11600 -a 0 7z.hash /path/to/rockyou.txt --force
```

## 5. John 备用

```bash
john --format=zip zip.hash
john --show zip.hash
```

John 可以自动识别部分格式：

```bash
john --wordlist=/path/to/rockyou.txt zip.hash
```

## 6. 用规则扩大候选

```bash
hashcat -m 17200 -a 0 zip.hash rockyou.txt \
  -r /path/to/hashcat/rules/best64.rule \
  -o cracked.txt --force
```

## 7. 验证密码

拿到明文后回到压缩包测试：

```bash
unzip -P '<password>' secret.zip -d /tmp/unzip-test
```

RAR：

```bash
unrar x -p'<password>' secret.rar /tmp/unrar-test/
```

7z：

```bash
7z x -p'<password>' secret.7z -o/tmp/7z-test
```

## 8. 排错

| 现象 | 原因 |
| --- | --- |
| hashcat 不识别 | 使用 John 提取的 hash 格式与模式不匹配 |
| 跑完无结果 | 字典或规则不够 |
| 提示设备错误 | 驱动/OpenCL/CUDA 问题 |
| 能解密但解压失败 | 明文错误或压缩包损坏 |

## 9. 安全边界

仅对授权靶场、自己的压缩包或明确允许的 CTF 附件运行。不要对真实用户数据做密码恢复。
