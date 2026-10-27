---
slug: "des-cipher-lab"
title: "DES 纯 C 实现"
description: "按 FIPS 46-3 从零实现 DES：16 轮 Feistel、PKCS#7 填充、ECB 模式与 NIST 标准向量验证。"
date: 2026-10-08T20:00:00+08:00
lastmod: 2026-10-08T20:00:00+08:00
repo: "https://github.com/xuanwoLQL/des-cipher-lab"
language: "C"
tech: ["C", "DES", "PKCS#7", "NIST"]
featured: true
ShowToc: false
comments: false
---

## 为什么手写 DES

密码学课上讲 DES 时，置换表看起来只是一堆数字。真正把它写一遍，才会理解「16 轮 Feistel」不是抽象名词，而是 16 次左右半区交换、密钥移位与 S 盒查表的组合。

这个实现不调用 OpenSSL，也不依赖任何第三方库，只用 C 标准库。

## 实现要点

- 16 轮 Feistel：IP / IP⁻¹、PC-1 / PC-2、E 扩展、8 个 S 盒、P 置换
- 密钥调度：56 位有效密钥 + 16 轮循环左移
- 分组模式：ECB
- 填充：PKCS#7，支持 `-n` 关闭填充
- 输入：字符串（UTF-8）或十六进制串
- 调试：`-v` 打印每轮 L、R 中间值

## 验证方式

用 FIPS PUB 81 与 NIST SP 800-17 的标准测试向量交叉验证；再与 Python 的 `pycryptodome` 对照任意长度明文的加密结果。

```bash
gcc -Wall -Wextra -O2 des.c -o des
./des -e 12345678 "hello"
./des -e 12345678 -x 68656c6c6f
./des -d 12345678 <十六进制密文>
```

## 踩坑

- 密钥只有 56 位有效位，PC-1 会丢掉校验位。
- 填充边界：明文长度正好是 8 的倍数时，PKCS#7 仍然要补一整块。
- 中文按 UTF-8 编码后是变长字节，分组前不能按字符切。
- Windows 控制台默认代码页不是 UTF-8，输出中文要先切换。

## 相关链接

- 仓库：<https://github.com/xuanwoLQL/des-cipher-lab>
- 博客内的实验笔记：[DES 加密算法实验](/notes/crypto-des-cipher/)
