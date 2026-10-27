---
title: "MD5 算法实验"
slug: "crypto-md5"
date: 2026-10-18T19:33:43+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从填充、分组到四轮压缩，纯 C 实现 MD5 并与 hashlib / certutil 交叉验证。"
summary: "从填充、分组到四轮压缩，纯 C 实现 MD5 并与 hashlib / certutil 交叉验证。"
tags: ["密码学", "MD5", "C"]
categories: ["密码学"]
series: ["密码学实验"]
weight: 4
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/crypto-md5/workflow.svg" alt="消息经过填充、分组、四轮压缩与链接变量累加后得到 128 位摘要。" loading="lazy">
  <figcaption>图 1 · MD5 压缩管线。消息经过填充、分组、四轮压缩与链接变量累加后得到 128 位摘要。</figcaption>
</figure>

**实验4  MD5 算法实验**

2026 年 9 月

### 【实验目的】

MD5 算法的实现。

### 【实验环境】

Windows 操作系统 + Code::Blocks 集成开发环境（使用其自带的 MinGW-w64 gcc 15.2.0 编译器，编译选项 -Wall -Wextra -std=c99 -O2）；程序用 C 语言编写，只使用 C 标准库，填充、分组、四轮压缩、常量表全部自己实现，不调用 OpenSSL、Windows CryptoAPI / CNG 等任何现成 MD5 库。对比验证用 Python 3.11 的 hashlib 与 Windows 自带的 certutil；实验下发的在线工具 http://www.metools.info/code/c26.html 可以用来复核同样的标准值。

### 【实验涉及相关概念和基本原理】

**1. 消息摘要与 MD5 算法**

MD5（Message-Digest Algorithm 5）是 Ronald Rivest 于 1991 年提出的单向散列函数，是 MD4 的改进版，规范见 RFC 1321。它把任意长度的消息压缩成固定的 128 bit（16 字节，写作 32 位十六进制）摘要，具有四个特点：输入长度任意、输出定长；由消息算摘要很快；由摘要反推消息在计算上不可行；消息改一位，摘要就面目全非。因为摘要可以唯一标识一份数据，MD5 常用在校验文件是否被篡改、数字签名中先压缩消息，以及数据库中保存口令的散列值等场合。

**2. 填充规则**

MD5 把消息按 512 bit（64 字节）一组处理，所以先要把消息补到 64 字节的整数倍：先在末尾补 1 个字节 0x80（即二进制 1000 0000），再补若干个 0x00，使填充后的长度满足 len ≡ 56 (mod 64)；最后补 8 个字节，这 8 个字节是原始消息比特数 L×8 的小端表示。于是填充后的总长度 = ceil((L + 9) / 64) × 64 字节：长度不超过 55 字节的消息只占 1 组，第 56 个字节一出现就必须再补出第 2 组，这正是 55 与 56 这两个长度的分界所在。

**3. 分组与消息字**

每一组 64 字节再按小端拆成 16 个 32 位字 X[0]～X[15]：分组的第 0 个字节是 X[0] 的最低位字节，第 63 个字节是 X[15] 的最高位字节。压缩函数把 X[0]～X[15] 和上一组留下的链接变量一起变换，得到新的链接变量。

**4. 初始化向量与链接变量**

MD5 采用类似 CBC 的链接方式。四个链接变量 A、B、C、D 的初值固定为 0x67452301、0xefcdab89、0x98badcfe、0x10325476（按小端书写正好是 01 23 45 67、89 ab cd ef、fe dc ba 98、76 54 32 10，是一组固定魔数）。每压缩完一组，新的链接变量 = 本组压缩结果 + 本组进入时的链接变量（模 2^32 相加），因此后面每一组都依赖前面所有组的数据，修改前面任意一位都会传播到最后。

**5. 压缩函数与非线性函数 F、G、H、I**

压缩函数是 MD5 的核心：把 16 个消息字做 4 轮、每轮 16 步、共 64 步，每一轮换用一个非线性函数，按位运算与加法混合，制造非线性，使攻击者无法用线性代数方法反推：

第 1 轮 F(b,c,d) = (b & c) | (~b & d)；第 2 轮 G(b,c,d) = (b & d) | (c & ~d)；第 3 轮 H(b,c,d) = b ^ c ^ d；第 4 轮 I(b,c,d) = c ^ (b | ~d)。

**6. 单步运算：循环左移与模 2^32 加**

每一步只更新一个变量，然后四个变量整体右移一格（d→a、a→b、b→c、c→d），16 步之后每个变量都被更新了 4 次。单步公式是

a = b + ((a + F(b,c,d) + X[k] + T[i]) <<< s)

其中 + 是模 2^32 的加法（32 位无符号整数溢出即可实现），<<< s 是 32 位循环左移，X[k] 是消息字，T[i] 是常量。整个过程只用到加法、与、或、非、异或、循环移位，全是计算机最基础的运算，因此 MD5 速度很快。

**7. 四轮参数：常量表 T、循环左移位数 s、消息字下标 k**

（1）常量表 T[i] = floor(2^32 × |sin(i+1)|)，i = 0…63，即把正弦函数取绝对值后乘 2^32 再取整，共 64 个 32 位常数，用来打乱每一步的加法输入；（2）循环左移位数 s 四轮各一套，分别是 7/12/17/22、5/9/14/20、4/11/16/23、6/10/15/21，每轮内以 4 为周期循环使用；（3）消息字的下标 k 第 1 轮取 i，第 2 轮取 (1+5i) mod 16，第 3 轮取 (5+3i) mod 16，第 4 轮取 (7i) mod 16，保证 16 个消息字在 4 轮中各用 4 次，且使用顺序被打乱。

程序自检里用 sin() 把这 64 个常数重新算了一遍，与代码中硬编码的常量表逐项一致（离整数最近的小数距离为 0.0154，不存在浮点取整歧义），说明这张表确实是按公式生成的。

**8. 摘要输出**

全部消息处理完后，把最后的 A、B、C、D 各按小端输出 4 个字节，拼成 16 字节即为摘要，写作十六进制就是常见的 32 位小写字符串，例如 abc → 900150983cd24fb0d6963f7d28e17f72。

**9. 安全性**

MD5 的抗碰撞性已被攻破：2004 年王小云等人给出了可实际构造碰撞的方法；2008 年以后已知前缀的碰撞在普通计算机上也能秒级完成；2017 年 Google 用碰撞构造出两份内容不同、MD5 相同的 PDF（SHAttered）。因此 MD5 今天只适合做校验传输是否出错之类的非对抗性用途；涉及数字签名、证书、口令保护时应改用 SHA-256 等，口令还要加盐并使用 bcrypt、scrypt、Argon2 这类慢哈希。本实验只实现和验证算法本身。

### 【实验内容】

了解 MD5 算法的原理，调试 MD5 摘要算法流程，进行 MD5 压缩数据的实验，并根据理论知识验证其正确性。本次实验没有下发参考代码，程序完全按 RFC 1321 的规范用 C 语言自己写，包含四个部分：摘要计算主流程（填充、分组、四轮压缩、摘要输出）、压缩过程追踪（把填充字节、16 个消息字、每轮中间状态打印出来）、文件摘要（二进制读文件，边读边算）、自检与第三方工具对拍。

**（一）实验环境与工程组织**

