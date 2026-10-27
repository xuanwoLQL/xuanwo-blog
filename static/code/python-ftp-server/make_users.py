# -*- coding: utf-8 -*-
"""
生成用户账号文件 users.json（服务器只存“盐 + 哈希”，不存明文密码）

用法：
    python make_users.py                  # 生成默认账号
    python make_users.py add 用户名 密码    # 追加/修改一个账号
    python make_users.py list              # 查看现有账号（看不到密码，只能看到盐和哈希）

默认账号：
    alice  / alice123
    bob    / bob123
    admin  / admin@123

users.json 的结构：
    {
      "alice": {"salt": "十六进制随机盐", "hash": "PBKDF2-HMAC-SHA256 摘要", "iterations": 120000},
      ...
    }
即使这个文件被泄露，攻击者也不知道明文口令（要靠暴力破解，代价很高）。
"""

import json
import os
import sys

from ftp_protocol import PBKDF2_ITERATIONS, hash_password, new_salt

HERE = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(HERE, 'users.json')

DEFAULT_USERS = [
    ('alice', 'alice123'),
    ('bob', 'bob123'),
    ('admin', 'admin@123'),
]


def load():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def add_user(users, name, password):
    salt = new_salt()
    users[name] = {
        'salt': salt,
        'hash': hash_password(password, salt),
        'iterations': PBKDF2_ITERATIONS,
    }
    print('已设置账号：%s（口令长度 %d，已加盐哈希后保存）' % (name, len(password)))


def main():
    args = sys.argv[1:]

    if args and args[0] == 'list':
        users = load()
        if not users:
            print('还没有任何账号，先运行 python make_users.py 生成默认账号')
            return
        print('共 %d 个账号（%s）：' % (len(users), USERS_FILE))
        for name, rec in users.items():
            print('  %-10s salt=%s… hash=%s…（%d 次迭代）'
                  % (name, rec['salt'][:8], rec['hash'][:16], rec.get('iterations', 0)))
        return

    if args and args[0] == 'add':
        if len(args) < 3:
            print('用法：python make_users.py add 用户名 密码')
            return
        users = load()
        add_user(users, args[1], args[2])
        save(users)
        print('已写入 %s' % USERS_FILE)
        return

    # 不带参数：生成默认账号（已存在的账号会被重置成默认口令）
    users = {}
    for name, password in DEFAULT_USERS:
        add_user(users, name, password)
    save(users)
    print('\n已写入 %s，可以直接启动服务端：python ftp_server.py' % USERS_FILE)
    print('登录信息：' + '、'.join('%s/%s' % (n, p) for n, p in DEFAULT_USERS))


if __name__ == '__main__':
    main()
