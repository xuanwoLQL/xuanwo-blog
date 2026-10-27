---
title: "SecLists 字典用途说明"
slug: "seclists-guide"
date: 2026-09-09T14:25:55+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "按场景整理 SecLists 的目录字典、用户名字典、密码字典与 Payload 清单。"
summary: "按场景整理 SecLists 的目录字典、用户名字典、密码字典与 Payload 清单。"
tags: ["SecLists", "字典", "信息收集"]
categories: ["安全工具"]
series: ["安全工具箱"]
weight: 6
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes/blob/main/web-security/26.SecLists字典说明.md"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/seclists-guide/workflow.svg" alt="先从目标类型确定字典类别，再用工具加载并裁剪，最后看命中率。" loading="lazy">
  <figcaption>图 1 · SecLists 字典选择。先从目标类型确定字典类别，再用工具加载并裁剪，最后看命中率。</figcaption>
</figure>

> 适用目录：`~/hashcat-7.1.2\常见与默认密码\SecLists-master`
> 整理时间：2026-09-09
>
> 本仓库（danielmiessler/SecLists）并不只是“密码字典”，而是 Web 渗透、密码爆破、模糊测试等领域常用词表的合集，共约 **5800 个文件**。文件多按目录分类，文件名通常就是用途。下文按顶层目录逐个解释，**重点讲清“什么场景该用哪一个”**。

---

### 1. 目录总览

| 顶层目录 | 文件数 | 一句话作用 |
| --- | ---: | --- |
| `Passwords` | 392 | 密码爆破/哈希破解用的弱口令、默认口令、泄露密码等 |
| `Discovery` | 435 | 信息收集/资产发现：子域名、Web 目录、文件、端口、SNMP 等 |
| `Fuzzing` | 4645 | 模糊测试载荷：注入、XSS、SQLi、LFI、User-Agent、数字/日期等 |
| `Miscellaneous` | 272 | 杂项：词典、脏话、学校/城市名单、HTML 标签、请求头等 |
| `Ai` | 13 | 面向 LLM（大模型）的提示词测试集 |
| `Usernames` | 14 | 用户名候选：通用账号、默认账号、人名、蜜罐捕获等 |
| `.bin` / `.github` | 42 | 维护脚本与 CI 配置，不是字典，日常使用可忽略 |

---

### 2. 使用场景速查

