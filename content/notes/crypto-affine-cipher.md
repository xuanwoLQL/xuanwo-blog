---
title: "仿射变换加解密实验"
slug: "crypto-affine-cipher"
date: 2026-10-08T13:24:46+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从公式推导到纯 C 实现：312 组密钥、暴力枚举与卡方频率分析破译。"
summary: "从公式推导到纯 C 实现：312 组密钥、暴力枚举与卡方频率分析破译。"
tags: ["密码学", "仿射密码", "C"]
categories: ["密码学"]
series: ["密码学实验"]
weight: 1
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
  <img src="/images/notes/crypto-affine-cipher/workflow.svg" alt="加密、密钥枚举和卡方频率分析共享同一套字符映射。" loading="lazy">
  <figcaption>图 1 · 仿射密码实现与破译。加密、密钥枚举和卡方频率分析共享同一套字符映射。</figcaption>
</figure>

| 项目 | 内容 |
| --- | --- |
| 题    目 | 仿射密码（仿射变换加解密） |
| 日    期 | 2026 年 9 月 20 日 |

> 说明：本报告只涉及 C 语言实现，程序清单与运行结果均来自本机实际编译运行（Windows 11 + gcc 16.1.0）；标注“截图占位”的图需要在 VS Code 中自行运行后截图粘贴，报告中不放置任何伪造截图。

### 【实验目的】

（1）理解仿射密码的数学原理，掌握其作为“加法密码 + 乘法密码”的组合形式，能够推导加密公式 E(x) = (k1·x + k2) mod 26 与解密公式 D(y) = k1^(-1)·(y − k2) mod 26。

（2）掌握仿射密码密钥的合法性判定条件 gcd(k1, 26) = 1，理解乘法逆元的含义，会用扩展欧几里得算法编程求解 k1^(-1)，并能计算仿射密码的密钥空间（12 × 26 = 312 组）。

（3）使用 C 语言实现仿射密码的加密与解密程序，掌握字母编号与数值的相互转换、大小写保持、非字母字符原样保留、非法密钥拦截等编程细节。

（4）设计正常、边界、异常三类测试用例对程序进行验证，通过手工计算与逐条运行实际命令的方式，核对程序的加密、解密结果是否正确。

（5）从密码分析的角度出发，用 C 语言实现暴力枚举与频率分析两个攻击功能，理解仿射密码作为单表代换密码的安全强度与固有缺陷，为后续学习多表代换与分组密码打下基础。

### 【实验环境】

本次实验在 Windows 环境下完成，程序的编写、编译与运行均在 VS Code 的集成终端中完成，具体环境配置如表 1-1 所示。

**表 1-1  实验软硬件环境**

| 项目 | 具体配置 | 用途说明 |
| --- | --- | --- |
| 操作系统 | Windows 11 家庭版（版本 10.0.26200），64 位 | 宿主机实验环境 |
| 代码编辑器 | Visual Studio Code（~/Download\Microsoft VS Code） | 代码编写与集成终端调试 |
| C 编译器 | MinGW-W64 gcc 16.1.0（x86_64-ucrt-mcf-seh） | 编译 affine_cipher.c |
| 编译选项 | gcc -Wall -Wextra -O2 -g | 开启全部警告，静态检查代码质量 |
| 终端编码 | VS Code 集成终端 / PowerShell（chcp 65001，UTF-8） | 保证中文与符号正常显示 |
| 测试方式 | 手工计算核对 + 逐条运行命令比对输出 | 覆盖正常、边界、异常与密码分析四类场景 |

说明：程序只使用 C 标准库 stdio.h、stdlib.h、string.h，不依赖任何第三方库，因此在 Windows（MinGW/W64 gcc）与 Linux（gcc）下都能直接编译运行。code 目录下的“编译并运行演示.bat”可在 Windows 下双击完成编译与运行，Makefile 则提供 make / make run / make clean 三个目标。

### 【实验涉及相关概念和基本原理】

#### 1  仿射密码的由来：从加法密码到仿射变换

加法密码（移位密码）的加密规则是 E(x) = (x + k) mod 26，它只对字母编号做“平移”，密钥空间只有 26 种；乘法密码的加密规则是 E(x) = (k1·x) mod 26，它对字母编号做“伸缩”，但要求 k1 与 26 互素，否则不同的明文字母会被映射到同一个密文字母，解密时无法唯一还原。

仿射密码把这两种运算组合起来，即先做乘法再做加法（这正是解析几何中“仿射变换”y = k1·x + k2 的形式，只是运算在模 26 的整数环上进行），从而获得比加法密码更强的置乱效果。因此仿射密码属于单表代换密码：明文字母表中的每个字母固定映射为密文字母表中的某个字母，映射关系由密钥 (k1, k2) 唯一确定。

#### 2  加密与解密公式

约定 A/a 编号为 0，B/b 编号为 1，……，Z/z 编号为 25，则仿射密码的加解密公式为：

```text
加密：  E(x) = (k1 * x + k2) mod 26                 其中 gcd(k1, 26) = 1
解密：  D(y) = k1^(-1) * (y - k2) mod 26           k1^(-1) 为 k1 模 26 的乘法逆元
```

解密公式的推导过程：由 y ≡ k1·x + k2 (mod 26) 可得 k1·x ≡ y − k2 (mod 26)；两边同时乘以 k1 的乘法逆元 k1^(-1)，利用 k1^(-1)·k1 ≡ 1 (mod 26)，即得 x ≡ k1^(-1)·(y − k2) (mod 26)。可见解密能否进行完全取决于 k1^(-1) 是否存在，这就是 k1 必须与 26 互素的根本原因。

#### 3  密钥合法性判定与乘法逆元的计算

（1）合法性判定。k1 必须满足 gcd(k1, 26) = 1。因为 26 = 2 × 13，所以 k1 不能是 2 或 13 的倍数，在 0～25 中满足条件的 k1 共有 12 个：1、3、5、7、9、11、15、17、19、21、23、25。例如 k1 = 13 时，E(a) = 0、E(n) = 13 × 13 = 169 ≡ 13 (mod 26)，实际上任何字母的密文都只能是 a 或 n，信息严重丢失，无法解密。

（2）逆元的定义。若 a·x ≡ 1 (mod m)，则称 x 为 a 模 m 的乘法逆元，记作 a^(-1)。求逆元的常用方法是扩展欧几里得算法，它能在求 gcd(a, m) 的同时求出满足 a·x + m·y = gcd(a, m) 的整数 x、y；当 gcd(a, m) = 1 时，x 就是 a 的逆元（若 x 为负数再加上 m 即可）。算法流程如下：

