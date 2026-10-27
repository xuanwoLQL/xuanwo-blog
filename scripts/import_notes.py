#!/usr/bin/env python3
"""Import curated security notes into Hugo content.

Sources:
  * xuanwoLQL/security-notes (public GitHub repository)
  * selected local Obsidian notes (crypto labs, OS note)

The script normalises Obsidian-flavoured Markdown into readable Hugo posts:
  * adds front matter (title / description / tags / categories / series)
  * turns tab-indented outlines into headings, lists and fenced code blocks
  * copies referenced images into static/images/notes/<slug>/
  * redacts demo credentials and personal information

Usage:
    SECURITY_NOTES_DIR=/path/to/security-notes python scripts/import_notes.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "content" / "notes"
IMG_DIR = ROOT / "static" / "images" / "notes"

REPO = Path(os.environ.get("SECURITY_NOTES_DIR", r"D:/tmp-blog/security-notes"))
LOCAL = Path(os.environ.get("NOTES_VAULT", r"D:/Program Files/Obsidian/zuodebiji/网络安全笔记"))

# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

CTF = "CTF Writeup"
WEB = "Web 安全"
PENTEST = "渗透测试"
CRYPTO = "密码学"
NET = "网络编程"
AI = "AI × 安全"
TOOLS = "安全工具"
GUIDE = "安全指南"
OS = "操作系统"

MANIFEST = [
    # ---- CTF Writeups -----------------------------------------------------
    dict(src="ctf-writeups/1.XXEmoeCTF2025.md", base="repo", slug="ctf-xxemoe-2025",
         title="XXE 实体注入读取 flag（XXEmoeCTF 2025）",
         desc="用外部实体直接读取 /var/www/html/flag.txt，最短的一次 XXE 通关记录。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "XXE", "Web"], weight=1),
    dict(src="ctf-writeups/2.伪装主页 + 隐藏入口 + 反序列化.md", base="repo", slug="ctf-npc-hidden-entry",
         title="伪装主页 + 隐藏入口 + 反序列化（NPCCTF 2025）",
         desc="从伪装首页找到隐藏入口，再顺着反序列化点拿下 flag。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "反序列化", "Web"], weight=2),
    dict(src="ctf-writeups/3.条件竞争解法(面对文件上传).md", base="repo", slug="ctf-upload-race-condition",
         title="文件上传条件竞争",
         desc="利用「检测通过 → 删除之前」的时间差，在上传文件被删前访问并执行。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "文件上传", "条件竞争"], weight=3),
    dict(src="ctf-writeups/4.php反序列化漏洞(pop链利用2).md", base="repo", slug="ctf-php-pop-chain-2",
         title="PHP 反序列化 POP 链（二）",
         desc="从题目源码出发，手工构造 PHP POP 链并验证危险方法调用。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "PHP", "反序列化"], weight=4),
    dict(src="ctf-writeups/5.使用curl 发POST,PUT,GET等等.md", base="repo", slug="ctf-curl-requests",
         title="用 curl 发送 POST / PUT / GET",
         desc="CTF 中常用的 curl 请求写法：参数编码、指定方法、带 Cookie 与文件上传。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "curl", "工具"], weight=5),
    dict(src="ctf-writeups/6.SQL注入题目示例.md", base="repo", slug="ctf-sqli-example",
         title="SQL 注入题目示例",
         desc="从登录框到联合查询，记录一道 SQL 注入题的分析与利用过程。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "SQL注入", "Web"], weight=6),
    dict(src="ctf-writeups/7.命令注入题型有回显.md", base="repo", slug="ctf-command-injection-echo",
         title="命令注入（有回显）",
         desc="有回显的命令注入题：探测分隔符、读取文件、定位 flag。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "命令注入", "RCE"], weight=7),
    dict(src="ctf-writeups/8.一个文件上传漏洞.md", base="repo", slug="ctf-upload-user-ini",
         title="文件上传：.user.ini + 图片马",
         desc="用 .user.ini 配合图片马绕过上传限制，拿到 WebShell。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "文件上传", ".user.ini"], weight=8),
    dict(src="ctf-writeups/9.非常经典的php无参数RCE绕过（无参数远程代码执行）.md", base="repo", slug="ctf-php-parameterless-rce",
         title="PHP 无参数 RCE 绕过",
         desc="无参数远程代码执行经典题：利用 PHP 内置函数完成命令执行。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "PHP", "RCE"], weight=9),
    dict(src="ctf-writeups/10.9th-ACTF-2025里面的upload.md", base="repo", slug="ctf-actf-2025-upload",
         title="9th ACTF 2025：多阶段漏洞链 upload",
         desc="SQL 注入、文件读取、身份伪造、命令注入与无回显外带串成的一条完整攻击链。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "ACTF", "漏洞链"], weight=10),
    dict(src="ctf-writeups/11.TGCTF 2025 AAA偷渡阴平(复仇).md", base="repo", slug="ctf-tgctf-2025-aaa",
         title="TGCTF 2025 AAA 偷渡阴平（复仇）",
         desc="利用 PHP 自身机制与函数特性完成编码绕过。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "TGCTF", "PHP"], weight=11),
    dict(src="ctf-writeups/12. TGCTF2025文件上传(伪装)+反序列化(实际).md", base="repo", slug="ctf-tgctf-2025-upload-deserialization",
         title="TGCTF 2025：伪装上传 + 反序列化",
         desc="文件上传只是表象，真正的考点是 PHP 反序列化。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "TGCTF", "文件上传", "反序列化"], weight=12),
    dict(src="ctf-writeups/13.SSRF(服务端请求伪造)，考察内网探测、协议利用和组合攻击.md", base="repo", slug="ctf-ssrf-intranet-exploit",
         title="SSRF：内网探测、协议利用与组合攻击",
         desc="从 URL 请求工具打到 Redis，利用 gopher 协议与编码绕过完成 SSRF 组合攻击。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "SSRF", "Redis", "内网"], weight=13),
    dict(src="ctf-writeups/14.TGCTF2025文件上传+PHP反序列化链.md", base="repo", slug="ctf-tgctf-2025-php-chain",
         title="TGCTF 2025：文件上传 + PHP 反序列化链",
         desc="上传伪装 + POP 链构造，通关 TGCTF 文件上传复仇题。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "TGCTF", "反序列化"], weight=14),
    dict(src="ctf-writeups/15.PHP协议与编码 压缩绕过.md", base="repo", slug="ctf-php-filter-encoding-bypass",
         title="PHP 协议与编码压缩绕过",
         desc="php://filter 被拉黑后，用编码与压缩包装器继续读取源码。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "PHP", "php://filter"], weight=15),
    dict(src="ctf-writeups/16.SQL注入题目.md", base="repo", slug="ctf-moectf-2026-sql-blind",
         title="moectf 2026 江洋大盗：黑名单绕过与布尔盲注",
         desc="在大量关键字被过滤的情况下，用布尔盲注逐字符还原数据。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "SQL注入", "盲注"], weight=16),
    dict(src="ctf-writeups/18.eval(命令注入).md", base="repo", slug="ctf-eval-command-injection",
         title="eval 命令注入",
         desc="只有一个 GET 参数的 eval 题，从信息收集到命令执行。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "命令注入", "RCE"], weight=18),
    dict(src="ctf-writeups/19.fastjson(WAF绕过+JNDI远程类加载RCE).md", base="repo", slug="ctf-fastjson-waf-bypass-rce",
         title="fastjson：WAF 绕过 + JNDI 远程类加载 RCE",
         desc="fastjson 1.2.24 经典漏洞：绕过 WAF 后用 JNDI 远程加载恶意类。",
         cat=CTF, series="CTF Writeup", tags=["CTF", "fastjson", "JNDI", "RCE"], weight=19),
    # ---- Web security -----------------------------------------------------
    dict(src="web-security/1.XML外部实体(XXE)注入(如检查库存).md", base="repo", slug="xxe-injection",
         title="XXE 外部实体注入",
         desc="从文件读取、SSRF 到盲 XXE，系统梳理外部实体注入的利用面与检测方法。",
         cat=WEB, series="Web 安全笔记", tags=["XXE", "Web安全", "SSRF"], weight=1),
    dict(src="web-security/2.参数爆破+PHP伪协议的利用.md", base="repo", slug="param-fuzz-php-wrapper",
         title="参数爆破与 PHP 伪协议利用",
         desc="moeCTF 2025 Web 第十一题：参数爆破配合 php://filter 读取源码。",
         cat=WEB, series="Web 安全笔记", tags=["PHP", "参数爆破", "php://filter"], weight=2),
    dict(src="web-security/4.蚁剑的使用.md", base="repo", slug="antsword-usage",
         title="蚁剑的安装与使用",
         desc="把 AntSword 装进终端命令，记录 WebShell 管理器的基本用法。",
         cat=TOOLS, series="安全工具箱", tags=["蚁剑", "WebShell", "工具"], weight=1),
    dict(src="web-security/5.文件上传漏洞.md", base="repo", slug="php-upload-prefix-bypass",
         title="文件上传：FF D8 FF 前缀绕过",
         desc="在 PHP 木马前补上 JPEG 文件头，绕过 MIME 与内容检测。",
         cat=WEB, series="Web 安全笔记", tags=["文件上传", "PHP", "绕过"], weight=3),
    dict(src="web-security/6.Apache的特殊文件：.htaccess文件.md", base="repo", slug="apache-htaccess-exploit",
         title="Apache .htaccess 利用",
         desc="上传 .htaccess 改变解析规则，让图片文件按 PHP 执行。",
         cat=WEB, series="Web 安全笔记", tags=["Apache", ".htaccess", "文件上传"], weight=4),
    dict(src="web-security/7.dirsearch的使用.md", base="repo", slug="dirsearch-usage",
         title="dirsearch 目录扫描",
         desc="目录与接口发现的基本参数、字典选择与结果判读。",
         cat=TOOLS, series="安全工具箱", tags=["dirsearch", "信息收集", "工具"], weight=2),
    dict(src="web-security/8.hashcat使用.md", base="repo", slug="hashcat-usage",
         title="hashcat 哈希破解",
         desc="常见哈希类型、字典与掩码攻击的参数速查。",
         cat=TOOLS, series="安全工具箱", tags=["hashcat", "密码破解", "工具"], weight=3),
    dict(src="web-security/9.压缩包的解密.md", base="repo", slug="archive-cracking-john",
         title="压缩包解密：zip2john / rar2john / 7z2john",
         desc="先从压缩包提取可破解哈希，再交给 John 跑字典。",
         cat=TOOLS, series="安全工具箱", tags=["John", "压缩包", "密码破解"], weight=4),
    dict(src="web-security/10.PHP代码的本地文件包含漏洞.md", base="repo", slug="php-lfi",
         title="PHP 本地文件包含（LFI）",
         desc="控制 file 参数包含任意文件，并分析自动追加 .php 后缀带来的限制。",
         cat=WEB, series="Web 安全笔记", tags=["PHP", "LFI", "文件包含"], weight=5),
    dict(src="web-security/11.PHP反序列化漏洞.md", base="repo", slug="php-deserialization",
         title="PHP 反序列化漏洞",
         desc="通过控制反序列化数据触发 __destruct，最终执行系统命令。",
         cat=WEB, series="Web 安全笔记", tags=["PHP", "反序列化", "RCE"], weight=6),
    dict(src="web-security/12.php反序列化漏洞(pop链利用).md", base="repo", slug="php-pop-chain",
         title="PHP 反序列化 POP 链",
         desc="从题目代码解析属性传递关系，构造 POP 链完成利用。",
         cat=WEB, series="Web 安全笔记", tags=["PHP", "POP链", "反序列化"], weight=7),
    dict(src="web-security/13.SSTI(服务器模板注入).md", base="repo", slug="ssti-template-injection",
         title="SSTI 服务器模板注入",
         desc="从模板语法探测到命令执行，记录 SSTI 的常见利用路径。",
         cat=WEB, series="Web 安全笔记", tags=["SSTI", "模板注入", "RCE"], weight=8),
    dict(src="web-security/14.Java反序列化.md", base="repo", slug="java-deserialization-lab",
         title="Java 反序列化靶场实录",
         desc="从 readObject、可控反射和 HashMap 触发点出发，拆解完整的 Java 反序列化利用链。",
         cat=WEB, series="Web 安全笔记", tags=["Java", "反序列化", "HashMap", "靶场"], weight=9,
         curated=True),
    dict(src="web-security/15.SQL注入.md", base="repo", slug="sql-injection-detection",
         title="SQL 注入原理与检测",
         desc="注入点类型、查询位置、UNION 与盲注的检测思路。",
         cat=WEB, series="Web 安全笔记", tags=["SQL注入", "Web安全", "检测"], weight=10),
    dict(src="web-security/19.Vite开发服务类型.md", base="repo", slug="vite-arbitrary-file-read",
         title="Vite 开发服务任意文件读取",
         desc="从版本指纹到 CVE 检索，复现 Vite 开发服务的任意文件读取。",
         cat=WEB, series="Web 安全笔记", tags=["Vite", "CVE", "文件读取"], weight=11),
    dict(src="web-security/20.TG2025前端GAME Plus(任意文件读取漏洞).md", base="repo", slug="tgctf-2025-vite-game-plus",
         title="TGCTF 2025 前端 GAME Plus：任意文件读取",
         desc="前端游戏的版本指纹与 CVE 组合利用。",
         cat=WEB, series="Web 安全笔记", tags=["Vite", "CVE", "TGCTF"], weight=12),
    dict(src="web-security/21.web安全+基础设施渗透(内网横向).md", base="repo", slug="web-infrastructure-lateral",
         title="Web 安全 + 基础设施渗透（内网横向）",
         desc="业务逻辑漏洞与速率限制绕过之后，继续向基础设施层横向。",
         cat=WEB, series="Web 安全笔记", tags=["内网横向", "业务逻辑", "渗透"], weight=13),
    dict(src="web-security/22.原型污染(Prototype Pollution).md", base="repo", slug="prototype-pollution",
         title="原型污染（Prototype Pollution）",
         desc="moeCTF 2026 合乎周礼：从原型污染到属性覆盖的利用思路。",
         cat=WEB, series="Web 安全笔记", tags=["原型污染", "JavaScript", "Web安全"], weight=14),
    dict(src="web-security/18.OpenCode辅助解题(提示词的利用).md", base="repo", slug="opencode-ctf-solving",
         title="OpenCode 辅助 CTF 解题",
         desc="用 OpenCode Agent 读取题目、调用工具并逐步收敛解法的实践。",
         cat=AI, series="AI × 安全", tags=["AI", "OpenCode", "CTF"], weight=1),
    dict(src="web-security/24.Web_CTF提示词模板_增强版.md", base="repo", slug="web-ctf-prompt-template",
         title="Web CTF 解题提示词模板",
         desc="适配本机工具链的 Web CTF 提示词模板，强调验证与证据链。",
         cat=AI, series="AI × 安全", tags=["AI", "提示词", "Web CTF"], weight=2),
    dict(src="web-security/25.Reverse_CTF提示词模板_增强版.md", base="repo", slug="reverse-ctf-prompt-template",
         title="Reverse / Misc CTF 解题提示词模板",
         desc="逆向与 Misc 题的 Agent 提示词模板，包含工具索引与验证要求。",
         cat=AI, series="AI × 安全", tags=["AI", "提示词", "Reverse"], weight=3),
    dict(src="web-security/31.渗透测试提示词.md", base="repo", slug="pentest-prompt-template",
         title="渗透测试提示词模板",
         desc="面向靶场渗透的提示词模板，强调授权边界与结果复核。",
         cat=AI, series="AI × 安全", tags=["AI", "提示词", "渗透"], weight=4),
    dict(src="web-security/26.SecLists字典说明.md", base="repo", slug="seclists-guide",
         title="SecLists 字典用途说明",
         desc="按场景整理 SecLists 的目录字典、用户名字典、密码字典与 Payload 清单。",
         cat=TOOLS, series="安全工具箱", tags=["SecLists", "字典", "信息收集"], weight=6),
    # ---- Pentest ----------------------------------------------------------
    dict(src="pentest/1.bug库渗透测试1 wp.md", base="repo", slug="pentest-bugku-1",
         title="甲公司内网渗透测试（11/11 FLAG）",
         desc="从外网入口到 Docker 内网横向，11 个 FLAG 的完整攻击链与复盘。",
         cat=PENTEST, series="内网渗透", tags=["内网渗透", "Docker", "靶场"], weight=1),
    dict(src="pentest/2.bug库渗透测试2.md", base="repo", slug="pentest-bugku-2",
         title="渗透测试 2：Typecho 靶场（9/9 FLAG）",
         desc="Typecho 博客靶场：入口打点、权限提升与内网横向的完整记录。",
         cat=PENTEST, series="内网渗透", tags=["内网渗透", "Typecho", "靶场"], weight=2),
    dict(src="pentest/3.LingJing的vulntarget-b.md", base="repo", slug="pentest-vulntarget-b",
         title="LingJing vulntarget-b 靶场",
         desc="vulntarget-b 靶场通关笔记与参考资料整理。",
         cat=PENTEST, series="内网渗透", tags=["内网渗透", "vulntarget", "靶场"], weight=3),

    # ---- Guide ------------------------------------------------------------
    dict(src="ctf-beginner-guide/网络安全与CTF新手起步指南_精修版.md", base="repo", slug="security-ctf-beginner-guide",
         title="网络安全与 CTF 新手起步指南",
         desc="从第一道 Flag 到 AI 时代的技能路线：方向选择、靶场、Writeup、知识库与授权边界。",
         cat=GUIDE, series="安全入门", tags=["CTF", "学习路线", "新手"], weight=1,
         local="CTF比赛/CTF/网络安全与CTF新手起步指南_精修版.md"),

    # ---- Cryptography (local labs, redacted) ------------------------------
    dict(src="密码学/实验1 仿射变换加解密实验报告/实验1 仿射变换加解密实验报告.md", base="local", slug="crypto-affine-cipher",
         title="仿射变换加解密实验",
         desc="从公式推导到纯 C 实现：312 组密钥、暴力枚举与卡方频率分析破译。",
         cat=CRYPTO, series="密码学实验", tags=["密码学", "仿射密码", "C"], weight=1),
    dict(src="密码学/实验2 DES加密算法实验/README.md", base="local", slug="crypto-des-cipher",
         title="DES 加密算法实验",
         desc="按 FIPS 46-3 从零实现 DES：16 轮 Feistel、PKCS#7 填充与标准向量验证。",
         cat=CRYPTO, series="密码学实验", tags=["密码学", "DES", "C"], weight=2),
    dict(src="cryptography/rsa-lab/README.md", base="repo", slug="crypto-rsa-lab",
         title="RSA 加解密实验",
         desc="不依赖第三方密码库的 RSA 教学实现：大整数、素数检测、CRT 加速与分块处理。",
         cat=CRYPTO, series="密码学实验", tags=["密码学", "RSA", "C++"], weight=3,
         local="密码学/实验3 RSA/README_C++版.md"),
    dict(src="密码学/实验4 MD5算法实验/实验4 MD5算法实验报告.md", base="local", slug="crypto-md5",
         title="MD5 算法实验",
         desc="从填充、分组到四轮压缩，纯 C 实现 MD5 并与 hashlib / certutil 交叉验证。",
         cat=CRYPTO, series="密码学实验", tags=["密码学", "MD5", "C"], weight=4, drop_first_h1=True),
    dict(src="密码学/密码学发展历程、原理算法与应用挑战研究.md", base="local", slug="crypto-history-paper",
         title="密码学发展历程、原理算法与应用挑战",
         desc="从古典密码到后量子时代：对称密码、公钥密码、哈希与数字签名的演进脉络。",
         cat=CRYPTO, series="密码学实验", tags=["密码学", "后量子", "论文"], weight=5, drop_first_h1=True),

    # ---- Python network programming --------------------------------------
    dict(src="python-learning/socketserver编程实验/README.md", base="repo", slug="python-socketserver-lab",
         title="socketserver 编程实验",
         desc="用 socketserver 写 TCP / UDP / 多线程 / 混合模式服务器与客户端。",
         cat=NET, series="Python 网络编程", tags=["Python", "Socket", "并发"], weight=1,
         local="python学习/socketserver编程实验/README.md"),
    dict(src="python-learning/基于Socket编程的FTP服务器/README.md", base="repo", slug="python-ftp-server",
         title="基于 Socket 的 FTP 服务器",
         desc="手写 FTP 协议、用户认证、目录浏览与文件传输，配套 tkinter 客户端。",
         cat=NET, series="Python 网络编程", tags=["Python", "FTP", "Socket"], weight=2,
         local="python学习/基于Socket编程的FTP服务器/README.md"),
    dict(src="python-learning/基于非阻塞IO模型(select)的并发实验/README.md", base="repo", slug="python-select-io",
         title="select 非阻塞 IO 并发实验",
         desc="用 select 多路复用同时处理多个客户端连接。",
         cat=NET, series="Python 网络编程", tags=["Python", "select", "IO多路复用"], weight=3,
         local="python学习/基于非阻塞IO模型(select)的并发实验/README.md"),
    dict(src="python-learning/multiprocessing作业/README.md", base="repo", slug="python-multiprocessing-copy",
         title="multiprocessing 多进程文件复制",
         desc="按字节对半切分文件，用多进程并行复制并校验结果。",
         cat=NET, series="Python 网络编程", tags=["Python", "多进程", "文件IO"], weight=4,
         local="python学习/multiprocessing作业/README.md"),
    dict(src="python-learning/多进程文件下载作业/README.md", base="repo", slug="python-multiprocess-download",
         title="多进程文件下载",
         desc="把文件分段交给多个进程下载，再合并校验。",
         cat=NET, series="Python 网络编程", tags=["Python", "多进程", "下载"], weight=5,
         local="python学习/多进程文件下载作业/README.md"),
    dict(src="python-learning/实验五-基于多线程的文件下载实验/README.md", base="repo", slug="python-multithread-download",
         title="多线程文件下载",
         desc="多线程分块下载、进度显示与并发一致性测试。",
         cat=NET, series="Python 网络编程", tags=["Python", "多线程", "下载"], weight=6,
         local="python学习/实验五-基于多线程的文件下载实验/README.md"),
    dict(src="python-learning/GUI聊天室实例作业/README.md", base="repo", slug="python-gui-chatroom",
         title="GUI 聊天室",
         desc="基于 Socket 与 tkinter 的图形化聊天室，包含协议设计与消息广播。",
         cat=NET, series="Python 网络编程", tags=["Python", "tkinter", "聊天室"], weight=7,
         local="python学习/GUI聊天室实例作业/README.md"),
    dict(src="python-learning/fork理解和使用/README.md", base="repo", slug="python-fork-chatroom",
         title="fork 理解与群聊聊天室",
         desc="用 fork 派生多进程处理客户端，理解进程模型与群聊广播。",
         cat=NET, series="Python 网络编程", tags=["Python", "fork", "多进程"], weight=8,
         local="python学习/fork理解和使用/README.md"),

    # ---- Operating system -------------------------------------------------
    dict(src="操作系统/宏内核和微内核.md", base="local", slug="os-monolithic-vs-microkernel",
         title="宏内核与微内核",
         desc="从通信方式、性能、稳定性与扩展性四个维度对比宏内核与微内核。",
         cat=OS, series="系统基础", tags=["操作系统", "内核架构"], weight=1),
]

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

IDENTITY = re.compile(r"(?:姓\s*名|学\s*号|班\s*号|评阅老师|成\s*绩)\s*[:：]?")
SECRETS = [
    (re.compile(r"secret_pAss_[A-Za-z0-9]+"), "[已脱敏]"),
    (re.compile(r"app_escccret_[A-Za-z0-9]+"), "[已脱敏]"),
    (re.compile(r"root123"), "[已脱敏]"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[已脱敏]"),
    (re.compile(r"(?<!\d)\d{10,12}(?!\d)"), "[已脱敏]"),
    (re.compile(r"(?<![A-Za-z])D:\\"), "~/"),
    (re.compile(r"(?<![A-Za-z])D:/"), "~/"),
]
PRIVATE_REDACTIONS_FILE = Path(__file__).with_name("private_redactions.txt")


def load_private_redactions() -> list[re.Pattern[str]]:
    if not PRIVATE_REDACTIONS_FILE.exists():
        return []
    patterns: list[re.Pattern[str]] = []
    for line in PRIVATE_REDACTIONS_FILE.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        patterns.append(re.compile(value))
    return patterns


PRIVATE_REDACTIONS = load_private_redactions()


CODE_CMD = re.compile(
    r"^(?:\$ )?(?:curl|wget|nmap|sqlmap|python3?|pip3?|gcc|g\+\+|make|ssh|scp|nc|ncat|netcat|"
    r"dirsearch|gobuster|ffuf|hashcat|john|zip2john|rar2john|7z2john|docker|msfconsole|msfvenom|"
    r"chmod|chown|sudo|ls|cd|cat|echo|grep|awk|sed|find|tar|unzip|zip|7z|rar|systemctl|service|"
    r"redis-cli|mysql|psql|telnet|ping|dig|nslookup|whoami|id|uname|ifconfig|netstat|ss|export|"
    r"source|git|hugo|npm|yarn|node|php|java|javac|javap|jar|base64|xxd|strings|binwalk|foremost|"
    r"volatility|tshark|tcpdump|searchsploit|whatweb|nikto|wpscan|nuclei|httpx|subfinder|amass|"
    r"masscan|hydra|medusa|crackmapexec|impacket|bloodhound|chisel|frp|proxychains|ssh-keygen|"
    r"openssl|apt|apt-get|yum|dnf|pacman|vim|nano|touch|mkdir|rm|cp|mv|ln|ps|kill|pkill|"
    r"route|arp|iptables|ufw|firewall-cmd|tcpdump|python)\b",
    re.I,
)
CODE_PREFIX = re.compile(
    r"^(?:<[?!]?[A-Za-z]|SELECT\b|INSERT\b|UPDATE\b|DELETE\b|UNION\b|WHERE\b|ORDER BY\b|"
    r"FROM\b|CREATE\b|DROP\b|ALTER\b|import\s|from\s+\S+\s+import\s|def\s|class\s|"
    r"public\s|private\s|protected\s|package\s|#include|int\s+main|<\?php|function\s|"
    r"(?:var|const|let)\s+\w+\s*=|return\s|\}\s*$)",
    re.I,
)
JSONISH = re.compile(r"^[\[{]\s*[\"'\w]")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
NUM_HEAD = re.compile(r"^(\d+)[.、)]\s*(\S.*)$")
CN_HEAD = re.compile(r"^([一二三四五六七八九十]+)[、.]\s*(\S.*)$")


def strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return text


def sanitize(text: str) -> str:
    for pattern, repl in SECRETS:
        text = pattern.sub(repl, text)
    for pattern in PRIVATE_REDACTIONS:
        text = pattern.sub("[已脱敏]", text)
    return text


def is_code_line(content: str) -> bool:
    if CODE_CMD.match(content):
        return True
    if CODE_PREFIX.match(content):
        return True
    if JSONISH.match(content) and (content.endswith("}") or content.endswith("]")):
        return True
    # A line that is entirely one long inline-code command.
    if content.startswith("`") and content.endswith("`") and len(content) > 12:
        inner = content.strip("`").strip()
        if CODE_CMD.match(inner):
            return True
    return False


def code_language(lines: list[str]) -> str:
    joined = "\n".join(lines)
    head = lines[0].strip() if lines else ""
    if "<?xml" in joined or "<!DOCTYPE" in joined or head.startswith("<"):
        return "xml"
    if "<?php" in joined:
        return "php"
    if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|UNION|WHERE|ORDER BY)\b", joined, re.I):
        return "sql"
    if re.search(r"^\s*(import|from|def|class)\s", joined, re.M):
        return "python"
    if re.search(r"^\s*(public|private|protected|package|class)\s", joined, re.M):
        return "java"
    if "#include" in joined or "int main" in joined:
        return "c"
    if JSONISH.match(head):
        return "json"
    if head.startswith("```"):
        return ""
    return "bash"


def dedent_lines(lines: list[str]) -> list[str]:
    nonblank = [l for l in lines if l.strip()]
    if not nonblank:
        return []
    indent = min(len(l) - len(l.lstrip(" ")) for l in nonblank)
    return [l[indent:] if len(l) >= indent else l for l in lines]


def convert_body(text: str, title: str, drop_first_h1: bool = False) -> str:
    text = strip_front_matter(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = sanitize(text)

    raw_lines = text.split("\n")
    out: list[str] = []
    code_buf: list[str] = []
    fence_lang = ""
    in_fence = False
    fence_lines: list[str] = []
    first_h1_dropped = False
    prev_blank = True
    block_type = ""

    def flush_code() -> None:
        nonlocal code_buf, fence_lang, prev_blank
        if not code_buf:
            return
        body = dedent_lines(code_buf)
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        if body:
            lang = fence_lang or code_language(body)
            if out and not prev_blank:
                out.append("")
            out.append(f"```{lang}")
            out.extend(l.rstrip() for l in body)
            out.append("```")
            out.append("")
            prev_blank = True
        code_buf = []
        fence_lang = ""

    def blank() -> None:
        nonlocal prev_blank
        if out and not prev_blank:
            out.append("")
        prev_blank = True

    for raw in raw_lines:
        line = raw.expandtabs(4)

        # Preserve source fenced blocks verbatim instead of re-wrapping them.
        if in_fence:
            fence_lines.append(line.rstrip())
            if line.strip().startswith("```"):
                in_fence = False
                if out and not prev_blank:
                    out.append("")
                out.extend(fence_lines)
                out.append("")
                prev_blank = True
                fence_lines = []
            continue

        if line.strip().startswith("```"):
            flush_code()
            in_fence = True
            fence_lines = [line.rstrip()]
            continue

        if not line.strip():
            flush_code()
            if block_type:
                out.append("")
                block_type = ""
                prev_blank = True
            blank()
            continue

        if IDENTITY.search(line.strip()):
            continue

        content = line.strip()
        level = (len(line) - len(line.lstrip(" "))) // 4

        # Markdown table / blockquote pass-through. Consecutive rows must stay
        # adjacent, otherwise Goldmark renders each row as a separate table.
        is_table = content.startswith("|")
        is_quote = content.startswith(">")
        if is_table or is_quote:
            flush_code()
            new_type = "table" if is_table else "quote"
            if block_type != new_type:
                if out and not prev_blank:
                    out.append("")
                prev_blank = False
            block_type = new_type
            out.append(content)
            prev_blank = False
            continue

        if block_type:
            out.append("")
            block_type = ""
            prev_blank = True

        # Source headings.
        m = HEADING.match(content)
        if m:
            flush_code()
            htext = m.group(2).strip()
            if len(m.group(1)) == 1 and not first_h1_dropped and (
                drop_first_h1 or title[:6] in htext or htext[:6] in title
            ):
                first_h1_dropped = True
                continue
            level_out = min(len(m.group(1)) + 1, 4)
            if not prev_blank:
                out.append("")
            out.append("#" * level_out + " " + htext)
            out.append("")
            prev_blank = True
            continue

        # "#1." / "#2." are Obsidian step markers, not headings.
        content = re.sub(r"^#(?=\d)", "", content)
        content = re.sub(r"^#([0-9]+\()", r"\1", content)

        # Top-level Chinese / numeric section headings.
        if level == 0:
            m = NUM_HEAD.match(content)
            if (
                m
                and len(content) <= 80
                and not content.endswith("。")
                and "](" not in content
                and not content.startswith("[")
            ):
                flush_code()
                if not prev_blank:
                    out.append("")
                out.append(f"## {m.group(1)}. {m.group(2).strip()}")
                out.append("")
                prev_blank = True
                continue
            m = CN_HEAD.match(content)
            if m and len(content) <= 80 and "](" not in content:
                flush_code()
                if not prev_blank:
                    out.append("")
                out.append(f"## {m.group(1)}、{m.group(2).strip()}")
                out.append("")
                prev_blank = True
                continue

        if is_code_line(content):
            if content.startswith("`") and content.endswith("`") and len(content) > 12:
                content = content.strip("`").strip()
            code_buf.append(content)
            continue

        flush_code()

        # Indented outline -> nested bullet.
        if level > 0:
            bullet = "  " * (level - 1) + "- " + content
            out.append(bullet)
            prev_blank = False
            continue

        # Plain prose at top level.
        if content.startswith(("- ", "* ", "+ ")):
            out.append("- " + content[2:].strip())
        else:
            out.append(content)
        prev_blank = False

    flush_code()
    body = "\n".join(out)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def copy_images(text: str, src_path: Path, slug: str) -> str:
    out_dir = IMG_DIR / slug
    mapping: dict[str, str] = {}
    counter = 0

    def register(original: Path) -> str | None:
        nonlocal counter
        if not original.exists() or not original.is_file():
            return None
        if original.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            return None
        key = str(original)
        if key in mapping:
            return mapping[key]
        counter += 1
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = f"img-{counter:02d}{original.suffix.lower()}"
        shutil.copy2(original, out_dir / safe)
        url = f"/images/notes/{slug}/{safe}"
        mapping[key] = url
        return url

    # Standard Markdown images.
    def repl_md(match: re.Match) -> str:
        alt, href = match.group(1), match.group(2)
        href = unquote(href.strip().strip("<>"))
        if href.startswith(("http://", "https://", "data:", "/")):
            return match.group(0)
        candidates = [
            (src_path.parent / href).resolve(),
            (LOCAL / href).resolve(),
            (LOCAL / "attachments" / href).resolve(),
            (REPO / "attachments" / Path(href).name).resolve(),
            (LOCAL / Path(href).name).resolve(),
        ]
        url = next((u for p in candidates if (u := register(p))), None)
        return f"![{alt}]({url})" if url else f"*[图片：{alt or '已省略'}]*"

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl_md, text)

    # Obsidian embeds: ![[name|width]]
    def repl_obs(match: re.Match) -> str:
        name = unquote(match.group(1).split("|")[0].strip())
        for base in (src_path.parent, LOCAL, LOCAL / "attachments", REPO / "attachments"):
            url = register(base / name)
            if url:
                return f"![]({url})"
        return ""

    text = re.sub(r"!\[\[([^\]]+)\]\]", repl_obs, text)
    return text


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_local_cache: dict[str, Path | None] = {}


def local_path_for(item: dict) -> Path | None:
    if item.get("local"):
        p = LOCAL / item["local"]
        return p if p.exists() else None
    if item["base"] == "local":
        p = LOCAL / item["src"]
        return p if p.exists() else None
    name = Path(item["src"]).name
    if name not in _local_cache:
        matches = list(LOCAL.rglob(name))
        _local_cache[name] = matches[0] if len(matches) == 1 else None
    return _local_cache[name]


def resolve_date(item: dict, index: int) -> datetime:
    p = local_path_for(item)
    if p and p.exists():
        stamp = p.stat().st_mtime
    else:
        # Public repo snapshot date.
        stamp = datetime(2026, 10, 21, 20, 0).timestamp()
    dt = datetime.fromtimestamp(stamp)
    if dt.hour == 0 and dt.minute == 0:
        dt = dt.replace(hour=20, minute=index % 60)
    return dt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not REPO.exists():
        print(f"security-notes not found: {REPO}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0

    for index, item in enumerate(MANIFEST, start=1):
        target = OUT_DIR / f"{item['slug']}.md"
        if item.get("curated") and target.exists():
            print(f"  SKIP {item['slug']}  (curated file already exists)")
            continue

        if item["base"] == "repo":
            src_path = REPO / item["src"]
            source_repo = f"https://github.com/xuanwoLQL/security-notes/blob/main/{item['src']}"
        else:
            src_path = LOCAL / item["src"]
            source_repo = None
        if not src_path.exists():
            print(f"  MISS {src_path}")
            continue

        text = src_path.read_text(encoding="utf-8", errors="ignore")
        body = convert_body(text, item["title"], item.get("drop_first_h1", False))
        body = copy_images(body, src_path, item["slug"])
        if len(body.strip()) < 80:
            print(f"  EMPTY {item['slug']}")
            continue

        dt = resolve_date(item, index)
        date_str = dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        fm = [
            "---",
            f"title: {json.dumps(item['title'], ensure_ascii=False)}",
            f"slug: {json.dumps(item['slug'], ensure_ascii=False)}",
            f"date: {date_str}",
            f"lastmod: {date_str}",
            "draft: false",
            'author: ["xuanwo"]',
            f"description: {json.dumps(item['desc'], ensure_ascii=False)}",
            f"summary: {json.dumps(item['desc'], ensure_ascii=False)}",
            f"tags: {json.dumps(item['tags'], ensure_ascii=False)}",
            f"categories: {json.dumps([item['cat']], ensure_ascii=False)}",
            f"series: {json.dumps([item['series']], ensure_ascii=False)}",
            f"weight: {item['weight']}",
            "ShowToc: true",
            "TocOpen: false",
            "hidemeta: false",
            "comments: false",
            "showReadingTime: true",
            "ShowBreadCrumbs: true",
            "ShowPostNavLinks: true",
            "ShowCodeCopyButtons: true",
        ]
        if source_repo:
            fm.append(f"source_repo: {json.dumps(source_repo, ensure_ascii=False)}")
        fm.append("---")
        out_text = "\n".join(fm) + "\n\n" + body + "\n"
        (OUT_DIR / f"{item['slug']}.md").write_text(out_text, encoding="utf-8")
        generated += 1
        print(f"  OK  {item['slug']}  ({len(body)} chars)")

    print(f"\nGenerated {generated} notes into {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
