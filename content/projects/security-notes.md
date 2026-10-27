---
slug: "security-notes"
title: "网络安全学习笔记"
description: "19 篇 CTF Writeup、25 篇 Web 安全笔记、3 篇内网靶场实战，以及密码学与网络编程练习。"
date: 2026-10-21T20:00:00+08:00
lastmod: 2026-10-21T20:00:00+08:00
repo: "https://github.com/xuanwoLQL/security-notes"
language: "Markdown"
tech: ["CTF", "Web 安全", "内网渗透", "Obsidian"]
featured: true
ShowToc: false
comments: false
---

## 这个仓库是什么

`security-notes` 是我学习网络安全过程中整理的主知识库。它不是一个「收藏夹」，而是把每道题、每个漏洞、每次靶场实战拆成可复盘的步骤：目标是什么、看到了什么现象、为什么这样判断、最后怎么验证。

所有内容来自公开 CTF 比赛、公开练习靶场和课程学习，不包含真实业务系统或真实凭据。

## 内容分布

| 目录 | 内容 | 数量 |
| --- | --- | --- |
| `ctf-writeups/` | CTF 比赛题解：文件上传、反序列化、SSRF、SQL 注入、fastjson | 19 |
| `web-security/` | Web 漏洞原理、利用链与工具笔记 | 25 |
| `pentest/` | Bugku、vulntarget 等公开靶场的内网渗透记录 | 3 |
| `ctf-beginner-guide/` | 网络安全与 CTF 新手起步指南 | 1 |
| `cryptography/` | RSA 等密码学实验 | 1 |
| `python-learning/` | Socket、并发与文件传输练习 | 8 |

## 我关注的东西

- **漏洞链**：不满足于单点 payload，更关心「入口 → 权限 → 横向 → 目标」的完整路径。
- **可复现**：命令、回显、失败分支都留在笔记里，方便下一次复用。
- **边界**：只记录授权环境与公开靶场，公网地址统一替换为 RFC 5737 文档地址段。

## 相关链接

- GitHub：<https://github.com/xuanwoLQL/security-notes>
- 博客内的笔记库：[/notes/](/notes/)
- 内网渗透实战：[Bugku 渗透测试 3](/projects/bugku-pentest-writeup/)