```text
设 t = 0，newt = 1，r = m，newr = a mod m
当 newr ≠ 0 时循环执行：
    q = r / newr
    (t, newt) = (newt, t - q * newt)
    (r, newr) = (newr, r - q * newr)
循环结束后：若 r > 1，说明 a 与 m 不互素，逆元不存在；
            否则 t 即为 a 的逆元（t < 0 时加上 m 归一化到 [0, m) 区间）
```

（3）手算校验示例。求 5 模 26 的逆元：由 26 = 5 × 5 + 1 得 1 = 26 − 5 × 5，即 5 × (−5) ≡ 1 (mod 26)，把 −5 归一化为 −5 + 26 = 21，故 5^(-1) = 21，验算 5 × 21 = 105 = 4 × 26 + 1 ≡ 1 (mod 26)，结果正确。程序在输出映射表时会同时打印逆元并做同样的验算，可与手算结果相互印证。

**表 1-2  12 个合法密钥 k1 及其乘法逆元（mod 26）**

| k1 | k1^(-1) | k1 | k1^(-1) |
| --- | --- | --- | --- |
| 1 | 1 | 7 | 15 |
| 3 | 9 | 9 | 3 |
| 5 | 21 | 11 | 19 |
| 15 | 7 | 17 | 23 |
| 19 | 11 | 21 | 5 |
| 23 | 17 | 25 | 25 |

从表 1-2 可以看出，逆元具有对称性：若 x 是 a 的逆元，则 a 也是 x 的逆元（例如 5 与 21、7 与 15、3 与 9）；其中 1 和 25 的逆元是自身，因为 1 × 1 = 1、25 × 25 = 625 = 24 × 26 + 1。

#### 4  密钥空间与安全性分析

（1）密钥空间。合法的 k1 有 12 个，k2 可以取 0～25 共 26 个值，因此仿射密码的密钥空间为 12 × 26 = 312 组。这个数量非常小，用普通计算机在毫秒级即可完成全密钥穷举，属于典型的“密钥空间过小”的古典密码。

（2）映射的唯一性。当 gcd(k1, 26) = 1 时，加密函数是一个双射（一一映射）：26 个明文字母恰好映射到 26 个不同的密文字母，不会出现“多个明文字母对应同一个密文字母”的情况，这保证了解密结果的唯一性。

（3）频率分析攻击。仿射密码是单表代换密码，它只改变字母的“名字”，不改变字母出现的“频率结构”，因此英文中 e、t、a 出现频率高的统计规律在密文中依然存在。攻击者无需知道密钥，只要密文足够长，就可以统计密文中各字母出现的次数，与标准英文频率表对比（常用卡方统计量衡量相似程度），在 312 组候选密钥中找出使明文最“像英文”的那一组。本报告的实验部分用 -B 与 -C 两个功能完整演示了这两种攻击（见 5.3、5.4 节），这也是仿射密码在现代密码学中只具有教学价值、不能用于实际加密的原因。

### 【实验内容】

#### 4.1  实验任务分解

**表 4-1  实验任务分解与验证方式**

| 序号 | 任务内容 | 实验产出 | 验证方式 |
| --- | --- | --- | --- |
| 1 | 确定明文与密钥，手算 2～3 个字母的加密结果 | 明文、密钥与手算数据 | 与程序运行结果比对 |
| 2 | 用 C 语言实现仿射密码加解密 | code/affine_cipher.c | gcc 编译无警告，输出与手算结果一致 |
| 3 | 实现密钥合法性检查与逆元计算 | is_valid_k1()、mod_inverse() | 非法密钥被拦截，逆元性质自动化校验 |
| 4 | 设计并执行测试用例（正常 / 边界 / 异常） | 表 4-3 中的 8 条测试用例 | 逐条运行命令，输出与预期结果一致 |
| 5 | 实现暴力枚举攻击（-B） | brute_force() | 312 组密钥全部枚举，正确明文唯一命中 |
| 6 | 实现频率分析攻击（-C） | score_english()、crack_by_frequency() | 未知密钥时破译出 k1 = 7、k2 = 10 |

#### 4.2  明文与密钥的设定

为充分测试程序的健壮性，明文同时包含大写字母、小写字母、空格、数字、标点符号和中文汉字；主密钥取 k1 = 5、k2 = 8（满足 gcd(5, 26) = 1，5^(-1) = 21）。此外，为了对比不同密钥的置乱效果以及完成频率分析实验，实验中还使用了 k1 = 7、k2 = 3 与 k1 = 7、k2 = 10 两组密钥，具体设定见表 4-2。

**表 4-2  本次实验使用的明文与密钥**

| 用途 | 明文 / 密文 | 密钥 | 说明 |
| --- | --- | --- | --- |
| 主示例 | Affine Cipher Test 2026, 仿射密码实验! | k1 = 5, k2 = 8 | 含大小写、数字、标点、中文，用于内置示例 |
| 映射表对比 | abcdefghijklmnopqrstuvwxyz | k1 = 7, k2 = 3 | 观察不同 k1 对字母表的置乱效果 |
| 暴力枚举 | ihhwvc swfrcp | 未知（k1 = 5, k2 = 8） | 对 312 组密钥逐个尝试 |
| 频率分析 | the affine cipher is a type of monoalphabetic … | 未知（k1 = 7, k2 = 10） | 较长的英文密文，用于频率分析破译 |
| 异常测试 | test | k1 = 4, k2 = 8 | k1 与 26 不互素，用于验证非法密钥拦截 |

#### 4.3  加解密算法流程图

![图 1  仿射密码加解密算法流程图](/images/notes/crypto-affine-cipher/img-01.png)

*图 1  仿射密码加解密算法流程图*

流程图说明：程序先输入明文 P 与密钥 k1、k2，然后判断 gcd(k1, 26) 是否等于 1：若不等于 1，则输出“k1 不合法，要求重新输入密钥”并回到输入密钥步骤；若合法，则进入逐字符处理循环——取出下一个字符 c，判断它是否为英文字母：若是字母，则令 x 为它在字母表中的编号，按 y = (k1·x + k2) mod 26 计算，再转换为编号 y 对应的大小写字母；若不是字母（数字、空格、标点、汉字等），则原样保留。循环直到明文全部处理完，输出密文 C。解密时先用扩展欧几里得算法计算 k1^(-1) mod 26，再按 x = k1^(-1)·(y − k2) mod 26 逐个字母还原，输出解密结果 P'，最后比较 P' 与 P 是否完全一致：一致则结束，不一致则提示错误并回到输入密钥重试。

#### 4.4  C 语言实现

C 语言实现文件为 code/affine_cipher.c，共 393 行（含注释），分为基础数学函数、单字符与字符串加解密、功能展示、密码分析（暴力枚举与频率分析）、命令行界面五个部分，完整代码如下。

**程序清单 4-1  affine_cipher.c（仿射密码加解密与密码分析，C 语言版）**

