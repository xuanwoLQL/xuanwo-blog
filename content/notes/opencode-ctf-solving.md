---
title: "OpenCode 辅助 CTF 解题"
slug: "opencode-ctf-solving"
date: 2026-09-08T12:50:17+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "用 OpenCode Agent 读取题目、调用工具并逐步收敛解法的实践。"
summary: "用 OpenCode Agent 读取题目、调用工具并逐步收敛解法的实践。"
tags: ["AI", "OpenCode", "CTF"]
categories: ["AI × 安全"]
series: ["AI × 安全"]
weight: 1
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/18.OpenCode辅助解题(提示词的利用).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/opencode-ctf-solving/workflow.svg" alt="把题面检索、假设生成、工具执行和人工验证串成可追踪流程。" loading="lazy">
  <figcaption>图 1 · Agent 辅助 CTF 解题闭环。把题面检索、假设生成、工具执行和人工验证串成可追踪流程。</figcaption>
</figure>

## 1. 安装与检查

```bash
opencode --version
opencode --help
```

如果使用 API Key：

```bash
opencode auth login
```

列出 MCP 连接：

```bash
opencode mcp list
```

## 2. 工作目录

每道题独立目录，避免上下文和附件混在一起：

```bash
export CASE="$HOME/homework/ctf-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$CASE"
cd "$CASE"
```

要求 Agent 始终维护：

```text
progress.md   实时命令与真实输出摘要
SOLVE.md      最终可复现 write-up
artifacts/    原始请求、脚本、截图、输出
```

## 3. 启动

```bash
opencode
```

对 Web 题使用：

```text
请作为 CTF Web 解题 Agent，处理当前目录中的题目。

目标：<URL 或附件路径>
授权：仅限该 CTF/靶场。

要求：
1. 每一步真实执行前先写原因；
2. 执行后立刻把完整命令、真实输出摘要、涉及 URL/文件追加到 progress.md；
3. 不伪造输出；
4. 先做信息收集，再提出最小验证，再扩大利用；
5. 得到 flag 前不要停止；
6. 最后生成 SOLVE.md，包含环境、完整步骤、代码、验证和失败分支。

现在先读取题目与当前目录，列出前三个假设，不要直接扫描。
```

逆向题：

```text
请作为 CTF Reverse 解题 Agent，处理当前目录中的附件。

先做文件识别、保护检查和字符串/符号分析。
每一步命令写入 progress.md。
找到校验逻辑后，编写 solve.py 或等效脚本复现 flag。
最终 SOLVE.md 要包含静态分析、动态验证、脚本和两组验证结果。
```

## 4. MCP 边界

建议只接入需要的能力：

| MCP | 允许 | 禁止 |
| --- | --- | --- |
| Burp MCP | 读取请求/响应、重放 | 自动提交比赛答案 |
| Kali MCP | 执行授权命令 | 访问真实第三方资产 |
| 知识库 | 检索 payload/WP | 把未验证内容当结论 |

## 5. 过程验证

查看进度：

```bash
wc -l progress.md
tail -n 80 progress.md
```

检查每条记录是否至少有：

```text
原因
命令/请求
输出摘要
文件/URL
```

最终报告：

```bash
test -s SOLVE.md
rg -n 'flag\{' SOLVE.md
```

## 6. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| Agent 只给建议不执行 | 提示词没有执行要求 | 明确要求调用工具并验证 |
| 重复扫描 | 没有进度文件 | 把 progress.md 加入每轮上下文 |
| 结果不可复现 | 命令未记录 | 要求完整命令与原始输出 |
| MCP 连不上 | 进程/端口/配置错误 | 先 `opencode mcp list` |
| 上下文膨胀 | 把大文件全塞进去 | 先索引、再按需读取 |

## 7. 安全边界

- 只在授权环境执行；
- 不把比赛 token 交给 Agent；
- 不让 Agent 自动提交 flag；
- 所有利用先在授权目标验证；
- 保留失败分支，不追求“看起来成功”的输出。
