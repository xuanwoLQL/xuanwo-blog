---
slug: "codex-computer-use"
title: "Codex Computer Use"
description: "让桌面 AI 读屏并操控键鼠：UIA 无障碍树 + Windows OCR + PowerShell 输入模块。"
date: 2026-10-09T20:00:00+08:00
lastmod: 2026-10-09T20:00:00+08:00
repo: "https://github.com/xuanwoLQL/codex-computer-use"
language: "PowerShell"
tech: ["PowerShell", "UIA", "OCR", "Computer Use"]
featured: true
ShowToc: false
comments: false
---

## 背景

桌面版 Codex 的 Computer Use 在 Windows 上的支持面并不稳定。与其等待，不如自己搭一条最小闭环：**把屏幕变成文字交给 AI，再把 AI 的指令变回点击与输入。**

## 三个模块

| 模块 | 作用 | 入口 |
| --- | --- | --- |
| 读屏 | UIA 无障碍树（带坐标）/ Windows 内置 OCR / 自动切换 | `脚本/read-screen.ps1` |
| 截图 | 全屏、指定窗口、指定区域，支持缩放 | `脚本/capture.ps1` |
| 键鼠 | `Click-Control` / `Type-Text` / `Send-Hotkey` / `Set-AppWindow` | `脚本/InputHelper.psm1` |

## 一条典型链路

```powershell
# 1) 读屏：先试 UIA，文字太少自动转 OCR
powershell -NoProfile -ExecutionPolicy Bypass -File ".\脚本\read-screen.ps1"

# 2) 预演点击：先拿到坐标，不真正点击
Import-Module ".\脚本\InputHelper.psm1" -DisableNameChecking
Click-Control -Name "登录" -Window msedge -DryRun

# 3) 真点 + 输入
Click-Control -Name "登录" -Window msedge
Type-Text "whoami"
Send-Hotkey "{ENTER}"
```

## 踩过的坑

- **DPI 缩放**：UIA 返回的是物理像素还是逻辑像素，取决于进程的 DPI awareness，坐标必须统一。
- **前台锁**：Windows 不允许后台进程随意抢焦点，`Set-AppWindow` 需要先把窗口可靠地拉到前台。
- **输入法**：直接发送 Unicode 字符与模拟按键是两条路径，中文输入要避开输入法候选框。
- **编码**：PowerShell 5.1 会按 GBK 解析无 BOM 脚本，含中文的 `.ps1` 必须保存为 UTF-8 with BOM。

## 适合谁

想把桌面 AI 从「聊天」推进到「操作」的人。代码不依赖第三方库，Windows 10/11 + PowerShell 5.1 可直接运行。

## 相关链接

- 仓库：<https://github.com/xuanwoLQL/codex-computer-use>
