# multiprocessing 作业：按字节对半复制文件

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