| 我想做什么 | 去哪里找 |
| --- | --- |
| hashcat / John 爆破哈希 | `Passwords\Common-Credentials\` 优先，其次 `Passwords\` 根目录大字典 |
| 登录页弱口令 | `Passwords\Common-Credentials\` + `Fuzzing\login_bypass.txt` |
| 不知道用户名 / 先做账号枚举 | `Usernames\`：先用 `top-usernames-shortlist.txt`，再 `cirt-default-usernames.txt` |
| 设备/中间件默认口令 | `Passwords\Default-Credentials\` |
| 路由器默认账号密码 | `Passwords\Default-Credentials\Routers\` |
| Web 目录/文件发现 | `Discovery\Web-Content\` |
| 子域名爆破 | `Discovery\DNS\` |
| 端口、路由器 IP 等内网枚举 | `Discovery\Infrastructure\` |
| SQL 注入测试 | `Fuzzing\Databases\SQLi\` |
| XSS 测试 | `Fuzzing\XSS\` |
| LFI/路径穿越 | `Fuzzing\LFI\` |
| 金额、日期、数字字段 fuzz | `Fuzzing\Amounts\`、`Fuzzing\Dates\`、`Fuzzing\` 根目录数字表 |
| API 路径/动作发现 | `Discovery\Web-Content\api\` |
| User-Agent 伪装/枚举 | `Fuzzing\User-Agents\` |

---

#### 2.1 `Usernames\`——用户名候选字典（已补全）

官方 SecLists 顶层自带 `Usernames` 目录，但本机早期拷贝漏掉了这个目录；现已补到
`~/hashcat-7.1.2\常见与默认密码\SecLists-master\Usernames\`。

| 文件 | 作用 |
| --- | --- |
| `top-usernames-shortlist.txt` | 最高频通用账号短名单（root/admin/test/guest 等），未知账号时第一轮用 |
| `cirt-default-usernames.txt` | CIRT 默认账号全集，覆盖路由器/设备/服务（约 600+ 行） |
| `CommonAdminBase64.txt` | 常见管理账号的 Base64 编码版 |
| `xato-net-10-million-usernames.txt` | xato.net 千万级用户名泄露整理，**最大规模用户名字典（约 85 MB）**，适合无锁定机制时做全面枚举 |
| `xato-net-10-million-usernames-dup.txt` | 上述列表中重复出现过的用户名（约 5 MB），命中率更高 |
| `sap-default-usernames.txt` | SAP 默认用户名 |
| `mssql-usernames-nansh0u-guardicore.txt` | MSSQL 蜜罐捕获用户名（当前为占位小文件） |
| `Names\malenames-usa-top1000.txt` / `femalenames-usa-top1000.txt` / `familynames-usa-top1000.txt` | 美国常用男/女/姓 Top 1000，适合拼“人名式”账号 |
| `Names\forenames-india-top1000.txt` | 印度常用名 Top 1000 |
| `Honeypot-Captures\multiplesources-users-fabian-fingerle.de.txt` | 蜜罐多来源捕获的真实用户名 |

> 用法：先在登录框试 `admin/root/administrator`；能区分“用户不存在/密码错误”时，用 `top-usernames-shortlist.txt` 做账号枚举；确认无锁定后再考虑 `xato-net-10-million-usernames.txt` 大表。

---

### 3. `Passwords`——密码/凭据字典（本目录最常用）

官方说明：Passwords 目录用于凭据猜测，收集了 RockYou、SkullSecurity、CIRT 等多套经典词典。

#### 3.1 `Passwords\` 根目录

| 文件 | 作用 |
| --- | --- |
| `README.md` | 说明文档 |
| `darkc0de.txt` | 经典 darkc0de 综合弱口令大字典（约 15 MB），包含从纯符号到常规单词的大量常见口令 |
| `openwall.net-all.txt` | Openwall 项目词表（John the Ripper 系），通用英文/多语种高频口令，约 41 MB，覆盖面大 |
| `clarkson-university-82.txt` | Clarkson University 密码研究产生的口令表，适合当“研究型”候选词补充 |
| `corporate_passwords.txt` | 企业账号常见密码模式，如 `ChangeMe!`、`Winter2021`、`<球队/爱好>321`，测试域内/办公系统很好用 |
| `days.txt` | 星期几名称的 l33t（如 `$aturday`）变体 + 符号/数字/年份扩展，适合年份-星期口令 |
| `months.txt` | 月份名称的 l33t + 符号/年份扩展（含到 2022 年的年份后缀），适合 `Mon@2021` 类口令 |
| `seasons.txt` | 季节名称的 l33t + 符号/年份扩展，作用同上 |
| `Most-Popular-Letter-Passes.txt` | 按“常见字母开头/字母习惯”整理的口令集合，用于猜按首字母分布的口令 |
| `mssql-passwords-nansh0u-guardicore.txt` | Guardicore MSSQL 蜜罐捕获的真实口令，爆破 MSSQL `sa` 等账号可用 |
| `scraped-JWT-secrets.txt` | 从公开环境抓取的 JWT `secret` 词表，用来爆破 JWT HS256 签名密钥 |
| `SCRABBLE-hackerhouse.tgz` | hackerhouse 制作的 Scrabble 词表压缩包：4.5 万个词大小写 × 尾加 0-9，共约 59 万行，适合爆破带数字尾的口令 |
| `stupid-ones-in-production.txt` | 极小清单（仅 4 行 `pu/god/sex/secret`），可当“快速碰运气”列表 |
| `unkown-azul.txt` | 来历标注不明的词表，内容以巴西风格人名+数字、随机串为主，可作为补充候选 |
| `Cracked-Hashes\milw0rm-dictionary.txt` | milw0rm 时代流传的经典破解字典，老站/旧系统常能用上 |
| `Books\greatest_books_of_all_time_*.txt` | “史上百大名著”书名词表，提供 original / lowercase / uppercase / leet 四类变体，用于基于书名的口令猜测 |

#### 3.2 `Common-Credentials\`——最值得先用的通用弱口令

这是整个仓库里最适合先喂给 hashcat 的目录，覆盖按年份、泄露库、平台整理的各类高频口令。

| 文件 | 内容/作用 |
| --- | --- |
| `100k-most-used-passwords-NCSC.txt` | 英国 NCSC 发布的 10 万最常用口令 |
| `10k-most-common.txt` | 通用 1 万高频口令 |
| `1900-2020.txt` | 1900-2020 逐日日期口令（`DDMMYYYY` 类），爆破生日型口令 |
| `2020-200_most_used_passwords.txt` | 2020 年 Top 200 弱口令 |
| `2023-200_most_used_passwords.txt` | 2023 年 Top 200 弱口令 |
| `2024-197_most_used_passwords.txt` | 2024 年 Top ~200 弱口令 |
| `2025-199_most_used_passwords.txt` | 2025 年 Top ~200 弱口令 |
| `500-worst-passwords.txt` | 500 个最差口令 |
| `common-passwords-win.txt` | Windows 环境常见口令 |
| `darkweb2017_top-10 / 100 / 1000 / 10000.txt` | 2017 年暗网泄露口令 Top N 切片 |
| `four-digit-pin-codes-sorted-by-frequency-withcount.csv` | 4 位 PIN 按频率排序并带次数，爆破手机 PIN/ATM 类可用 |
| `medical-devices.txt` | 医疗设备常见弱口令/口令集合 |
| `probable-v2_top-207 / 1575 / 12000.txt` | berzerk0 Probable-Wordlists v2 切片，综合多起泄露的高频口令 |
| `Pwdb_top-1000 … Pwdb_top-10000000.txt` | Pwdb-Public 泄露库 Top N（最大千万级） |
| `SplashData-2014.txt`、`SplashData-2015-1/2.txt` | SplashData 年度“最差口令”榜 |
| `top-20-common-SSH-passwords.txt` | SSH 服务最常见的 Top 20 口令（`root/toor/raspberry/dietpi` 等） |
| `top-passwords-shortlist.txt` | 最小高频口令清单，适合先快速试一轮 |
| `worst-passwords-2017-top100-slashdata.txt` | SplashData 2017 Top 100 最差口令 |
| `xato-net-10-million-passwords.txt` | xato.net 千万口令泄露整理后的**去重完整版**，约 519 万条唯一口令，按频率从高到低 |
| `xato-net-10-million-passwords-10 / 100 / … / 1000000.txt` | 上述完整列表的 Top-N 切片（10 条到 100 万条），按需取用 |
| `xato-net-10-million-passwords-dup.txt` | 原数据中出现**不止一次**的口令（约 75.6 万条），更贴近真实重复使用习惯 |
| `README.md` | 说明文档 |

#### `Common-Credentials\Language-Specific\` 多语种口令

| 文件模式 | 说明 |
| --- | --- |
| `*_Pwdb_common-password-list-top-150.txt` | Pwdb-Public 按语种整理的 Top 150 高频口令，涵盖 Cantonese、Croatian、Danish、Dutch、Estonian、Finnish、French、German、Greek、Hebrew、Hindi、Hungarian、Icelandic、Indonesian、Italian、Japanese、Latvian、Lithuanian、Malay、Mandarin、Norwegian、Polish、Portuguese、Russian、Slovak、Spanish、Swedish、Thai、Turkish、Ukrainian 等 |
| `Chinese-common-password-list*.txt` | 中文常用口令 Top 1000 / 10000 / 100000 / 1000000，**爆破中文环境网站/系统首选** |
| `German_common-password-list*.txt` | 德语常用口令 Top 1000-1000000 |
| `French-common-password-list-top-5000 / 20000.txt` | 法语常用口令 |
| `Dutch_common-pasword-list.txt` | 荷兰语常用口令 |
| `Spanish_*usernames-and-passwords*.txt` | 西班牙语常用用户名+口令 |
| `Polish-common-password-list.txt` | 波兰语常用口令 |

#### 3.3 `Default-Credentials\`——默认口令/出厂凭据

| 文件 | 作用 |
| --- | --- |
| `default-passwords.csv` | 主数据源：`Vendor, Username, Password, Comments` 四列，适合脚本化检索 |
| `default-passwords.txt` | 从 CSV 自动生成的纯口令列表（不区分厂商），可直接喂 hashcat |
| `cirt-net_collection.txt` | CIRT.net 默认口令全集，覆盖约 523 家厂商、2084 条口令 |
| `avaya_defaultpasslist.txt` | Avaya 电话系统默认口令（`user:pass` 格式） |
| `citrix.txt` | Citrix 网关/设备常见默认口令 |
| `cryptominers.txt` | 矿机/ASIC 设备（HTTP/SSH/Telnet）默认口令 |
| `db2-betterdefaultpasslist.txt` | DB2 数据库默认口令组合 |
| `ftp-betterdefaultpasslist.txt` | FTP 默认口令组合 |
| `mssql-betterdefaultpasslist.txt` | MSSQL 默认口令组合（`sa:sa` 等） |
| `mysql-betterdefaultpasslist.txt` | MySQL 默认口令组合 |
| `oracle-betterdefaultpasslist.txt` | Oracle 数据库默认口令组合 |
| `postgres-betterdefaultpasslist.txt` | PostgreSQL 默认口令组合 |
| `ssh-betterdefaultpasslist.txt` | SSH 服务默认口令组合 |
| `telnet-betterdefaultpasslist.txt` | Telnet 默认口令组合 |
| `telnet-phenoelit.txt` | phenoelit 老牌 Telnet 默认口令/设备库 |
| `tomcat-betterdefaultpasslist.txt` | Tomcat manager 默认口令 |
| `tomcat-betterdefaultpasslist_base64encoded.txt` | 上面的 Base64 编码版（应对 Tomcat Basic Auth 场景） |
| `vnc-betterdefaultpasslist.txt` | VNC 默认口令 |
| `windows-betterdefaultpasslist.txt` | Windows/瘦客户端等默认管理员口令 |
| `Oracle EBS passwordlist.txt` / `Oracle EBS userlist.txt` | Oracle EBS 系统的默认密码表/用户名表 |
| `scada-pass.csv` | SCADA/工控设备默认/硬编码口令表（含厂商、设备、端口、协议、来源） |
| `Routers\` | 路由器默认账号密码，见下 |

#### `Default-Credentials\Routers\`

目录规则非常统一：对每个厂商提供一对文件：

- `<厂商>_default-users.txt`：该厂商路由器的默认/可能用户名
- `<厂商>_default-passwords.txt`：该厂商路由器的默认/可能密码

共约 **132 个厂商**，包括 `cisco`、`huawei`、`linksys`、`asus`、`d-link`、`netgear`、`belkin`、`fritz-box`、`zyxel`、`mikrotik` 等。文件名中的厂商名就是用途，例如爆破 TP-Link 路由器时找 `tplink_default-users.txt` + `tplink_default-passwords.txt`。

另有 `0ALL-USERNAMES-AND-PASSWORDS.txt`：把所有厂商常见账号/口令合并在一起的候选总表。

> 技巧：文件是纯账号/密码候选，与工具爆破时可交叉组合；README 建议优先试空用户名/空密码、设备 MAC、机身标签密码、无线密码、序列号等。

---

### 4. `Discovery`——信息收集 / 资源发现词表

#### 4.1 `Discovery\DNS\` 子域名爆破

| 文件                                                     | 作用                                                |
| ------------------------------------------------------ | ------------------------------------------------- |
| `bitquark-subdomains-top100000.txt`                    | bitquark 整理的前 10 万常用子域名词表                         |
| `subdomains-top1million-5000 / 20000 / 110000.txt`     | 2026 年从 Cloudflare Radar 获取的前 100 万子域名中的 Top-N 切片 |
| `subdomains-top1million-full.7z`                       | 完整版（出现至少 2 次的子域名），压缩包                             |
| `combined_subdomains.txt`                              | 上述多套子域名词表合并去重，日常爆破推荐先用它                           |
| `shubs-subdomains.txt`                                 | shubs 整理的综合子域名表                                   |
| `dns-Jhaddix.txt`                                      | Jason Haddix 方法论中的 DNS/子域名词表                      |
| `fierce-hostlist.txt`                                  | Fierce 扫描器内置主机名词表                                 |
| `deepmagic.com-prefixes-top500 / top50000.txt`         | DeepMagic 主机名前缀 Top 500 / 50000                   |
| `namelist.txt`                                         | 通用名称/主机名候选                                        |
| `services-names.txt`                                   | 服务/主机名命名习惯（如 `ftp`、`mail`、`vpn` 类前缀），可与主域名拼接      |
| `sortedcombined-knock-dnsrecon-fierce-reconng.txt`     | Knock、dnsrecon、Fierce、recon-ng 词表合并排序版            |
| `n0kovo_subdomains.txt`                                | n0kovo 子域名表                                       |
| `shubs-stackoverflow.txt`                              | 从 StackOverflow 等来源提取的子域名/主机名                     |
| `bug-bounty-program-subdomains-trickest-inventory.txt` | 赏金项目常见子域名清单（Trickest）                             |
| `FUZZSUBS_CYFARE_1.txt` / `FUZZSUBS_CYFARE_2.txt`      | Cyfare 子域名 fuzz 表                                 |
| `italian-subdomains.txt`、`subdomains-spanish.txt`      | 意大利语/西班牙语站点常见子域名（如 `negozi`、`tienda`）             |
| `tlds.txt`                                             | 顶级域列表，用于测域名接管/批量域名检查                              |

#### 4.2 `Discovery\File-System\`

- `OBEX_common.txt` / `OBEX_rare.txt`：OBEX 协议（蓝牙/红外文件传输）中常见/少见对象路径，测试蓝牙 OBEX 服务用。

#### 4.3 `Discovery\Infrastructure\`

| 文件 | 作用 |
| --- | --- |
| `All-Ipv4-ClassA-10.10.txt` | 生成 `10.10.x.x` 私网段常用 IP，测试内网边界/网络设备 |
| `All-Ipv4-ClassC-192.168.txt` | `192.168.x.x` 常见网段 IP |
| `common-http-ports.txt` | 常见 HTTP 端口（含非常规端口） |
| `common-router-ips.txt` | 家用/企业路由器常见管理 IP（`192.168.1.1` 等） |
| `IPGenerator.sh` | IP 生成脚本 |
| `nmap-ports-top1000.txt` | Nmap Top 1000 端口列表 |
| `Ports-1-To-65535.txt` | 1-65535 全端口列表 |

#### 4.4 `Discovery\Mainframe\`

- `default_cics_transactions.txt`：大型机 CICS 默认事务名，测 IBM 主机应用用。

#### 4.5 `Discovery\SNMP\`

| 文件 | 作用 |
| --- | --- |
| `common-snmp-community-strings.txt` | 常见 SNMP 团体名（public/private 等） |
| `common-snmp-community-strings-onesixtyone.txt` | 配合 onesixtyone 使用的精简常见团体名 |
| `snmp.txt` | SNMP 综合字典 |
| `snmp-onesixtyone.txt` | onesixtyone 格式字典 |

#### 4.6 `Discovery\Variables\`

- `awesome-environment-variable-names.txt`：常见环境变量名（配合 SSRF/云元数据/环境注入测试）
- `secret-keywords.txt`：密钥/令牌相关关键词（找硬编码 secret、API key 时做关键词匹配）

#### 4.7 `Discovery\Web-Content\` Web 目录/文件爆破（重点）

#### 通用目录/文件词表

| 文件 | 作用 |
| --- | --- |
| `common.txt` | 最常见的 Web 路径/文件名，配合 ffuf/gobuster 的第一轮扫描 |
| `big.txt` | 比 common.txt 更大的通用路径词表 |
| `combined_words.txt` | big/common/raft 等词表自动合并的单词总表 |
| `combined_directories.txt` | 多套目录词表自动合并总表，优先用于“目录发现” |
| `common_directories.txt` | 常见目录名（含 CMS/后台路径习惯） |
| `quickhits.txt` | 高危敏感文件“快速命中”表（备份、配置文件、`.git` 等） |
| `raft-small / medium / large-words/directories/files/extensions*.txt` | Google RAFT 项目词表，按体积 small/medium/large 和内容类型 words/directories/files/extensions 划分，并有 lowercase 版；词表越大覆盖越全、耗时越长 |
| `DirBuster-2007_directory-list-2.3-small/medium/big.txt` | 老牌 DirBuster 目录列表（含 lowercase 版），测试老系统时可换用 |
| `dsstorewordlist.txt` | 从 Alexa Top 百万站点 `.DS_Store` 中提取的文件/目录名，测 macOS 服务器信息泄露 |
| `web-extensions.txt` / `web-extensions-big.txt` | 常见 Web 文件扩展名 |
| `web-all-content-types.txt` | 全部 MIME/Content-Type（测上传白名单） |
| `web-mutations.txt` | Web 路径变异（大小写、点、双写等） |
| `default-web-root-directory-linux.txt` / `-windows.txt` | Linux/Windows 默认 Web 根目录路径 |
| `LinuxFileList.txt` | Linux 系统常见文件路径，配合 Web 目录穿越/LFI 场景 |
| `versioning_metafiles.txt` | 版本控制元文件（`.git`、`.svn`、`.hg` 等）路径 |
| `Common-DB-Backups.txt` | 常见数据库备份文件名 |
| `Public-Source-Repo-Issues.json` | 公开仓库 issue 数据（研究/索引用） |
| `mcp-server.txt` | MCP（Model Context Protocol）服务端点发现 |
| `graphql.txt` | GraphQL 端点/路径发现 |

#### `Discovery\Web-Content\api\` API 发现

来源为 chrislockard/api_wordlist：

| 文件 | 作用 |
| --- | --- |
| `actions.txt` / `actions-lowercase.txt` / `actions-uppercase.txt` | API 动作/动词（get、create、delete 等），不同大小写格式 |
| `objects.txt` / `objects-lowercase.txt` / `objects-uppercase.txt` | API 资源/名词（user、order 等），不同大小写格式 |
| `api-endpoints.txt` | API 端点总表 |
| `api-endpoints-res.txt` | 把 actions + objects + wild 等合并的“可直接使用”端点表 |
| `api-seen-in-wild.txt` | 实战中真实见过的 API 词 |
| `ispsystem_billmanager_api.txt` | ISPmanager/BillManager 特定 API |
| `salesforce-aura-objects.txt` | Salesforce Aura 对象列表 |

#### `Discovery\Web-Content\CMS\` CMS 专属

根目录文件针对具体 CMS：

| 文件/模式 | 作用 |
| --- | --- |
| `wordpress.fuzz.txt`、`wp-plugins.fuzz.txt`、`wp-themes.fuzz.txt` | WordPress 常见文件/插件/主题路径 |
| `Drupal.txt`、`drupal-themes.fuzz.txt` | Drupal 常见文件与主题 |
| `joomla-plugins.fuzz.txt`、`joomla-themes.fuzz.txt` | Joomla 插件/主题路径 |
| `Sharepoint.txt`、`Sharepoint-Ennumeration.txt` | SharePoint 路径与枚举 |
| `Adobe-AEM_2021.txt`、`AdobeCQ-AEM_2017.txt` | Adobe Experience Manager 敏感路径 |
| `ColdFusion.fuzz.txt`、`AdobeXML.fuzz.txt` | ColdFusion 路径/XML 接口 |
| `Django.txt`、`symfony-315-demo.txt`、`php-nuke.fuzz.txt` 等 | 对应框架/老 CMS 的已知路径 |
| `Oracle-EBS-wordlist.txt` | Oracle EBS v11 敏感路径/接口 |
| `SAP.fuzz.txt` | SAP Web 路径 |
| `Sitecore`、`Umbraco.txt`、`dotnetnuke.txt` 等 | .NET 系 CMS 路径 |
| `cms-configuration-files.txt` | CMS 通用配置文件路径 |
| `trickest-cms-wordlist\*.txt` | Trickest 维护的 **40+ 款 CMS 逐产品词表**：aimeos、bagisto、bolt、craftcms、crater、directus、django-cms、dolibarr、drupal、erpnext、espocrm、fatfreecrm、flarum、forkcms、ghost、grav、joomla、keystonejs、laravel、magento、mautic、modx、nopcommerce、octobercms、opencart、opensourcepos、pagekit、phpbb、pico、prestashop、pyrocms、shopware、snipe-it、statamic、strapi、suitecrm、sylius、tomcat、umbraco-cms、vanilla、woocommerce、wordpress、yetiforcecrm、zammad；每个产品均有普通版 `产品.txt` 与深度版 `产品-all-levels.txt` |

#### `Discovery\Web-Content\Web-Servers\` 按 Web 服务器

| 文件                                   | 作用                                                  |
| ------------------------------------ | --------------------------------------------------- |
| `Apache.txt`                         | Apache 常见敏感路径                                       |
| `Apache-Axis.txt`                    | Apache Axis（SOAP 服务）路径                              |
| `Apache-Tomcat.txt`                  | Tomcat 管理/示例/部署路径                                   |
| `IIS.txt`                            | IIS 常见路径                                            |
| `IIS-POST.txt`                       | 必须用 POST 才能探测的 IIS 文件                               |
| `IIS-systemweb.txt`                  | IIS `aspnet_client/system_web` 下 CGI/脚本路径（配合短文件名扫描） |
| `nginx.txt`                          | Nginx 常见路径/别名特性利用路径                                 |
| `JBoss.txt`                          | JBoss 控制台/部署路径                                      |
| `Glassfish-Sun-Microsystems.txt`     | Glassfish 路径                                        |
| `Java-Servlet-Runner-Adobe-JRun.txt` | JRun 老应用服务器路径                                       |
| `Oracle-Sun-iPlanet.txt`             | iPlanet 老服务器路径                                      |

#### 其他 Web-Content 子目录

| 子目录/文件                                                                                                     | 作用                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Service-Specific\`                                                                                        | 按服务分类：`Docker-API.txt`、`Kubernetes.txt`、`GitLab.txt`、`Jenkins-Hudson.txt`、`Grafana.txt`、`Keycloak-Identity-Access-Management.txt`、`Elasticsearch-Kibana.txt`、`Prometheus-Alertmanager.txt`、`Swagger.txt`、`Oracle-WebLogic.txt`、`PulseSecure-VPN.txt`、`confluence-administration.txt`、`rstp.txt`（摄像头）、`openwrt-luci-enpoints.txt` 等，均为对应服务的管理/接口/敏感路径 |
| `Programming-Language-Specific\`                                                                           | 按开发语言：`PHP.fuzz.txt`、`CommonBackdoors-PHP.fuzz.txt`、`CommonBackdoors-JSP.fuzz.txt`、`Java-Spring-Boot.txt`（actuator 端点与 RCE 路径）、`golang.txt`、`ror.txt`（Rails）、ASP.NET 常见后门等                                                                                                                                                                           |
| `BurpSuite-ParamMiner\`                                                                                    | Burp ParamMiner 使用的小写/大写请求头词表                                                                                                                                                                                                                                                                                                                        |
| `Domino-Hunter\`                                                                                           | IBM Domino 扫描：`Domino-Files.txt`、NSF/视图/命令路径 + `dh.pl` 脚本                                                                                                                                                                                                                                                                                            |
| `LEGACY-SERVICES\` 与 `CGIs\`                                                                               | 2000 年前后遗留系统/CGI 路径（CGIs、FrontPage、CGI POST 等）                                                                                                                                                                                                                                                                                                       |
| `File-Extensions-Universal-SVNDigger-Project\`                                                             | SVNDigger 的“通用文件扩展名”库，细分为 `all`、`all-dirs`、`all-extensionless`，以及按分类（`Conf` 配置、`Database` 数据库文件、`Language` 各种语言源码扩展名、`Project` 工程文件）和上下文（admin/debug/error/log 等）的扩展名字典                                                                                                                                                                              |
| `URLs\`                                                                                                    | 已知 URL 全列表（WordPress 3.3.1、Drupal 7.20、Joomla 3.0.3、SAP），丢给代理可快速铺开站点树                                                                                                                                                                                                                                                                                |
| `trickest-robots-disallowed-wordlists\`                                                                    | 从 robots.txt 中收集的 Disallow 路径 Top 100/1000/10000，测试敏感目录                                                                                                                                                                                                                                                                                              |
| `dutch\`                                                                                                   | 荷兰语 Web 内容字典（多来源合并）                                                                                                                                                                                                                                                                                                                                  |
| `coldfusion.txt`、`domino-*.txt`、`netware.txt`、`ntlm-directories.txt`                                       | 对应老系统/协议目录路径                                                                                                                                                                                                                                                                                                                                         |
| `sap-analytics-cloud.txt`、`SAP-NetWeaver.txt`、`wso2-enterprise-integrator.txt`                             | 对应 SAP/中间件路径                                                                                                                                                                                                                                                                                                                                         |
| `oauth-oidc-scopes.txt`                                                                                    | OAuth/OIDC scope 名称，测越权授权                                                                                                                                                                                                                                                                                                                            |
| `Logins.fuzz.txt`、`Passwords.fuzz.txt`                                                                     | “登录页/密码页”相关路径，而非口令内容                                                                                                                                                                                                                                                                                                                                 |
| `reverse-proxy-inconsistencies.txt`                                                                        | 反向代理不一致绕过（找被隐藏的后台/管理接口）                                                                                                                                                                                                                                                                                                                              |
| `roundcube`/`rssfeed`/`Microsoft-Frontpage`/`hashicorp-consul-api`/`hashicorp-vault`/`JavaScript-Miners` 等 | 对应应用/服务端点与敏感文件                                                                                                                                                                                                                                                                                                                                       |
| `common-api-endpoints-mazen160.txt`                                                                        | 常见 API 端点                                                                                                                                                                                                                                                                                                                                            |
| `ActiveDirectory-small.txt`                                                                                | 小型 AD 相关路径表                                                                                                                                                                                                                                                                                                                                          |
| `SOAP-functions.txt`                                                                                       | SOAP 方法名                                                                                                                                                                                                                                                                                                                                             |
| `uri-from-top-55-most-popular-apps.txt` / `url-params_from-top-55-most-popular-apps.txt`                   | 55 个热门 App 的 URI/参数                                                                                                                                                                                                                                                                                                                                  |
| `JavaServlets-Common.fuzz.txt`、`Oracle9i.fuzz.txt`、`OracleAppServer.fuzz.txt`、`AdobeXML.fuzz.txt` 等        | 老平台 fuzz 路径                                                                                                                                                                                                                                                                                                                                          |

---

### 5. `Fuzzing`——注入/模糊测试载荷

> 目录中数量庞大的部分来自 User-Agent 与日期自动生成词表。注意部分 SQLi 词表包含破坏性语句，只应在授权目标上测试。

#### 5.1 数字、字符与通用 fuzz（根目录）

| 文件 | 作用 |
| --- | --- |
| `1-4_all_letters_a-z.txt` | 1-4 位全小写字母组合 |
| `3-digits-000-999.txt` / `4-digits-0000-9999.txt` / `5-digits-00000-99999.txt` / `6-digits-000000-999999.txt` | 对应位数的纯数字组合 |
| `alphanum-case.txt` / `alphanum-case-extra.txt` | 大小写字母+数字组合 |
| `char.txt` | 常见特殊字符单字符 |
| `special-chars.txt` / `special-chars + urlencoded.txt` | 特殊字符及其 URL 编码形式 |
| `Unicode.txt` | Unicode/全角等特殊字符 |
| `big-list-of-naughty-strings.txt` | 著名的 “Naughty Strings” 全集，测输入边界/字符处理 |
| `Metacharacters.fuzzdb.txt` | shell/表达式元字符 |
| `numeric-fields-only.txt` | 数值字段测试值（负数、超大数、浮点、溢出等） |
| `email-top-100-domains.txt` | 邮箱字段常见域名 |
| `0-999999-hashgen.py` | 脚本：生成 0-999999 的 MD5/SHA 等哈希，供哈希类 fuzz 用 |

#### 5.2 `Fuzzing\Amounts\` 金额/数值 fuzz

| 文件 | 含义 |
| --- | --- |
| `one.txt` | 以 1 为基准的全部变形 |
| `zero.txt` / `zero_point_one.txt` | 0 / 0.1 基准变形 |
| `ten.txt` / `hundred.txt` / `thousand.txt` / `ten_thousand.txt` / `hundred_thousand.txt` / `milion.txt` | 以 10/100/1000/10000/100000/1000000 为基准 |
| `all.txt` | 上述综合 |
| `other.txt` | 其它金额型数值 |

用途：绕过金额上下限、整数/浮点校验，测试“金融业务逻辑漏洞”。

#### 5.3 `Fuzzing\Dates\`

每个年份目录（2019-2025）下有一个 `YYYY-MM-DD.txt`，内容是当年全部日期，用来 fuzz 生日/日期字段格式与逻辑。

#### 5.4 编码/转义与注入类

| 文件 | 作用 |
| --- | --- |
| `URI-hex.txt` / `doble-uri-hex.txt` | URI 十六进制编码 / 双重 URI 编码 |
| `FormatString-Jhaddix.txt` | 格式化字符串漏洞载荷 |
| `HTML5sec-Injections-Jhaddix.txt` | HTML5 安全研究注入 |
| `SSI-Injection-Jhaddix.txt` | SSI 服务端包含注入 |
| `command-injection-commix.txt` | Commix 收集的命令注入载荷 |
| `UnixAttacks.fuzzdb.txt` / `Windows-Attacks.fuzzdb.txt` | Unix / Windows 系统攻击载荷 |
| `login_bypass.txt` | 登录绕过载荷（SQLi/认证绕过/万能密码） |
| `template-engines-expression.txt` / `template-engines-special-vars.txt` | SSTI 模板表达式与特殊变量 |
| `php-magic-methods.txt` | PHP 魔术方法名（反序列化等场景） |
| `fully-qualified-java-classes.txt` | Java 全限定类名，测反序列化/类型混淆 |
| `XML-FUZZ.txt` | XML 注入/畸形 XML |
| `XXE-Fuzzing.txt` | XXE 外部实体载荷 |
| `JSON.Fuzzing.txt` | JSON 解析畸形输入 |
| `LDAP.Fuzzing.txt` / LDAP 属性类/类名表 | LDAP 注入与对象类枚举 |
| `IBMMQSeries-channels.txt` | IBM MQ 通道名 |
| `curl-protocols.txt` / `schemes.txt`（Misc） | URL scheme/协议枚举，测 SSRF |
| `extensions-Bo0oM.txt`、`extensions-compressed.fuzz.txt`、`extensions-most-common.fuzz.txt`、`extensions-skipfish.fuzz.txt`、`file-extensions*.txt` | 各类扩展名/压缩包扩展名 |
| `fuzz-Bo0oM.txt` / `fuzz-Bo0oM-friendly.txt` | Bo0oM 的 Web 敏感路径 fuzz 集合 |
| `FuzzingStrings-SkullSecurity.org.txt` | SkullSecurity fuzz 字符串 |
| `os-names.txt` / `os-names-mutated.txt` | 操作系统名及变异 |
| `environment-identifiers.txt` | 环境/平台标识符（配合路径与报错识别） |
| `regional_country-codes*.txt`、`regional_languages-codes.txt`、`regional_locale-codes.txt` | 国家/语言/locale 代码 |
| `http-request-methods.txt` | HTTP 方法枚举 |

#### 5.5 `Fuzzing\Databases\` 数据库探测与 SQLi

| 文件 | 作用 |
| --- | --- |
| `db2enumeration.fuzzdb.txt` | DB2 枚举语句 |
| `MSSQL-Enumeration.fuzzdb.txt` | MSSQL 枚举语句 |
| `MySQL-Read-Local-Files.fuzzdb.txt` | MySQL 读本地文件语句 |
| `Postgres-Enumeration.fuzzdb.txt` | PostgreSQL 枚举语句 |
| `OracleDB-SID.txt` | Oracle SID 名字典 |
| `SQLi\Generic-SQLi.txt` | 通用 SQL 注入载荷 |
| `SQLi\Generic-BlindSQLi.fuzzdb.txt` | 通用盲注载荷 |
| `SQLi\MSSQL.fuzzdb.txt` / `SQLi\MySQL.fuzzdb.txt` / `SQLi\Oracle.fuzzdb.txt` | 各数据库方言注入 |
| `SQLi\MySQL-SQLi-Login-Bypass.fuzzdb.txt` | MySQL 登录绕过 |
| `SQLi\NoSQL.txt` | NoSQL 注入（`$ne`、`$gt` 等） |
| `SQLi\quick-SQLi.txt` | 快速精简 SQLi 候选 |
| `SQLi\sqli.auth.bypass.txt` | SQLi 认证绕过 |
| `SQLi\SQLi-Polyglots.txt` | 兼容多种数据库的 polyglot 注入串 |

#### 5.6 `Fuzzing\LFI\` 本地文件包含/路径穿越

| 文件 | 作用 |
| --- | --- |
| `LFI-Jhaddix.txt` | Jason Haddix 综合 LFI 路径/载荷 |
| `LFI-LFISuite-pathtotest.txt` / `-huge.txt` | LFISuite 路径测试（普通/完整版） |
| `LFI-linux-and-windows_by-1N3@CrowdShield.txt` | 跨 Linux/Windows LFI 候选 |
| `Linux\LFI-etc-files-of-all-linux-packages.txt` | 各 Linux 软件包在 `/etc` 下文件路径（探测包是否安装） |
| `Linux\LFI-gracefulsecurity-linux.txt` | Linux 常见可读文件列表 |
| `Linux\OMI-Agent-Linux.txt` | OMI Agent 相关文件 |
| `Windows\Windows-LFI-Payloads_by-adeadfed.txt` | Windows 已知路径/文件 payload |
| `Windows\Windows-Paths.txt` | Windows 盲读路径 |

#### 5.7 `Fuzzing\XSS\`

分为两套平行版本：

- `human-friendly\`：带注释、可读性强，适合人工手测
- `robot-friendly\`：已压缩成工具可用的单行形式，适合 ZAP/Burp 自动化

| 文件（两目录同名文件作用相同） | 来源/特点 |
| --- | --- |
| `XSS-Jhaddix.txt` | Haddix 综合 XSS |
| `XSS-Vectors-Mario.txt` | Mario 向量集 |
| `XSS-BruteLogic.txt` / `XSS-Bypass-Strings-BruteLogic.txt` | 过滤绕过字符串 |
| `XSS-Cheat-Sheet-PortSwigger.txt` | PortSwigger 备忘单向量 |
| `XSS-EnDe-*` | 编码/解码绕过（h4k/mario/xssAttacks） |
| `XSS-payloadbox.txt` | Payloadbox 常用载荷 |
| `XSS-RSNAKE.txt` | RSnake 经典向量 |
| `XSS-Somdev.txt` | Somdev 收集向量 |
| `XSS-OFJAAAH.txt` | “Obfuscated JavaScript Alerts”向量 |
| `XSS-With-Context-Jhaddix.txt` | 按上下文（HTML/属性/JS/URL）分类的 XSS |
| `xss-without-parentheses-semi-colons-portswigger.txt` | 无括号/分号 XSS |
| `XSS-Fuzzing.txt`（仅 robot） | 自动化 XSS fuzz |
| `Polyglots\XSS-Polyglots*.txt` | 一段载荷兼容多上下文/多过滤器的 polyglot |

#### 5.8 `Fuzzing\User-Agents\`

| 文件/目录 | 作用 |
| --- | --- |
| `UserAgents.fuzz.txt` | 传统 User-Agent fuzz 集合 |
| `UserAgents-IE.txt` | IE 系列 UA |
| `user-agents-whatismybrowserdotcom-small/mid/large.txt` | WhatIsMyBrowser 数据集，按规模选 |
| `hardware-type-specific\` | 按硬件类型：car、game-console、mobile、phone、tablet、tv、server 等 16 类 |
| `layout-engine-name\` | 按浏览器内核（Blink、Gecko、WebKit 等）分类 |
| `operating-platform\` | **最大目录（约 4149 个文件）**：每个文件按“平台/具体版本”命名，如 `android.txt`、`blackberry-10.txt`、`windows-10.txt`，每个文件内含该平台所有 UA 变体；需要伪造哪类客户端就直接读对应文件名 |
| `operating-system-name\` | 按操作系统名称（android、ios、linux、windows 等 27 类）聚合 |
| `software-name\` | 按软件/浏览器名聚合（280 个文件） |
| `software-type-specific\` | 按软件类型（浏览器、爬虫、下载器、邮件客户端等）分类 |

---

### 6. `Miscellaneous`——杂项词表

#### 6.1 根目录

| 文件 | 作用 |
| --- | --- |
| `control-chars.txt` | ASCII/Unicode 控制字符，测输入过滤 |
| `dns-resolvers.txt` | 公开 DNS 解析器 IP 列表 |
| `domains-1million-top.txt` | 百万级域名清单（已做去点/连字符等变形），可做域名/主机名候选池 |
| `top-domains-alexa.csv.zip` / `top-domains-majestic.csv.zip` | Alexa / Majestic 排名域名（rank,domain）CSV 压缩包 |
| `ike-groupid.txt` | IKE（IPsec VPN）group ID 候选 |
| `lang-english.txt`、`lang-french-full/small.txt`、`lang-german.txt`、`lang-portuguese.txt`、`lang-spanish.txt` | 英语/法语/德语/葡语/西语词典，可做目录发现基础词或口令词根 |
| `pi-large.txt` | π 的超长数字串（一整行），数字型输入/文件解析 fuzz 用 |
| `schemes.txt` | URL scheme 大全（http、ws、file、gopher 等），SSRF/协议探测用 |
| `us-cities.txt` | 美国城市名（安全问答/社工词根） |
| `wordlist-skipfish.fuzz.txt` | Skipfish 扫描器内置词表 |

#### 6.2 `List-Of-Swear-Words\`

按语言（ISO 代码）命名的脏话/敏感词表，共 29 个：`en/zh/ru/de/fr/es/ja/ko/ar` 等，用于内容过滤测试、WAF 规则验证。

#### 6.3 `Security-Question-Answers\`

安全找回问题答案词表（社工/账号找回测试）：

| 文件/目录 | 作用 |
| --- | --- |
| `cities.txt`、`us-cities.txt`、`city-state-country.txt` | “你出生的城市”类问题 |
| `common-surnames.txt`、`dates.txt`、`zip-codes.txt` | 常见姓氏 / 日期 / 邮编 |
| `street-names.txt` | “你住的街道”类问题 |
| `html-colors.txt` | 颜色名（“最喜欢的颜色”） |
| `us-colleges\` | 美国各州大学名单（“毕业学校”） |
| `us-private-schools\` | 各州私立中学名单 |
| `us-public-schools\` | 各州公立中学名单 |

#### 6.4 `Web\`

- `html-events.txt`：HTML 事件属性（`onclick`、`onerror` 等），XSS/事件注入
- `html-tags.txt`：HTML 标签名
- `http-request-headers\`：HTTP 请求头候选，细分为标准字段/非标准字段/常见 IP 头（`X-Forwarded-For` 等），测 IP 伪造、缓存投毒
- `session-id.txt`：常见会话 Cookie 名（`JSESSIONID`、`ASP.NET_SessionId` 等）
- `keyhacks-api.md`：API Key 验证方法备忘（非字典）

#### 6.5 `Source-Code\c-linux\`

Linux 提权用的小段 C 源码：`root-shell.c`、`root-shell2.c`、`root-shell3.c`、`drop-shell.c`、`tiny-shell.c` + Makefile。

#### 6.6 `Words\` 词表

| 文件/目录 | 作用 |
| --- | --- |
| `Dutch-words.txt`、`German-words.txt`、`real_academia_espanola_RAE_spanish_105582_words.txt` | 荷/德/西语全量词典 |
| `EFF-Dice\` | EFF 掷骰子口令生成词表：`large` 大表、`small_1`、`small_2` 小表，并带 `*_words` 纯词版（去掉骰子序号），适合做 Diceware passphrase 基础 |
| `Moby-Project\` | 公有领域 Moby 词汇库：`Moby-Words-II`（常用词/复合词/缩写/人名/地名/拼写错误词等 14 个文件）、`Moby-Language-II`（法/德/意/日/西语）、`Moby-Thesaurus-II`（30 万词根与同义词） |

#### 6.7 `Danish-Wordlists-n0kovo\`

n0kovo 的丹麦语词表：丹麦女性/男性名字 2021、姓氏、街道名、补充城市名、旧约词、全格式词（`ddo_fullforms.txt`）。

---

### 7. `Ai\LLM_Testing\`——LLM 提示词测试集

| 目录/文件 | 作用 |
| --- | --- |
| `Bias_Testing\gender_bias.txt` / `nationality_geographic_bias.txt` / `race_ethnicity_bias.txt` | 测试模型在性别/国籍/种族上的偏见（使用前替换 `[占位符]`） |
| `Data_Leakage\metadata.txt` / `personal_data.txt` | 测试模型是否会泄露训练元数据/生成个人隐私数据 |
| `Divergence_attack\escape_out_of_allignment_training.txt` / `pre-training_data.txt` | 测试越狱/预训练记忆泄露 |
| `Ethical_and_Safety_Boundaries\forbidden_question_set.csv` | 违规问题集 |
| `Ethical_and_Safety_Boundaries\jailbreak_prompts_2023_05_07.csv` / `2023_12_25.csv` | 2023 年两批真实 jailbreak 提示词（ACM CCS 2024 论文数据集） |
| `Memory_Recall_Testing\session_recall.txt` | 会话/训练记忆提取测试 |

---

### 8. 开发目录（可忽略）

- `.bin\`：仓库维护用的生成器/校验器/更新脚本
- `.github\`：GitHub Actions 与模板

---

### 9. 与常用工具配合的示例

#### hashcat（本机 `~/hashcat-7.1.2\hashcat.exe`）

```powershell
# 先用最高频口令切片快速试
hashcat -m 0 hash.txt "SecLists-master\Passwords\Common-Credentials\xato-net-10-million-passwords-1000000.txt"