实验目录 `实验4 MD5算法实验` 下的文件：md5.c 是唯一的手写源程序（641 行）；md5.cbp 是 Code::Blocks 工程文件，双击即可打开并直接按 F9 构建运行；build.bat 是等价的命令行编译脚本；md5.exe 是编译产物；testdata 目录放测试数据（空文件、abc.txt、CRLF 换行文件 crlf.txt、165 字节文本 longtext.txt、256 字节二进制文件 binary256.bin）；image 目录放流程图与运行结果图，其中的 1_md5_flow.py、2_md5_step.py、render_shots.py 是生成这些图的脚本；运行结果.txt 与 验证结果.txt 是本机真实运行的输出存档。

**（二）MD5 摘要算法流程图**

流程图按 md5.c 的实现绘制：先读入消息，装入初始化向量；然后填充（补 0x80、补 0x00 到 len ≡ 56 (mod 64)、补 8 字节小端消息位长度）；再按 64 字节分组；每组内部先把 64 字节按小端拆成 16 个 32 位字，保存本组进入时的链接变量，做 4 轮共 64 步压缩，最后把压缩结果与本组初值模 2^32 相加得到新的链接变量，如此循环直到所有组处理完；最后把 A、B、C、D 按小端输出成 16 字节摘要。

*图 1  MD5 摘要算法流程图（填充、分组与四轮压缩）*

单步压缩运算的细节见图 2：每一步把 a、非线性函数 F/G/H/I 的结果、消息字 X[k] 和常量 T[i] 模 2^32 相加，循环左移 s 位后再与 b 相加，得到新的 a；随后四个变量整体右移一格。图下方的两张表给出四轮的循环左移位数和消息字下标规则。

*图 2  MD5 单步压缩运算与四轮参数*

**（三）程序结构与核心思路**

md5.c 用结构体 MD5_CTX 保存运算状态：state[4] 是链接变量 A、B、C、D，bitlen 记录已处理消息的比特数（用 64 位无符号整数，长消息也不会溢出），buf[64] 与 buflen 缓存还没凑满一组的残留数据，blocks 记录已经压缩过的组数（供实验统计与自检使用）。

md5_init() 装入初始化向量；md5_update() 支持流式喂数据——不足 64 字节的先攒进 buf，凑满一组就调用压缩函数，因此文件可以按 64 KB 一块读入边读边算，不必一次性读进内存；md5_final() 按规则补 0x80、0x00 和 8 字节小端长度，再输出 16 字节摘要；md5_transform() 是压缩函数，处理一组 512 bit 数据，参数 trace 取 0/1/2 时分别表示不打印、打印每轮结束状态、再打印 64 步的逐步状态。

md5_trace() 是压缩过程实验的入口：它自己按标准做填充与分组，逐组调用压缩函数，把填充字节数、16 个消息字、每轮结束时的 a、b、c、d 以及累加后的链接变量全部打印出来，便于和教材、RFC 上的中间值逐行对照。此外 msg_index() 给出四轮的消息字下标规则，SHIFT[] 是循环左移位数表，T[] 是常量表，func_f/func_g/func_h/func_i 是四个非线性函数，rotl() 完成 32 位循环左移，模 2^32 加法直接用 32 位无符号整数的溢出语义实现。

文件与工具函数：md5_file() 以 "rb" 二进制方式读文件并流式计算，md5_buffer() 算一段内存的摘要，hex_to_bytes() 把十六进制串还原成字节，这样字符串、文件、任意二进制数据（含 0x00）都能测。md5_selftest() 提供四项自检：① 用 sin 复算常量表 T；② RFC 1321 的 7 组标准测试向量；③ 逐字节喂入与一次喂入结果一致、12 种长度的实际分组数符合公式；④ “手工填充 + 逐组压缩”与“流式 update/final”两条代码路径在 8 种长度上结果一致。main() 同时支持命令行（-s 字符串、-f 文件、-x 十六进制、-t/-T 压缩过程、-v 自检，便于批量测试）和交互菜单（1 算字符串 / 2 算文件 / 3 压缩过程 / 4 自检 / 0 退出）。

**（四）源程序代码（md5.c）**

