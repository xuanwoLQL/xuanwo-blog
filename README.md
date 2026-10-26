# 漩涡（xuanwo）博客工程

基于 **Hugo + PaperMod + Nginx** 的静态博客工程，默认深色主题、Profile 首页、中文界面、全站搜索、阅读时间、代码复制和自动目录。

源码仓库：<https://github.com/xuanwoLQL/xuanwo-blog>

项目内置的 PaperMod 来自 `master` 快照，提交：

```text
118119693d8b5ac211b939775678310973bcb232
2026-10-25T06:23:51Z
```

## 目录结构

```text
博客的构建/
├─ hugo.yaml
├─ content/
│  ├─ _index.md
│  ├─ about.md
│  ├─ archives.md
│  ├─ search.md
│  └─ posts/
│     ├─ _index.md
│     └─ hello-xuanwo.md
├─ assets/css/extended/zz-xuanwo.css
├─ docs/previews/
├─ static/
│  ├─ images/profile.png
│  ├─ images/og-cover.png
│  ├─ favicon.svg
│  ├─ favicon-16x16.png
│  ├─ favicon-32x32.png
│  ├─ apple-touch-icon.png
│  └─ safari-pinned-tab.svg
├─ themes/PaperMod/
├─ nginx/blog
├─ scripts/generate-assets.py
├─ scripts/build-upload.sh
├─ scripts/build-upload.ps1
├─ THEME_VERSION.md
└─ .deploy.env.example
```

## 效果预览

- [首页深色桌面版](docs/previews/home-desktop.png)
- [首页深色移动版](docs/previews/home-mobile.png)
- [首页浅色桌面版](docs/previews/home-light.png)
- [文章页目录与代码块](docs/previews/post-desktop.png)
- [关于页移动版](docs/previews/about-mobile.png)

## 1. 上线前必须确认

### 社交与联系方式

已配置为：

```yaml
socialIcons:
  - name: github
    title: GitHub
    url: "https://github.com/xuanwoLQL"
  - name: email
    title: 邮箱
    url: "mailto:15060801795@163.com"
```

`content/about.md` 中的 GitHub 和邮箱已同步更新。

### 域名

当前 `hugo.yaml` 使用：

```yaml
baseURL: "http://47.93.123.112/"
```

绑定域名后改成：

```yaml
baseURL: "https://blog.example.com/"
```

### 头像

`static/images/profile.png` 是程序生成的占位头像。替换成自己的照片时保持文件名不变即可；如果更换尺寸，同步调整：

```yaml
profileMode:
  imageWidth: 180
  imageHeight: 180
```

## 2. 本地预览

需要 **Hugo Extended 0.158+**。本项目已用 Hugo Extended `v0.168.0` 验证。

Windows 可用：

```powershell
winget install Hugo.Hugo.Extended
```

在 Git Bash 中进入项目目录：

```bash
cd "/d/Program Files/Obsidian/zuodebiji/网络安全笔记/博客的构建"
hugo server -D
```

浏览器打开 `http://127.0.0.1:1313/`。

## 3. 构建并上传

### Git Bash / Linux / macOS

```bash
cd "/d/Program Files/Obsidian/zuodebiji/网络安全笔记/博客的构建"
cp .deploy.env.example .deploy.env
# 编辑 .deploy.env，填写 SSH 用户、主机和私钥路径
bash scripts/build-upload.sh
```

推荐使用 SSH 配置别名，避免在脚本里写私钥路径：

```sshconfig
Host xuanwo-blog
    HostName 47.93.123.112
    User root
    IdentityFile ~/.ssh/xuanwo_blog_deploy
    IdentitiesOnly yes
```

然后在 `.deploy.env` 中设置：

```bash
DEPLOY_TARGET=xuanwo-blog
```

### PowerShell（Windows）

```powershell
cd "D:\Program Files\Obsidian\zuodebiji\网络安全笔记\博客的构建"
$env:SSH_KEY = "C:\Users\Administrator\.ssh\xuanwo_blog_deploy"
.\scripts\build-upload.ps1
```

PowerShell 脚本通过 tar + scp 上传，不会删除服务器上的旧文件；Git Bash 脚本在存在 `rsync` 时会使用 `--delete` 清理旧文件。正式部署建议使用 Git Bash + rsync。

## 4. 配置 Nginx

服务器是 Ubuntu 24.04。首次部署：

```bash
sudo apt update
sudo apt install -y nginx
sudo mkdir -p /var/www/blog /var/www/certbot

sudo cp nginx/blog /etc/nginx/sites-available/blog
sudo ln -sfn /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/blog
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
```

如果 `nginx -t` 提示 `default_server` 重复，说明还有其他默认站点仍被启用，先检查：

```bash
ls -l /etc/nginx/sites-enabled/
```

配置完成后访问：

```text
http://47.93.123.112/
```

### Nginx 安全配置包含

- 拒绝 `.git`、`.env` 等隐藏文件
- 拒绝 `.bak`、`.zip`、`.sql`、`.dump`、`.tar.gz` 等备份和数据库文件
- 拒绝常见 WordPress、phpMyAdmin、管理后台扫描路径
- 每 IP 基础请求限流和并发连接限制
- 隐藏 Nginx 版本号
- 基础安全响应头与 CSP
- HTML 和搜索索引短缓存，CSS/JS/字体长缓存，图片 30 天缓存
- 仅允许静态页面常用的 `GET` 和 `HEAD`

这些措施用于降低自动化扫描和误配置风险，不等同于 WAF 或 DDoS 防护。

## 5. 域名、ICP 与 HTTPS

服务器位于阿里云北京地域。正式绑定域名前，需要完成 **ICP 备案**，再把域名的 A 记录指向：

```text
47.93.123.112
```

备案和 DNS 生效后安装 Certbot：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d blog.example.com
```

Certbot 会自动补充 443 配置和 HTTP 跳转。**确认 HTTPS 连续运行稳定后，再考虑开启 HSTS**；不要在证书或域名尚未稳定时提前启用。

## 6. 写新文章

```bash
hugo new content posts/your-post-name.md
```

文章使用 Markdown 编写。建议的 Front Matter：

```yaml
---
title: "文章标题"
date: 2026-10-26T20:30:00+08:00
draft: false
author: ["xuanwo"]
description: "一句话摘要"
tags: ["CTF", "Web"]
categories: ["Writeup"]
ShowToc: true
TocOpen: false
---
```

## 7. 安全检查清单

- 阿里云安全组只放行 `22/80/443`，数据库和管理端口不要开放。
- SSH 使用密钥登录；条件允许时创建普通部署用户，不要长期直接使用 root 部署。
- 发布前确认公开邮箱、域名和联系方式无误，不要提交 `.deploy.env`。
- 不要在 `static/`、`content/` 中放置密钥、票据、真实靶场密码或未打码的敏感数据。
- 发布漏洞复现文章前检查是否包含内网地址、账号口令、个人隐私和未授权目标信息。
- 定期更新 Ubuntu、Nginx 和 Hugo；定期备份 `content/`、`hugo.yaml`、`assets/` 与 `static/`。
- 限流只能降低低质量扫描压力，遇到持续攻击应使用阿里云 WAF、DDoS 防护和访问日志分析。

