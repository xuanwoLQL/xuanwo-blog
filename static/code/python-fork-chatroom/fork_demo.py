# -*- coding: utf-8 -*-
"""
os.fork 理解与使用（对照老师给的截图）

os.fork() 只在 Linux / macOS 等类 Unix 系统可用，Windows 没有这个函数。
它“调用一次，返回两次”：
  - 父进程里返回子进程的 pid（大于 0）
  - 子进程里返回 0
  - 失败返回负数
父进程和子进程各自从 fork 之后继续往下执行。

两个容易踩的坑（下面代码都处理了）：
  1. 子进程如果不 os._exit()，会继续把父进程后面的代码再跑一遍；
  2. fork 会把标准输出缓冲区复制一份，父子各打一遍，所以要及时 flush。

用法（在 Kali / Linux 里跑）： python3 fork_demo.py
"""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)   # 每行立刻写出，避免 fork 复制缓冲区导致重复


def demo_basic():
    """截图 1：根据 fork 的返回值区分父子进程。"""
    print('--- demo 1: 基本 fork ---', flush=True)
    pid = os.fork()
    if pid < 0:
        print('failed', flush=True)
    elif pid == 0:
        # 子进程
        print('new（我是子进程，pid=%d，父进程 pid=%d）' % (os.getpid(), os.getppid()), flush=True)
        print('fork test over（子进程也打印这一行）', flush=True)
        os._exit(0)
    else:
        # 父进程
        print('old（我是父进程，我的子进程 pid=%d）' % pid, flush=True)
        print('fork test over（父进程也打印这一行）', flush=True)
        os.waitpid(pid, 0)      # 回收子进程，避免留下僵尸进程给后面的 demo 误收


def demo_wait():
    """截图 2：父进程 wait 回收子进程，检查退出状态。"""
    print('--- demo 2: fork + wait ---', flush=True)
    pid = os.fork()
    if pid < 0:
        print('create process failed', flush=True)
    elif pid == 0:
        print('child pid:%d，get parent pid:%d' % (os.getpid(), os.getppid()), flush=True)
        os._exit(2)             # 子进程用退出码 2 结束
    else:
        child_pid, status = os.wait()      # 阻塞等待子进程结束
        print('wait 返回：子进程 pid=%d，status=%d，退出码=%d'
              % (child_pid, status, os.waitstatus_to_exitcode(status)), flush=True)


def demo_shared():
    """说明 fork 之后父子进程的变量是各自独立的拷贝（写时复制）。"""
    print('--- demo 3: 父子进程变量互相独立 ---', flush=True)
    value = 100
    pid = os.fork()
    if pid == 0:
        value += 1
        print('子进程里 value = %d（改的是自己的副本）' % value, flush=True)
        os._exit(0)
    else:
        os.wait()               # 等子进程先打印
        print('父进程里 value = %d（不受子进程影响）' % value, flush=True)


if __name__ == '__main__':
    if not hasattr(os, 'fork'):
        print('当前系统（%s）没有 os.fork，请在 Kali / Linux 里运行本程序。' % sys.platform)
        sys.exit(0)
    demo_basic()
    time.sleep(0.1)
    demo_wait()
    demo_shared()
