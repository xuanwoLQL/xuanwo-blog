# 漩涡（xuanwo）博客工程

基于 **Hugo + PaperMod + Nginx** 的个人安全博客。<br>
线上地址：<http://47.93.123.112/> · 源码：<https://github.com/xuanwoLQL/xuanwo-blog>

这一版把原先「一张居中卡片」的 Profile 首页重做成了完整的个人站点：

- **个人档案首页**：首屏直接呈现方向、近期竞赛、企业实践与公开产出
- **阅读路径**：先看笔记专题，再看最近更新，降低首次访问者的选择成本
- **Bento 项目墙**：17 个公开项目，按方向筛选，明确区分 6 个站内详情与 11 个 GitHub 外链
- **笔记库**：61 篇笔记，9 个专题，支持即时搜索与分类筛选
- **阅读体验**：阅读进度、粘性目录、代码复制、系列上下篇、相关笔记、图片灯箱
- **复现质量**：61 篇笔记均配流程图 / 架构图 / 数据流图，代码与命令按步骤展开
- **完整源码**：网络编程、DES、RSA、SSRF、盲注等实验提供完整文件或源码包下载
- **完整页面**：项目、笔记、归档、标签、搜索、关于、404
- **明暗双主题**：默认深色，右上角切换，`prefers-reduced-motion` 下自动降级动画

## 当前状态

| 项 | 内容 |
| --- | --- |
| 线上地址 | <http://47.93.123.112/> |
| 服务器 | 阿里云 Ubuntu 24.04，Nginx 1.24 |
| 构建 | Hugo Extended `v0.168.0` |
| 主题 | PaperMod 快照 + 项目级自定义模板 / CSS / JS |
| 发布质量门 | GitHub Actions + 内链检查 + 首页 / SEO / CSP 检查 |
| 部署 | tar + scp，独立 release 目录原子切换，保留上一版 |
| HTTPS | 等待域名与 ICP 备案，本次未处理 |

> 2026-10-27 完成面试评审修复、首页信息架构重排并重新部署；旧站保留在 `/var/www/blog-old-*`，可人工回滚。

## 内容来源与边界

### 已收录

- **`security-notes` 公开仓库**：CTF Writeup、Web 安全笔记、内网靶场、CTF 入门指南
- **本地密码学实验**：仿射密码、DES、RSA、MD5（已移除姓名、学号、院校、教师信息）
- **本地操作系统笔记**：宏内核 / 微内核
- **Agent Skills 工程记录**：CTF、应急响应、MCP 边界与验收
- **GitHub 公开仓库**：17 个项目，来自 GitHub API（`data/projects.yaml`）

### 暂不收录

- **OpenHarmony 笔记**：暂不收录；`xuanwo` 仓库以项目卡片形式列出，博客内不展开其笔记内容
- 课程作业中的个人隐私、家教、TypeScript 流水笔记
- 真实业务系统、真实凭据、内网地址

### 脱敏规则

`scripts/import_notes.py` 会处理：

- 已知演示口令：`root123`、`secret_pAss_*`、`app_esccret_*` → `[已脱敏]`
- 手机号、10–12 位学号等通用敏感模式 → `[已脱敏]`
- 姓名、班号、评阅老师、成绩等身份字段行 → 删除
- 本机绝对路径 `D:\...` → `~/...`
- 公开靶场中作为解题步骤出现的演示口令保留（如 `admin/admin`），与 `security-notes` 仓库的公开说明一致

项目自身的姓名、院校等非通用词不要写进公开源码。复制
`scripts/private_redactions.example.txt` 为 `scripts/private_redactions.txt`，
把本地脱敏规则放进去；该文件已被 `.gitignore` 排除。

发布新笔记前，仍建议人工检查是否包含真实目标、个人信息或未授权内容。

## 目录结构

