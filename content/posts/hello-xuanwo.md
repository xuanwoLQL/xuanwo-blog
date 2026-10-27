---
title: "你好，漩涡"
slug: "hello-xuanwo"
date: 2026-10-26T20:30:00+08:00
lastmod: 2026-10-27T10:15:00+08:00
draft: false
author: ["xuanwo"]
description: "漩涡博客的第一篇文章：为什么开始写作，以及这里会记录什么。"
tags: ["公告", "Hugo", "PaperMod"]
categories: ["建站日志"]
series: ["建站日志"]
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
---

## 为什么写博客

学习安全的过程中，很多结论如果只停留在“做过一次”，很快就会变成模糊的记忆。写下来，才会被迫把概念、前提、失败路径和最终结论重新梳理一遍。

**漩涡** 是一个安静的个人角落。它不追求高频更新，只希望每一篇内容都比上一次更清楚一点。

## 这里会有什么

- CTF 比赛中的 Writeups 与赛后复盘
- 漏洞原理、复现过程与修复建议
- Linux、Nginx、日志分析和自动化脚本
- 学习过程中值得记录的踩坑与思考

所有测试与复现内容都应限定在授权环境中。技术细节的价值，不等于可以越过边界。

## 第一段命令

博客使用 Hugo 构建，本地预览只需要：

```bash
hugo server -D
```

生产构建与上传：

```bash
bash scripts/build-upload.sh
```

如果你看到右上角的复制按钮，说明代码块复制、阅读时间和自动目录都已经生效。

## 现在

现在这里已经收录了 61 篇笔记与 17 个项目：CTF Writeup、Web 安全、内网靶场、密码学实验、AI × 安全与网络编程。首页也改成了个人档案、专题入口、Bento 项目墙和可筛选的笔记库。

慢一点没关系，重要的是能够被未来的自己看懂。