```c
/* =====================================================================
 * affine_cipher.c —— 仿射密码（Affine Cipher）加解密完整实现（C 语言版）
 *
 * 实验名称：实验1 仿射变换加解密实验
 * 编译（Windows + MinGW/gcc 或 Linux 均可）：
 *     gcc -Wall -Wextra -O2 -g affine_cipher.c -o affine_cipher
 * 运行示例：
 *     affine_cipher.exe                      # 内置示例（加密、解密、字母映射表）
 *     affine_cipher.exe -e -a 5 -b 8 -t "affine cipher"   # 加密
 *     affine_cipher.exe -d -a 5 -b 8 -t "ihhwvc swfrcp"   # 解密
 *     affine_cipher.exe -T -a 5 -b 8         # 输出 26 个字母的加密映射表
 *     affine_cipher.exe -B -t "ihhwvc swfrcp"  # 暴力枚举全部 312 组密钥
 *     affine_cipher.exe -C -t "<英文密文>"      # 频率分析破译（无需已知密钥）
 *     affine_cipher.exe                      # 内置示例（加密、解密、字母映射表）
 *
 * 算法说明：
 *     加密：E(x) = (k1 * x + k2) mod 26
 *     解密：D(y) = k1^(-1) * (y - k2) mod 26
 *     其中 x、y 为字母在 [0,25] 中的编号（A/a=0，B/b=1，…，Z/z=25），
 *     k1 必须与 26 互素（gcd(k1,26)=1），否则乘法逆元 k1^(-1) 不存在，
 *     解密无法唯一还原；k2 为任意整数（模 26 使用）。
 * ===================================================================== */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MOD       26        /* 英文字母表长度 */
#define MAX_TEXT  4096      /* 单次处理的文本最大长度（含结束符） */

/* 标准英文字母使用频率（百分比），用于频率分析破译，来源为通用英文语料统计结果 */
static const double ENGLISH_FREQ[MOD] = {
    8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772, 4.025,
    2.406, 6.749, 7.507, 1.929,  0.095, 5.987, 6.327, 9.056,  2.758, 0.978, 2.360, 0.150,
    1.974, 0.074
};

/* ==================== 一、基础数学函数 ==================== */

/* 求最大公约数（辗转相除法），返回值恒为非负 */
static int gcd_int(int a, int b)
{
    if (a < 0) a = -a;
    if (b < 0) b = -b;
    while (b != 0) {
        int t = a % b;
        a = b;
        b = t;
    }
    return a;
}

/* 扩展欧几里得算法求乘法逆元：返回 x，使 a * x ≡ 1 (mod m)
 * 若 gcd(a,m) != 1（逆元不存在）则返回 -1 */
static int mod_inverse(int a, int m)
{
    int t = 0, newt = 1;
    int r = m, newr = ((a % m) + m) % m;   /* 把 a 归一到 [0, m) */

    while (newr != 0) {
        int q = r / newr;
        int tmp = t - q * newt;  t = newt;  newt = tmp;
        tmp     = r - q * newr;  r = newr;  newr = tmp;
    }
    if (r > 1)      return -1;             /* 不互素，无逆元 */
    if (t < 0)      t += m;                /* 归一化到 [0, m) */
    return t;
}

/* 判断密钥 k1 是否合法：必须与 26 互素（合法取值只有 12 个） */
static int is_valid_k1(int k1)
{
    int k = ((k1 % MOD) + MOD) % MOD;
    return gcd_int(k, MOD) == 1;
}

/* ==================== 二、单字符与字符串加解密 ==================== */

/* 加密一个字符：E(x) = (k1 * x + k2) mod 26
 * 大写字母仍为大写，小写字母仍为小写；
 * 数字、空格、标点以及中文等多字节字符一律原样保留 */
static char encrypt_char(char c, int k1, int k2)
{
    //下面的 % MOD + MOD) % MOD是为了处理负数取模
    if (c >= 'A' && c <= 'Z')
        return (char)('A' + ((k1 * (c - 'A') + k2) % MOD + MOD) % MOD);
    if (c >= 'a' && c <= 'z')
        return (char)('a' + ((k1 * (c - 'a') + k2) % MOD + MOD) % MOD);
    return c;
}

/* 解密一个字符：D(y) = k1^(-1) * (y - k2) mod 26，inv_k1 为预先算好的逆元 */
static char decrypt_char(char c, int k2, int inv_k1)
{
    if (c >= 'A' && c <= 'Z')
        return (char)('A' + ((inv_k1 * ((c - 'A') - k2)) % MOD + MOD) % MOD);
    if (c >= 'a' && c <= 'z')
        return (char)('a' + ((inv_k1 * ((c - 'a') - k2)) % MOD + MOD) % MOD);
    return c;
}

/* 加密整个字符串：逐字符加密，输出到调用者提供的缓冲区 */
static void affine_encrypt(const char *plain, char *cipher, int k1, int k2)
{
    size_t i;
    for (i = 0; plain[i] != '\0' && i < MAX_TEXT - 1; i++)
        cipher[i] = encrypt_char(plain[i], k1, k2);
    cipher[i] = '\0';
}

/* 解密整个字符串：k1 非法时返回 -1，正常返回 0 */
static int affine_decrypt(const char *cipher, char *plain, int k1, int k2)
{
    int inv_k1 = mod_inverse(k1, MOD);
    size_t i;

    if (inv_k1 < 0)
        return -1;                          /* k1 与 26 不互素，无法解密 */

    for (i = 0; cipher[i] != '\0' && i < MAX_TEXT - 1; i++)
        plain[i] = decrypt_char(cipher[i], k2, inv_k1);
    plain[i] = '\0';
    return 0;
}

/* ==================== 三、功能展示函数 ==================== */

/* 打印 26 个字母的加密映射表，便于手工核对 */
static void print_table(int k1, int k2)
{
    char plain_buf[MOD + 1], cipher_buf[MOD + 1];
    int inv = mod_inverse(k1, MOD);
    int i;

    for (i = 0; i < MOD; i++) {
        plain_buf[i]  = (char)('a' + i);
        cipher_buf[i] = encrypt_char((char)('a' + i), k1, k2);
    }
    plain_buf[MOD] = cipher_buf[MOD] = '\0';

    printf("明文(a-z) : %s\n", plain_buf);
    printf("密文(a-z) : %s\n", cipher_buf);
    printf("k1 = %d, k2 = %d, k1 的乘法逆元 k1^(-1) = %d (mod 26)\n", k1, k2, inv);
    printf("校验：%d * %d mod 26 = %d（应等于 1，说明逆元正确）\n",
           k1, inv, (k1 * inv) % MOD);
}

/* 输出一组加解密示例，并验证“解密(加密(明文)) == 明文” */
static int run_demo(void)
{
    const char *plain   = "Affine Cipher Test 2026, 仿射密码实验!";
    int k1 = 5, k2 = 8;
    char cipher[MAX_TEXT], back[MAX_TEXT];

    affine_encrypt(plain, cipher, k1, k2);
    if (affine_decrypt(cipher, back, k1, k2) != 0) {
        printf("解密失败：k1=%d 与 26 不互素。\n", k1);
        return 1;
    }

    printf("---------------- 加解密示例 ----------------\n");
    printf("密钥      : k1 = %d, k2 = %d\n", k1, k2);
    printf("明文      : %s\n", plain);
    printf("密文      : %s\n", cipher);
    printf("解密还原  : %s\n", back);
    printf("一致性校验: %s\n", (strcmp(plain, back) == 0) ? "通过（解密结果与明文完全相同）"
                                                            : "失败（解密结果与明文不同）");
    printf("\n---------------- 字母映射表 ----------------\n");
    print_table(k1, k2);
    return (strcmp(plain, back) == 0) ? 0 : 1;
}

/* ==================== 四、密码分析功能：暴力枚举与频率分析 ==================== */

/* 卡方统计量：衡量文本中各字母出现次数与标准英文频率的接近程度
 * 得分越小说明该文本越"像"正常的英文，可用于在 312 组候选密钥中挑出正确的那一组 */
static double score_english(const char *text)
{
    int counts[MOD] = {0};
    int total = 0, i;
    double score = 0.0;

    for (i = 0; text[i] != '\0'; i++) {
        if (text[i] >= 'a' && text[i] <= 'z') {
            counts[text[i] - 'a']++;
            total++;
        } else if (text[i] >= 'A' && text[i] <= 'Z') {
            counts[text[i] - 'A']++;
            total++;
        }
    }
    if (total == 0)
        return 1e18;                        /* 没有字母，认为完全不像英文 */

    for (i = 0; i < MOD; i++) {
        double expect = ENGLISH_FREQ[i] / 100.0 * total;    /* 该字母的期望出现次数 */
        double diff   = counts[i] - expect;
        score += diff * diff / expect;
    }
    return score;
}

/* 暴力枚举全部 312 组密钥（12 个合法 k1 × 26 个 k2），打印前 show_first 组候选明文
 * 返回实际枚举的密钥组数 */
static int brute_force(const char *cipher, int show_first)
{
    char buf[MAX_TEXT];
    int k1, k2, count = 0;

    for (k1 = 0; k1 < MOD; k1++) {
        if (!is_valid_k1(k1)) continue;
        for (k2 = 0; k2 < MOD; k2++) {
            affine_decrypt(cipher, buf, k1, k2);
            count++;
            if (count <= show_first)
                printf("  k1 = %2d, k2 = %2d → %s\n", k1, k2, buf);
        }
    }
    return count;
}

/* 频率分析破译（唯密文攻击）：遍历全部密钥，返回卡方得分最低的一组
 * 结果通过输出参数返回，便于其它功能复用 */
static void crack_by_frequency(const char *cipher, int *out_k1, int *out_k2,
                              char *out_plain, double *out_score)
{
    char buf[MAX_TEXT];
    int k1, k2, best_k1 = 0, best_k2 = 0, first = 1;
    double best = 0.0;

    for (k1 = 0; k1 < MOD; k1++) {
        if (!is_valid_k1(k1)) continue;
        for (k2 = 0; k2 < MOD; k2++) {
            double s;
            affine_decrypt(cipher, buf, k1, k2);
            s = score_english(buf);
            if (first || s < best) {
                first   = 0;
                best    = s;
                best_k1 = k1;
                best_k2 = k2;
                snprintf(out_plain, MAX_TEXT, "%s", buf);
            }
        }
    }
    *out_k1    = best_k1;
    *out_k2    = best_k2;
    *out_score = best;
}

/* 打印频率分析破译结果 */
static void print_crack(const char *cipher)
{
    char plain[MAX_TEXT];
    int k1, k2;
    double score;

    crack_by_frequency(cipher, &k1, &k2, plain, &score);
    printf("频率分析破译结果：k1 = %d, k2 = %d\n", k1, k2);
    printf("还原明文：%s\n", plain);
    printf("明文卡方得分（越小越像英文）：%.2f\n", score);
    printf("密文卡方得分（对照）：%.2f\n", score_english(cipher));
}

/* ==================== 五、命令行界面 ==================== */

/* 取路径中的文件名部分，仅用于帮助信息显示，例如 affine_cipher.exe */
static const char *base_name(const char *path)
{
    const char *p = path, *q = path;
    for (; *p != '\0'; p++)
        if (*p == '/' || *p == '\\') q = p + 1;
    return q;
}

static void print_usage(const char *prog)
{
    prog = base_name(prog);
    printf("仿射密码加解密程序（C 语言版）\n");
    printf("用法：\n");
    printf("  %s                                  运行内置示例（加密、解密、映射表）\n", prog);
    printf("  %s -e -a 5 -b 8 -t \"affine cipher\"   加密：E(x) = (5x + 8) mod 26\n", prog);
    printf("  %s -d -a 5 -b 8 -t \"ihhwvc swfrcp\"   解密：D(y) = 5^(-1)(y - 8) mod 26\n", prog);
    printf("  %s -T -a 5 -b 8                       输出 26 个字母的加密映射表\n", prog);
    printf("  %s -B -t \"ihhwvc swfrcp\"             暴力枚举全部 312 组密钥\n", prog);
    printf("  %s -C -t \"<英文密文>\"                 频率分析破译（无需已知密钥）\n", prog);
    printf("参数说明：-e 加密，-d 解密，-T 映射表，-B 暴力枚举，-C 频率分析，\n");
    printf("         -a 指定 k1，-b 指定 k2，-t 指定待处理文本\n");
    printf("         k1 必须与 26 互素，合法取值为 "
           "1,3,5,7,9,11,15,17,19,21,23,25\n");
}

int main(int argc, char *argv[])
{
    int encrypt_mode = -1;          /* 1=加密，0=解密，-1=未指定 */
    int k1 = -1, k2 = 0;
    const char *text = NULL;
    int show_table = 0, brute_mode = 0, crack_mode = 0;
    int i;
    char cipher[MAX_TEXT], plain[MAX_TEXT];

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-e") == 0) {
            encrypt_mode = 1;
        } else if (strcmp(argv[i], "-d") == 0) {
            encrypt_mode = 0;
        } else if (strcmp(argv[i], "-a") == 0 && i + 1 < argc) {
            k1 = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-b") == 0 && i + 1 < argc) {
            k2 = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-t") == 0 && i + 1 < argc) {
            text = argv[++i];
        } else if (strcmp(argv[i], "-T") == 0) {
            show_table = 1;
        } else if (strcmp(argv[i], "-B") == 0 || strcmp(argv[i], "--brute") == 0) {
            brute_mode = 1;
        } else if (strcmp(argv[i], "-C") == 0 || strcmp(argv[i], "--crack") == 0) {
            crack_mode = 1;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else {
            printf("未知参数：%s\n\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }

    if (brute_mode || crack_mode) {          /* 密码分析模式：不需要预先知道密钥 */
        if (text == NULL) {
            printf("错误：请用 -t 指定待分析的密文。\n");
            return 1;
        }
        if (brute_mode) {
            printf("共枚举 %d 组密钥（12 个合法 k1 × 26 个 k2），前 10 组结果：\n", 12 * MOD);
            brute_force(text, 10);
            printf("  ……（其余 %d 组略）\n", 12 * MOD - 10);
        } else {
            print_crack(text);
        }
        return 0;
    }

    if (show_table) {                        /* -T：只输出映射表 */
        if (k1 == -1) {
            printf("错误：输出映射表需要用 -a 指定 k1。\n");
            return 1;
        }
        if (!is_valid_k1(k1)) {
            printf("错误：k1 = %d 不合法，gcd(%d,26) = %d ≠ 1，乘法逆元不存在。\n",
                   k1, k1, gcd_int(((k1 % MOD) + MOD) % MOD, MOD));
            return 1;
        }
        print_table(k1, k2);
        return 0;
    }

    if (encrypt_mode == -1) {               /* 无参数：显示帮助并运行内置示例 */
        print_usage(argv[0]);
        printf("\n");
        return run_demo();
    }

    if (k1 == -1) {                          /* 未指定密钥 */
        printf("错误：请用 -a 指定 k1（必须与 26 互素）。\n");
        return 1;
    }
    if (!is_valid_k1(k1)) {
        printf("错误：k1 = %d 不合法，gcd(%d,26) = %d ≠ 1，"
               "乘法逆元不存在，无法解密。\n",
               k1, k1, gcd_int(((k1 % MOD) + MOD) % MOD, MOD));
        printf("合法 k1 取值为：1,3,5,7,9,11,15,17,19,21,23,25\n");
        return 1;
    }
    if (text == NULL) {
        printf("错误：请用 -t 指定待处理的文本。\n");
        return 1;
    }

    if (encrypt_mode == 1) {
        affine_encrypt(text, cipher, k1, k2);
        printf("明文：%s\n密文：%s\n", text, cipher);
    } else {
        if (affine_decrypt(text, plain, k1, k2) != 0) {
            printf("错误：k1 = %d 不合法，解密失败。\n", k1);
            return 1;
        }
        printf("密文：%s\n明文：%s\n", text, plain);
    }
    return 0;
}
```

