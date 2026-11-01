---
slug: "bumimang-ctf-workbench"
title: "不迷茫 · Multi-Agent CTF Workbench"
description: "四 Agent 并行、共享黑板、证据驱动提交与低延迟比赛面板的 Windows CTF 工作台。"
date: 2026-11-01T12:20:00+08:00
lastmod: 2026-11-01T12:20:00+08:00
repo: "https://github.com/xuanwoLQL/bumimang-ctf-workbench"
language: "TypeScript"
tech: ["Electron", "ACP", "MCP", "SQLite", "TypeScript"]
featured: true
ShowToc: true
comments: false
---

![不迷茫工作台](/images/projects/bumimang/workbench.png)

## 为什么做它

比赛时真正拖慢速度的不是模型不会做，而是：题单同步慢、多个 Agent 各做一遍、结论散落在终端、flag 没有证据、界面每次刷新都卡。不迷茫把这些环节收进一个本地桌面工作台，让 Agent 负责解题，人只处理边界。

## 四个核心设计

1. **平台层**：Nest/CyberPeace、CTFd、CTFy MCP 适配，题单、附件、靶机和提交统一。
2. **编排层**：Codex/Claude/OpenCode/DSH 四路 ACP，单题 4 Agent、全局 12 并发。
3. **证据层**：共享黑板 + E0/E1/E2 + 平台拒绝回灌，不接受无证据 flag。
4. **低延迟 UI**：隐藏视图不渲染、分区脏检查、300ms 黑板刷新合并。

## 实测性能

| 指标 | 改造前 | 改造后 |
| --- | ---: | ---: |
| 可见 DOM | 2431 | 699 |
| Performance.Nodes | 24466 | 5131 |
| 视图切换 p95 | 无法稳定测量 | 16.6ms |
| 切换 longtask | 多次 | 0 |

## 比赛验证

第九届“强网”拟态预选赛中，平台可访问 24 题、完成 18 题，排行榜截图第 157 名、7547 分；本地保留并确认 14 个 flag 原文。全部 18 题 WP 已按方向发布，证据不足的题目明确标注缺口。

## 快速开始

```powershell
git clone https://github.com/xuanwoLQL/bumimang-ctf-workbench.git
cd bumimang-ctf-workbench
Copy-Item config/app.example.json config/app.json
Copy-Item config/platform.example.json config/platform.json
npm install
npm run smoke
```

## 质检

- `npm run verify:all`：全量通过
- `npm run smoke`：渲染层 ALL PASS
- `npm run verify:flags`：214/214
- `npm run verify:concurrency`：19/19
- `npm run verify:hardening`：49/49
- 公开源码敏感信息审计：0 findings

仓库：<https://github.com/xuanwoLQL/bumimang-ctf-workbench>

比赛总复盘：[第九届强网拟态 18 题复盘](/posts/2026/11/nest-2026-bumimang-overview/)