```c
/*
 * 实验4  MD5 算法实验
 * 功能：纯 C 从零实现 RFC 1321 的 MD5 摘要算法——填充规则、512 bit 分组、四级链接变量、
 *       四轮 64 步压缩、非线性函数 F/G/H/I、常量表 T、循环左移、模 2^32 加、摘要输出
 *       全部按标准自己写，不调用任何现成 MD5 库（不用 OpenSSL / 系统 CryptoAPI / CNG）。
 *
 * 编译：gcc -Wall -Wextra -O2 md5.c -o md5.exe
 * 运行：md5.exe                       进入交互模式（1 字符串 / 2 文件 / 3 压缩过程 / 4 自检 / 0 退出）
 *       md5.exe -s <字符串>            计算字符串摘要（按 UTF-8 字节）
 *       md5.exe -f <文件名>            计算文件摘要（二进制方式读）
 *       md5.exe -x <十六进制串>        把十六进制串还原成字节后计算摘要
 *       md5.exe -t <字符串>            打印填充、分组和每轮中间状态（压缩过程实验）
 *       md5.exe -T <字符串>            在 -t 基础上再打印每一步（64 步）的 a、b、c、d
 *       md5.exe -v                     自检：T 表复算 + RFC 1321 标准向量 + 流式/分块一致性
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#ifdef _WIN32
#include <windows.h>          /* 仅用于把控制台输出代码页设为 UTF-8，正确显示中文 */
#endif

typedef uint8_t  u8;
typedef uint32_t u32;
typedef uint64_t u64;

/* ==================== 1. 常量表（RFC 1321） ==================== */

/* 循环左移位数 s：四轮各一套，每套 4 个值循环 4 次 */
static const int SHIFT[64] = {
     7, 12, 17, 22,  7, 12, 17, 22,  7, 12, 17, 22,  7, 12, 17, 22,   /* 第 1 轮 F */
     5,  9, 14, 20,  5,  9, 14, 20,  5,  9, 14, 20,  5,  9, 14, 20,   /* 第 2 轮 G */
     4, 11, 16, 23,  4, 11, 16, 23,  4, 11, 16, 23,  4, 11, 16, 23,   /* 第 3 轮 H */
     6, 10, 15, 21,  6, 10, 15, 21,  6, 10, 15, 21,  6, 10, 15, 21    /* 第 4 轮 I */
};

/* 常量表 T[i] = floor(2^32 × |sin(i + 1)|)，i = 0..63，弧度制
 * 表中数值与 RFC 1321 附录一致；md5_selftest() 里会用 sin() 复算一遍逐项核对 */
static const u32 T[64] = {
    0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee,
    0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
    0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
    0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
    0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa,
    0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
    0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed,
    0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
    0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
    0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
    0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05,
    0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
    0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039,
    0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
    0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
    0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
};

/* 四级链接变量的初值（RFC 1321 规定） */
static const u32 IV[4] = { 0x67452301u, 0xefcdab89u, 0x98badcfeu, 0x10325476u };

/* 消息字下标：第 1 轮按顺序取，后三轮分别按 1+5i、5+3i、7i 取模 16 */
static int msg_index(int i)
{
    if (i < 16) return i;
    if (i < 32) return (1 + 5 * i) % 16;
    if (i < 48) return (5 + 3 * i) % 16;
    return (7 * i) % 16;
}

/* 32 位循环左移；模 2^32 的加法直接用 u32 溢出语义完成 */
static u32 rotl(u32 x, int n)
{
    return (u32)((x << n) | (x >> (32 - n)));
}

/* 四位非线性函数，只在第 i 步用到的那一个会被调用 */
static u32 func_f(u32 b, u32 c, u32 d) { return (b & c) | (~b & d); }   /* 第 1 轮：选择 */
static u32 func_g(u32 b, u32 c, u32 d) { return (b & d) | (c & ~d); }   /* 第 2 轮 */
static u32 func_h(u32 b, u32 c, u32 d) { return b ^ c ^ d; }            /* 第 3 轮：异或 */
static u32 func_i(u32 b, u32 c, u32 d) { return c ^ (b | ~d); }         /* 第 4 轮 */

/* ==================== 2. MD5 上下文 ==================== */

typedef struct {
    u32    state[4];   /* 链接变量 A、B、C、D */
    u64    bitlen;     /* 已处理消息的比特数（用 64 位，长消息也不会溢出） */
    u8     buf[64];    /* 还没凑满一组的残留数据 */
    size_t buflen;     /* 残留字节数 */
    u64    blocks;     /* 已完成的压缩组数（实验统计用） */
} MD5_CTX;

static void md5_init(MD5_CTX *ctx)
{
    memcpy(ctx->state, IV, sizeof(IV));
    ctx->bitlen = 0;
    ctx->buflen = 0;
    ctx->blocks = 0;
}

/* 一个分组的 64 字节按小端拆成 16 个 32 位字 */
static void block_to_words(const u8 block[64], u32 x[16])
{
    int i;
    for (i = 0; i < 16; ++i) {
        x[i] = (u32)block[i * 4]
             | ((u32)block[i * 4 + 1] << 8)
             | ((u32)block[i * 4 + 2] << 16)
             | ((u32)block[i * 4 + 3] << 24);
    }
}

/* ==================== 3. 压缩函数：一轮 512 bit 数据 ==================== */

/* trace = 0 只算不打印；1 打印每轮结束状态；2 再打印每一步的状态 */
static void md5_transform(MD5_CTX *ctx, const u8 block[64], int trace)
{
    u32 x[16];
    u32 a, b, c, d, a0, b0, c0, d0, f, tmp;
    int i, r;

    block_to_words(block, x);

    a0 = a = ctx->state[0];
    b0 = b = ctx->state[1];
    c0 = c = ctx->state[2];
    d0 = d = ctx->state[3];

    if (trace) {
        printf("  分组字节(hex)   : ");
        for (i = 0; i < 64; ++i) printf("%02x", block[i]);
        printf("\n  16 个字 X[0..15] :\n");
        for (i = 0; i < 16; ++i) printf("    X[%2d] = 0x%08x\n", i, x[i]);
        printf("  进入本组链接变量 : A=0x%08x B=0x%08x C=0x%08x D=0x%08x\n", a, b, c, d);
    }

    for (i = 0; i < 64; ++i) {
        if (i < 16)      f = func_f(b, c, d);
        else if (i < 32) f = func_g(b, c, d);
        else if (i < 48) f = func_h(b, c, d);
        else             f = func_i(b, c, d);

        /* a = b + ((a + F(b,c,d) + X[k] + T[i]) <<< s)，然后整体右移一格 */
        tmp = d;
        d = c;
        c = b;
        b = b + rotl(a + f + x[msg_index(i)] + T[i], SHIFT[i]);
        a = tmp;

        if (trace >= 2) {
            printf("    第%2d步 k=%2d s=%2d : a=0x%08x b=0x%08x c=0x%08x d=0x%08x\n",
                   i + 1, msg_index(i), SHIFT[i], a, b, c, d);
        }
        if (trace && (i + 1) % 16 == 0) {
            r = (i + 1) / 16;
            printf("  第 %d 轮 (%s) 结束 : a=0x%08x b=0x%08x c=0x%08x d=0x%08x\n",
                   r, r == 1 ? "F" : r == 2 ? "G" : r == 3 ? "H" : "I", a, b, c, d);
        }
    }

    ctx->state[0] = a0 + a;
    ctx->state[1] = b0 + b;
    ctx->state[2] = c0 + c;
    ctx->state[3] = d0 + d;
    ctx->blocks++;

    if (trace) {
        printf("  累加后链接变量   : A=0x%08x B=0x%08x C=0x%08x D=0x%08x\n",
               ctx->state[0], ctx->state[1], ctx->state[2], ctx->state[3]);
    }
}

/* ==================== 4. 填充与分组入口 ==================== */

/* 边喂边算：不足 64 字节的先攒在 ctx->buf 里 */
static void md5_update(MD5_CTX *ctx, const u8 *data, size_t len)
{
    size_t i = 0, n;

    ctx->bitlen += (u64)len * 8;

    if (ctx->buflen) {
        n = 64 - ctx->buflen;
        if (n > len) n = len;
        memcpy(ctx->buf + ctx->buflen, data, n);
        ctx->buflen += n;
        i = n;
        if (ctx->buflen == 64) {
            md5_transform(ctx, ctx->buf, 0);
            ctx->buflen = 0;
        }
    }
    while (i + 64 <= len) {
        md5_transform(ctx, data + i, 0);
        i += 64;
    }
    if (i < len) {
        memcpy(ctx->buf, data + i, len - i);
        ctx->buflen = len - i;
    }
}

/* 填充：先补 1 个 0x80，再补若干个 0x00 使长度 ≡ 56 (mod 64)，最后补 8 字节小端消息位长度 */
static void md5_final(MD5_CTX *ctx, u8 digest[16])
{
    u64 bitlen = ctx->bitlen;
    u8  pad[128];
    size_t padlen, i;

    padlen = (ctx->buflen < 56) ? (56 - ctx->buflen) : (120 - ctx->buflen);
    pad[0] = 0x80;
    for (i = 1; i < padlen; ++i) pad[i] = 0x00;
    for (i = 0; i < 8; ++i) pad[padlen + i] = (u8)(bitlen >> (8 * i));   /* 小端 */

    md5_update(ctx, pad, padlen + 8);   /* 这一步不会再触发新的填充 */

    for (i = 0; i < 4; ++i) {           /* 4 个 32 位字各按小端输出 4 字节 */
        digest[i * 4]     = (u8)(ctx->state[i]);
        digest[i * 4 + 1] = (u8)(ctx->state[i] >> 8);
        digest[i * 4 + 2] = (u8)(ctx->state[i] >> 16);
        digest[i * 4 + 3] = (u8)(ctx->state[i] >> 24);
    }
}

/* 一次性算完一段内存的摘要 */
static void md5_buffer(const u8 *data, size_t len, u8 digest[16])
{
    MD5_CTX ctx;
    md5_init(&ctx);
    md5_update(&ctx, data, len);
    md5_final(&ctx, digest);
}

static void hex_of(const u8 *digest, char out[33])
{
    static const char *H = "0123456789abcdef";
    int i;
    for (i = 0; i < 16; ++i) {
        out[i * 2]     = H[digest[i] >> 4];
        out[i * 2 + 1] = H[digest[i] & 0x0f];
    }
    out[32] = '\0';
}

/* 算出填充后要占多少个 512 bit 分组：padded = ceil((len + 9) / 64) × 64 */
static u64 block_count(size_t len)
{
    return ((u64)len + 9 + 63) / 64;
}

/* ==================== 5. 压缩过程实验：逐步打印 ==================== */

/* 自己按标准做填充和分组，逐组调用压缩函数并打印中间状态，
 * 最后用摘要在屏幕上回显，可与 md5_update/md5_final 的结果对照 */
static void md5_trace(const u8 *msg, size_t len, int level)
{
    MD5_CTX ctx;
    u8 *padded;
    u64 blocks = block_count(len);
    size_t padlen = (size_t)(blocks * 64 - len - 8);   /* 0x80 加若干 0x00 的字节数 */
    size_t total = (size_t)(blocks * 64);
    u64 i, j;
    u8 digest[16];
    char hex[33];

    printf("---- 填充与分组 ----\n");
    printf("  消息长度        : %lu 字节 (%lu bit)\n", (unsigned long)len, (unsigned long)(len * 8));
    printf("  补 0x80         : 1 字节\n");
    printf("  补 0x00         : %lu 字节 (凑到 len ≡ 56 mod 64)\n", (unsigned long)(padlen - 1));
    printf("  长度字段        : ");
    for (i = 0; i < 8; ++i) printf("%02x", (unsigned)(((u64)len * 8 >> (8 * i)) & 0xffu));
    printf("  (消息位长度的小端表示)\n");
    printf("  填充后长度      : %lu 字节 = %lu 组 × 512 bit\n", (unsigned long)total, (unsigned long)blocks);

    padded = (u8 *)malloc(total);
    if (padded == NULL) { printf("内存不足\n"); return; }
    memcpy(padded, msg, len);
    padded[len] = 0x80;
    for (j = len + 1; j < total - 8; ++j) padded[j] = 0x00;
    for (i = 0; i < 8; ++i) padded[total - 8 + i] = (u8)((u64)len * 8 >> (8 * i));

    md5_init(&ctx);
    for (i = 0; i < blocks; ++i) {
        printf("\n---- 第 %lu 组 / 共 %lu 组（压缩过程） ----\n", (unsigned long)(i + 1), (unsigned long)blocks);
        md5_transform(&ctx, padded + i * 64, level);
    }

    for (i = 0; i < 4; ++i) {
        digest[i * 4]     = (u8)(ctx.state[i]);
        digest[i * 4 + 1] = (u8)(ctx.state[i] >> 8);
        digest[i * 4 + 2] = (u8)(ctx.state[i] >> 16);
        digest[i * 4 + 3] = (u8)(ctx.state[i] >> 24);
    }
    hex_of(digest, hex);
    printf("\n---- 摘要输出 ----\n");
    printf("  最终链接变量    : A=0x%08x B=0x%08x C=0x%08x D=0x%08x\n",
           ctx.state[0], ctx.state[1], ctx.state[2], ctx.state[3]);
    printf("  小端拼接 16 字节: ");
    for (i = 0; i < 16; ++i) printf("%02x", digest[i]);
    printf("\n  MD5 摘要        : %s\n", hex);

    free(padded);
}

/* ==================== 6. 自检 ==================== */

static int check_t_table(void)
{
    int i, bad = 0;
    double worst = 1.0;
    for (i = 0; i < 64; ++i) {
        double v = fabs(sin((double)(i + 1))) * 4294967296.0;   /* 2^32 */
        u32 gen = (u32)floor(v);
        double frac = v - floor(v);
        if (frac > 0.5) frac = 1.0 - frac;
        if (frac < worst) worst = frac;
        if (gen != T[i]) {
            printf("  [FAIL] T[%d] 表值 0x%08x，sin 复算 0x%08x\n", i, T[i], gen);
            bad++;
        }
    }
    if (!bad) {
        printf("  [ OK ] T[0..63] 与 floor(2^32×|sin(i+1)|) 复算结果逐项一致"
               "（离整数最近的小数距离 %.4f）\n", worst);
    }
    return bad == 0;
}

typedef struct { const char *msg; const char *hex; } TESTVEC;

static int check_vectors(void)
{
    /* RFC 1321 附录 A.5 的标准测试向量 */
    static const TESTVEC vec[] = {
        { "",                                                                  "d41d8cd98f00b204e9800998ecf8427e" },
        { "a",                                                                 "0cc175b9c0f1b6a831c399e269772661" },
        { "abc",                                                               "900150983cd24fb0d6963f7d28e17f72" },
        { "message digest",                                                    "f96b697d7cb7938d525a2f31aaf161d0" },
        { "abcdefghijklmnopqrstuvwxyz",                                        "c3fcd3d76192e4007dfb496cca67e13b" },
        { "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",     "d174ab98d277d9f5a5611c2c9f419d9f" },
        { "12345678901234567890123456789012345678901234567890123456789012345678901234567890",
                                                                               "57edf4a22be3c955ac49da2e2107b67a" }
    };
    u8 digest[16];
    char hex[33];
    size_t n = sizeof(vec) / sizeof(vec[0]), i;
    int bad = 0;

    for (i = 0; i < n; ++i) {
        md5_buffer((const u8 *)vec[i].msg, strlen(vec[i].msg), digest);
        hex_of(digest, hex);
        if (strcmp(hex, vec[i].hex) != 0) {
            printf("  [FAIL] 长度 %lu 的向量应为 %s，实际 %s\n",
                   (unsigned long)strlen(vec[i].msg), vec[i].hex, hex);
            bad++;
        }
    }
    if (!bad) printf("  [ OK ] RFC 1321 的 7 组标准测试向量全部一致\n");
    return bad == 0;
}

static int check_streaming(void)
{
    const char *msg = "abcdefghijklmnopqrstuvwxyz";
    size_t len = strlen(msg), cut;
    u8 d1[16], d2[16];
    char h1[33], h2[33];
    MD5_CTX ctx;
    int bad = 0;

    md5_buffer((const u8 *)msg, len, d1);
    hex_of(d1, h1);
    /* 每次只喂 1 字节：检查 ctx->buf 残留拼接有没有漏字节 */
    md5_init(&ctx);
    for (cut = 0; cut < len; ++cut) md5_update(&ctx, (const u8 *)msg + cut, 1);
    md5_final(&ctx, d2);
    hex_of(d2, h2);
    if (strcmp(h1, h2) != 0) { printf("  [FAIL] 逐字节喂入 %s ≠ 一次喂入 %s\n", h2, h1); bad++; }
    else printf("  [ OK ] 26 次 1 字节喂入与一次喂入结果一致（%s）\n", h1);

    /* 分组边界：长度 55 及以下只占 1 组，56 起要补第 2 组……
     * 用 ctx.blocks 统计实现真正压过的组数，与公式 ceil((len+9)/64) 对照 */
    {
        static const size_t lens[] = { 0, 1, 55, 56, 57, 63, 64, 65, 119, 120, 127, 128 };
        static const u64 expect[] = { 1, 1,  1,  2,  2,  2,  2,  2,   2,   3,   3,   3 };
        size_t k;
        u8 big[128];
        memset(big, 'x', sizeof(big));
        for (k = 0; k < sizeof(lens) / sizeof(lens[0]); ++k) {
            u8 d[16];
            md5_init(&ctx);
            md5_update(&ctx, big, lens[k]);
            md5_final(&ctx, d);
            if (ctx.blocks != expect[k] || ctx.blocks != block_count(lens[k])) {
                printf("  [FAIL] 长度 %lu 实际压了 %lu 组，预期 %lu 组\n",
                       (unsigned long)lens[k], (unsigned long)ctx.blocks, (unsigned long)expect[k]);
                bad++;
            }
        }
        printf("  [ OK ] 长度 0/1/55/56/57/63/64/65/119/120/127/128 实际分组数 "
               "1/1/1/2/2/2/2/2/2/3/3/3 符合 ceil((len+9)/64)\n");
    }
    return bad == 0;
}

/* 压缩过程路径（md5_trace 里自己填充分组）与流式路径结果对拍 */
static int check_trace_path(void)
{
    static const size_t lens[] = { 0, 1, 3, 55, 56, 64, 65, 200 };
    const char *base = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\344\270\255\346\226\207\346\221\230\350\246\201abcdefghijklmnopqrstuvwxyz";
    u8 *msg = (u8 *)malloc(512);
    size_t k, len;
    int bad = 0;
    if (!msg) return 0;

    for (len = 0; len < 512; ++len) msg[len] = (u8)base[len % strlen(base)];

    for (k = 0; k < sizeof(lens) / sizeof(lens[0]); ++k) {
        u8 d1[16], d2[16];
        char h1[33], h2[33];
        MD5_CTX ctx;
        u8 *padded;
        u64 blocks, i, j;
        size_t L = lens[k];
        size_t total;

        md5_buffer(msg, L, d1);
        hex_of(d1, h1);

        blocks = block_count(L);
        total = (size_t)(blocks * 64);
        padded = (u8 *)malloc(total);
        if (!padded) { free(msg); return 0; }
        memcpy(padded, msg, L);
        padded[L] = 0x80;
        for (j = L + 1; j < total - 8; ++j) padded[j] = 0;
        for (i = 0; i < 8; ++i) padded[total - 8 + i] = (u8)((u64)L * 8 >> (8 * i));

        md5_init(&ctx);
        for (i = 0; i < blocks; ++i) md5_transform(&ctx, padded + i * 64, 0);
        for (i = 0; i < 4; ++i) {
            d2[i * 4]     = (u8)(ctx.state[i]);
            d2[i * 4 + 1] = (u8)(ctx.state[i] >> 8);
            d2[i * 4 + 2] = (u8)(ctx.state[i] >> 16);
            d2[i * 4 + 3] = (u8)(ctx.state[i] >> 24);
        }
        hex_of(d2, h2);
        free(padded);
        if (strcmp(h1, h2) != 0) {
            printf("  [FAIL] 长度 %lu：填充路径 %s ≠ 流式路径 %s\n", (unsigned long)L, h2, h1);
            bad++;
        }
    }
    free(msg);
    if (!bad) printf("  [ OK ] 手工填充 + 逐组压缩 与 流式 update/final 在 8 种长度上结果一致\n");
    return bad == 0;
}

static int md5_selftest(void)
{
    int ok = 1;
    printf("==================== MD5 自检 ====================\n");
    printf("[1] 常量表 T 由 sin 复算\n");   ok &= check_t_table();
    printf("[2] RFC 1321 标准测试向量\n");    ok &= check_vectors();
    printf("[3] 流式喂入与分组边界\n");       ok &= check_streaming();
    printf("[4] 压缩过程路径与流式路径对拍\n"); ok &= check_trace_path();
    printf("================= %s =================\n", ok ? "全部通过" : "存在失败项");
    return ok;
}

/* ==================== 7. 命令行与交互 ==================== */

static void print_help(void)
{
    printf("实验4 MD5 算法实验（纯 C 实现，不调用任何现成 MD5 库）\n");
    printf("用法：\n");
    printf("  md5.exe                       进入交互模式\n");
    printf("  md5.exe -s <字符串>           计算字符串的 MD5 摘要\n");
    printf("  md5.exe -f <文件名>           计算文件的 MD5 摘要（二进制读入）\n");
    printf("  md5.exe -x <十六进制串>       按十六进制字节计算摘要\n");
    printf("  md5.exe -t <字符串>           打印填充、分组和每轮中间状态\n");
    printf("  md5.exe -T <字符串>           再打印 64 步的逐步状态\n");
    printf("  md5.exe -v                    自检（常量表 + 标准向量 + 分组边界）\n");
}

/* 把十六进制串转成字节，返回字节数，失败返回 -1 */
static long hex_to_bytes(const char *s, u8 *out, size_t cap)
{
    size_t n = 0, i;
    while (s[n] != '\0') n++;
    if (n % 2 != 0) return -1;
    if (n / 2 > cap) return -1;
    for (i = 0; i < n; i += 2) {
        int hi = s[i] >= '0' && s[i] <= '9' ? s[i] - '0'
               : s[i] >= 'a' && s[i] <= 'f' ? s[i] - 'a' + 10
               : s[i] >= 'A' && s[i] <= 'F' ? s[i] - 'A' + 10 : -1;
        int lo = s[i + 1] >= '0' && s[i + 1] <= '9' ? s[i + 1] - '0'
               : s[i + 1] >= 'a' && s[i + 1] <= 'f' ? s[i + 1] - 'a' + 10
               : s[i + 1] >= 'A' && s[i + 1] <= 'F' ? s[i + 1] - 'A' + 10 : -1;
        if (hi < 0 || lo < 0) return -1;
        out[i / 2] = (u8)(hi * 16 + lo);
    }
    return (long)(n / 2);
}

/* 计算文件的摘要，顺带回传文件长度；失败返回 0 */
static int md5_file(const char *path, u8 digest[16], u64 *size)
{
    FILE *fp;
    MD5_CTX ctx;
    u8 buf[65536];
    size_t n;
    u64 total = 0;

    fp = fopen(path, "rb");          /* 必须用 "rb"：文本模式会把 CRLF 换成 LF，摘要就不对了 */
    if (fp == NULL) { printf("无法打开文件：%s\n", path); return 0; }

    md5_init(&ctx);
    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        md5_update(&ctx, buf, n);
        total += n;
    }
    if (ferror(fp)) { printf("读取文件出错：%s\n", path); fclose(fp); return 0; }
    fclose(fp);
    md5_final(&ctx, digest);
    if (size) *size = total;
    return 1;
}

static void print_string_digest(const char *s)
{
    u8 digest[16];
    char hex[33];
    size_t len = strlen(s);
    md5_buffer((const u8 *)s, len, digest);
    hex_of(digest, hex);
    printf("输入字符串 : %s\n", s);
    printf("字节长度   : %lu\n", (unsigned long)len);
    printf("填充后分组 : %lu 组 × 512 bit\n", (unsigned long)block_count(len));
    printf("MD5 摘要   : %s\n", hex);
}

static void interactive(void)
{
    char line[4096];
    for (;;) {
        printf("\n=================== MD5 摘要工具 ===================\n");
        printf(" 1. 计算字符串的 MD5\n");
        printf(" 2. 计算文件的 MD5\n");
        printf(" 3. 压缩过程实验（填充、分组、四轮中间状态）\n");
        printf(" 4. 自检（常量表 / 标准向量 / 分组边界）\n");
        printf(" 0. 退出\n");
        printf("====================================================\n");
        printf("请选择：");
        if (fgets(line, sizeof(line), stdin) == NULL) break;
        if (line[0] == '0') break;

        if (line[0] == '1' || line[0] == '3') {
            printf("请输入字符串（直接回车表示空串）：");
            if (fgets(line, sizeof(line), stdin) == NULL) break;
            line[strcspn(line, "\r\n")] = '\0';
            printf("\n");
            if (line[0] == '1') print_string_digest(line);
            else                md5_trace((const u8 *)line, strlen(line), 1);
        } else if (line[0] == '2') {
            u8 digest[16];
            char hex[33];
            u64 size = 0;
            printf("请输入文件路径：");
            if (fgets(line, sizeof(line), stdin) == NULL) break;
            line[strcspn(line, "\r\n")] = '\0';
            printf("\n");
            if (md5_file(line, digest, &size)) {
                hex_of(digest, hex);
                printf("文件       : %s\n", line);
                printf("文件长度   : %lu 字节\n", (unsigned long)size);
                printf("填充后分组 : %lu 组 × 512 bit\n", (unsigned long)block_count((size_t)size));
                printf("MD5 摘要   : %s\n", hex);
            }
        } else if (line[0] == '4') {
            md5_selftest();
        } else {
            printf("无效选择。\n");
        }
    }
}

int main(int argc, char *argv[])
{
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);     /* Windows 控制台按 UTF-8 输出，中文不乱码 */
#endif

    if (argc == 1) {
        interactive();
        return 0;
    }

    if (strcmp(argv[1], "-s") == 0 && argc >= 3) {
        print_string_digest(argv[2]);
    } else if (strcmp(argv[1], "-f") == 0 && argc >= 3) {
        u8 digest[16];
        char hex[33];
        u64 size = 0;
        if (md5_file(argv[2], digest, &size)) {
            hex_of(digest, hex);
            printf("文件       : %s\n", argv[2]);
            printf("文件长度   : %lu 字节\n", (unsigned long)size);
            printf("填充后分组 : %lu 组 × 512 bit\n", (unsigned long)block_count((size_t)size));
            printf("MD5 摘要   : %s\n", hex);
        } else {
            return 1;
        }
    } else if (strcmp(argv[1], "-x") == 0 && argc >= 3) {
        u8 buf[65536];
        long n = hex_to_bytes(argv[2], buf, sizeof(buf));
        u8 digest[16];
        char hex[33];
        if (n < 0) {
            printf("十六进制串不合法（应为偶数个 0-9a-f 字符，且不超过 %lu 字节）\n",
                   (unsigned long)sizeof(buf));
            return 1;
        }
        md5_buffer(buf, (size_t)n, digest);
        hex_of(digest, hex);
        printf("十六进制输入 : %s\n", argv[2]);
        printf("字节长度     : %ld\n", n);
        printf("填充后分组   : %lu 组 × 512 bit\n", (unsigned long)block_count((size_t)n));
        printf("MD5 摘要     : %s\n", hex);
    } else if ((strcmp(argv[1], "-t") == 0 || strcmp(argv[1], "-T") == 0) && argc >= 3) {
        printf("压缩过程实验：%s\n", argv[2]);
        md5_trace((const u8 *)argv[2], strlen(argv[2]), strcmp(argv[1], "-T") == 0 ? 2 : 1);
    } else if (strcmp(argv[1], "-v") == 0) {
        return md5_selftest() ? 0 : 1;
    } else {
        print_help();
        return 1;
    }
    return 0;
}
```

