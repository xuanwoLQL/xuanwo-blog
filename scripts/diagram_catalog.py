"""Content-specific diagram catalog for published notes."""


def flow(slug, title, desc, takeaway, steps):
    return {
        "slug": slug,
        "kind": "flow",
        "title": title,
        "desc": desc,
        "takeaway": takeaway,
        "steps": steps,
    }


def pipeline(slug, title, desc, takeaway, steps):
    return {
        "slug": slug,
        "kind": "pipeline",
        "title": title,
        "desc": desc,
        "takeaway": takeaway,
        "steps": steps,
    }


def layers(slug, title, desc, layers_):
    return {
        "slug": slug,
        "kind": "layers",
        "title": title,
        "desc": desc,
        "takeaway": "",
        "layers": layers_,
    }


def arch(slug, title, desc, takeaway, zones, edges):
    return {
        "slug": slug,
        "kind": "arch",
        "title": title,
        "desc": desc,
        "takeaway": takeaway,
        "zones": zones,
        "edges": edges,
    }


def n(tag, title, subs, focal=False):
    return {"tag": tag, "title": title, "sub": subs, "focal": focal}


DIAGRAMS = [
    arch(
        "agent-skills-ctf-dfir",
        "Agent Skills 单源与执行边界",
        "同一份技能源经过适配层进入不同运行时，工具调用被限制在只读检索与受控脚本。",
        "单源解决版本漂移，人工确认守住比赛平台边界。",
        [
            {
                "label": "DEFINE",
                "nodes": [
                    {
                        "id": "skills",
                        "tag": "SOURCE",
                        "title": "ctf-0day / solver",
                        "sub": "SKILL.md + 索引 + 脚本",
                        "y": 190,
                    },
                    {
                        "id": "adapters",
                        "tag": "ADAPTER",
                        "title": "运行时适配层",
                        "sub": "路径 / 加载 / MCP 配置",
                        "y": 310,
                    },
                ],
            },
            {
                "label": "RUNTIME",
                "nodes": [
                    {
                        "id": "runtime",
                        "tag": "AGENT",
                        "title": "Claude / Codex",
                        "sub": "按 description 路由",
                        "y": 190,
                    },
                    {
                        "id": "project",
                        "tag": "TASK",
                        "title": "当前比赛任务",
                        "sub": "先读路由，再按需加载",
                        "y": 310,
                    },
                ],
            },
            {
                "label": "CONTROL",
                "nodes": [
                    {
                        "id": "mcp",
                        "tag": "MCP",
                        "title": "只读 + 受控执行",
                        "sub": "kb_search / run_weapon",
                        "y": 190,
                        "focal": True,
                    },
                    {
                        "id": "human",
                        "tag": "HUMAN",
                        "title": "人工确认",
                        "sub": "开环境 / 提交 flag / 读 token",
                        "y": 310,
                    },
                ],
            },
        ],
        [
            {"from": "skills", "to": "runtime"},
            {"from": "runtime", "to": "mcp", "focal": True},
            {"from": "adapters", "to": "project"},
            {"from": "project", "to": "human"},
        ],
    ),
    flow(
        "antsword-usage",
        "蚁剑最小验证链",
        "从受控 PHP 文件到蚁剑连接，再到只读验证和证据记录。",
        "连接成功前先确认 URL、参数名和返回格式三件事。",
        [
            n("01", "准备一句话", ["授权靶场文件"]),
            n("02", "上传或写入", ["确认路径可访问"]),
            n("03", "配置连接", ["URL / 参数 / 编码"]),
            n("04", "测试会话", ["whoami · pwd"]),
            n("05", "只读取证", ["目录 / 配置 / 日志"], True),
        ],
    ),
    flow(
        "apache-htaccess-exploit",
        ".htaccess 上传利用链",
        "先改变 Apache 解析规则，再上传图片文件并触发 PHP 执行。",
        "能控制 .htaccess 往往比寻找新后缀更直接。",
        [
            n("01", "上传 .htaccess", ["AddType / SetHandler"]),
            n("02", "上传图片马", ["保留合法文件头"]),
            n("03", "访问目标文件", ["请求图片路径"]),
            n("04", "Apache 解析", ["按 PHP 执行"]),
            n("05", "验证执行", ["whoami / id"], True),
        ],
    ),
    pipeline(
        "archive-cracking-john",
        "压缩包密码恢复流程",
        "从加密压缩包中提取可验证哈希，再用字典或规则恢复密码。",
        "先确认 hash 类型，再选 hashcat 模式；跑完必须回解压缩包验证。",
        [
            n("01", "确认格式", ["ZIP / RAR / 7Z"]),
            n("02", "提取哈希", ["zip2john / 7z2john"]),
            n("03", "识别模式", ["hashcat --identify"]),
            n("04", "字典攻击", ["wordlist + rules"]),
            n("05", "回解验证", ["解压测试文件"], True),
        ],
    ),
    pipeline(
        "crypto-affine-cipher",
        "仿射密码实现与破译",
        "加密、密钥枚举和卡方频率分析共享同一套字符映射。",
        "密钥空间只有 312 组，穷举后必须用语言频率和可读性复核。",
        [
            n("01", "明文归一化", ["保留大小写 / 非字母"]),
            n("02", "密钥校验", ["gcd(k1,26)=1"]),
            n("03", "仿射加密", ["E(x)=k1x+k2"]),
            n("04", "312 组枚举", ["解密候选集合"]),
            n("05", "卡方筛选", ["最小统计量 + 人工复核"], True),
        ],
    ),
    pipeline(
        "crypto-des-cipher",
        "DES 加密数据流",
        "从 PKCS#7 填充到 16 轮 Feistel，再到逆初始置换输出密文。",
        "实现正确性的关键不是轮数，而是每个置换表、轮密钥和字节序都一致。",
        [
            n("01", "明文 / 密钥", ["8 字节分组"]),
            n("02", "PKCS#7 填充", ["补齐到 8 字节"]),
            n("03", "IP + 16 轮", ["Feistel · PC-1/2"]),
            n("04", "IP⁻¹", ["交换 L/R 后逆置换"]),
            n("05", "密文 / 向量验证", ["FIPS / NIST 对拍"], True),
        ],
    ),
    flow(
        "crypto-history-paper",
        "密码学演进主线",
        "从古典代换到对称密码、公钥密码、哈希签名和后量子迁移。",
        "技术演进的主线始终是攻击能力变化推动安全模型重建。",
        [
            n("01", "古典密码", ["代换 / 置换"]),
            n("02", "现代对称", ["DES → AES"]),
            n("03", "公钥密码", ["RSA / ECC"]),
            n("04", "完整性与身份", ["Hash / 签名 / PKI"]),
            n("05", "后量子迁移", ["PQC / QKD"], True),
        ],
    ),
    pipeline(
        "crypto-md5",
        "MD5 压缩管线",
        "消息经过填充、分组、四轮压缩与链接变量累加后得到 128 位摘要。",
        "验证实现时先对拍填充和中间变量，再对拍最终摘要。",
        [
            n("01", "消息输入", ["任意字节长度"]),
            n("02", "填充", ["0x80 + 0x00 + 长度"]),
            n("03", "512-bit 分组", ["16 个 32-bit 字"]),
            n("04", "4 轮 × 16 步", ["F/G/H/I + 常量表"]),
            n("05", "链接变量 / 摘要", ["小端输出 16 字节"], True),
        ],
    ),
    pipeline(
        "crypto-rsa-lab",
        "RSA 密钥与加解密流程",
        "从素数选择到公私钥生成，再到模幂加解密和 CRT 加速。",
        "教学实现验证正确性，生产系统必须使用成熟库和安全填充。",
        [
            n("01", "选择 p, q", ["Miller-Rabin"]),
            n("02", "计算 n, φ(n)", ["n=pq"]),
            n("03", "生成 e, d", ["e·d ≡ 1 mod φ"]),
            n("04", "模幂加密", ["c=m^e mod n"]),
            n("05", "CRT 解密 / 自检", ["m=c^d mod n"], True),
        ],
    ),
    flow(
        "ctf-actf-2025-upload",
        "ACTF 多阶段攻击链",
        "从 SQL 注入登录到路径穿越读源码，再破解管理员密码并写入命令结果。",
        "每一阶段都要保留可重复请求，最后用同一路径读取 RCE 证据。",
        [
            n("01", "SQLi 登录", ["弱口令 / OR 1=1"]),
            n("02", "上传路径穿越", ["file_path 参数"]),
            n("03", "读取源码", ["/app/app.py"]),
            n("04", "破解密码", ["hashcat -m 1400"]),
            n("05", "管理员 RCE", ["os.system 拼接"]),
            n("06", "写入并读取证据", ["结果文件 / flag"], True),
        ],
    ),
    flow(
        "ctf-command-injection-echo",
        "有回显命令注入",
        "URL 参数进入 shell 后，用分隔符追加命令并读取回显。",
        "先用 whoami 证明执行，再用 ls 和 cat 做最小化取证。",
        [
            n("01", "输入 URL", ["功能会调用 ping/dig"]),
            n("02", "shell 字符串拼接", ["未做参数隔离"]),
            n("03", "分隔符探测", ["; · && · |"]),
            n("04", "whoami 验证", ["确认执行用户"]),
            n("05", "ls / env / cat", ["定位并读取 flag"], True),
        ],
    ),
    pipeline(
        "ctf-curl-requests",
        "curl 请求构造流程",
        "把请求方法、Header、Cookie、Body 和文件上传拆成可复现参数。",
        "复制浏览器请求后，先删无关 Header，再逐项加回验证。",
        [
            n("01", "确定方法", ["GET / POST / PUT"]),
            n("02", "设置 Header", ["Content-Type / Cookie"]),
            n("03", "构造 Body", ["JSON / form / raw"]),
            n("04", "发送请求", ["-i -v 保留证据"]),
            n("05", "检查响应", ["状态 / 长度 / 回显"], True),
        ],
    ),
    flow(
        "ctf-eval-command-injection",
        "eval 命令注入链",
        "用户输入进入 eval 后，通过函数调用和过滤绕过实现命令执行。",
        "先证明代码执行，再证明系统命令执行，两个阶段证据要分开。",
        [
            n("01", "GET 参数", ["进入 eval"]),
            n("02", "语法探测", ["函数 / 分号 / 引号"]),
            n("03", "过滤绕过", ["替代函数 / 编码"]),
            n("04", "命令执行", ["system / exec"]),
            n("05", "定位 flag", ["whoami / ls / cat"], True),
        ],
    ),
    arch(
        "ctf-fastjson-waf-bypass-rce",
        "fastjson JNDI 攻击面",
        "JSON 请求触发自动类型解析，应用随后向外部 LDAP/RMI 服务发起 JNDI 查询。",
        "核心证据是应用发起的外连与远程类加载，而不是单纯 500 响应。",
        [
            {
                "label": "PUBLIC",
                "nodes": [
                    {
                        "id": "client",
                        "tag": "INPUT",
                        "title": "恶意 JSON",
                        "sub": "@type / 编码变形",
                        "y": 190,
                    },
                    {
                        "id": "waf",
                        "tag": "BYPASS",
                        "title": "WAF 绕过",
                        "sub": "关键字 / 大小写 / 分段",
                        "y": 310,
                    },
                ],
            },
            {
                "label": "APPLICATION",
                "nodes": [
                    {
                        "id": "parse",
                        "tag": "PARSE",
                        "title": "fastjson 解析",
                        "sub": "autoType / 反序列化",
                        "y": 190,
                    },
                    {
                        "id": "lookup",
                        "tag": "SINK",
                        "title": "JNDI 查询",
                        "sub": "ldap:// / rmi://",
                        "y": 310,
                        "focal": True,
                    },
                ],
            },
            {
                "label": "ATTACK SERVER",
                "nodes": [
                    {
                        "id": "ldap",
                        "tag": "REMOTE",
                        "title": "LDAP / RMI",
                        "sub": "返回 Reference",
                        "y": 190,
                    },
                    {
                        "id": "exec",
                        "tag": "IMPACT",
                        "title": "远程类加载",
                        "sub": "命令执行 / 外带",
                        "y": 310,
                    },
                ],
            },
        ],
        [
            {"from": "client", "to": "parse"},
            {"from": "parse", "to": "ldap", "external": True},
            {"from": "waf", "to": "lookup"},
            {"from": "lookup", "to": "exec", "focal": True},
        ],
    ),
    flow(
        "ctf-moectf-2026-sql-blind",
        "布尔盲注提取流程",
        "在黑名单限制下，把问题转成真假判断，再逐字符恢复数据。",
        "盲注的可靠性来自稳定基线、脚本重试和边界字符处理。",
        [
            n("01", "定位参数", ["观察真假响应"]),
            n("02", "建立基线", ["真 / 假 / 异常"]),
            n("03", "过滤绕过", ["替代函数 / 编码"]),
            n("04", "逐位比较", ["ASCII / 二分"]),
            n("05", "脚本提取", ["超时 / 重试"]),
            n("06", "还原 flag", ["人工复核结果"], True),
        ],
    ),
    flow(
        "ctf-npc-hidden-entry",
        "NPC 隐藏入口与反序列化",
        "从极简首页和抓包结果找到隐藏入口，再进入反序列化链。",
        "隐藏入口通常藏在静态资源、按钮请求和非常规状态码里。",
        [
            n("01", "首页观察", ["按钮 / 静态资源"]),
            n("02", "Burp 抓包", ["请求路径 / 参数"]),
            n("03", "隐藏入口", ["源码或接口线索"]),
            n("04", "反序列化输入", ["对象 / 魔法方法"]),
            n("05", "POP 链验证", ["命令执行 / flag"], True),
        ],
    ),
    pipeline(
        "ctf-php-filter-encoding-bypass",
        "php://filter 编码压缩绕过",
        "当 Base64 过滤器被禁用后，用压缩过滤器输出二进制，再离线还原源码。",
        "先保存原始字节，再做 zlib 解压；不要把浏览器显示文本直接当源码。",
        [
            n("01", "LFI 参数", ["file=..."]),
            n("02", "过滤探测", ["base64 被禁"]),
            n("03", "压缩过滤器", ["zlib.deflate"]),
            n("04", "保存原始响应", ["二进制 / Base64"]),
            n("05", "解压还原源码", ["zlib.decompress(-15)"], True),
        ],
    ),
    flow(
        "ctf-php-parameterless-rce",
        "PHP 无参数 RCE 绕过",
        "在 $、引号和括号被限制时，用内置函数读取当前作用域中的请求变量。",
        "绕过不是猜 payload，而是逐个确认哪些函数和符号仍可用。",
        [
            n("01", "读取过滤规则", ["preg_match 黑名单"]),
            n("02", "确认 eval", ["输入进入代码"]),
            n("03", "get_defined_vars", ["拿到超全局变量"]),
            n("04", "current / end", ["取最后一个参数"]),
            n("05", "嵌套 eval", ["system('cat /flag')"]),
            n("06", "验证 flag", ["响应与文件双证"], True),
        ],
    ),
    flow(
        "ctf-php-pop-chain-2",
        "PHP POP 链对象跳转",
        "从反序列化入口出发，经析构、唤醒和魔术调用最终进入危险函数。",
        "POP 链必须按真实方法名和属性名构造，不能用“看起来像”的类名代替。",
        [
            n("01", "unserialize", ["GET person"]),
            n("02", "PersonA::__destruct", ["动态方法调用"]),
            n("03", "PersonB::__wakeup", ["对象属性跳转"]),
            n("04", "危险 callable", ["system / 写文件"]),
            n("05", "生成序列化", ["URL 编码并发送"], True),
        ],
    ),
    flow(
        "ctf-sqli-example",
        "联合查询 SQL 注入流程",
        "先确定列数，再依次枚举库表、字段和值。",
        "每一步都使用可回显字段，并在最后用原始数据复核。",
        [
            n("01", "登录框注入点", ["单引号测试"]),
            n("02", "确定列数", ["UNION SELECT NULL"]),
            n("03", "枚举表名", ["information_schema"]),
            n("04", "枚举字段", ["column_name"]),
            n("05", "读取 flag", ["UNION SELECT value"], True),
        ],
    ),
    arch(
        "ctf-ssrf-intranet-exploit",
        "SSRF 内网组合攻击",
        "公网输入被服务端转发后触及内网 HTTP、元数据和 Redis，最终扩大影响。",
        "SSRF 的关键证据是目标侧真实发起连接，而不是浏览器直接访问。",
        [
            {
                "label": "PUBLIC",
                "nodes": [
                    {
                        "id": "attacker",
                        "tag": "ACTOR",
                        "title": "攻击者",
                        "sub": "可控 URL / 协议",
                        "y": 190,
                    },
                    {
                        "id": "url",
                        "tag": "PAYLOAD",
                        "title": "恶意 URL / 协议",
                        "sub": "http · gopher · file",
                        "y": 310,
                    },
                ],
            },
            {
                "label": "INTERNAL",
                "nodes": [
                    {
                        "id": "fetch",
                        "tag": "SSRF",
                        "title": "服务端请求器",
                        "sub": "目标侧发起连接",
                        "y": 190,
                    },
                    {
                        "id": "redis",
                        "tag": "PROTOCOL",
                        "title": "Redis / gopher",
                        "sub": "写入文件或任务",
                        "y": 310,
                        "focal": True,
                    },
                ],
            },
            {
                "label": "IMPACT",
                "nodes": [
                    {
                        "id": "metadata",
                        "tag": "TARGET",
                        "title": "元数据 / 内网 HTTP",
                        "sub": "配置 / 凭据 / flag",
                        "y": 190,
                    },
                    {
                        "id": "rce",
                        "tag": "IMPACT",
                        "title": "RCE / 横向",
                        "sub": "计划任务 / WebShell",
                        "y": 310,
                    },
                ],
            },
        ],
        [
            {"from": "attacker", "to": "fetch", "external": True},
            {"from": "fetch", "to": "metadata"},
            {"from": "url", "to": "redis"},
            {"from": "redis", "to": "rce", "focal": True},
        ],
    ),
    flow(
        "ctf-tgctf-2025-aaa",
        "TGCTF AAA 编码绕过",
        "把被过滤的输入转成等价形式，经过 PHP 自身机制还原后进入执行点。",
        "任何编码绕过都要在本地恢复原文并解释中间变换。",
        [
            n("01", "读取过滤", ["字符 / 函数限制"]),
            n("02", "选择编码", ["URL / Base64 / Hex"]),
            n("03", "构造等价输入", ["保持语义"]),
            n("04", "PHP 解码", ["进入 eval / 函数"]),
            n("05", "读取 flag", ["最小命令验证"], True),
        ],
    ),
    flow(
        "ctf-tgctf-2025-php-chain",
        "TGCTF 上传 + POP 链",
        "先让上传文件成为反序列化入口，再沿对象链调用危险方法。",
        "上传只是投递方式，真正要证明的是反序列化和方法调用顺序。",
        [
            n("01", "伪装上传", ["合法文件头"]),
            n("02", "识别解析入口", ["phar / unserialize"]),
            n("03", "构造对象", ["属性 / 引用"]),
            n("04", "触发 POP 链", ["析构 / 唤醒"]),
            n("05", "验证 RCE", ["whoami / flag"], True),
        ],
    ),
    flow(
        "ctf-tgctf-2025-upload-deserialization",
        "TGCTF 伪装上传与反序列化",
        "上传环节负责把可控内容送进应用，反序列化环节负责触发对象行为。",
        "先证明文件可控，再证明入口可达，最后证明危险方法执行。",
        [
            n("01", "上传请求", ["文件名 / 内容可控"]),
            n("02", "绕过检测", ["头部 / 后缀 / 路径"]),
            n("03", "定位反序列化", ["cookie / 参数 / 文件"]),
            n("04", "构造 payload", ["类属性 / 魔术方法"]),
            n("05", "验证效果", ["命令 / 文件 / flag"], True),
        ],
    ),
    flow(
        "ctf-upload-race-condition",
        "上传条件竞争时间窗",
        "文件通过检查后、被删除前存在短暂可执行窗口。",
        "竞争利用必须用可观测事件证明：请求发生在删除之前。",
        [
            n("01", "上传文件", ["临时路径可预测"]),
            n("02", "检查通过", ["内容 / 类型"]),
            n("03", "并发访问", ["持续请求临时文件"]),
            n("04", "删除发生", ["窗口关闭"]),
            n("05", "执行成功", ["写入 WebShell"], True),
        ],
    ),
    flow(
        "ctf-upload-user-ini",
        ".user.ini + 图片马",
        "先上传配置改变 PHP 自动包含行为，再让图片文件进入解释器。",
        "配置文件与图片马必须落在同一可解析目录，并确认 auto_prepend_file 生效。",
        [
            n("01", "上传 .user.ini", ["auto_prepend_file"]),
            n("02", "上传图片马", ["合法图片头 + PHP"]),
            n("03", "访问 PHP 页面", ["目录内触发 prepend"]),
            n("04", "图片马执行", ["命令解释器"]),
            n("05", "连接并验证", ["whoami / flag"], True),
        ],
    ),
    flow(
        "ctf-xxemoe-2025",
        "XXE 文件读取最小链",
        "XML 解析器展开外部实体，把本地 flag 文件带入响应。",
        "先确认 XML 可控，再分别验证实体定义、解析和回显位置。",
        [
            n("01", "XML 输入", ["可控 DOCTYPE"]),
            n("02", "定义实体", ["SYSTEM file://..."]),
            n("03", "解析实体", ["XML 解析器启用 DTD"]),
            n("04", "内容回显", ["响应字段"]),
            n("05", "读取 flag", ["固定文件路径"], True),
        ],
    ),
    pipeline(
        "dirsearch-usage",
        "目录扫描验证流程",
        "从授权目标、字典和线程设置开始，最终把扫描命中变成手工证据。",
        "扫描器给候选，手工请求给结论；不要直接相信状态码。",
        [
            n("01", "确认目标", ["协议 / 根路径"]),
            n("02", "选择字典", ["通用 + 技术栈"]),
            n("03", "控制并发", ["线程 / 超时"]),
            n("04", "过滤结果", ["状态码 / 长度"]),
            n("05", "手工复核", ["curl / Burp 证据"], True),
        ],
    ),
    pipeline(
        "hashcat-usage",
        "hashcat 破解流程",
        "先识别哈希模式和攻击类型，再选择设备、字典与规则，最后回算验证。",
        "记录模式、字典、规则和耗时，才能说明结果如何得到。",
        [
            n("01", "识别哈希", ["--identify / 前缀"]),
            n("02", "选择模式", ["-m 数值"]),
            n("03", "选择攻击", ["字典 / 掩码 / 规则"]),
            n("04", "执行与监控", ["温度 / 速度 / restore"]),
            n("05", "回算验证", ["重新哈希明文"], True),
        ],
    ),
    flow(
        "java-deserialization-lab",
        "Java 反序列化利用链",
        "Base64 进入 ObjectInputStream，HashMap 触发 hashCode，最终经反射执行命令。",
        "命令在 readObject 内部执行，最后的 ClassCastException 不影响结果。",
        [
            n("01", "Base64 请求", ["/dogs/import"]),
            n("02", "readObject", ["无类型白名单"]),
            n("03", "HashMap", ["重建哈希表"]),
            n("04", "Dog.hashCode", ["wagTail 可控反射"]),
            n("05", "chainWagTail", ["getMethod → invoke"]),
            n("06", "Runtime.exec", ["命令执行 / 外带"], True),
        ],
    ),
    flow(
        "opencode-ctf-solving",
        "Agent 辅助 CTF 解题闭环",
        "把题面检索、假设生成、工具执行和人工验证串成可追踪流程。",
        "模型负责加速搜索和生成，最终结论必须由脚本或请求证明。",
        [
            n("01", "读取题面", ["附件 / 目标 / 限制"]),
            n("02", "检索同类", ["索引 / WP / payload"]),
            n("03", "提出假设", ["最小验证步骤"]),
            n("04", "运行工具", ["保存输入输出"]),
            n("05", "人工复核", ["重复实验 / 提交"], True),
        ],
    ),
    layers(
        "os-monolithic-vs-microkernel",
        "宏内核与微内核分层",
        "用户程序通过系统调用进入内核服务，区别在于服务运行在哪个地址空间。",
        [
            {"index": "L5", "title": "应用程序", "sub": "进程、文件、网络 API", "note": "user space"},
            {"index": "L4", "title": "系统调用接口", "sub": "陷入内核的统一边界", "note": "ABI"},
            {"index": "L3", "title": "内核服务", "sub": "调度 · 内存 · 文件 · 网络", "note": "宏内核集中"},
            {"index": "L2", "title": "驱动 / IPC", "sub": "微内核拆到用户态服务", "note": "IPC 成本", "focal": True},
            {"index": "L1", "title": "硬件", "sub": "CPU · 中断 · 页表 · 设备", "note": "privileged"},
        ],
    ),
    flow(
        "param-fuzz-php-wrapper",
        "参数发现与伪协议利用",
        "先找到真正进入 include 的参数，再用 PHP 包装器读取源码。",
        "参数名、过滤器和包装器能力必须分别验证。",
        [
            n("01", "发现参数", ["字典 / 源码"]),
            n("02", "确认 include", ["报错 / 路径变化"]),
            n("03", "测试包装器", ["filter / data / phar"]),
            n("04", "绕过过滤", ["编码 / 双写"]),
            n("05", "读取源码", ["解码并还原"], True),
        ],
    ),
    flow(
        "pentest-bugku-1",
        "Bugku 内网渗透主线",
        "从外网 SSRF 和 FastCGI 打点，经过容器横向到多类应用收尾。",
        "按证据链推进，不按工具清单推进；每一步都要知道下一跳为什么可达。",
        [
            n("01", "外网入口", ["SSRF / 文件读取"]),
            n("02", "PHP-FPM", ["FastCGI RCE"]),
            n("03", "容器信息", ["进程 / 网络 / 凭据"]),
            n("04", "内网横向", ["Redis / 数据库 / CMS"]),
            n("05", "应用收尾", ["SQLi / XXE"]),
            n("06", "汇总 11 个 flag", ["逐项验证"], True),
        ],
    ),
    flow(
        "pentest-bugku-2",
        "Typecho 靶场攻击链",
        "从后台入口和 Typecho 配置出发，串联多主机权限与 flag。",
        "先确认入口和版本，再针对配置、插件与数据库分线推进。",
        [
            n("01", "信息收集", ["端口 / 指纹 / 版本"]),
            n("02", "后台入口", ["弱口令 / 认证绕过"]),
            n("03", "Typecho 配置", ["数据库 / 主题 / 插件"]),
            n("04", "跨主机移动", ["凭据 / 隧道"]),
            n("05", "逐台取证", ["9 个 flag 对账"], True),
        ],
    ),
    flow(
        "pentest-prompt-template",
        "渗透任务编排流程",
        "把授权范围、资产假设、验证动作和输出格式写成可执行约束。",
        "提示词只负责约束流程，不能替代现场验证和人工判断。",
        [
            n("01", "授权边界", ["域名 / 网段 / 禁止项"]),
            n("02", "资产收集", ["端口 / 服务 / 指纹"]),
            n("03", "假设排序", ["影响 × 可得性"]),
            n("04", "最小验证", ["只读请求"]),
            n("05", "证据报告", ["命令 / 响应 / 时间"], True),
        ],
    ),
    flow(
        "pentest-vulntarget-b",
        "vulntarget-b 攻击路径",
        "从公开入口收集到凭据复用、横向和最终权限提升。",
        "记录每次凭据复用和横向的源/目的地址，避免把不同主机混在一起。",
        [
            n("01", "入口扫描", ["端口 / Web 指纹"]),
            n("02", "漏洞验证", ["文件 / 参数 / 弱口令"]),
            n("03", "凭据获取", ["配置 / 数据库"]),
            n("04", "横向移动", ["SSH / SMB / 隧道"]),
            n("05", "权限提升", ["SUID / 服务 / 内核"], True),
        ],
    ),
    flow(
        "php-deserialization",
        "PHP 反序列化魔术方法链",
        "可控字符串进入 unserialize，属性值在魔术方法中转化为危险调用。",
        "先列入口和魔法方法，再按调用顺序构造对象图。",
        [
            n("01", "可控输入", ["cookie / GET / 文件"]),
            n("02", "unserialize", ["对象恢复"]),
            n("03", "魔术方法", ["destruct / wakeup / toString"]),
            n("04", "危险 sink", ["include / eval / call_user_func"]),
            n("05", "生成 payload", ["序列化 + 编码"], True),
        ],
    ),
    flow(
        "php-lfi",
        "PHP 本地文件包含链",
        "参数进入 include 后，利用路径遍历和可写入载体扩大为代码执行。",
        "LFI 不等于 RCE；必须证明包含内容可控或日志/临时文件可写入。",
        [
            n("01", "定位 include", ["参数 / 页面变化"]),
            n("02", "路径遍历", ["../../etc/passwd"]),
            n("03", "可写载体", ["日志 / 临时文件 / session"]),
            n("04", "伪协议", ["php://filter"]),
            n("05", "代码执行 / flag", ["包含并验证"], True),
        ],
    ),
    flow(
        "php-pop-chain",
        "PHP POP 链构造",
        "从对象入口开始，沿属性引用和魔术方法寻找危险函数调用。",
        "链的每一步都要有源码依据，不能只靠 autoload 猜类。",
        [
            n("01", "源码审计", ["类 / 属性 / 方法"]),
            n("02", "找入口", ["unserialize"]),
            n("03", "串对象", ["属性引用"]),
            n("04", "触发魔术方法", ["destruct / wakeup"]),
            n("05", "危险调用", ["system / file_put_contents"], True),
        ],
    ),
    flow(
        "php-upload-prefix-bypass",
        "文件上传文件头绕过",
        "用合法图片头满足内容检测，再用解析配置让文件按 PHP 执行。",
        "文件头只能绕过检测，最终能否执行取决于服务器解析规则。",
        [
            n("01", "上传点", ["Content-Type / 后缀"]),
            n("02", "内容检测", ["getimagesize"]),
            n("03", "添加文件头", ["FF D8 FF"]),
            n("04", "改变解析", [".htaccess / 配置"]),
            n("05", "请求执行", ["命令回显"], True),
        ],
    ),
    pipeline(
        "prototype-pollution",
        "原型污染数据链",
        "可控属性经过不安全的递归合并进入 Object.prototype，再影响下游 sink。",
        "污染点是写原型，利用点是有代码读取被污染的属性。",
        [
            n("01", "输入 JSON", ["__proto__ / constructor"]),
            n("02", "不安全合并", ["递归 assign"]),
            n("03", "修改原型", ["prototype 属性"]),
            n("04", "读取污染值", ["配置 / 权限检查"]),
            n("05", "进入 sink", ["模板 / RCE / XSS"], True),
        ],
    ),
    arch(
        "python-fork-chatroom",
        "fork 群聊进程模型",
        "监听进程接受连接，子进程处理单个客户端，结果再广播给其他连接。",
        "子进程必须管理连接生命周期，否则会出现僵尸进程或写已关闭 socket。",
        [
            {
                "label": "CLIENTS",
                "nodes": [
                    {
                        "id": "client",
                        "tag": "SOCKET",
                        "title": "多个客户端",
                        "sub": "连接 + 发送消息",
                        "y": 250,
                    }
                ],
            },
            {
                "label": "SERVER",
                "nodes": [
                    {
                        "id": "fork",
                        "tag": "FORK",
                        "title": "父进程 accept → fork",
                        "sub": "子进程 recv / send",
                        "y": 250,
                        "focal": True,
                    },
                ],
            },
            {
                "label": "OUTPUT",
                "nodes": [
                    {
                        "id": "broadcast",
                        "tag": "BROADCAST",
                        "title": "消息广播",
                        "sub": "向其他客户端写回",
                        "y": 250,
                    }
                ],
            },
        ],
        [
            {"from": "client", "to": "fork", "external": True},
            {"from": "fork", "to": "broadcast", "focal": True},
        ],
    ),
    arch(
        "python-ftp-server",
        "FTP 控制面与数据面",
        "客户端命令走控制连接，文件内容走独立数据连接，服务器最终读写共享目录。",
        "FTP 的排错重点是控制连接状态、PASV 端口和数据连接是否真正建立。",
        [
            {
                "label": "CLIENT",
                "nodes": [
                    {
                        "id": "ctl_client",
                        "tag": "CONTROL",
                        "title": "FTP 客户端",
                        "sub": "USER / PASS / LIST / RETR",
                        "y": 190,
                    },
                    {
                        "id": "data_client",
                        "tag": "DATA",
                        "title": "数据连接",
                        "sub": "PASV / PORT",
                        "y": 310,
                    },
                ],
            },
            {
                "label": "SERVER",
                "nodes": [
                    {
                        "id": "ctl_server",
                        "tag": "CONTROL",
                        "title": "命令解析",
                        "sub": "认证 / 状态机",
                        "y": 190,
                    },
                    {
                        "id": "data_server",
                        "tag": "DATA",
                        "title": "数据通道",
                        "sub": "LIST / RETR / STOR",
                        "y": 310,
                        "focal": True,
                    },
                ],
            },
            {
                "label": "STORAGE",
                "nodes": [
                    {
                        "id": "listing",
                        "tag": "FILES",
                        "title": "目录列表",
                        "sub": "共享根目录",
                        "y": 190,
                    },
                    {
                        "id": "transfer",
                        "tag": "FILES",
                        "title": "文件读写",
                        "sub": "分块发送 / 落地",
                        "y": 310,
                    },
                ],
            },
        ],
        [
            {"from": "ctl_client", "to": "ctl_server", "external": True},
            {"from": "data_client", "to": "data_server", "external": True},
            {"from": "ctl_server", "to": "listing"},
            {"from": "data_server", "to": "transfer", "focal": True},
        ],
    ),
    arch(
        "python-gui-chatroom",
        "GUI 聊天室组件关系",
        "Tkinter 界面负责输入和显示，网络线程负责收发，服务器负责广播。",
        "GUI 线程不要直接阻塞在网络 read；用队列或事件回到主线程更新界面。",
        [
            {
                "label": "CLIENT",
                "nodes": [
                    {
                        "id": "client",
                        "tag": "TKINTER",
                        "title": "GUI + 网络线程",
                        "sub": "输入 / recv / send",
                        "y": 250,
                    },
                ],
            },
            {
                "label": "SERVER",
                "nodes": [
                    {
                        "id": "server",
                        "tag": "TCP",
                        "title": "聊天服务器",
                        "sub": "连接管理",
                        "y": 250,
                        "focal": True,
                    }
                ],
            },
            {
                "label": "STATE",
                "nodes": [
                    {
                        "id": "broadcast",
                        "tag": "BROADCAST",
                        "title": "消息广播",
                        "sub": "在线客户端集合",
                        "y": 250,
                    }
                ],
            },
        ],
        [
            {"from": "client", "to": "server", "external": True},
            {"from": "server", "to": "broadcast", "focal": True},
        ],
    ),
    pipeline(
        "python-multiprocess-download",
        "多进程分块下载",
        "服务端提供文件与偏移量，多个进程各自下载分片，最后按顺序合并。",
        "每个分片独立校验，最终合并后再次计算全文摘要。",
        [
            n("01", "读取文件大小", ["HEAD / stat"]),
            n("02", "切分区间", ["offset + length"]),
            n("03", "多进程下载", ["Pool / Process"]),
            n("04", "落盘分片", ["part-0001"]),
            n("05", "合并并校验", ["MD5 / SHA-256"], True),
        ],
    ),
    pipeline(
        "python-multiprocessing-copy",
        "多进程文件复制",
        "大文件按块切分，由多个进程并行读取并写入独立目标区域。",
        "进程数不是越多越好，磁盘顺序写和内存占用要一起观察。",
        [
            n("01", "打开源文件", ["仅二进制读"]),
            n("02", "计算分块", ["块号 × 块大小"]),
            n("03", "进程池分配", ["Pool.map"]),
            n("04", "并行写入", ["seek + write"]),
            n("05", "大小 / 哈希校验", ["对比源文件"], True),
        ],
    ),
    pipeline(
        "python-multithread-download",
        "多线程分段下载",
        "HTTP Range 让多个线程下载同一文件的不同区间，主线程负责合并与校验。",
        "服务器不支持 Range 时，要回退单线程下载而不是静默拼接。",
        [
            n("01", "探测 Range", ["Accept-Ranges"]),
            n("02", "划分区间", ["start-end"]),
            n("03", "线程下载", ["requests / urllib"]),
            n("04", "等待全部完成", ["异常汇总"]),
            n("05", "合并校验", ["长度 / 哈希"], True),
        ],
    ),
    pipeline(
        "python-select-io",
        "select 非阻塞 IO 模型",
        "单线程用 select 监听多个 socket，只对就绪描述符执行 read/write。",
        "必须处理部分读写、连接关闭和 EAGAIN，不能假设一次 recv 收到完整消息。",
        [
            n("01", "监听 socket", ["bind / listen"]),
            n("02", "注册集合", ["readfds / writefds"]),
            n("03", "select 等待", ["超时 / 就绪"]),
            n("04", "处理事件", ["accept / recv / send"]),
            n("05", "维护连接状态", ["buffers / close"], True),
        ],
    ),
    arch(
        "python-socketserver-lab",
        "socketserver 并发模型",
        "请求处理器负责协议逻辑，服务器类负责监听和并发调度，存储层负责文件读写。",
        "并发提升前先确认协议解析、超时和异常关闭都正确。",
        [
            {
                "label": "CLIENTS",
                "nodes": [
                    {
                        "id": "clients",
                        "tag": "TCP",
                        "title": "多个客户端",
                        "sub": "并发请求",
                        "y": 250,
                    }
                ],
            },
            {
                "label": "SERVER",
                "nodes": [
                    {
                        "id": "handler",
                        "tag": "HANDLER",
                        "title": "Server + Handler",
                        "sub": "并发调度 / 协议解析",
                        "y": 250,
                        "focal": True,
                    },
                ],
            },
            {
                "label": "STORAGE",
                "nodes": [
                    {
                        "id": "storage",
                        "tag": "FILES",
                        "title": "文件目录",
                        "sub": "read / write / list",
                        "y": 250,
                    }
                ],
            },
        ],
        [
            {"from": "clients", "to": "handler", "external": True},
            {"from": "handler", "to": "storage", "focal": True},
        ],
    ),
    flow(
        "reverse-ctf-prompt-template",
        "Reverse / Misc 解题流程",
        "从文件识别开始，经过静态分析、动态验证和小样本复现，最后形成解题脚本。",
        "先确定文件类型和保护机制，再选择 IDA、调试器或脚本工具。",
        [
            n("01", "识别文件", ["file / strings / DIE"]),
            n("02", "静态分析", ["IDA / Ghidra / jadx"]),
            n("03", "定位校验", ["输入 → 比较"]),
            n("04", "动态验证", ["断点 / trace"]),
            n("05", "脚本复现", ["solve.py / flag"], True),
        ],
    ),
    flow(
        "seclists-guide",
        "SecLists 字典选择",
        "先从目标类型确定字典类别，再用工具加载并裁剪，最后看命中率。",
        "字典不是越大越好；目录、参数、用户名和密码使用不同列表。",
        [
            n("01", "明确目标", ["目录 / 参数 / 口令"]),
            n("02", "选目录", ["Discovery / Fuzzing"]),
            n("03", "裁剪规模", ["前缀 / 扩展名"]),
            n("04", "工具加载", ["dirsearch / ffuf"]),
            n("05", "评估命中", ["状态 / 长度 / 时间"], True),
        ],
    ),
    layers(
        "security-ctf-beginner-guide",
        "CTF 入门能力分层",
        "从基础工具和协议，到 Web 漏洞、脚本能力、比赛复盘和长期方向。",
        [
            {"index": "L5", "title": "赛道方向", "sub": "Web · Misc · Crypto · Reverse · Pwn", "note": "choose"},
            {"index": "L4", "title": "比赛方法", "sub": "读题 · 分工 · 时间盒 · 复盘", "note": "practice"},
            {"index": "L3", "title": "漏洞与算法", "sub": "OWASP · 密码学 · 逆向基础", "note": "core"},
            {"index": "L2", "title": "编程与脚本", "sub": "Python · HTTP · Shell · 调试", "note": "automate"},
            {"index": "L1", "title": "系统与网络", "sub": "Linux · TCP/IP · Web 基础", "note": "foundation", "focal": True},
        ],
    ),
    flow(
        "security-toolbox-guide",
        "安全工具工作流",
        "从授权边界开始，选择最小工具验证假设，再保留证据和失败分支。",
        "工具输出是候选事实，交叉验证后的结果才是结论。",
        [
            n("01", "确认授权", ["目标 / 时间 / 禁止项"]),
            n("02", "选择最小工具", ["只读优先"]),
            n("03", "执行与记录", ["命令 / 输出 / 时间"]),
            n("04", "第二证据复核", ["第二个工具"]),
            n("05", "归档与复盘", ["报告 / 失败分支"], True),
        ],
    ),
    flow(
        "sql-injection-detection",
        "SQL 注入检测决策",
        "从参数和响应差异出发，判断注入类型，再进行最小化证明和利用。",
        "先证明可控输入改变 SQL 语义，再谈数据库枚举。",
        [
            n("01", "找候选参数", ["GET / POST / Cookie"]),
            n("02", "基线请求", ["长度 / 时间 / 报错"]),
            n("03", "类型判断", ["联合 / 报错 / 布尔 / 时间"]),
            n("04", "最小验证", ["真 / 假条件"]),
            n("05", "数据库信息", ["version / user"]),
            n("06", "枚举并取证", ["表 / 字段 / flag"], True),
        ],
    ),
    flow(
        "ssti-template-injection",
        "SSTI 模板注入链",
        "用户输入进入模板引擎后，通过表达式求值逐步获得对象方法和命令执行能力。",
        "先证明模板表达式执行，再证明沙箱绕过和系统命令执行。",
        [
            n("01", "发现模板点", ["{{7*7}} / ${...}"]),
            n("02", "确认引擎", ["Jinja / Twig / Freemarker"]),
            n("03", "对象探测", ["config / self / globals"]),
            n("04", "沙箱绕过", ["属性链 / 过滤器"]),
            n("05", "命令执行", ["RCE / flag"], True),
        ],
    ),
    flow(
        "tgctf-2025-vite-game-plus",
        "Vite GAME Plus 文件读取",
        "前端资源暴露开发服务器入口，路径参数被 Vite 用于读取任意文件。",
        "先从前端 bundle 找请求路径，再用最小路径遍历验证。",
        [
            n("01", "前端资源", ["bundle / sourcemap"]),
            n("02", "发现接口", ["path / file 参数"]),
            n("03", "路径遍历", ["../ 编码"]),
            n("04", "读取源码", ["flag / 配置"]),
            n("05", "验证回显", ["固定文件内容"], True),
        ],
    ),
    flow(
        "vite-arbitrary-file-read",
        "Vite 任意文件读取",
        "开发服务器的文件服务接口未正确限制根目录，导致路径穿越读取敏感文件。",
        "开发服务不要暴露公网；修复要规范化路径并限制在项目根目录内。",
        [
            n("01", "确认 Vite", ["/@vite/client"]),
            n("02", "探测文件参数", ["路径 / 编码"]),
            n("03", "路径穿越", ["../ 多级"]),
            n("04", "读取敏感文件", ["配置 / 源码"]),
            n("05", "修复复核", ["root 限制"], True),
        ],
    ),
    flow(
        "web-ctf-prompt-template",
        "Web CTF 解题流程",
        "从页面请求与源码开始，按入口、过滤、利用和证据四步推进。",
        "先找可控输入，再找危险 sink，最后构造最短闭环。",
        [
            n("01", "页面与请求", ["路由 / Header / 参数"]),
            n("02", "源码审计", ["入口 / 过滤 / sink"]),
            n("03", "最小假设", ["单变量改动"]),
            n("04", "构造利用", ["编码 / 对象 / 协议"]),
            n("05", "回显与 flag", ["重复验证"], True),
        ],
    ),
    arch(
        "web-infrastructure-lateral",
        "Web 基础设施横向",
        "公网应用进入 DMZ，通过配置和凭据触及内部主机，再扩大权限。",
        "横向前先证明网络可达和凭据有效，避免把浏览器直连误当服务端能力。",
        [
            {
                "label": "PUBLIC",
                "nodes": [
                    {
                        "id": "entry",
                        "tag": "ENTRY",
                        "title": "公网 Web",
                        "sub": "上传 / SSRF / SQLi",
                        "y": 190,
                    },
                    {
                        "id": "config",
                        "tag": "LEAK",
                        "title": "配置泄露",
                        "sub": "数据库 / 密钥 / 内网地址",
                        "y": 310,
                    },
                ],
            },
            {
                "label": "DMZ",
                "nodes": [
                    {
                        "id": "webapp",
                        "tag": "APP",
                        "title": "Web 容器",
                        "sub": "RCE / 文件读取",
                        "y": 190,
                    },
                    {
                        "id": "redis",
                        "tag": "SERVICE",
                        "title": "Redis / DB",
                        "sub": "未授权 / 弱口令",
                        "y": 310,
                        "focal": True,
                    },
                ],
            },
            {
                "label": "INTERNAL",
                "nodes": [
                    {
                        "id": "host",
                        "tag": "HOST",
                        "title": "内部主机",
                        "sub": "凭据复用 / 隧道",
                        "y": 190,
                    },
                    {
                        "id": "impact",
                        "tag": "IMPACT",
                        "title": "权限与数据",
                        "sub": "root / 域控 / flag",
                        "y": 310,
                    },
                ],
            },
        ],
        [
            {"from": "entry", "to": "webapp"},
            {"from": "webapp", "to": "host"},
            {"from": "config", "to": "redis"},
            {"from": "redis", "to": "impact", "focal": True},
        ],
    ),
    flow(
        "xxe-injection",
        "XXE 外部实体与盲外带",
        "XML 实体在解析阶段读取本地文件或发起内网请求，再通过回显或外带通道输出。",
        "能回显时读文件，不能回显时优先构造 DNS/HTTP 外带通道。",
        [
            n("01", "可控 XML", ["DOCTYPE / 实体"]),
            n("02", "外部实体", ["file / http / ftp"]),
            n("03", "解析触发", ["XML parser"]),
            n("04", "内容输出", ["响应 / 报错"]),
            n("05", "盲外带", ["DNS / HTTP 监听"], True),
        ],
    ),
]
