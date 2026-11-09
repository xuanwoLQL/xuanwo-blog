---
slug: "multiagent-workbench"
title: "MultiAgent 协作工作台"
description: "Windows 原生多 Agent 任务编排工作台：Git worktree 隔离、合并审阅、进程审计与 Electron 桌面打包。"
date: 2026-11-09T11:00:00+08:00
lastmod: 2026-11-09T11:00:00+08:00
repo: "https://github.com/xuanwoLQL/multiagent-workbench"
language: "Python / TypeScript"
tech: ["Electron", "FastAPI", "React", "SQLite", "Git worktree", "多 Agent"]
featured: true
ShowToc: false
comments: false
---

## 项目定位

MultiAgent 是一个本地优先的多 Agent 编排工作台。它不内置大模型，也不替代 Agent 本身，而是把本机已安装的 Codex、Claude Code、OpenCode、DeepSeek Harness 或任意 CLI Agent 组织成一支可调度的执行队伍，在同一个真实项目目录上完成编码、文档、调研、数据整理与审阅。

它主要解决四个问题：

- 把目标拆成带依赖的任务 DAG，按全局与项目级并发上限派发；
- 为每次执行准备隔离工作副本或 Git worktree，限制写入范围；
- 以退出码、文件改动、验收条件和产物证据判定成败，而不是相信 Agent 的自述；
- 把改动、日志、交接、审批和版本快照留在本机，供人工审阅后再合并。

它适合已经在本机使用多个 Agent、又不想让它们直接改动主工作区的开发者。它不是托管 SaaS、模型服务或多租户权限系统，也不是 VM / 容器级安全沙箱；默认策略是**先审后合**，不追求无人值守地自动合并所有改动。

## 核心能力

**任务看板与依赖 DAG**

任务按待执行、执行中、待人工、成功、失败 / 阻塞分列。创建任务时可以声明产出文件、执行 Agent、任务类型、隔离方式、写范围、超时与最大尝试次数；也可以一键拆成「调研 → 初稿 → 审阅」三段依赖。调度器使用原子认领与并发槽位派发，支持重试、恢复、扇出和前置任务闸门。

<img src="/images/projects/multiagent-workbench/tasks.png" alt="MultiAgent 任务看板，按状态展示待执行、执行中、待人工、成功与失败任务" width="720" height="430" loading="lazy">

**Git worktree 隔离**

Git 仓库中的任务优先使用独立 worktree，在 `ma/<task>` 分支上提交交付物；非 Git 目录、缺少 Git 或 worktree 创建失败时，退化为文件级 copy 隔离，并在任务详情中显示降级原因。写入范围由 `write_scope` 约束，`.multiagent`、`config`、`.git` 等控制面路径不会进入交付物。

**先审后合**

默认 `git.auto_merge=false`：任务验收通过后只提交到任务分支，不直接改动基线。人工在任务详情或审阅页逐文件查看统一 diff，确认后再「合并到基线」。默认 `git.require_merged_for_dependents=true`，前置任务未真正合并时下游保持 pending，合并后自动恢复 ready；基线存在未提交改动时会被脏树检查阻断。

<img src="/images/projects/multiagent-workbench/task-merged.png" alt="任务合并成功后的状态、分支与合并记录" width="720" height="430" loading="lazy">

**冲突与缺失分支终态**

合并冲突时执行 `git merge --abort`，仓库保持干净，API 返回结构化 409 与冲突文件列表，任务从 success 转入 blocked（`merge_conflict`），由人工在工作目录解决后重试合并。任务分支被外部删除时返回结构化的 `missing_branch`，任务进入 `merge_missing_branch` 终态，而不是继续显示成功或落入模糊失败。

<img src="/images/projects/multiagent-workbench/task-conflict.png" alt="合并冲突面板，展示冲突文件、任务状态与重试合并入口" width="720" height="430" loading="lazy">

**重建分支**

缺失分支场景提供「重建分支」入口：按任务记录的分支名重建 worktree 与分支，重建失败会回滚，避免留下半成品；重建成功后可重新验收、合并，任务恢复 success。放弃任务分支则会回收 worktree，并可按需删除 `ma/...` 分支，任务进入 `discarded`。

<img src="/images/projects/multiagent-workbench/missing-branch.png" alt="任务分支缺失后的结构化提示与重建分支入口" width="720" height="430" loading="lazy">

**进程与端口审计**

Agent 调用前后会审计新增的监听端口。只有能证明属于本任务工作目录的进程才会被回收；归属不明、PID 复用或探测失败时只告警，不误杀。Windows 下可用 CIM 补齐 netstat 漏报，审计与孤儿回收均可通过策略开关控制。

**多 Agent 适配**

ACP 是首选协议，支持流式事件、权限请求与统一握手；没有 ACP 的 Agent 可走 CLI 适配器，也可由人工接手、人工产出和人工验收。模型由 Agent 自身配置决定：ACP v1 不发送请求级 model，CLI 仅在参数中真的包含 `{model}` 占位符时注入，控制台按同一语义展示模型控制方。