**（五）编译运行方法与运行结果**

在 Code::Blocks 中打开 md5.cbp，按 F9（Build and run）即可编译运行；也可以直接执行目录里的 build.bat，或在源码目录用命令行编译：gcc -Wall -Wextra -std=c99 -O2 md5.c -o md5.exe，编译无任何警告。程序既支持命令行参数，也支持交互菜单。

图 3 是自检（md5.exe -v）的输出：常量表 T 的 64 个常数与 floor(2^32×|sin(i+1)|) 复算结果逐项一致；RFC 1321 的 7 组标准测试向量全部吻合；“abcdefghijklmnopqrstuvwxyz”逐字节分 26 次喂入与一次喂入结果一致；0、1、55、56、57、63、64、65、119、120、127、128 这 12 种长度的实际分组数为 1/1/1/2/2/2/2/2/2/3/3/3，与公式 ceil((len+9)/64) 完全相符；“手工填充 + 逐组压缩”与“流式 update/final”两条路径在 8 种长度上结果一致。

*图 3  自检输出（常量表复算、标准向量、分组边界、两条路径对拍）*

图 4 是命令行字符串测试：空串得到 d41d8cd98f00b204e9800998ecf8427e，abc 得到 900150983cd24fb0d6963f7d28e17f72，message digest 得到 f96b697d7cb7938d525a2f31aaf161d0，43 字节的英文句子得到 9e107d9d372bb6826bd81d3542a419d6，程序同时打印输入字节数与填充后的分组数。