```text
博客的构建/
├─ hugo.yaml                       # 站点配置、菜单、Permalink、搜索索引
├─ content/
│  ├─ _index.md
│  ├─ about.md                     # 关于页
│  ├─ archives.md                  # 归档页
│  ├─ search.md                    # 搜索页
│  ├─ tags/_index.md               # 标签 / 分类 / 系列的标题
│  ├─ categories/_index.md
│  ├─ series/_index.md
│  ├─ notes/                       # 61 篇笔记 + _index.md
│  ├─ projects/                    # 6 个重点项目详情 + _index.md
│  └─ posts/hello-xuanwo.md        # 建站首文
├─ data/projects.yaml              # 17 个公开项目卡片数据
├─ layouts/
│  ├─ index.html                   # 个人档案与内容入口首页
│  ├─ _default/single.html         # 文章页（目录 / 系列 / 相关）
│  ├─ notes/list.html              # 笔记库（筛选 + 搜索）
│  ├─ projects/list.html           # 项目墙
│  ├─ projects/single.html         # 项目详情
│  ├─ _partials/                   # header / footer / 图标 / 分类 slug
│  └─ 404.html
├─ assets/
│  ├─ css/extended/                # 00 tokens → 07 responsive
│  └─ js/                          # bootstrap / 筛选 / TOC / 灯箱 / 复制
├─ static/
│  ├─ images/                      # 头像、OG 封面、笔记配图
│  └─ favicon*.png / .svg
├─ scripts/
│  ├─ import_notes.py              # 笔记导入与脱敏
│  ├─ check_links.py               # 内链检查
│  ├─ quality_check.py             # 首页统计 / meta / OG / 内联脚本检查
│  ├─ diagram_catalog.py           # 61 张笔记图的类型与节点定义
│  ├─ generate_note_diagrams.py    # 生成 diagram-design HTML
│  ├─ export_note_diagrams.py      # 批量导出 SVG
│  ├─ apply_note_figures.py        # 将图插入笔记
│  ├─ build-upload.sh              # Git Bash 原子部署
│  ├─ build-upload.ps1             # PowerShell 原子部署
│  ├─ private_redactions.example.txt
│  └─ generate-assets.py           # 头像 / favicon / OG 封面
├─ .github/workflows/build.yml     # CI：构建 + 两类检查
├─ nginx/blog                      # Nginx 站点配置
├─ docs/diagrams/                  # diagram-design 源文件
├─ static/code/                    # 完整源码与源码包
├─ .diagram-design                 # 图表 profile 选择
├─ themes/PaperMod/                # 主题快照
└─ docs/previews/                  # 新版页面截图
```

## 本地预览

需要 **Hugo Extended 0.158+**，本项目在 `v0.168.0` 验证。

```bash
# Windows
winget install Hugo.Hugo.Extended

cd "/d/Program Files/Obsidian/zuodebiji/网络安全笔记/博客的构建"
hugo server -D
```

打开 <http://127.0.0.1:1313/>。

也可以直接构建后起一个静态服务器：

```bash
hugo --gc --minify --cleanDestinationDir --baseURL "http://127.0.0.1:1313/"
python -m http.server 1313 --directory public --bind 127.0.0.1
```

截图在 [`docs/previews/`](docs/previews/)：

- [首页 · 深色](docs/previews/home-desktop.png)
- [首页 · 浅色](docs/previews/home-light.png)
- [首页 · 移动端](docs/previews/home-mobile.png)
- [笔记库 · 浅色](docs/previews/notes-desktop.png)
- [项目墙](docs/previews/projects-desktop.png)
- [文章页 · 深色](docs/previews/post-desktop.png)
- [文章页 · 浅色](docs/previews/post-light.png)
- [RSA 实验图与完整代码](docs/previews/diagram-rsa.png)
- [移动端文章](docs/previews/mobile-article.png)
- [搜索页](docs/previews/search-desktop.png)
- [404](docs/previews/not-found.png)

## 重新导入笔记

`content/notes/` 是生成结果。源笔记来自公开仓库 `security-notes` 与本地 Obsidian 笔记。

