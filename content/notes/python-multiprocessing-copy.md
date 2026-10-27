---
title: "multiprocessing 多进程文件复制"
slug: "python-multiprocessing-copy"
date: 2026-10-12T16:44:18+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "按字节对半切分文件，用多进程并行复制并校验结果。"
summary: "按字节对半切分文件，用多进程并行复制并校验结果。"
tags: ["Python", "多进程", "文件IO"]
categories: ["网络编程"]
series: ["Python 网络编程"]
weight: 4
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/python-learning/multiprocessing作业/README.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/python-multiprocessing-copy/workflow.svg" alt="大文件按块切分，由多个进程并行读取并写入独立目标区域。" loading="lazy">
  <figcaption>图 1 · 多进程文件复制。大文件按块切分，由多个进程并行读取并写入独立目标区域。</figcaption>
</figure>

## 需求
创建两个进程，分别复制一个文件的上下半部分，将复制内容分别放到两个新的文件中（按字节分文件）。

## 文件
- `split_copy.py` —— 完整实现

## 运行
```bash
python split_copy.py 源文件 [上半输出] [下半输出]
```
不写输出文件名时，默认生成 `源文件名.part1`（上半）和 `源文件名.part2`（下半）。

例如：
```bash
python split_copy.py big.dat
```

## 思路
1. 用 `os.path.getsize` 拿到总字节数 `total`，`half = total // 2`（按“字节”分，不按行）。
2. 开两个 `multiprocessing.Process`：
   - 进程 1：复制 `[0, half)` → 上半部分；
   - 进程 2：复制 `[half, total)` → 下半部分（长度是奇数时，下半比上半多 1 字节）。
3. 每个进程各自 `open()`、`seek()` 到起点，按 1MB 分块读写，最后父进程 `join()` 等待两个子进程结束。

## 自测结果
用 25609 字节（奇数）的文件测试：上半 12804 字节、下半 12805 字节，两部分拼起来与原文件完全一致。

## 完整源码包

所有 Python 文件、README 和测试辅助文件已打包：

[下载 python-multiprocessing-copy 完整源码包](/code/python-multiprocessing-copy/source.zip)

项目目录：

```text
multiprocessing作业/
├─ split_copy.py
└─ README.md
```

## 完整代码

<details>
<summary>打开完整代码：split_copy.py</summary>

```python
# -*- coding: utf-8 -*-
"""
multiprocessing 作业
需求：创建两个进程，分别复制一个文件的上下半部分，
      将复制内容分别放到两个新的文件中（按字节分文件）。

思路：
  1. 先按“字节”求出文件总大小 total，和后半部分的起始偏移 half = total // 2
     —— 用字节定位，不能按“行”数，因为一行里有多少字节事先并不知道。
  2. 开两个 Process：
       进程1：从偏移 0  复制到 half           -> 上半部分
       进程2：从偏移 half 复制到 total        -> 下半部分（奇数长度时下半部分多 1 字节）
     每个进程用自己的文件句柄，先 seek 到起始位置，再按块读写。
  3. 父进程 join 两个子进程，等待它们都复制完再统计结果。

用法：
  python split_copy.py 源文件 [上半部分输出文件] [下半部分输出文件]
  不写输出文件名时，默认为 源文件名.part1 / 源文件名.part2
"""

import os
import sys
from multiprocessing import Process

BLOCK = 1024 * 1024  # 每次读写 1MB，大文件也不会一次把内存吃满


def copy_range(src, dst, start, end, tag):
    """把 src 文件的 [start, end) 字节区间复制到 dst 文件。"""
    copied = 0
    with open(src, 'rb') as fin, open(dst, 'wb') as fout:
        fin.seek(start)               # 定位到本进程负责的起点
        remaining = end - start
        while remaining > 0:
            data = fin.read(min(BLOCK, remaining))
            if not data:              # 理论上不会发生，防御性判断
                break
            fout.write(data)
            copied += len(data)
            remaining -= len(data)
    # 子进程的打印能直接显示在父进程的控制台上（Windows/Linux 都行）
    print('[%s] 进程 pid=%d 复制完成，写入 %s，共 %d 字节'
          % (tag, os.getpid(), dst, copied))
    return copied


def main():
    if len(sys.argv) < 2:
        print('用法: python split_copy.py 源文件 [上半输出] [下半输出]')
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.isfile(src):
        print('错误：找不到源文件 %s' % src)
        sys.exit(1)

    out1 = sys.argv[2] if len(sys.argv) > 2 else src + '.part1'
    out2 = sys.argv[3] if len(sys.argv) > 3 else src + '.part2'

    total = os.path.getsize(src)
    half = total // 2
    print('源文件 %s 共 %d 字节，按字节对半分为：上半 [0, %d)、下半 [%d, %d)'
          % (src, total, half, half, total))

    # 两个进程，分别负责上/下半部分
    p1 = Process(target=copy_range, args=(src, out1, 0, half, '上半'))
    p2 = Process(target=copy_range, args=(src, out2, half, total, '下半'))

    print('父进程 pid=%d，启动两个子进程……' % os.getpid())
    p1.start()
    p2.start()

    # 阻塞等待两个子进程结束
    p1.join()
    p2.join()

    s1 = os.path.getsize(out1)
    s2 = os.path.getsize(out2)
    print('两个子进程都结束了：%s=%d 字节，%s=%d 字节，合计 %d 字节'
          % (out1, s1, out2, s2, s1 + s2))
    print('校验：合计 %s 源文件 %d 字节' % ('==' if s1 + s2 == total else '!=', total))


if __name__ == '__main__':
    main()
```

</details>