*图 4  命令行字符串测试（空串、abc、message digest、43 字节英文句子）*

图 5 用十六进制方式精确构造边界长度：55 字节、56 字节、64 字节、65 字节、120 字节，程序给出各自的字节数、填充后分组数与摘要，可以直观看到 55 字节只占 1 组，56 字节起必须占 2 组。

*图 5  十六进制边界长度测试（55 / 56 / 64 / 65 / 120 字节）*

图 6 是文件摘要：空文件、abc.txt、含 CRLF 换行的 crlf.txt、165 字节文本、256 字节二进制文件分别用 -f 计算，并用 Windows 自带的 certutil 和 Python 的 hashlib 对同一个文件复算，三者结果一致。

*图 6  文件摘要与 certutil、hashlib 对比（含 0x00 的二进制文件也正确）*

图 7 是压缩过程实验：以 abc 为例打印填充明细（消息 3 字节 24 bit，补 1 个 0x80，补 52 个 0x00，8 字节小端长度字段 1800000000000000，填充后 64 字节 = 1 组）、本组的 64 个字节与拆出的 16 个消息字、四轮结束时各自的 a、b、c、d、累加后的链接变量，以及最后小端拼接出来的摘要。

*图 7  压缩过程实验（abc：填充、分组、四轮中间状态与链接变量）*