```bash
git clone https://github.com/xuanwoLQL/security-notes.git /path/to/security-notes

cd "/d/Program Files/Obsidian/zuodebiji/网络安全笔记/博客的构建"
SECURITY_NOTES_DIR=/path/to/security-notes \
  python scripts/import_notes.py
```

脚本会：

1. 读取 `scripts/import_notes.py` 里的 `MANIFEST`（标题、slug、分类、系列、标签、权重）
2. 补 front matter，转换 Obsidian 缩进为标题 / 列表 / 代码块
3. 复制本地配图到 `static/images/notes/<slug>/`
4. 脱敏并写入 `content/notes/<slug>.md`

新增或删除文章时，编辑 `MANIFEST` 后重跑即可。标记为 `curated=True`
的手工精修文章不会被导入器覆盖；生成了但不再需要的旧文件需要手动删除。

## 写一篇新文章

```bash
hugo new content notes/your-note.md
```

推荐的 front matter：

```yaml
---
title: "文章标题"
slug: "your-note"
date: 2026-10-26T20:30:00+08:00
lastmod: 2026-10-26T20:30:00+08:00
draft: false
author: ["xuanwo"]
description: "一句话摘要，会出现在卡片与搜索结果里"
tags: ["CTF", "Web"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 20
ShowToc: true
TocOpen: false
---
```

分类建议使用以下之一，便于首页专题与筛选保持一致：

`CTF Writeup` · `Web 安全` · `渗透测试` · `密码学` · `网络编程` · `AI × 安全` · `安全工具` · `安全指南` · `操作系统`

图片放在 `static/images/` 下，用 `/images/...` 引用。

## 更新项目墙

`data/projects.yaml` 是项目卡片的数据源（17 个公开项目，6 个重点详情页，11 个 GitHub 外链）。字段：

```yaml
- name: repo-name
  title: 展示标题
  tagline: 一句话副标题
  description: 卡片描述
  language: Python
  language_color: "#3572A5"
  category: 安全
  accent: teal          # teal / gold / violet / blue / rose / green
  url: https://github.com/xuanwoLQL/repo-name
  detail: /projects/repo-name/   # 可选，重点项目填本地详情页
  featured: true                 # 是否进入首页 Bento
  span: large                    # large / small
  updated: "2026-10-21"
  tech: [Socket, 多线程]
```

重点项目还需要在 `content/projects/<slug>.md` 写详情页，并在 front matter 写 `slug`（与 `name` 一致）、`repo`、`language`、`tech`。

## 构建与部署

### 1. 构建

```bash
cd "/d/Program Files/Obsidian/zuodebiji/网络安全笔记/博客的构建"
hugo --gc --minify --cleanDestinationDir \
  --baseURL "http://47.93.123.112/"
```

如果 Hugo 不在 PATH，使用 `HUGO_BIN` 指定：

```bash
HUGO_BIN=/path/to/hugo bash scripts/build-upload.sh
```

### 2. 质量门

```bash
hugo --gc --minify --cleanDestinationDir --baseURL "http://47.93.123.112/"
python scripts/check_links.py
python scripts/quality_check.py
```

`quality_check.py` 会阻断以下问题：

- 首页统计 fallback 与 `data-count` 不一致，或仍为 0
- 首页 description 过短
- 仍存在可执行内联脚本
- OG 图片超过 120 KB
- 项目页没有区分站内详情与 GitHub 外链
- 任一笔记缺少复现流程图
- 搜索索引超过 120 KB

### 3. 原子部署

```bash
cp .deploy.env.example .deploy.env
# 编辑 .deploy.env：DEPLOY_USER、DEPLOY_HOST、DEPLOY_PATH、SSH_KEY
bash scripts/build-upload.sh
```

或 PowerShell：

```powershell
$env:SSH_KEY = "<path-to-deploy-key>"
.\scripts\build-upload.ps1
```

两个脚本现在执行同一套流程：

