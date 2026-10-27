---
title: "安全工具手册：从选型到结果验证"
slug: "security-toolbox-guide"
date: 2026-10-27T09:58:00+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "把零散的工具笔记整理成一条可复用工作流：先定边界，再选工具、留证据、做复核，最后写清失败分支。"
summary: "工具不是答案。真正可复用的是一套从选型、执行到验证的工作流。"
tags: ["安全工具", "信息收集", "方法论", "复盘"]
categories: ["安全工具"]
series: ["安全工具手册"]
weight: 1
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/security-toolbox-guide/workflow.svg" alt="从授权边界开始，选择最小工具验证假设，再保留证据和失败分支。" loading="lazy">
  <figcaption>图 1 · 安全工具工作流。从授权边界开始，选择最小工具验证假设，再保留证据和失败分支。</figcaption>
</figure>

> 所有扫描、利用和取证操作都必须发生在明确授权的靶场或演练环境中。

工具笔记最容易写成「命令清单」：nmap 怎么扫、dirsearch 怎么跑、hashcat 用什么参数。命令当然重要，但面试官更关心的是：你为什么选这个工具、如何判断结果可信、失败时怎么换线。

这篇把散落的工具笔记串成一条工作流。

## 1. 先定边界，再开工具

在输入第一条命令前，先回答四个问题：

1. 目标是否在授权范围内？
2. 现在缺的是资产、服务、漏洞，还是证据？
3. 这个工具会主动修改目标，还是只读探测？
4. 结果如何保存和复核？

如果没有答案，先不要扫。工具跑得越快，越容易制造无法解释的日志和副作用。

## 2. 工具地图

| 阶段 | 典型目标 | 工具 | 结果应该回答什么 |
| --- | --- | --- | --- |
| 资产发现 | 找到存活主机、端口与服务 | Nmap、httpx、fscan | 哪些目标真实存在？服务指纹是什么？ |
| Web 枚举 | 找目录、参数、接口与框架 | dirsearch、Burp Suite、浏览器开发者工具 | 哪些入口可重复访问？返回差异是什么？ |
| 漏洞验证 | 复现一个具体假设 | Burp Repeater、sqlmap、curl | 漏洞是否稳定？前置条件是什么？ |
| 凭据分析 | 验证弱口令、恢复密码 | hashcat、John | 成功证据是什么？耗时与资源如何？ |
| 会话管理 | 查看已授权的 WebShell | AntSword | 连接是否成功？最小验证动作是什么？ |
| 主机与流量 | 复盘入侵或异常 | tshark、Volatility、Sysinternals | 时间线、进程、连接和文件证据能否互证？ |

已有专题：

- [dirsearch 目录扫描](/notes/dirsearch-usage/)
- [hashcat 哈希破解](/notes/hashcat-usage/)
- [压缩包解密：zip2john / rar2john / 7z2john](/notes/archive-cracking-john/)
- [蚁剑的安装与使用](/notes/antsword-usage/)
- [用 curl 发送 POST / PUT / GET](/notes/ctf-curl-requests/)

## 3. 一条可复用的执行流程

### 3.1 先做最小探测

不要一上来就全端口、全字典、全 payload。先确认目标存活、协议和响应特征，再决定是否扩大范围。

例如 Web 打点：

```text
访问首页
  → 看响应头与页面指纹
  → 抓一条正常请求
  → 只修改一个变量
  → 记录状态码、长度、时间和回显差异
```

如果最小请求没有差异，继续堆 payload 通常只会制造噪音。

### 3.2 每个结论都保留证据

至少保留三类证据：

- **请求证据**：完整 URL、方法、Header、参数；
- **结果证据**：响应状态、关键回显、文件哈希；
- **环境证据**：时间、目标地址、使用的工具版本和参数。

截图可以辅助说明，但不能替代可复制的命令和原始响应。

### 3.3 结果必须二次复核

一个「看起来成功」的结果，可能来自缓存、WAF、旧会话或误判。

复核方式：

- 换一个无害参数重复；
- 换请求方式或编码方式重复；
- 换一个独立会话重复；
- 用第二个工具或手工请求交叉验证；
- 检查时间戳和日志是否一致。

## 4. 工具输出不等于漏洞结论

### 4.1 扫描器命中

看到 high / critical 不要直接写结论。确认：

- 目标版本是否确实匹配；
- 请求是否真正到达目标，而不是代理缓存；
- 响应是否来自漏洞，而不是默认页或错误页；
- 是否有最小化、无害化复现。

### 4.2 哈希破解

看到明文不要急着关闭任务：

- 记录 hashcat 模式、字典和耗时；
- 确认明文能通过原算法重新计算；
- 区分「字典命中」和「真正破解了算法」。

### 4.3 连接 WebShell

不要用删除、上传大文件或修改配置来「测试权限」。先用 `whoami`、只读目录列表或一条无害 echo 验证会话。

## 5. 常用工具的安全设置

### 5.1 控制并发与超时

扫描器默认配置通常偏激进。公开靶场也要控制并发，避免把容器打挂：

```bash
# 只做示意：按具体工具调整参数
dirsearch -u "http://127.0.0.1:<port>" -t 10 --timeout 8
```

### 5.2 不把真实凭据写进命令历史

命令行会落在 shell history、进程列表和日志里。演示环境可以使用占位符：

```bash
tool --host <target> --password '<redacted>'
```

### 5.3 输出统一归档

建议为每次任务建立：

```text
case-YYYYMMDD/
├─ raw/          # 原始请求、响应、抓包
├─ notes/        # 时间线与假设
├─ screenshots/  # 只放关键截图
└─ report.md     # 结论、证据、失败分支
```

## 6. 失败分支比成功命令更有价值

一次 CTF 复盘至少应该记录：

- 尝试了什么；
- 为什么失败；
- 失败暴露了目标的什么特征；
- 下一次应该先看哪里。

面试时，能解释「为什么没有继续打这条线」通常比单纯列出 flag 更能说明判断力。

## 7. 发布前检查

- [ ] 目标处于授权范围
- [ ] 请求已最小化
- [ ] 真实 IP、端口和凭据已脱敏
- [ ] 命令与响应可复现
- [ ] 结论有至少两种证据
- [ ] 失败分支和时间线已记录
- [ ] 截图不含个人信息和 token

## 8. 延伸阅读

- [把 CTF 与应急响应做成 Agent Skills](/notes/agent-skills-ctf-dfir/)
- [渗透测试提示词模板](/notes/pentest-prompt-template/)
- [漩涡博客项目记录](/projects/xuanwo-blog/)

## 可复现补充

## 可直接执行的工具示例

### 端口与服务

```bash
nmap -Pn -sV --top-ports 1000 127.0.0.1 -oN /tmp/nmap.txt
```

### Web 目录

```bash
ffuf -u 'http://127.0.0.1:8080/FUZZ' \
  -w /path/to/SecLists/Discovery/Web-Content/common.txt \
  -mc all -fs 0
```

### HTTP 手工验证

```bash
curl -i -sS 'http://127.0.0.1:8080/' \
  -H 'User-Agent: authorized-lab'
```

### 流量

```bash
tshark -r capture.pcapng -q -z io,phs
tshark -r capture.pcapng -Y 'http.request' \
  -T fields -e frame.time -e ip.src -e ip.dst \
  -e http.host -e http.request.uri
```

### 哈希

```bash
hashcat --identify hash.txt
hashcat -m 0 -a 0 hash.txt wordlist.txt --force
```

### 结果复核

```bash
sha256sum evidence.bin
```

把命令、退出码、输出摘要和文件哈希写入同一个 case 目录。