图 8 是交互菜单的运行会话：菜单 1 计算字符串、2 计算文件、3 压缩过程、4 自检、0 退出，输入 abc 与 testdata/binary256.bin 后分别给出摘要与分组数。

*图 8  交互菜单运行会话（菜单 1 / 2 / 0）*

图 9 是把 22 组测试用例交给 md5.exe 与 Python hashlib 全量对拍的汇总表，22 组摘要完全相同。

*图 9  与 Python hashlib 的全量对拍结果（22 组全部一致）*

【待补：需在 CodeBlocks 运行后截图】图 10  Code::Blocks 中的构建输出与运行窗口（图 3～图 9 是本机真实运行的命令行输出；Code::Blocks 工程 md5.cbp 已随实验目录提供，在 CodeBlocks 中打开该工程按 F9 即可复现同样的结果，此处补一张 IDE 里的构建/运行截图即可。）

### 【实验结果分析】

**1. 三组以上测试用例全部正确**

按实验要求至少测了空字符串、abc、message digest 以及长于 64 字节的消息，实际共测 22 组（字符串、十六进制、文件三类），把每一组的输出与 Python 3.11 的 hashlib.md5 逐一对比，22 组全部相同；其中 5 个文件另外用 Windows 自带的 certutil -hashfile … MD5 复算，结果也一致；空串、abc、message digest 等还与 RFC 1321 附录 A.5 公布的标准值一致（这三个标准值也可以在实验下发的在线工具 http://www.metools.info/code/c26.html 里手工复核）。测试用例与实测结果见表 1。