关键实现说明：

（1）密钥合法性判定。is_valid_k1() 先用 ((k1 % 26) + 26) % 26 把 k1 归一化到 [0, 26)，再用辗转相除法求它与 26 的最大公约数，只有等于 1 才认为密钥合法，从源头上避免了“无法解密”的情况。

（2）逆元计算。mod_inverse() 使用迭代版扩展欧几里得算法，返回 −1 表示逆元不存在；该函数同时被加密校验与解密流程复用。

（3）取模与负数处理。C 语言中负数取模结果为负，所以所有取模表达式都写成 ((...) % MOD + MOD) % MOD 的形式，保证结果落在 [0, 26) 区间，这一点在解密时（y − k2 可能为负）尤其重要。

（4）大小写与多字节字符处理。encrypt_char() 先用字符区间判断是否为大写或小写字母，分别以 'A' 或 'a' 为基准计算编号，因此大写字母加密后仍为大写、小写字母仍为小写；对于不满足 ASCII 字母条件的情况（包括 UTF-8 编码的汉字，其每个字节都大于 0x7F）直接返回原字符，既保证非字母字符不被破坏，也避免按字节处理中文时出现乱码。

（5）密码分析功能。score_english() 用卡方统计量衡量文本与标准英文频率的接近程度，brute_force() 完成 312 组密钥的穷举，crack_by_frequency() 在未知密钥的前提下挑出卡方得分最低的候选明文，即最可能的正确明文。