**桌面打包**

Electron 桌面壳会自动选择空闲端口、拉起 Python 后端、等待健康检查通过后打开窗口，关闭窗口时结束后端进程树。后端由 PyInstaller 冻结，安装包通过 electron-builder 生成 NSIS setup 与 portable 两种 Windows 产物。当前安装包未签名，首次运行可能触发 SmartScreen「未知发布者」提示。

<img src="/images/projects/multiagent-workbench/settings-merge.png" alt="设置页中的 Git 合并策略、脏树检查与下游依赖闸门配置" width="720" height="430" loading="lazy">

## 架构简图

```text
React v2 控制台 / Electron / CLI
              │ REST + WebSocket
              ▼
          FastAPI API ─────────────── SQLite WAL
              │
              ▼
        调度引擎（并发槽位 / 原子认领 / 重试 / 恢复）
              │
              ▼
          单任务执行器
   ├─ Agent 适配器：ACP / CLI / Human
   ├─ 隔离层：baseline / copy / worktree
   ├─ Git 操作：worktree / diff / commit / merge
   ├─ 黑板：交接 / 审批 / 事件
   └─ 验收：退出码 / 产物 / 验收条件
```

| 模块 | 职责 |
| --- | --- |
| `multiagent/api/` | REST + WebSocket、安全策略、文件 / Git / 验证路由与静态资源 |
| `multiagent/orchestrator/` | 调度、并发槽位、原子认领、单任务执行、重试 / 恢复 / 扇出 |
| `multiagent/workspace/` | 项目、快照、baseline、隔离副本、改动日志、冲突与回滚 |
| `multiagent/gitops/` | Git worktree、分支命名、diff 摘要、任务提交与合并 |
| `multiagent/validation/` | 技术栈探测、检查命令生成、受限执行与报告 |
| `multiagent/tasks/` | 任务 DAG、状态机、验收条件、产物与类型模板 |
| `multiagent/safety/` | 危险操作拦截、人工确认队列与 Agent 额度 |
| `webapp/` | React 控制台（Vite + React Query + Zustand） |
| `desktop/` | Electron 外壳、后端拉起与打包配置 |

## 快速开始

前置条件：Python 3.10+、Node.js（仅构建前端时需要）、Git（仅 worktree 隔离需要），以及至少一个可用的 Agent CLI。

```powershell
git clone https://github.com/xuanwoLQL/multiagent-workbench.git
cd multiagent-workbench

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

.\.venv\Scripts\python.exe -m multiagent init
.\.venv\Scripts\python.exe -m multiagent doctor
.\.venv\Scripts\python.exe scripts\serve.py --port 8770 --open
```

开发模式下可另开终端启动 Vite：

```powershell
cd webapp
npm install
npm run dev
```

也可以直接启动桌面壳：

```powershell
cd desktop
npm install
npm start
```

## 验证结果

以下数字来自 2026-11-09 的最终主线复跑与最终安装包构建：

| 检查 | 结果 |
| --- | --- |
| Python 全量测试 | **764 passed / 10 skipped / 0 failed**（171.72s） |
| 控制台冒烟 | **67 / 67 PASS** |
| 真实浏览器 E2E | **8 flows / 182 checks PASS**，0 uncaught / 0 console error |
| 安装包验证 | **3 / 3** 次启动 / 健康检查 / 优雅退出通过，前后台与 Electron 均无残留进程 |
| 520 文件性能 | prepare worktree **1.327s**、run **3.196s**、merge **0.678s**；页面加载 **1.046s**、任务详情 **1.691s**、console error **0** |

源码版本为 `2.0.0`，数据库 schema 为 `6`。验证覆盖合并冲突、缺失分支、重建分支、脏树阻断、进程审计、依赖闸门与打包版生命周期；安装包签名仍未完成，属于已知发布限制。

## 下载与源码

- [GitHub Release v2.0.0](https://github.com/xuanwoLQL/multiagent-workbench/releases/tag/v2.0.0)
- [Windows 安装版 setup](https://github.com/xuanwoLQL/multiagent-workbench/releases/download/v2.0.0/multiagent-2.0.0-x64-setup.exe)（约 122.1 MiB）
- [Windows 便携版 portable](https://github.com/xuanwoLQL/multiagent-workbench/releases/download/v2.0.0/multiagent-2.0.0-x64.exe)（约 122.0 MiB）
- [源码仓库](https://github.com/xuanwoLQL/multiagent-workbench)

安装包当前未签名，Windows SmartScreen 可能提示「未知发布者」；下载后建议先校验 Release 页面提供的 SHA256，再运行。

## 许可证

本项目采用 [MIT License](https://github.com/xuanwoLQL/multiagent-workbench/blob/main/LICENSE)。
