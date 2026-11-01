---
title: "第九届强网拟态：不迷茫多 Agent 工作台 18 题复盘"
slug: "nest-2026-bumimang-overview"
date: 2026-11-01T12:30:00+08:00
lastmod: 2026-11-01T12:30:00+08:00
draft: false
author: ["xuanwo"]
description: "第九届“强网”拟态防御国际精英挑战赛预选赛赛后总复盘：四 Agent 并行、共享黑板、低延迟界面、14 个已确认 flag 与分方向 WP。"
tags: ["CTF", "强网拟态", "不迷茫"]
categories: ["CTF Writeup", "第九届强网拟态"]
series: ["第九届强网拟态 2026"]
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
cover:
  image: "/images/projects/bumimang/workbench.png"
  relative: false
---

> 参赛队：不迷茫队 · 平台完成 18 题 · 排行榜截图 7547 分 · 本地终态快照折算 7555 分  
> 项目源码：[https://github.com/xuanwoLQL/bumimang-ctf-workbench](https://github.com/xuanwoLQL/bumimang-ctf-workbench)

![不迷茫多 Agent 工作台](/images/projects/bumimang/workbench.png)

## 这次比赛做成了什么

- 连接比赛平台并完整展示当前账号可见题单、分值、附件、靶机与解题状态。
- 把 Codex、Claude Code、OpenCode、DeepSeek Harness 编成四路 Agent。
- 单题最多 4 Agent，全局最多 12 并发；共享事实、死路、意图和租约。
- 用 E0/E1/E2 证据等级约束提交，平台拒绝后把原因回灌给所有 Agent。
- 比赛面板按视图订阅和分区脏检查，实测切换 p95 16.6ms、longtask 0。

## 最终结果

| 指标 | 结果 |
| --- | ---: |
| 平台可访问题 | 24 |
| 平台完成 | 18 |
| 排行榜截图 | 第 157 名 / 7547 分 / 18/26 |
| 本地终态折算 | 7555 分 |
| 已确认 flag 原文 | 14 |

![比赛排行榜](/images/projects/bumimang/platform-rank.png)

## 分方向 WP

所有文章都保留完整复现逻辑、关键命令、证据等级和修复建议。平台完成但本地没有 flag 原文的题目会明确标注“证据缺口”。

### Web

- [Ghost-in-the-Queue](/posts/2026/11/nest-2026-web-ghost-in-the-queue/)
- [Undercurrent](/posts/2026/11/nest-2026-web-undercurrent/)
- [Crossed Signals](/posts/2026/11/nest-2026-web-crossed-signals/)

### Pwn

- [Pending Review](/posts/2026/11/nest-2026-pwn-pending-review/)
- [Smart Surveillance Camera](/posts/2026/11/nest-2026-pwn-smart-surveillance/)
- [SilGate](/posts/2026/11/nest-2026-pwn-silgate/)

### Crypto

- [dropout](/posts/2026/11/nest-2026-crypto-dropout/)
- [Immobilizer](/posts/2026/11/nest-2026-crypto-immobilizer/)
- [Off the Curve](/posts/2026/11/nest-2026-crypto-off-the-curve/)
- [Premaster](/posts/2026/11/nest-2026-crypto-premaster/)

### Misc

- [FilmReader](/posts/2026/11/nest-2026-misc-filmreader/)
- [Pickle-Me-Not](/posts/2026/11/nest-2026-misc-pickle-me-not/)
- [LLM Pipeline](/posts/2026/11/nest-2026-misc-llm-pipeline/)
- [UAE](/posts/2026/11/nest-2026-misc-uae/)
- [Causal Mosaic](/posts/2026/11/nest-2026-misc-causal-mosaic/)
- [SilentWeights](/posts/2026/11/nest-2026-misc-silentweights/)

### Reverse

- [Wasmnesia](/posts/2026/11/nest-2026-reverse-wasmnesia/)
- [Bootleg Update](/posts/2026/11/nest-2026-reverse-bootleg-update/)

## 发布口径

- 账号、密码、JWT、Cookie、API Key 和私钥全部脱敏。
- 动态靶机地址改为 `<TARGET_HOST>` / `<TARGET_PORT>` 或环境变量。
- 只发布授权比赛内容，不提供对公网未授权资产的操作指令。
- 所有本地推断都标注证据等级，不把猜测写成事实。

完整源码、脚本和台账：<https://github.com/xuanwoLQL/bumimang-ctf-workbench>