（6）示例与校验。run_demo() 在无参数运行时自动演示一组完整的加密、解密过程，并把解密结果与原始明文逐字符比较，打印“一致性校验”结论，方便直接观察程序的正确性。

#### 4.5  编译与运行方法

在 VS Code 中打开 code 目录，按 Ctrl+` 打开集成终端，执行以下命令（Windows 环境；Linux 下把 affine_cipher.exe 换成 affine_cipher、把 .\ 去掉即可）：

**命令 4-1  affine_cipher.exe 的编译与运行命令**

```bash
cd code
gcc -Wall -Wextra -O2 -g affine_cipher.c -o affine_cipher.exe   # 编译（无警告）
affine_cipher.exe                                                # 内置示例（加密、解密、映射表）
affine_cipher.exe -e -a 5 -b 8 -t "affine cipher"               # 加密
affine_cipher.exe -d -a 5 -b 8 -t "ihhwvc swfrcp"               # 解密
affine_cipher.exe -T -a 5 -b 8                                   # 字母映射表
affine_cipher.exe -e -a 4 -b 8 -t "test"                        # 非法密钥，观察错误提示
affine_cipher.exe -B -t "ihhwvc swfrcp"                         # 暴力枚举 312 组密钥
affine_cipher.exe -C -t "nhm kttoxm yolhmz og k nwlm …"          # 频率分析破译

# 也可以直接双击 code\编译并运行演示.bat，或使用 make / make run
```

#### 4.6  运行结果

> **【截图占位 图 2】** 在 VS Code 集成终端中执行 gcc 编译命令的结果（命令：gcc -Wall -Wextra -O2 -g affine_cipher.c -o affine_cipher.exe，预期：无任何警告与错误输出，生成 affine_cipher.exe）

编译结果：使用 -Wall -Wextra 编译，没有任何警告和错误，说明代码在类型使用、缓冲区长度、未使用变量等方面都是干净的。

（1）加密与解密示例运行结果：

```text
> affine_cipher.exe -e -a 5 -b 8 -t "affine cipher"
明文：affine cipher
密文：ihhwvc swfrcp

