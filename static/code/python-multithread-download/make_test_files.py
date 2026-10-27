# -*- coding: utf-8 -*-
"""
实验五 辅助脚本 —— 生成下载测试用的大文件

用法：
  python make_test_files.py [目录] [文件个数] [每个文件多少MB]
  默认：脚本目录下的 shared 目录（和服务端默认共享目录一致）、6 个文件、每个 8MB。

文件内容用固定随机种子生成，所以每次生成的内容都一样、MD5 也可复现，
方便在实验报告里写明校验值。
"""

import hashlib
import os
import random
import sys
import time

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared')


def make_one(path, size, seed):
    """写一个随机内容的大文件，返回它的 MD5。"""
    rnd = random.Random(seed)                      # 每个文件用自己的种子，内容才是不同的
    md5 = hashlib.md5()
    remain = size
    with open(path, 'wb') as f:
        while remain > 0:
            n = min(1024 * 1024, remain)           # 一次生成 1MB，避免一次申请太大内存
            data = rnd.randbytes(n)
            f.write(data)
            md5.update(data)
            remain -= n
    return md5.hexdigest()


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    size_mb = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    os.makedirs(target, exist_ok=True)
    size = size_mb * 1024 * 1024
    print('在 %s 生成 %d 个测试文件，每个 %.0f MB' % (target, count, size_mb))

    t0 = time.time()
    for i in range(1, count + 1):
        name = 'test%d.bin' % i
        path = os.path.join(target, name)
        digest = make_one(path, size, 20261018 + i)     # 种子不同 → 内容不同 → MD5 不同
        print('  %-12s %10d 字节  MD5=%s' % (name, size, digest))
    print('生成完毕，用时 %.2f 秒' % (time.time() - t0))
    print('现在可以运行：python download_server.py  （共享目录就是 %s）' % target)


if __name__ == '__main__':
    main()
