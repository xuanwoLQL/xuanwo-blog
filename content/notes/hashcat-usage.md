---
title: "hashcat 哈希破解"
slug: "hashcat-usage"
date: 2026-08-29T13:47:18+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "常见哈希类型、字典与掩码攻击的参数速查。"
summary: "常见哈希类型、字典与掩码攻击的参数速查。"
tags: ["hashcat", "密码破解", "工具"]
categories: ["安全工具"]
series: ["安全工具箱"]
weight: 3
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/8.hashcat使用.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/hashcat-usage/workflow.svg" alt="先识别哈希模式和攻击类型，再选择设备、字典与规则，最后回算验证。" loading="lazy">
  <figcaption>图 1 · hashcat 破解流程。先识别哈希模式和攻击类型，再选择设备、字典与规则，最后回算验证。</figcaption>
</figure>

## 1. 检查设备

```bash
hashcat -I
hashcat -b
```

如果使用 CPU：

```bash
hashcat -m 0 -a 0 hash.txt wordlist.txt --force
```

## 2. 识别哈希

```bash
hashcat --identify hash.txt
```

常见模式：

| 哈希 | 模式 |
| --- | --- |
| MD5 | 0 |
| SHA-1 | 100 |
| SHA-256 | 1400 |
| NTLM | 1000 |
| bcrypt | 3200 |
| ZIP | 17200 |
| RAR | 13000 |
| 7z | 11600 |

## 3. 字典攻击示例

```bash
hashcat -m 0 -a 0 \
  -o cracked.txt \
  hash.txt \
  /path/to/rockyou.txt \
  --force
```

查看结果：

```bash
cat cracked.txt
```

## 4. 规则攻击

```bash
hashcat -m 0 -a 0 \
  hash.txt rockyou.txt \
  -r /path/to/hashcat/rules/best64.rule \
  -o cracked.txt \
  --force
```

## 5. 掩码攻击

六位小写字母：

```bash
hashcat -m 0 -a 3 hash.txt '?l?l?l?l?l?l' --force
```

八位数字：

```bash
hashcat -m 0 -a 3 hash.txt '?d?d?d?d?d?d?d?d' --force
```

## 6. 恢复会话

按 `q` 暂停后，用：

```bash
hashcat --restore
```

查看 potfile：

```bash
hashcat -m 0 hash.txt --show
```

## 7. 回算验证

MD5：

```bash
printf '%s' '<plaintext>' | md5sum
```

Python：

```python
import hashlib
print(hashlib.sha256(b"<plaintext>").hexdigest())
```

输出必须与目标 hash 一致。

## 8. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `No devices found` | 驱动/OpenCL 未配置 | 用 `--force` 或安装驱动 |
| `Token length exception` | hash 格式错误 | 重新提取/去掉用户名 |
| `Exhausted` | 字典/掩码没命中 | 换规则或扩大空间 |
| 过热/降频 | 硬件负载 | 限功率、降低 workload |

## 9. 注意

密码恢复只对授权数据使用。不要把真实凭据或破解结果写进公开笔记。