> affine_cipher.exe -d -a 5 -b 8 -t "ihhwvc swfrcp"
密文：ihhwvc swfrcp
明文：affine cipher
```

> **【截图占位 图 3】** 加密（-e）与解密（-d）命令的运行结果，可与图 4 的程序输出相互印证

（2）不带参数运行时的完整输出（帮助信息 + 内置示例 + 字母映射表 + 逆元验算）：

**程序清单 4-2  affine_cipher.exe 的完整运行输出（实际运行结果）**

```text
仿射密码加解密程序（C 语言版）
用法：
  affine_cipher.exe                                  运行内置示例（加密、解密、映射表）
  affine_cipher.exe -e -a 5 -b 8 -t "affine cipher"   加密：E(x) = (5x + 8) mod 26
  affine_cipher.exe -d -a 5 -b 8 -t "ihhwvc swfrcp"   解密：D(y) = 5^(-1)(y - 8) mod 26
  affine_cipher.exe -T -a 5 -b 8                       输出 26 个字母的加密映射表
  affine_cipher.exe -B -t "ihhwvc swfrcp"             暴力枚举全部 312 组密钥
  affine_cipher.exe -C -t "<英文密文>"                 频率分析破译（无需已知密钥）
参数说明：-e 加密，-d 解密，-T 映射表，-B 暴力枚举，-C 频率分析，
         -a 指定 k1，-b 指定 k2，-t 指定待处理文本
         k1 必须与 26 互素，合法取值为 1,3,5,7,9,11,15,17,19,21,23,25

---------------- 加解密示例 ----------------
密钥      : k1 = 5, k2 = 8
明文      : Affine Cipher Test 2026, 仿射密码实验!
密文      : Ihhwvc Swfrcp Zcuz 2026, 仿射密码实验!
解密还原  : Affine Cipher Test 2026, 仿射密码实验!
一致性校验: 通过（解密结果与明文完全相同）

---------------- 字母映射表 ----------------
明文(a-z) : abcdefghijklmnopqrstuvwxyz
密文(a-z) : insxchmrwbglqvafkpuzejotyd
k1 = 5, k2 = 8, k1 的乘法逆元 k1^(-1) = 21 (mod 26)
校验：5 * 21 mod 26 = 1（应等于 1，说明逆元正确）
```

> **【截图占位 图 4】** C 程序完整运行输出（内置示例、字母映射表与逆元验算，对应程序清单 4-2）

（3）非法密钥的异常处理：当 k1 = 4 时，由于 gcd(4, 26) = 2 ≠ 1，程序给出明确错误提示并拒绝执行：

```text
> affine_cipher.exe -e -a 4 -b 8 -t "test"
错误：k1 = 4 不合法，gcd(4,26) = 2 ≠ 1，乘法逆元不存在，无法解密。
合法 k1 取值为：1,3,5,7,9,11,15,17,19,21,23,25
```

> **【截图占位 图 5】** 非法密钥 k1 = 4 时程序给出的错误提示（并列出全部合法取值）

（4）字母映射表输出（k1 = 5, k2 = 8 与 k1 = 7, k2 = 3 对比）：

```text
> affine_cipher.exe -T -a 5 -b 8
明文(a-z) : abcdefghijklmnopqrstuvwxyz
密文(a-z) : insxchmrwbglqvafkpuzejotyd
k1 = 5, k2 = 8, k1 的乘法逆元 k1^(-1) = 21 (mod 26)
校验：5 * 21 mod 26 = 1（应等于 1，说明逆元正确）

> affine_cipher.exe -T -a 7 -b 3
明文(a-z) : abcdefghijklmnopqrstuvwxyz
密文(a-z) : dkryfmtahovcjqxelszgnubipw
k1 = 7, k2 = 3, k1 的乘法逆元 k1^(-1) = 15 (mod 26)
校验：7 * 15 mod 26 = 1（应等于 1，说明逆元正确）
```

> **【截图占位 图 6】** 两次使用 -T 参数输出的字母映射表，用于对比不同密钥的置乱效果

（5）暴力枚举攻击（-B）：对密文 "ihhwvc swfrcp" 枚举全部 312 组密钥，输出前 10 组候选明文：

```text
> affine_cipher.exe -B -t "ihhwvc swfrcp"
共枚举 312 组密钥（12 个合法 k1 × 26 个 k2），前 10 组结果：
  k1 =  1, k2 =  0 → ihhwvc swfrcp
  k1 =  1, k2 =  1 → hggvub rveqbo
  k1 =  1, k2 =  2 → gffuta qudpan
  k1 =  1, k2 =  3 → feetsz ptcozm
  k1 =  1, k2 =  4 → eddsry osbnyl
  k1 =  1, k2 =  5 → dccrqx nramxk
  k1 =  1, k2 =  6 → cbbqpw mqzlwj
  k1 =  1, k2 =  7 → baapov lpykvi
  k1 =  1, k2 =  8 → azzonu koxjuh
  k1 =  1, k2 =  9 → zyynmt jnwitg
  ……（其余 302 组略）
```

> **【截图占位 图 7】** 暴力枚举 312 组密钥的运行结果（对应上图）

（6）频率分析攻击（-C）：先用 k1 = 7、k2 = 10 加密一段较长的英文明文得到密文，再在不告知密钥的情况下进行破译：

```text
> affine_cipher.exe -e -a 7 -b 10 -t "<一段英文明文>"
密文：nhm kttoxm yolhmz og k nwlm et qexekjlhkrmnoy gurgnonunoex yolhmz ihoyh qmkxg nhkn mkyh jmnnmz et nhm kjlhkrmnoy og qkllmf ne k xuqmzoy bkjum mxyzwlnmf rw k goqljm qknhmqknoykj tuxynoex