# 中文环境爆破
hashcat -m 0 hash.txt "SecLists-master\Passwords\Common-Credentials\Language-Specific\Chinese-common-password-list-top-1000000.txt"

# 先跑常用表再套规则（如加年份/数字）
hashcat -m 0 hash.txt -r rules\best64.rule "SecLists-master\Passwords\Common-Credentials\10k-most-common.txt"
```

#### ffuf / gobuster / dirsearch（Web 目录）

```text
字典：SecLists-master\Discovery\Web-Content\raft-medium-directories.txt
快速：SecLists-master\Discovery\Web-Content\common.txt
```

#### 子域名爆破

```text
字典：SecLists-master\Discovery\DNS\combined_subdomains.txt
```

---

### 10. 注意事项

1. 本目录是英文 SecLists 原版，**文件名中的 `-lowercase/-uppercase` 只表示单词大小写格式不同**，不是另一个用途。
2. `Default-Credentials\Routers\` 中每个厂商文件成对出现，爆破时建议“用户名 × 密码”交叉组合，而不是只选其中一个。
3. `Fuzzing\Databases\SQLi\` 部分载荷会删库/破坏数据，务必只在授权或隔离的靶机/CTF 环境中使用。
4. SecLists 中不少“字典”不是给 hashcat 用的，例如 Discovery/Fuzzing 目录需要喂给 ffuf、Burp Intruder、nuclei 等对应工具。
5. 涉及真实目标时请确保有授权；本说明仅用于 CTF、靶场与授权的渗透测试/防御研究工作。

## 可复现补充

## 直接可用的命令示例

### 目录扫描

```bash
ffuf -u 'http://127.0.0.1:8080/FUZZ' \
  -w /path/to/SecLists/Discovery/Web-Content/common.txt \
  -mc all -fs 0
```

### 参数名

```bash
ffuf -u 'http://127.0.0.1:8080/?FUZZ=test' \
  -w /path/to/SecLists/Discovery/Web-Content/burp-parameter-names.txt \
  -mc all -fs 0
```

### 弱口令（仅授权靶场）

```bash
hydra -L users.txt -P passwords.txt \
  127.0.0.1 ssh -t 4
```

### 哈希字典

```bash
hashcat -m 0 -a 0 hash.txt \
  rockyou.txt --force
```

### 字典裁剪原则

- 目录：`common.txt` → `raft-small-directories.txt` → 大字典；
- 参数：`burp-parameter-names.txt`；
- 用户：从题目页面/协议/日志提取，不要直接用超大用户表；
- 口令：先 `top1000`，再 `rockyou`，再加规则；
- 扩展名：先 `php,html,js,txt,bak,zip`，再按指纹扩展。