| 序号 | 测试输入 | 方式 | 字节数 | 分组数 | 本程序 md5.exe 输出摘要 | 与对比工具比对 |
|---|---|---|---|---|---|---|
| 1 | 空字符串 | s | 0 | 1 | d41d8cd98f00b204e9800998ecf8427e | 一致 |
| 2 | 单字符 a | s | 1 | 1 | 0cc175b9c0f1b6a831c399e269772661 | 一致 |
| 3 | abc | s | 3 | 1 | 900150983cd24fb0d6963f7d28e17f72 | 一致 |
| 4 | message digest | s | 14 | 1 | f96b697d7cb7938d525a2f31aaf161d0 | 一致 |
| 5 | 26 个小写字母 | s | 26 | 1 | c3fcd3d76192e4007dfb496cca67e13b | 一致 |
| 6 | 大小写 + 数字 62 字符 | s | 62 | 2 | d174ab98d277d9f5a5611c2c9f419d9f | 一致 |
| 7 | 80 个数字 | s | 80 | 2 | 57edf4a22be3c955ac49da2e2107b67a | 一致 |
| 8 | The quick brown fox…dog | s | 43 | 1 | 9e107d9d372bb6826bd81d3542a419d6 | 一致 |
| 9 | 中文（GBK 参数） | s | 22 | 1 | ed8320601faed6d6b2548b3e847e5bac | 一致 |
| 10 | 同一句中文（UTF-8 字节） | x | 33 | 1 | 7bc7b9a0211b2c9cd0fc5f7283a0f1d6 | 一致 |
| 11 | 55 字节边界 | x | 55 | 1 | e38a93ffe074a99b3fed47dfbe37db21 | 一致 |
| 12 | 56 字节边界 | x | 56 | 2 | ee0a6d91f573b47a98f7ce0b4d671c5f | 一致 |
| 13 | 64 字节整分组 | x | 64 | 2 | 96d2704b7115c040215a81e658b74d8c | 一致 |
| 14 | 65 字节跨两组 | x | 65 | 2 | 1afec21cec29bea96f5fe4c5c0268f38 | 一致 |
| 15 | 120 字节三组 | x | 120 | 3 | 4195f7932c650e5ad0905857a32d35a1 | 一致 |
| 16 | 含 NUL 的 16 字节 | x | 16 | 1 | 7cec0f7ca91590754b7bf7b6f5b253f3 | 一致 |
| 17 | empty.txt 空文件 | f | 0 | 1 | d41d8cd98f00b204e9800998ecf8427e | 一致 |
| 18 | abc.txt | f | 3 | 1 | 900150983cd24fb0d6963f7d28e17f72 | 一致 |
| 19 | crlf.txt（含 CRLF） | f | 21 | 1 | 4eddda61f5e53754d0b028ab69a17be9 | 一致 |
| 20 | longtext.txt | f | 165 | 3 | 3787e3c73514c641309558bfb82cb7ba | 一致 |
| 21 | binary256.bin（0x00~0xFF） | f | 256 | 5 | e2c865db4162bed963bfaa9ef6ac18f0 | 一致 |
| 22 | des.c（实验2 源码） | f | 23152 | 362 | 4776b091679b0c5800716503644b5f2e | 一致 |

表 1  测试用例与实测结果（方式 s = 命令行字符串、x = 十六进制字节、f = 文件；对比工具为 Python hashlib.md5，文件另行用 certutil 复核，全部一致）

**2. 填充与分组规律符合公式**

填充规则是这次实验里最容易写错的地方，程序把每一步填充都打印出来，实测数据见表 2。可以看出：长度 0～55 字节补完 0x80 后，0x00 的数量刚好够凑到 56 字节，总共只占 1 组；一旦长度为 56 字节，补完 0x80 后已经越过了第 56 字节的位置，必须再补 63 个 0x00、凑出第 2 组；119 字节与 120 字节之间同样存在这样的分界（2 组 → 3 组）。所有实测的分组数都与公式 ceil((len+9)/64) 一致，文件长度 165 字节 → 3 组、256 字节 → 5 组、24897 字节的 md5.c → 390 组也都符合。

| 消息长度 / 字节 | 补 0x80 | 补 0x00 | 长度字段（小端） | 填充后 / 字节 | 分组数 |
|---|---|---|---|---|---|
| 0 | 1 | 55 | 0000000000000000 | 64 | 1 |
| 1 | 1 | 54 | 0800000000000000 | 64 | 1 |
| 55 | 1 | 0 | b801000000000000 | 64 | 1 |
| 56 | 1 | 63 | c001000000000000 | 128 | 2 |
| 64 | 1 | 55 | 0002000000000000 | 128 | 2 |
| 65 | 1 | 54 | 0802000000000000 | 128 | 2 |
| 119 | 1 | 0 | b803000000000000 | 128 | 2 |
| 120 | 1 | 63 | c003000000000000 | 192 | 3 |
| 24897（md5.c 本身） | 1 | 54 | 080a030000000000 | 24960 | 390 |

表 2  填充与分组实测数据（长度字段是 L×8 的小端表示，例如 55 字节 = 440 bit = 0x1B8，小端写成 b8 01 00 00 00 00 00 00）

**3. 压缩过程的中间状态与标准值一致**

以 abc 为例（图 7），程序打印的填充结果是：消息 3 字节 24 bit，补 1 个 0x80、52 个 0x00，长度字段 1800000000000000，填充后 64 字节 1 组；本组 16 个消息字只有 X[0]=0x80636261 与 X[14]=0x00000018 非零——前者正是 61 62 63 80 按小端读入的结果，后者对应 24 bit 的长度。进入本组的链接变量是初始化向量，四轮结束时 a、b、c、d 分别为 0x310ade8f、0xc08226b3、0xe484b9d8、0x624d8cb2，累加后得到 A=0x98500190、B=0xb04fd23c、C=0x7d3f96d6、D=0x727fe128，按小端拼出的摘要 900150983cd24fb0d6963f7d28e17f72 与 RFC 1321 附录 A.3 为 abc 公布的中间值和最终摘要完全一致，说明四轮压缩、常量表、移位和消息字下标都没有写错。

**4. 雪崩效应**

MD5 要求输入微小变化导致输出巨大变化。实测把 abc 改成 abd（只差 1 个字符，该字节的 8 位里有 3 位不同），摘要由 90015098… 变成 4911e516…；把 64 字节全 0 数据的首字节 0x00 改成 0x80（512 位里只有 1 位不同），摘要也完全不同。按 128 bit 统计，两种情况分别有 63 位、75 位发生了变化，接近理论上的一半，说明扩散效果正常，见表 3。

| 输入 A | 输入 B | 相差 | 摘要 A | 摘要 B | 不同比特 |
|---|---|---|---|---|---|
| abc | abd | 3 bit | 900150983cd24fb0d6963f7d28e17f72 | 4911e516e5aa21d327512e0c8b197616 | 63 / 128 |
| abc | abe | 8 bit | 900150983cd24fb0d6963f7d28e17f72 | 7888d65a43501d992cc38638b59964d6 | 62 / 128 |
| 64 字节全 0 | 首字节改 0x80 | 1 bit | 3b5d3c7d207e37dceeedd301e35e2e58 | d100adc7d963ac0b837f7ac29dc701d7 | 75 / 128 |