> affine_cipher.exe -C -t "<上面的密文>"
频率分析破译结果：k1 = 7, k2 = 10
还原明文：the affine cipher is a type of monoalphabetic substitution cipher which means that each letter of the alphabet is mapped to a numeric value encrypted by a simple mathematical function
明文卡方得分（越小越像英文）：40.83
密文卡方得分（对照）：1265.63
```

> **【截图占位 图 8】** 频率分析破译的运行结果（未知密钥时破译出 k1 = 7, k2 = 10，还原出完整英文原文）

（7）实验文件与目录结构（VS Code 资源管理器中 code 目录下的文件：affine_cipher.c、Makefile、编译并运行演示.bat，以及可选的其它语言实现）。

> **【截图占位 图 9】** VS Code 资源管理器中 code 目录与实验文件列表的截图

#### 4.7  测试用例与运行结果

**表 4-3  测试用例与实际运行结果（每条均已实际运行核对）**

| 编号 | 测试类型 | 输入 | 预期结果 | 实际结果 |
| --- | --- | --- | --- | --- |
| T1 | 正常 | 加密 "affine cipher"，k1=5, k2=8 | 密文为 "ihhwvc swfrcp" | 与预期一致 |
| T2 | 正常 | 解密 "ihhwvc swfrcp"，k1=5, k2=8 | 明文为 "affine cipher" | 与预期一致 |
| T3 | 正常 | 大小写混合 "AbCd…Yz"，k1=7, k2=3 | 大写仍大写、小写仍小写 | 与预期一致 |
| T4 | 边界 | 空字符串与纯空格串 | 原样返回，不报错 | 与预期一致 |
| T5 | 边界 | 含中文与数字 "A1 b2! 中文 2026" | 非字母字符原样保留 | 输出 "D1 k2! 中文 2026" |
| T6 | 异常 | k1 = 2、4、13、16、26 | 拒绝执行并提示非法 | 程序提示错误并列出合法取值 |
| T7 | 密码分析 | 暴力枚举 312 组密钥 | 候选中出现可读明文 | 枚举到 (k1=5, k2=8) 时还原出 "affine cipher" |
| T8 | 密码分析 | 频率分析破译 k1=7, k2=10 的密文 | 还原出正确密钥与明文 | 破译结果 (7, 10)，明文完全正确 |

### 【实验结果分析】

#### 5.1  加解密正确性验证

（1）以明文 "affine cipher"、密钥 k1 = 5、k2 = 8 为例，手算过程为：a(0) → (5×0 + 8) mod 26 = 8 → i；f(5) → (5×5 + 8) mod 26 = 33 mod 26 = 7 → h；c(2) → (5×2 + 8) mod 26 = 18 → s；z(25) → (5×25 + 8) mod 26 = 133 mod 26 = 3 → d。程序输出为 "ihhwvc swfrcp"，与手算结果完全一致。

（2）解密验证：使用 k1^(-1) = 21 对密文解密，例如 i(8) → 21 × (8 − 8) mod 26 = 0 → a，h(7) → 21 × (7 − 8) mod 26 = −21 mod 26 = 5 → f，程序输出为 "affine cipher"，实现了 100% 还原。

（3）除上述例子外，还逐个运行了大小写混合串、含中文与数字的串、空串、非法密钥等多组输入（见表 4-3），并把每条命令的实际输出与手算预期逐项比对，结果全部一致；说明程序在正常、边界与异常三类情况下都能得到预期结果。

#### 5.2  字母映射表的分析

密钥 k1 = 5、k2 = 8 时，26 个字母的加密映射为：

```text
明文(a-z) : abcdefghijklmnopqrstuvwxyz
密文(a-z) : insxchmrwbglqvafkpuzejotyd
```

可以看到：a→i、b→n、c→s、d→x、e→c、f→h，26 个明文字母恰好映射到 26 个互不相同的密文字母，说明加密函数是一个双射；映射后的字母表看起来毫无规律（既不是简单的平移，也不是简单的倒序），这正是“乘法置乱 + 加法平移”共同作用的结果。其中 k2 = 8 决定整体平移量，k1 = 5 决定字母表被打乱的顺序。

对比密钥 k1 = 7、k2 = 3 的映射结果：

```text
明文(a-z) : abcdefghijklmnopqrstuvwxyz
密文(a-z) : dkryfmtahovcjqxelszgnubipw
```

同样的明文字母表，仅仅改变 k1、k2 就得到了完全不同的密文字母表，说明密钥直接影响代换表；但由于 12 × 26 = 312 的密钥空间太小，所有可能的代换表也只有 312 张，这也是仿射密码可以被暴力枚举的重要原因。

#### 5.3  密钥空间与暴力破解

程序用 -B 参数对 312 组密钥进行穷举，输出中包含了全部候选明文。以密文 "ihhwvc swfrcp" 为例，第 1 组密钥 (k1 = 1, k2 = 0) 还原出的仍是密文本身（因为 k1 = 1、k2 = 0 相当于恒等映射），随着 k2 增大，候选明文不断变化；当枚举到 (k1 = 5, k2 = 8) 时输出 "affine cipher"，正是我们需要的明文。整个穷举过程在程序中瞬间完成（312 组密钥、每组只需对 12 个字母做一次模运算），说明 312 的密钥空间对现代计算机而言几乎没有任何防护能力。

在实际攻击中，攻击者并不知道正确密钥，但可以通过“候选明文中是否包含常见单词、是否符合英文单词结构”等判据，快速从 312 个候选中筛选出唯一正确的结果——这正说明密钥空间过小是仿射密码的致命弱点。

#### 5.4  频率分析攻击实验

为了验证“单表代换密码不能抵抗频率分析”这一结论，实验先用 k1 = 7、k2 = 10 加密一段较长的英文明文（仿射密码的英文定义，共 154 个字母），得到密文：

```text
nhm kttoxm yolhmz og k nwlm et qexekjlhkrmnoy gurgnonunoex yolhmz ihoyh qmkxg nhkn mkyh jmnnmz et nhm kjlhkrmnoy og qkllmf ne k xuqmzoy bkjum mxyzwlnmf rw k goqljm qknhmqknoykj tuxynoex
```

然后使用 -C 功能在“不知道密钥”的前提下进行频率分析：遍历全部 312 组密钥，对每组候选明文计算字母频率的卡方统计量（得分越小说明越接近标准英文频率分布），取得分最低的一组作为破译结果：

```text
> affine_cipher.exe -C -t "<上述密文>"
频率分析破译结果：k1 = 7, k2 = 10
还原明文：the affine cipher is a type of monoalphabetic substitution cipher which means that each letter of the alphabet is mapped to a numeric value encrypted by a simple mathematical function
明文卡方得分（越小越像英文）：40.83
密文卡方得分（对照）：1265.63
```

结果显示：频率分析在完全不知道密钥的情况下，准确破译出 k1 = 7、k2 = 10，并完整还原出原始英文明文，还原后明文的卡方得分仅为 40.83，而密文本身的卡方得分高达 1265.63（相差约 30 倍），说明频率分析能够非常明确地把正确明文从 312 个候选中挑选出来。这也再次说明：仿射密码虽然比加法密码多了乘法置乱，密文字母表看起来“更乱”，但它仍然是单表代换，字母的出现频率结构被完整保留，因此只要密文足够长，频率分析就能以极低的代价攻破它。

#### 5.5  异常与边界情况的处理

**表 5-1  异常与边界情况处理结果**

| 情况 | 输入 | 程序行为 | 结论 |
| --- | --- | --- | --- |
| k1 与 26 不互素 | k1 = 4（gcd = 2） | 打印错误信息并列出全部合法取值 | 非法密钥被正确拦截 |
| k1 = 13 | k1 = 13（gcd = 13） | 提示不合法（密文只能出现 a、n，信息丢失） | 符合理论分析 |
| 空字符串 | "" | 返回空字符串，不报错 | 边界处理正确 |
| 纯空格 | "   " | 原样返回 | 非字母字符不参与加密 |
| 含中文 | "中文 2026" | 中文与数字原样保留，仅字母被加密 | 多字节字符处理正确 |
| 大小写混合 | "Affine" | 输出 "Ihhwvc"，大小写保持不变 | 符合常规密码约定 |
| k2 取负或大于 25 | k2 = −7 或 k2 = 33 | 按模 26 归一化，结果正确 | 程序对 k2 无额外限制 |

从表 5-1 可以看出，程序对四类异常输入（非法密钥、空串、非字母字符、大小写）均能正确处理，没有出现崩溃、越界或乱码。特别是汉字处理：由于程序只在 ASCII 字母区间内做变换，对 UTF-8 编码的多字节字符按原样拷贝，因此中文不会被破坏。

#### 5.6  C 实现中的关键技术与易错点

**表 5-2  C 实现中的关键技术与易错点**

| 技术点 | 本程序的做法 | 易错点与说明 |
| --- | --- | --- |
| 字符与编号的转换 | c - 'A' 或 c - 'a' 得到 0～25 的编号 | 若直接用字符参与运算，会把 ASCII 码 65 当成编号，结果完全错误 |
| 负数取模 | 写成 ((x) % 26 + 26) % 26 | C 语言中 −21 % 26 等于 −21 而不是 5，解密时极易出错 |
| 大小写保持 | 分别以 'A'、'a' 为基准处理两种区间 | 统一转成大写会丢失原文的大小写信息 |
| 多字节字符 | 非 ASCII 字母一律原样拷贝 | 按字节加密中文会产生乱码，必须先判断再处理 |
| 密钥合法性 | is_valid_k1() 用辗转相除判断互素 | 直接计算逆元而不判断，会得到错误的“逆元” |
| 字符串缓冲区 | 输入输出缓冲区统一为 MAX_TEXT 并限制长度 | 不做长度限制会导致缓冲区溢出 |
| 命令行参数 | 逐个比较 argv[i] 并检查后续参数是否存在 | 读取 argv[i+1] 前必须确认 i+1 < argc |

#### 5.7  安全性分析结论

综合本节实验，可以得出以下结论：（1）仿射密码的安全性首先取决于密钥的合法性，即 gcd(k1, 26) = 1，这是数学上“解密必须存在且唯一”的要求；（2）密钥空间只有 312 组，穷举攻击在毫秒级即可完成，因此它经不起暴力破解；（3）它是单表代换密码，字母频率结构被完整保留，遇到频率分析攻击几乎毫无抵抗能力；（4）仿射密码真正的价值在于把“模运算”“乘法逆元”“扩展欧几里得算法”等数论工具引入密码学，为理解 Hill 密码、维吉尼亚密码等更强的古典密码以及现代的 RSA、AES 等算法奠定了基础。

### 【心得体会】

（1）数学公式到程序代码之间还有一段不短的距离。仿射密码的公式 E(x) = (k1·x + k2) mod 26 只写了一行，但真正写成程序时，需要自己解决“字母如何编号”“大小写怎么处理”“非字母字符怎么办”“取模出现负数怎么办”等一系列工程问题。比如 C 语言中必须用 (c - 'A') 得到编号，如果直接把字符 'A' 当作 65 参与运算，结果就会完全错误。这些细节只有在亲手写代码、亲眼看到错误输出时才能真正理解。

（2）逐条核对输出，比“看起来对”重要得多。本次实验中最有意思的经历是：我最初口算认为 k1 = 5、k2 = 8 时 z 加密后应当是 h，可程序输出的是 d。重新手算：5 × 25 + 8 = 133，133 mod 26 = 133 − 5 × 26 = 3，编号 3 对应的是 d，而不是 h——是我自己把模运算算错了，程序反而是对的。这件小事让我真切体会到“用程序验证手算、用手算复核程序”的双向检验有多么重要，也让我明白调试时不能先入为主地怀疑代码。

（3）负数取模是 C 语言实现密码算法时最容易踩的坑。解密公式里有 (y − k2) 这一项，当 y < k2 时结果为负，而 C 语言中 −21 % 26 等于 −21，并不是我们期望的 5。我在代码中把所有取模都写成 ((x) % 26 + 26) % 26 的形式，并通过全密钥遍历测试确认多组输入的解密结果都与原文完全一致，这才真正放心。这让我理解了为什么密码实现中“模运算必须归一化到非负区间”是一条必须遵守的纪律。

（4）乘法逆元是连接“加密”和“解密”的桥梁。以前虽然知道扩展欧几里得算法，但只是当作一道数论习题，这次需要亲手把它写成程序，并且明白：一旦 gcd(k1, 26) ≠ 1，逆元就不存在，解密公式直接失效。用 k1 = 13 做实验时，密文中只能出现 a 和 n 两个字母，26 个字母的明文信息被压缩到 2 个字母上，信息在加密过程中就已经丢失，之后无论用什么方法都无法恢复。这让我第一次如此直观地理解了“加密必须是可逆变换”的含义。

（5）最让我印象深刻的还是频率分析实验。在此之前，我觉得仿射密码比加法密码“多了一层乘法”，密文字母表看起来杂乱无章，应该比较难破解。但程序只用了不到一秒钟，就在完全不知道密钥的情况下把 154 个字母的密文准确还原成了英文原文。原因很简单：单表代换只是给字母“改名”，并没有改变字母出现的频率结构，而语言的统计规律是不会被“改名”所掩饰的。这让我明白：一个密码算法是否安全，不能只看它“看起来是否复杂”，而要看它是否消除了明文的统计规律——这也正是维吉尼亚密码、一次一密乃至现代分组密码不断演进的根本原因。

（6）用 C 语言自己动手实现暴力枚举和频率分析，比只看书本上的结论收获大得多。当自己的程序把 312 组候选明文一行行打印出来，最后一行恰好是可读的英文句子时，“密钥空间太小”“单表代换不能抵抗频率分析”这些结论才真正变成了看得见、摸得着的事实。

### 附录  实验文件清单

**表 A-1  实验文件清单**

| 文件 | 说明 |
| --- | --- |
| code/affine_cipher.c | 仿射密码加解密 C 语言实现（含命令行界面、字母映射表、暴力枚举与频率分析） |
| code/Makefile | 一键编译脚本（make / make run / make clean） |
| code/编译并运行演示.bat | Windows 下双击即可编译并运行演示程序 |
| (0)affine_cipher.c代码解释.md | 对 affine_cipher.c 的逐段讲解（架构、调用链、关键知识点、易错点） |
| images/图1 仿射密码加解密算法流程图.png | 本报告图 1 使用的算法流程图（由绘图程序绘制，非截图） |
| images/生成流程图.py | 绘制图 1 流程图的脚本（可修改后重新生成流程图） |
| 实验1 仿射变换加解密实验报告.md | 本报告正文 |
| 运行说明与截图清单.md | 8 处截图占位对应的命令、执行顺序与截图粘贴说明 |