1. Hugo 构建；
2. 内链与发布质量检查；
3. 上传 tar 包到 `/tmp`；
4. 解压到 `/var/www/blog-release-*`；
5. 权限归一化并检查 `index.html`；
6. 旧站移动到 `/var/www/blog-old-*`，新目录原子切换为 `/var/www/blog`；
7. HTTP 健康检查失败时尝试恢复上一版。

生产环境建议使用专用低权限账号（示例为 `blogdeploy`），只赋予
`/var/www` 部署所需权限；脚本仍保留 root 兼容路径，但会显式告警。

### 4. 手动回滚

```bash
ssh "$DEPLOY_TARGET" \
  "mv /var/www/blog /var/www/blog-failed && mv /var/www/blog-old-<release-id> /var/www/blog"
```

确认新旧路径后执行，不要在没有校验路径时递归删除历史版本。

### 5. Nginx

首次部署：

```bash
sudo cp nginx/blog /etc/nginx/sites-available/blog
sudo ln -sfn /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/blog
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

当前配置已包含：

- 隐藏文件、备份文件、数据库文件拦截
- 每 IP 请求限流与并发限制
- 隐藏 Nginx 版本号
- CSP、`X-Content-Type-Options`、`Referrer-Policy` 等响应头
- 可执行 JavaScript 只允许同源文件，`script-src` 不再包含 `unsafe-inline`
- HTML / 搜索索引短缓存，CSS / JS / 字体长缓存，图片 30 天缓存

> 新版 CSS / JS 带 fingerprint，缓存策略可以直接沿用。

## 设计实现

- `assets/css/extended/00-tokens.css`：颜色、字体、间距、明暗主题变量
- `01-base.css`：基础排版、按钮、卡片、动画、焦点样式
- `02-header-footer.css`：固定导航、移动菜单、页脚
- `03-home.css`：个人档案、经历、统计、专题、最近笔记、Bento、CTA
- `04-article.css`：文章布局、TOC、代码块、表格、系列、相关、灯箱
- `05-lists.css`：笔记 / 项目 / 归档 / 标签 / 搜索
- `06-projects.css`：项目详情
- `07-responsive.css`：断点、触摸设备、`prefers-reduced-motion`
- `assets/js/main.js`：无依赖原生 JS，负责筛选、TOC、灯箱、复制与主题交互

## 图表与源码资产

每篇笔记顶部都有一张内容相关的图，图表源文件在 `docs/diagrams/`，
导出后的 SVG 在 `static/images/notes/<slug>/workflow.svg`。

重新生成：

```bash
python scripts/generate_note_diagrams.py

# 使用 diagram-design 的导出脚本
python "$DIAGRAM_DESIGN/scripts/export_svg.py" --system-fonts \
  docs/diagrams/<slug>.html \
  static/images/notes/<slug>/workflow.svg

python scripts/apply_note_figures.py
```

完整代码和源码包在 `static/code/<slug>/`。网络编程、DES、RSA、SSRF、
盲注和 fastjson 的代码都可以从文章直接下载。

## 发布前检查

- [ ] `hugo --gc --minify` 无报错
- [ ] `python scripts/check_links.py` 输出 0 broken
- [ ] `python scripts/quality_check.py` 全部通过
- [ ] 桌面 / 移动端、深色 / 浅色都看过
- [ ] 新笔记不含真实目标、个人信息、真实凭据
- [ ] 图片路径可访问，内部链接无 404
- [ ] `.deploy.env`、私钥、抓包文件未提交
- [ ] Nginx 安全组只放行 22 / 80（443 等待域名）
- [ ] 部署后检查首页、文章、项目详情、搜索、404

## 后续

- 域名与 ICP 备案完成后再配置 HTTPS（本次未处理）
- OpenHarmony 笔记解除保密后，再补入 `content/notes/`；`xuanwo` 仓库已在项目墙列出
- 可以增加 RSS 全文、评论、访问统计，但需要重新评估隐私与 CSP