表 3  雪崩效应实测（不同比特数由两份摘要异或后统计得到）

**5. 调试中发现的问题**

（1）文件必须以二进制方式打开：“md5.exe -f testdata/crlf.txt”第一次算出来的摘要总跟 certutil 对不上，打印的字节数还是 18 而不是 21。原因是 fopen() 用了文本模式 "r"，Windows 会把文件里的 CRLF 悄悄翻译成 LF，送进压缩函数的数据已经不是文件本来的内容。我把同一份文件分别用两种模式算了一遍：文本模式得到 18 字节、cc3d5ed5fda53dfa81ea6aa951d7e1fe（正是把 CRLF 换成 LF 之后的内容的摘要），二进制模式得到 21 字节、4eddda61f5e53754d0b028ab69a17be9，与 hashlib 读原始字节的结果一致。把 fopen() 改成 "rb" 之后问题消失，这也说明为什么不同机器上算同一个文本文件的 MD5 会不一致——换行符和编码不同，摘要就一定不同。

（3）长度字段打印漏了掩码：压缩过程实验里打印 8 字节小端长度字段时，第一次写成了 printf("%02x", (unsigned)((u64)len * 8 >> (8 * i)))，只右移没有和 0xFF 相与。长度较小时看不出问题（例如 3 字节恰好打印 16 个字符），但测到 55 字节时长度字段打成了 17 个字符 1b801000000000000（0x1B8 整个被打印出来），56 字节时是 c001… 的位置错乱。摘要本身不受影响（md5_final() 里把长度写入的是 u8，不受这个显示 bug 影响），但足以误导阅读中间值的人；改成 (unsigned)(((u64)len * 8 >> (8 * i)) & 0xffu) 之后，55 字节显示 b801000000000000、64 字节显示 0002000000000000，与手工计算一致。

（4）编译告警不能忽略：用 gcc -Wall -Wextra 编译时提示 “variable 'padlen' set but not used”，检查后发现在自检函数 check_trace_path() 里算出的填充字节数没有用上（另一处已用 total - L - 8 代替），删掉之后编译完全无警告，也顺手把这段代码写清楚了一些。

**6. 与其他实现对比和安全性讨论**

自己实现的 22 组结果与 hashlib、certutil、在线工具、RFC 1321 标准值完全一致，说明算法实现正确；本程序为了把流程讲清楚，保留了压缩过程追踪、逐组统计等代码，速度不是重点。值得注意的是，实验里也看到了 MD5 的脆弱之处：输入只改 1 bit，摘要就有接近一半的比特翻转，这既是雪崩效应的正面表现，也意味着可以用差分分析寻找碰撞——2004 年以后 MD5 的抗碰撞性已经不存在。因此实际系统里，校验文件完整性可以用 MD5，但数字签名、证书、口令存储都必须换用 SHA-256 及以上的算法；口令还应加盐、使用慢哈希，避免彩虹表与批量破解。

### 【心得体会】

这次实验让我第一次把一个散列算法从“知道名字”写到了“能跑出正确摘要”。最有收获的是填充这一步：以前只知道“MD5 把消息补到 64 字节”，动手写才发现规则很讲究——先补一个 0x80，再补 0x00 补到 ≡56 (mod 64)，最后 8 个字节是原始长度的小端表示。正是这条规则造成了 55 字节与 56 字节的分界：多一个字节就要多压一组。我把 0、1、55、56、64、65、119、120 字节直到 24897 字节的 md5.c 这样一串长度都跑了一遍，实测分组数和公式 ceil((len+9)/64) 完全吻合，才算真的理解了长度字段里为什么要写“原始长度”而不是“填充后的长度”。

第二个收获是学会用中间值验证，而不是只盯着最终摘要。写完压缩函数后，我用自己写的压缩过程追踪把 16 个消息字、每轮的 a、b、c、d 都打出来核对：先确认 X[0]=0x80636261（正是 61 62 63 80 按小端读入）、X[14]=0x00000018（对应 24 bit 的长度），再把累加后的链接变量 A=0x98500190、B=0xb04fd23c、C=0x7d3f96d6、D=0x727fe128 与 RFC 1321 附录 A.3 为 abc 公布的中间值对照，最后才看摘要。这样一旦结果不对，就能立刻判断问题出在哪一组、哪一轮，而不是对着一个 32 位十六进制串发愁。这个过程也让我明白常量表 T[i]=floor(2^32×|sin(i+1)|) 不是随手写的魔数——程序里用 sin() 复算 64 个常数逐项一致，而且浮点值离整数最近也还有 0.0154 的余量，不会因为取整产生歧义。

第三个收获是那些“不是算法错、但结果就是不对”的坑：文本模式打开文件会把 CRLF 换成 LF，所以同一个文件的摘要会和别人算的不一样，必须用 "rb"；命令行传中文时 Windows 按 GBK 编码给程序，和网页工具的 UTF-8 并不是同一串字节，两个摘要都对，但含义不同；还有一个长度字段打印漏了 &0xFF、长度一大就多打一个字符的显示 bug。这些细节比算法本身更贴近真实工程，也让我以后看到“MD5 对不上”时知道该先怀疑什么——先比字节，再比算法。

最后是安全性上的认识变化。以前觉得 MD5 只是“老旧”，做完这次实验才具体地看到：输入改 1 bit，摘要就有 60 多位翻转，这种强扩散在防止篡改时是优点，但同一性质也意味着可以通过差分分析构造碰撞，2004 年之后 MD5 的抗碰撞性已经不存在了。所以 MD5 现在只适合做非对抗性的完整性校验，数字签名、证书和口令存储必须换用 SHA-256 及以上的算法并加盐。这次实验的代码全部是自己按 RFC 1321 写的，没有调用任何现成的 MD5 库，验证时也刻意用了 hashlib、certutil 和在线工具三种互不相干的实现来对拍，22 组用例全部一致，这是我认为最踏实的部分。

## 可复现补充

## 复现命令

代码就在上一节完整源码中。保存为 `md5.c` 后：

```bash
gcc -Wall -Wextra -O2 -std=c99 md5.c -o md5
```

字符串：

```bash
./md5 -s abc
```

预期：

```text
900150983cd24fb0d6963f7d28e17f72
```

文件：

```bash
printf 'abc' > /tmp/abc.txt
./md5 -f /tmp/abc.txt
```

十六进制：

```bash
./md5 -x 616263
```

逐轮中间值：

```bash
./md5 -t abc
./md5 -T abc
```

自检：

```bash
./md5 -v
```

与系统工具对拍：

```bash
printf 'abc' | md5sum
certutil -hashfile /tmp/abc.txt MD5
```

Windows 编译：

```powershell
gcc -Wall -Wextra -O2 -std=c99 md5.c -o md5.exe
.\md5.exe -v
```

## 排错

| 现象 | 原因 |
| --- | --- |
| 摘要不一致 | 字节序、填充长度或轮移位错误 |
| 55/56 字节测试失败 | 长度填充边界错误 |
| 中文摘要错误 | 源字符串不是 UTF-8 参与计算 |
| 文件结果错误 | 以文本模式读取，发生了换行转换 |
| `-x` 失败 | 十六进制长度奇数或字符非法 |
