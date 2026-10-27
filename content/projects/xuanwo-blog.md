---
slug: "xuanwo-blog"
title: "漩涡博客"
description: "Hugo + PaperMod + Nginx，自建个人档案首页、专题入口、Bento 项目墙、笔记检索与文章阅读体验。"
date: 2026-10-26T20:00:00+08:00
lastmod: 2026-10-27T11:30:00+08:00
repo: "https://github.com/xuanwoLQL/xuanwo-blog"
language: "HTML"
tech: ["Hugo", "PaperMod", "Nginx", "自建主题"]
featured: true
ShowToc: false
comments: false
---

## 你正在看的就是它

这个站点最初只是一个 PaperMod 默认首页：一张居中的卡片，四周大片留白。后来我把首页、文章页、笔记列表和项目墙全部重做了一遍，保留 PaperMod 的构建能力，用项目级模板与 CSS 覆盖视觉层。

## 技术栈

| 层 | 选择 | 原因 |
| --- | --- | --- |
| 静态生成 | Hugo Extended | 构建快、单二进制、模板灵活 |
| 基础主题 | PaperMod | 搜索、归档、代码高亮等基础设施完整 |
| 视觉层 | 原生 CSS | 不引入前端框架，保持加载速度与可维护性 |
| 托管 | Nginx | 静态文件、缓存、限流与安全头 |

## 做了什么

- **个人档案首页**：首屏汇总方向、近期竞赛、企业实践与公开产出，先给结论，再进入内容。
- **阅读路径重排**：笔记专题放在最近更新之前，降低首次访问者的选择成本。
- **Bento 项目墙**：按语言与方向筛选，明确区分 6 个站内详情与 11 个 GitHub 外链。
- **笔记库**：61 篇笔记按主题分类，支持即时搜索与筛选。
- **复现图表**：61 篇笔记均配有流程图、架构图或数据流图。
- **完整工程**：网络编程与密码学实验提供完整源码、构建命令和可下载源码包。
- **阅读体验**：阅读进度条、粘性目录、代码复制、系列上下篇、相关笔记。
- **可访问性**：键盘焦点、`prefers-reduced-motion`、语义化标签与响应式布局。
- **发布质量门**：CI 构建、内链检查、首页统计 / meta / OG / 内联脚本检查。
- **轻量搜索**：搜索索引只收录标题、摘要和标签，避免完整源码拖慢搜索。
- **原子部署**：新版本先解压到独立目录，验证后切换；失败可回到上一版。

## 部署

```bash
hugo --gc --minify --cleanDestinationDir --baseURL "http://47.93.123.112/"
python scripts/check_links.py
python scripts/quality_check.py
```

正式部署由 `scripts/build-upload.ps1` 或 `scripts/build-upload.sh` 完成。Nginx 配置包含隐藏文件拦截、备份文件拦截、每 IP 限流、CSP 与静态资源缓存。

## 相关链接

- 仓库：<https://github.com/xuanwoLQL/xuanwo-blog>
- 站点：<http://47.93.123.112/>
