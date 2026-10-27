// 实验3  RSA 加密解密算法（C++ 精简版）
//
// 编译：g++ -O2 -static rsa.cpp -o rsa_cpp.exe
// 只用 C++ 标准库，不依赖 GMP / OpenSSL，换台机器也能直接编译。
//
// 功能：
//   1. 生成密钥对：public.txt 只含 n、e；private.txt 含 n、d 及 CRT 参数
//   2. 密文按 n 的字节数分块输出，明文每块 nbytes-1 字节
//   3. 只保留交互菜单，不再接受任何命令行开关
//
// 安全须知：
//   1. 本程序仅用于教学演示，不能用于真实业务。
//   2. private.txt 中的私钥 d 是明文；进程内存中的 d 也是明文。
//      真实实现必须加密存储私钥，或使用硬件密码模块保护。
//   3. 真实实现应使用 PKCS#1 + OAEP 填充，并使用 CRT 加速解密。
//   4. 敏感内存应使用 memset_s / explicit_bzero 等安全函数擦除；
//      本教学版为了让代码保持简洁，没有实现内存擦除。
//   5. 本程序已移除 CLI 参数形式，避免私钥 d 出现在 shell history、
//      ps aux 或进程命令行中。请勿在后续版本重新加入
//      “-d <n> <d> <hex>” 之类的入口。
#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#ifdef _WIN32
#include <conio.h>
#include <windows.h>
#elif defined(__unix__) || defined(__APPLE__)
#include <termios.h>
#include <unistd.h>
#endif
namespace {

// ==================== 1. 大整数（基 2^32，小端存储） ====================
unsigned clz32(uint32_t x)
{
    if (x == 0)
        return 32;
#if defined(__GNUC__) || defined(__clang__)
    return static_cast<unsigned>(__builtin_clz(x));
#else
    unsigned n = 0;
    if ((x & 0xFFFF0000u) == 0) { n += 16; x <<= 16; }
    if ((x & 0xFF000000u) == 0) { n += 8;  x <<= 8;  }
    if ((x & 0xF0000000u) == 0) { n += 4;  x <<= 4;  }
    if ((x & 0xC0000000u) == 0) { n += 2;  x <<= 2;  }
    if ((x & 0x80000000u) == 0) { n += 1; }
    return n;
#endif
}
class BigUInt {
public:
    std::vector<uint32_t> a;   // 低位在前，去掉高位多余 0
    BigUInt() = default;
    explicit BigUInt(uint64_t v)
    {
        if (v) {
            a.push_back(static_cast<uint32_t>(v));
            if (v >> 32)
                a.push_back(static_cast<uint32_t>(v >> 32));
        }
    }
    bool zero() const { return a.empty(); }
    void trim()
    {
        while (!a.empty() && a.back() == 0)
            a.pop_back();
    }
    size_t bitLength() const
    {
        if (a.empty())
            return 0;
        return (a.size() - 1) * 32 + (32 - clz32(a.back()));
    }
    bool bit(size_t i) const
    {
        size_t w = i / 32;
        return w < a.size() && ((a[w] >> (i % 32)) & 1u);
    }
};
int compare(const BigUInt& x, const BigUInt& y)
{
    if (x.a.size() != y.a.size())
        return x.a.size() < y.a.size() ? -1 : 1;
    for (size_t i = x.a.size(); i-- > 0;)
        if (x.a[i] != y.a[i])
            return x.a[i] < y.a[i] ? -1 : 1;
    return 0;
}
bool operator==(const BigUInt& x, const BigUInt& y) { return compare(x, y) == 0; }
bool operator!=(const BigUInt& x, const BigUInt& y) { return compare(x, y) != 0; }
bool operator<(const BigUInt& x, const BigUInt& y)  { return compare(x, y) < 0; }
bool operator<=(const BigUInt& x, const BigUInt& y) { return compare(x, y) <= 0; }
bool operator>=(const BigUInt& x, const BigUInt& y) { return compare(x, y) >= 0; }
BigUInt operator+(const BigUInt& x, const BigUInt& y)
{
    BigUInt r;
    size_t n = std::max(x.a.size(), y.a.size());
    r.a.resize(n);
    uint64_t carry = 0;
    for (size_t i = 0; i < n; ++i) {
        uint64_t s = static_cast<uint64_t>(i < x.a.size() ? x.a[i] : 0)
                   + static_cast<uint64_t>(i < y.a.size() ? y.a[i] : 0)
                   + carry;
        r.a[i] = static_cast<uint32_t>(s);
        carry = s >> 32;
    }
    if (carry)
        r.a.push_back(static_cast<uint32_t>(carry));
    return r;
}
BigUInt operator-(const BigUInt& x, const BigUInt& y)   // 要求 x >= y
{
    if (x < y)
        throw std::runtime_error("大数减法出现负数");
    BigUInt r;
    r.a.resize(x.a.size());
    uint64_t borrow = 0;
    for (size_t i = 0; i < x.a.size(); ++i) {
        uint64_t yi = i < y.a.size() ? y.a[i] : 0;
        uint64_t sub = yi + borrow;
        uint64_t xi = x.a[i];
        r.a[i] = static_cast<uint32_t>(xi - sub);
        borrow = xi < sub ? 1 : 0;
    }
    r.trim();
    return r;
}
BigUInt operator*(const BigUInt& x, const BigUInt& y)
{
    if (x.zero() || y.zero())
        return BigUInt();
    BigUInt r;
    r.a.assign(x.a.size() + y.a.size(), 0);
    for (size_t i = 0; i < x.a.size(); ++i) {
        uint64_t carry = 0;
        for (size_t j = 0; j < y.a.size(); ++j) {
            uint64_t cur = static_cast<uint64_t>(x.a[i]) * y.a[j] + r.a[i + j] + carry;
            r.a[i + j] = static_cast<uint32_t>(cur);
            carry = cur >> 32;
        }
        r.a[i + y.a.size()] = static_cast<uint32_t>(carry);
    }
    r.trim();
    return r;
}
BigUInt mulSmall(const BigUInt& x, uint32_t m)
{
    BigUInt r;
    r.a.resize(x.a.size() + 1, 0);
    uint64_t carry = 0;
    for (size_t i = 0; i < x.a.size(); ++i) {
        uint64_t cur = static_cast<uint64_t>(x.a[i]) * m + carry;
        r.a[i] = static_cast<uint32_t>(cur);
        carry = cur >> 32;
    }
    r.a.back() = static_cast<uint32_t>(carry);
    r.trim();
    return r;
}
uint32_t divSmall(BigUInt& x, uint32_t d)   // 原地除以小整数，返回余数
{
    uint64_t rem = 0;
    for (size_t i = x.a.size(); i-- > 0;) {
        uint64_t cur = (rem << 32) | x.a[i];
        x.a[i] = static_cast<uint32_t>(cur / d);
        rem = cur % d;
    }
    x.trim();
    return static_cast<uint32_t>(rem);
}
BigUInt shiftLeft(const BigUInt& x, unsigned bits)
{
    if (x.zero())
        return BigUInt();
    unsigned words = bits / 32, b = bits % 32;
    BigUInt r;
    r.a.assign(x.a.size() + words + 1, 0);
    uint64_t carry = 0;
    for (size_t i = 0; i < x.a.size(); ++i) {
        uint64_t cur = (static_cast<uint64_t>(x.a[i]) << b) | carry;
        r.a[i + words] = static_cast<uint32_t>(cur);
        carry = cur >> 32;
    }
    r.a[x.a.size() + words] = static_cast<uint32_t>(carry);
    r.trim();
    return r;
}
BigUInt shiftRight(const BigUInt& x, unsigned bits)
{
    unsigned words = bits / 32, b = bits % 32;
    if (words >= x.a.size())
        return BigUInt();
    BigUInt r;
    r.a.assign(x.a.size() - words, 0);
    for (size_t i = 0; i < r.a.size(); ++i) {
        uint32_t lo = x.a[i + words];
        uint32_t hi = (i + words + 1 < x.a.size()) ? x.a[i + words + 1] : 0;
        r.a[i] = b ? ((lo >> b) | (hi << (32 - b))) : lo;
    }
    r.trim();
    return r;
}
// Knuth 除法：返回 {商, 余数}，复杂度 O(n^2)，比原版逐位长除法快得多
std::pair<BigUInt, BigUInt> divmod(const BigUInt& u, const BigUInt& v)
{
    if (v.zero())
        throw std::runtime_error("除以零");
    if (u < v)
        return {BigUInt(), u};
    if (v.a.size() == 1) {
        BigUInt q = u;
        uint32_t r = divSmall(q, v.a[0]);
        return {q, BigUInt(r)};
    }
    const size_t n = v.a.size();
    const unsigned shift = clz32(v.a.back());
    BigUInt vn = shiftLeft(v, shift);
    BigUInt un = shiftLeft(u, shift);
    un.a.resize(u.a.size() + 1, 0);
    const size_t m = u.a.size() - n;
    std::vector<uint32_t> q(m + 1, 0);
    const uint64_t B = 1ULL << 32;
    for (size_t jj = m + 1; jj-- > 0;) {
        const size_t j = jj;
        uint64_t num = (static_cast<uint64_t>(un.a[j + n]) << 32) | un.a[j + n - 1];
        uint64_t qhat = num / vn.a[n - 1];
        uint64_t rhat = num % vn.a[n - 1];
        while (qhat >= B ||
               qhat * vn.a[n - 2] > ((rhat << 32) | un.a[j + n - 2])) {
            --qhat;
            rhat += vn.a[n - 1];
            if (rhat >= B)
                break;
        }
        uint64_t carry = 0, borrow = 0;
        for (size_t i = 0; i < n; ++i) {
            uint64_t p = qhat * vn.a[i] + carry;
            carry = p >> 32;
            uint64_t sub = static_cast<uint32_t>(p) + borrow;
            uint64_t ui = un.a[j + i];
            un.a[j + i] = static_cast<uint32_t>(ui - sub);
            borrow = ui < sub ? 1 : 0;
        }
        uint64_t sub = carry + borrow;
        bool negative = un.a[j + n] < sub;
        un.a[j + n] = static_cast<uint32_t>(static_cast<uint64_t>(un.a[j + n]) - sub);
        if (negative) {
            --qhat;
            uint64_t c2 = 0;
            for (size_t i = 0; i < n; ++i) {
                uint64_t s = static_cast<uint64_t>(un.a[j + i]) + vn.a[i] + c2;
                un.a[j + i] = static_cast<uint32_t>(s);
                c2 = s >> 32;
            }
            un.a[j + n] = static_cast<uint32_t>(static_cast<uint64_t>(un.a[j + n]) + c2);
        }
        q[j] = static_cast<uint32_t>(qhat);
    }
    BigUInt quo;
    quo.a = std::move(q);
    quo.trim();
    BigUInt rem;
    rem.a.assign(un.a.begin(), un.a.begin() + static_cast<std::ptrdiff_t>(n));
    rem.trim();
    rem = shiftRight(rem, shift);
    return {quo, rem};
}
BigUInt operator%(const BigUInt& x, const BigUInt& y) { return divmod(x, y).second; }

// ==================== 2. 进制 / 字节转换 ====================
BigUInt fromDecimal(const std::string& s)
{
    if (s.empty())
        throw std::runtime_error("空数字");
    BigUInt x;
    for (char ch : s) {
        if (ch < '0' || ch > '9')
            throw std::runtime_error("不是合法的十进制数：" + s);
        x = mulSmall(x, 10);
        x = x + BigUInt(static_cast<uint64_t>(ch - '0'));
    }
    return x;
}
std::string toDecimal(const BigUInt& x)
{
    if (x.zero())
        return "0";
    BigUInt t = x;
    std::string s;
    while (!t.zero())
        s.push_back(static_cast<char>('0' + divSmall(t, 10)));
    std::reverse(s.begin(), s.end());
    return s;
}
BigUInt fromBytes(const std::vector<uint8_t>& b)
{
    BigUInt x;
    x.a.assign((b.size() + 3) / 4, 0);
    for (size_t i = 0; i < b.size(); ++i) {
        size_t j = b.size() - 1 - i;      // 大端：b[0] 是最高字节
        x.a[j / 4] |= static_cast<uint32_t>(b[i]) << (8 * (j % 4));
    }
    x.trim();
    return x;
}
std::vector<uint8_t> toBytes(const BigUInt& x, size_t fixed = 0)
{
    size_t n = (x.bitLength() + 7) / 8;
    if (n == 0)
        n = 1;
    if (fixed && fixed < n)
        throw std::runtime_error("目标字节数太小");
    size_t len = fixed ? fixed : n;
    std::vector<uint8_t> out(len, 0);
    size_t off = len - n;
    for (size_t i = 0; i < n; ++i) {
        size_t j = n - 1 - i;
        out[off + i] = static_cast<uint8_t>((x.a[j / 4] >> (8 * (j % 4))) & 0xFF);
    }
    return out;
}
uint32_t modSmall(const BigUInt& x, uint32_t m)
{
    uint64_t r = 0;
    for (size_t i = x.a.size(); i-- > 0;)
        r = ((r << 32) | x.a[i]) % m;
    return static_cast<uint32_t>(r);
}

// ==================== 3. 数论：模幂、模逆、素数 ====================
// 原平方-乘法实现，保留作为 modPowFast 的对拍基准，同时供 isPrime / modInverse 等内部使用。
BigUInt modPow(const BigUInt& base, const BigUInt& exp, const BigUInt& mod)
{
    if (mod.zero())
        throw std::runtime_error("模数不能为 0");
    if (mod == BigUInt(1))
        return BigUInt();
    BigUInt result(1), b = base % mod;
    for (size_t i = exp.bitLength(); i-- > 0;) {
        result = (result * result) % mod;
        if (exp.bit(i))
            result = (result * b) % mod;
    }
    return result;
}
// 4-bit 固定窗口模幂：预计算 0..15 号表，每次处理 4 位。
BigUInt modPowWindow(const BigUInt& base, const BigUInt& exp, const BigUInt& mod)
{
    if (mod.zero())
        throw std::runtime_error("模数不能为 0");
    if (mod == BigUInt(1))
        return BigUInt();
    BigUInt tbl[16];
    tbl[0] = BigUInt(1);
    tbl[1] = base % mod;
    for (unsigned i = 2; i < 16; ++i)
        tbl[i] = (tbl[i - 1] * tbl[1]) % mod;
    auto nibble = [&](size_t g) -> unsigned {
        unsigned v = 0;
        size_t start = g * 4;
        for (unsigned k = 0; k < 4; ++k)
            if (exp.bit(start + k))
                v |= 1u << k;
        return v;
    };
    size_t groups = (exp.bitLength() + 3) / 4;
    while (groups > 0 && nibble(groups - 1) == 0)
        --groups;
    if (groups == 0)
        return tbl[0] % mod;
    BigUInt result = tbl[nibble(groups - 1)];
    for (size_t i = groups - 1; i-- > 0;) {
        for (int k = 0; k < 4; ++k)
            result = (result * result) % mod;
        unsigned v = nibble(i);
        if (v)
            result = (result * tbl[v]) % mod;
    }
    return result;
}
BigUInt modPowFast(const BigUInt& base, const BigUInt& exp, const BigUInt& mod)
{
    return modPowWindow(base, exp, mod);
}
BigUInt gcd(BigUInt a, BigUInt b)
{
    while (!b.zero()) {
        BigUInt r = a % b;
        a = b;
        b = r;
    }
    return a;
}
BigUInt modInverse(const BigUInt& a, const BigUInt& m)
{
    BigUInt r0 = m, r1 = a % m;
    BigUInt t0(0), t1(1);
    while (!r1.zero()) {
        std::pair<BigUInt, BigUInt> qr = divmod(r0, r1);
        const BigUInt& q = qr.first;
        const BigUInt& r = qr.second;
        BigUInt prod = (q * t1) % m;
        BigUInt t2 = (t0 >= prod) ? t0 - prod : m - (prod - t0);
        r0 = r1; r1 = r;
        t0 = t1; t1 = t2;
    }
    if (r0 != BigUInt(1))
        throw std::runtime_error("该数在模 m 下没有逆元");
    return t0 % m;
}
const std::vector<uint32_t>& smallPrimes()
{
    static const std::vector<uint32_t> primes = [] {
        const int N = 2000;
        std::vector<bool> is(N + 1, true);
        is[0] = is[1] = false;
        for (int i = 2; i * i <= N; ++i)
            if (is[i])
                for (int j = i * i; j <= N; j += i)
                    is[j] = false;
        std::vector<uint32_t> v;
        for (int i = 2; i <= N; ++i)
            if (is[i])
                v.push_back(static_cast<uint32_t>(i));
        return v;
    }();
    return primes;
}
bool isPrime(const BigUInt& n)
{
    if (n < BigUInt(2))
        return false;
    for (uint32_t p : smallPrimes()) {
        if (n == BigUInt(p))
            return true;
        if (modSmall(n, p) == 0)
            return false;
    }
    BigUInt n1 = n - BigUInt(1);
    BigUInt d = n1;
    unsigned s = 0;
    while (!d.bit(0)) {
        d = shiftRight(d, 1);
        ++s;
    }
    static const uint32_t bases[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (uint32_t b : bases) {
        if (n <= BigUInt(b))
            continue;
        BigUInt x = modPow(BigUInt(b), d, n);
        if (x == BigUInt(1) || x == n1)
            continue;
        bool passed = false;
        for (unsigned r = 1; r < s; ++r) {
            x = (x * x) % n;
            if (x == n1) { passed = true; break; }
            if (x == BigUInt(1)) break;
        }
        if (!passed)
            return false;
    }
    return true;
}
std::mt19937_64& rng()
{
    static std::mt19937_64 g(std::random_device{}());
    return g;
}
BigUInt randomOdd(int bits)
{
    std::uniform_int_distribution<uint32_t> dist;
    BigUInt x;
    x.a.resize((bits + 31) / 32);
    for (auto& w : x.a)
        w = dist(rng());
    unsigned top = bits % 32;
    if (top)
        x.a.back() &= (1u << top) - 1;
    x.a.back() |= 1u << ((bits - 1) % 32);
    x.a[0] |= 1u;
    x.trim();
    return x;
}
// 仅供 selfTest 对拍使用，不参与主流程。
BigUInt randomPrimeRef(int bits)
{
    for (;;) {
        BigUInt c = randomOdd(bits);
        if (isPrime(c))
            return c;
    }
}
// isPrime 内部已做小素数预筛；此处只做增量搜索，避免重复预筛。
// 若要进一步加速需引入 wheel 30，教学版为可读性不做。
BigUInt randomPrimeFast(int bits)
{
    BigUInt c = randomOdd(bits);
    for (;;) {
        if (isPrime(c))
            return c;
        c = c + BigUInt(2);
        if (c.bitLength() != static_cast<size_t>(bits))
            c = randomOdd(bits);
    }
}
// ==================== 4. RSA 密钥与分组加解密 ====================
// 教学版说明：Key::d 以及 BigUInt::a 中保存的私钥都是明文。
// 本程序没有做敏感内存擦除，真实实现应在 Key 析构或作用域结束时
// 用 std::fill / memset_s / explicit_bzero 清零，并避免不必要的拷贝。
struct Key {
    BigUInt n, e, d;
    BigUInt p, q, dp, dq, qinv;   // CRT 参数，明文持有，安全级别等同 d
    bool hasE = false, hasD = false, hasCRT = false;
};
void generateKey(Key& k, int bits, BigUInt& p, BigUInt& q)
{
    k.e = BigUInt(65537);
    k.hasE = true;
    unsigned half = static_cast<unsigned>(bits / 2);
    unsigned gapBits = half > 100 ? half - 100 : 0;
    BigUInt minGap = shiftLeft(BigUInt(1), gapBits);  // 100 为经验值，教学用
    for (;;) {
        // 两次独立随机起点，不能从 p+2 继续找 q，否则两素数过近，
        // 容易被 Fermat 分解攻破。
        p = randomPrimeFast(bits / 2);
        q = randomPrimeFast(bits / 2);
        if (p == q)
            continue;
        BigUInt diff = (p >= q) ? p - q : q - p;
        if (diff <= minGap)
            continue;
        k.n = p * q;
        BigUInt phi = (p - BigUInt(1)) * (q - BigUInt(1));
        if (gcd(k.e, phi) != BigUInt(1))
            continue;
        k.d = modInverse(k.e, phi);
        k.p = p;
        k.q = q;
        k.dp = k.d % (p - BigUInt(1));
        k.dq = k.d % (q - BigUInt(1));
        k.qinv = modInverse(q, p);
        k.hasD = true;
        k.hasCRT = true;
        return;
    }
}
std::vector<uint8_t> rsaEncrypt(const std::vector<uint8_t>& in,
                                const BigUInt& n, const BigUInt& e)
{
    size_t nbytes = (n.bitLength() + 7) / 8;
    if (nbytes < 2)
        throw std::runtime_error("模数 n 太小，无法加密");
    size_t block = nbytes - 1;          // 保证明文块 < n
    std::vector<uint8_t> out;
    out.reserve(((in.size() + block - 1) / block) * nbytes);
    for (size_t i = 0; i < in.size(); i += block) {
        size_t len = std::min(block, in.size() - i);
        std::vector<uint8_t> chunk(in.begin() + static_cast<std::ptrdiff_t>(i),
                                   in.begin() + static_cast<std::ptrdiff_t>(i + len));
        BigUInt m = fromBytes(chunk);
        BigUInt c = (e.bitLength() < 128) ? modPow(m, e, n) : modPowFast(m, e, n);
        std::vector<uint8_t> cb = toBytes(c, nbytes);
        out.insert(out.end(), cb.begin(), cb.end());
    }
    return out;
}
// 无 CRT 参数时的兼容解密路径（原实现），同时作为 rsaDecryptCRT 的对拍基准。
std::vector<uint8_t> rsaDecryptPlain(const std::vector<uint8_t>& in,
                                     const BigUInt& n, const BigUInt& d)
{
    size_t nbytes = (n.bitLength() + 7) / 8;
    if (nbytes < 2)
        throw std::runtime_error("模数 n 太小");
    if (in.size() % nbytes != 0)
        throw std::runtime_error("密文长度必须是 n 字节数的整数倍");
    std::vector<uint8_t> out;
    for (size_t i = 0; i < in.size(); i += nbytes) {
        std::vector<uint8_t> chunk(in.begin() + static_cast<std::ptrdiff_t>(i),
                                   in.begin() + static_cast<std::ptrdiff_t>(i + nbytes));
        BigUInt m = modPow(fromBytes(chunk), d, n);
        std::vector<uint8_t> mb = toBytes(m);
        size_t start = 0;
        while (start + 1 < mb.size() && mb[start] == 0)
            ++start;
        out.insert(out.end(), mb.begin() + static_cast<std::ptrdiff_t>(start), mb.end());
    }
    return out;
}
// CRT 解密主路径：m1 = c^dp mod p，m2 = c^dq mod q，
// h = qinv*(m1-m2) mod p，m = m2 + h*q。
std::vector<uint8_t> rsaDecryptCRT(const std::vector<uint8_t>& in,
                                   const BigUInt& n,
                                   const BigUInt& p, const BigUInt& q,
                                   const BigUInt& dp, const BigUInt& dq,
                                   const BigUInt& qinv)
{
    size_t nbytes = (n.bitLength() + 7) / 8;
    if (nbytes < 2)
        throw std::runtime_error("模数 n 太小");
    if (in.size() % nbytes != 0)
        throw std::runtime_error("密文长度必须是 n 字节数的整数倍");
    std::vector<uint8_t> out;
    for (size_t i = 0; i < in.size(); i += nbytes) {
        std::vector<uint8_t> chunk(in.begin() + static_cast<std::ptrdiff_t>(i),
                                   in.begin() + static_cast<std::ptrdiff_t>(i + nbytes));
        BigUInt c = fromBytes(chunk);
        BigUInt m1 = modPowFast(c, dp, p);
        BigUInt m2 = modPowFast(c, dq, q);
        BigUInt diff;
        if (m1 >= m2) {
            diff = (m1 - m2) % p;
        } else {
            BigUInt t = (m2 - m1) % p;
            diff = t.zero() ? BigUInt() : p - t;
        }
        BigUInt h = (qinv * diff) % p;
        BigUInt m = m2 + h * q;
        std::vector<uint8_t> mb = toBytes(m);
        size_t start = 0;
        while (start + 1 < mb.size() && mb[start] == 0)
            ++start;
        out.insert(out.end(), mb.begin() + static_cast<std::ptrdiff_t>(start), mb.end());
    }
    return out;
}
// ==================== 5. 文件与输入输出 ====================
std::string trim(const std::string& s)
{
    size_t b = 0, e = s.size();
    while (b < e && (s[b] == ' ' || s[b] == '\t' || s[b] == '\r'))
        ++b;
    while (e > b && (s[e - 1] == ' ' || s[e - 1] == '\t' || s[e - 1] == '\r'))
        --e;
    return s.substr(b, e - b);
}
std::string readLine(const std::string& prompt = "")
{
    if (!prompt.empty())
        std::cout << prompt << std::flush;
    std::string s;
    if (!std::getline(std::cin, s))
        throw std::runtime_error("输入结束");
    if (!s.empty() && s.back() == '\r')
        s.pop_back();
    return s;
}
// 无回显读取敏感字符串（用于私钥 d）。
// Windows 用 _getch 逐字符读取并回显 '*'；POSIX 关闭 ECHO。
// 其他平台退化为 std::getline，并明确警告。
std::string readSecret(const std::string& prompt)
{
    std::cout << prompt << std::flush;
#ifdef _WIN32
    std::string s;
    for (;;) {
        int ch = _getch();
        if (ch == '\r' || ch == '\n')
            break;
        if (ch == 3) {                 // Ctrl+C
            std::cout << "\n";
            throw std::runtime_error("输入已取消");
        }
        if (ch == 8 || ch == 127) {    // Backspace
            if (!s.empty()) {
                s.pop_back();
                std::cout << "\b \b";
            }
        } else if (ch >= 32 && ch < 127) {
            s.push_back(static_cast<char>(ch));
            std::cout << '*';
        }
    }
    std::cout << "\n";
    return s;
#elif defined(__unix__) || defined(__APPLE__)
    // POSIX 分支用 tcgetattr/tcsetattr 成对恢复终端状态。
    // 真实工程建议封装 RAII 守卫，确保异常/提前返回时也恢复 ECHO。
    termios oldt{};
    if (tcgetattr(STDIN_FILENO, &oldt) != 0) {
        std::cerr << "[警告] 当前平台不支持无回显输入，d 会显示在终端上\n";
        return readLine();
    }
    termios newt = oldt;
    newt.c_lflag &= ~static_cast<tcflag_t>(ECHO);
    if (tcsetattr(STDIN_FILENO, TCSANOW, &newt) != 0) {
        std::cerr << "[警告] 当前平台不支持无回显输入，d 会显示在终端上\n";
        return readLine();
    }
    std::string s;
    std::getline(std::cin, s);
    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    std::cout << "\n";
    if (!std::cin)
        throw std::runtime_error("输入结束");
    if (!s.empty() && s.back() == '\r')
        s.pop_back();
    return s;
#else
    std::cerr << "[警告] 当前平台不支持无回显输入，d 会显示在终端上\n";
    return readLine();
#endif
}
bool fileExists(const std::string& path)
{
    std::ifstream f(path);
    return static_cast<bool>(f);
}
void savePublicKey(const std::string& path, const Key& k)
{
    std::ofstream f(path);
    if (!f)
        throw std::runtime_error("无法写入密钥文件：" + path);
    f << "# RSA 公钥文件（n、e 为十进制）\n"
      << "n = " << toDecimal(k.n) << "\n"
      << "e = " << toDecimal(k.e) << "\n";
    std::cout << " 公钥已保存到 " << path << "\n";
}
void savePrivateKey(const std::string& path, const Key& k)
{
    std::ofstream f(path);
    if (!f)
        throw std::runtime_error("无法写入密钥文件：" + path);
    f << "# 警告：明文私钥，仅用于教学演示，真实环境必须加密存储或使用硬件保护；"
         "CRT 参数用于加速解密，同样属于私钥材料，安全级别等同 d\n"
      << "n = " << toDecimal(k.n) << "\n"
      << "d = " << toDecimal(k.d) << "\n"
      << "p = " << toDecimal(k.p) << "\n"
      << "q = " << toDecimal(k.q) << "\n"
      << "dp = " << toDecimal(k.dp) << "\n"
      << "dq = " << toDecimal(k.dq) << "\n"
      << "qinv = " << toDecimal(k.qinv) << "\n";
    std::cout << " 私钥已保存到 " << path << "（明文，仅教学演示）\n";
}
// loadPrivate=false 时明确忽略 d 及全部 CRT 私钥字段，供加密路径和“查看文件”使用。
Key loadKey(const std::string& path, bool loadPrivate = true)
{
    std::ifstream f(path);
    if (!f)
        throw std::runtime_error("无法打开密钥文件：" + path);
    Key k;
    std::string line;
    int lineno = 0;
    bool gotP = false, gotQ = false, gotDp = false, gotDq = false, gotQinv = false;
    while (std::getline(f, line)) {
        ++lineno;
        line = trim(line);
        if (line.empty() || line[0] == '#')
            continue;
        size_t eq = line.find('=');
        if (eq == std::string::npos)
            throw std::runtime_error("密钥文件第 " + std::to_string(lineno) + " 行缺少等号");
        std::string name = trim(line.substr(0, eq));
        for (char& c : name)
            c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        bool privateField = (name == "d" || name == "p" || name == "q"
                             || name == "dp" || name == "dq" || name == "qinv");
        if (privateField && !loadPrivate)
            continue;                  // 公钥路径不读取任何私钥材料
        std::string value = trim(line.substr(eq + 1));
        if (name == "n") {
            k.n = fromDecimal(value);
        } else if (name == "e") {
            k.e = fromDecimal(value);
            k.hasE = true;
        } else if (name == "d") {
            if (loadPrivate) {
                k.d = fromDecimal(value);
                k.hasD = true;
            }
        } else if (name == "p") {
            k.p = fromDecimal(value);
            gotP = true;
        } else if (name == "q") {
            k.q = fromDecimal(value);
            gotQ = true;
        } else if (name == "dp") {
            k.dp = fromDecimal(value);
            gotDp = true;
        } else if (name == "dq") {
            k.dq = fromDecimal(value);
            gotDq = true;
        } else if (name == "qinv") {
            k.qinv = fromDecimal(value);
            gotQinv = true;
        } else {
            throw std::runtime_error("密钥文件第 " + std::to_string(lineno)
                                     + " 行：未知键名 " + name);
        }
    }
    k.hasCRT = gotP && gotQ && gotDp && gotDq && gotQinv;
    return k;
}
// 只检查文件中是否存在 d = ... 行，不解析 d 的数值。
bool fileHasPrivateKey(const std::string& path)
{
    std::ifstream f(path);
    if (!f)
        return false;
    std::string line;
    while (std::getline(f, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#')
            continue;
        size_t eq = line.find('=');
        if (eq == std::string::npos)
            continue;
        std::string name = trim(line.substr(0, eq));
        for (char& c : name)
            c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        if (name == "d")
            return true;
    }
    return false;
}
// 只检查 CRT 参数字段是否存在，不解析具体数值。
bool fileHasCRTParams(const std::string& path)
{
    std::ifstream f(path);
    if (!f)
        return false;
    std::string line;
    while (std::getline(f, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#')
            continue;
        size_t eq = line.find('=');
        if (eq == std::string::npos)
            continue;
        std::string name = trim(line.substr(0, eq));
        for (char& c : name)
            c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        if (name == "p" || name == "q" || name == "dp" || name == "dq" || name == "qinv")
            return true;
    }
    return false;
}
void printHex(const std::vector<uint8_t>& v)
{
    static const char* H = "0123456789ABCDEF";
    for (uint8_t b : v) {
        std::cout << H[b >> 4] << H[b & 0x0F];
    }
}
std::vector<uint8_t> parseHex(const std::string& s)
{
    if (s.empty() || s.size() % 2 != 0)
        throw std::runtime_error("十六进制串长度必须是偶数且不能为空");
    auto nib = [](char c) -> int {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return -1;
    };
    std::vector<uint8_t> out(s.size() / 2);
    for (size_t i = 0; i < out.size(); ++i) {
        int hi = nib(s[2 * i]), lo = nib(s[2 * i + 1]);
        if (hi < 0 || lo < 0)
            throw std::runtime_error("不是合法的十六进制串");
        out[i] = static_cast<uint8_t>((hi << 4) | lo);
    }
    return out;
}
bool isText(const std::vector<uint8_t>& b)
{
    size_t i = 0;
    while (i < b.size()) {
        uint8_t c = b[i];
        if (c < 0x80) {
            if (c < 0x20 || c == 0x7F)
                return false;
            ++i;
            continue;
        }
        int n;
        if ((c & 0xE0) == 0xC0)      n = 1;
        else if ((c & 0xF0) == 0xE0) n = 2;
        else if ((c & 0xF8) == 0xF0) n = 3;
        else return false;
        if (i + static_cast<size_t>(n) >= b.size())
            return false;
        for (int k = 1; k <= n; ++k)
            if ((b[i + k] & 0xC0) != 0x80)
                return false;
        i += static_cast<size_t>(n) + 1;
    }
    return true;
}
void printPlain(const std::vector<uint8_t>& b)
{
    if (isText(b)) {
        std::cout << " 明文(字符串) = \"";
        std::cout.write(reinterpret_cast<const char*>(b.data()),
                        static_cast<std::streamsize>(b.size()));
        std::cout << "\"\n";
    }
    std::cout << " 明文(HEX)    = ";
    printHex(b);
    std::cout << "\n";
}

// ==================== 6. 功能流程 ====================
void printPublicFields(const Key& k)
{
    std::cout << " n = " << toDecimal(k.n) << "\n";
    if (k.hasE)
        std::cout << " e = " << toDecimal(k.e) << "\n";
}
void keygenFlow(int bits)
{
    if (bits < 32 || bits > 1024 || bits % 2 != 0)
        throw std::runtime_error("密钥位数必须是 32~1024 之间的偶数");
    auto t0 = std::chrono::steady_clock::now();
    Key k;
    BigUInt p, q;
    generateKey(k, bits, p, q);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                  std::chrono::steady_clock::now() - t0).count();
    std::cout << "\n---- 生成 RSA 密钥对（" << bits << " 位）----\n";
    std::cout << " 素数 p     = " << toDecimal(p) << "\n 素数 q     = " << toDecimal(q) << "\n";
    std::cout << " 模数 n     = " << toDecimal(k.n) << "\n 公钥指数 e = " << toDecimal(k.e) << "\n";
    std::cout << " 私钥指数 d = [已写入 private.txt，不在屏幕显示]\n"
              << " 用时       = " << ms << " ms\n";
    savePublicKey("public.txt", k);
    savePrivateKey("private.txt", k);
    std::cout << " 注意：private.txt 中保存的是明文私钥，仅用于教学演示。\n";
    std::cout << " 如需查看 d，请自行打开 private.txt（明文，仅教学演示）。\n";
}
void encryptFlow(const BigUInt& n, const BigUInt& e,
                 const std::vector<uint8_t>& plain)
{
    if (plain.empty())
        throw std::runtime_error("明文不能为空");
    std::vector<uint8_t> cipher = rsaEncrypt(plain, n, e);
    size_t nbytes = (n.bitLength() + 7) / 8;
    size_t block = nbytes - 1;
    std::cout << "公钥 (n,e)：n = " << toDecimal(n) << "\n";
    std::cout << "明文 " << plain.size() << " 字节，分组 " << block
              << " 字节，共 " << ((plain.size() + block - 1) / block)
              << " 个分组，密文 " << cipher.size() << " 字节\n";
    std::cout << "密文(HEX) = ";
    printHex(cipher);
    std::cout << "\n";
}
// 注意：Key 中的 d 和 CRT 参数都是明文私钥，本教学版不做内存擦除。
void decryptFlow(const Key& k, const std::vector<uint8_t>& cipher)
{
    // 手动输入 d 的场景没有 CRT 参数，走 Plain 兼容路径；
    // private.txt / key.txt（含 CRT 参数）走 CRT 加速路径。
    std::vector<uint8_t> plain = k.hasCRT
        ? rsaDecryptCRT(cipher, k.n, k.p, k.q, k.dp, k.dq, k.qinv)
        : rsaDecryptPlain(cipher, k.n, k.d);
    std::cout << "私钥 (n,d)：n = " << toDecimal(k.n) << "\n";
    std::cout << "密文 " << cipher.size() << " 字节，还原明文 "
              << plain.size() << " 字节\n";
    printPlain(plain);
}
int selfTest()
{
    int fail = 0;
    auto check = [&](bool ok, const std::string& what) {
        std::cout << " " << what << (ok ? "  [通过]\n" : "  [失败]\n");
        if (!ok)
            fail = 1;
    };
    std::cout << "\n---- RSA 核心运算自检 ----\n";
    bool divOk = true;
    for (int i = 0; i < 100; ++i) {
        BigUInt a = randomOdd(512);
        BigUInt b = randomOdd(256);
        std::pair<BigUInt, BigUInt> qr = divmod(a, b);
        const BigUInt& qq = qr.first;
        const BigUInt& rr = qr.second;
        if (qq * b + rr != a || rr >= b) {
            divOk = false;
            break;
        }
    }
    check(divOk, "随机大数除法 100 组：q*b+r == a 且 r < b");
    bool invOk = true;
    for (int i = 0; i < 50;) {
        BigUInt m = randomOdd(256);
        BigUInt a = randomOdd(256) % m;
        if (a.zero() || gcd(a, m) != BigUInt(1))
            continue;
        BigUInt inv = modInverse(a, m);
        if ((a * inv) % m != BigUInt(1)) {
            invOk = false;
            break;
        }
        ++i;
    }
    check(invOk, "随机模逆 50 组：a * a^-1 mod m = 1");
    bool powOk = true;
    for (int i = 0; i < 20; ++i) {
        BigUInt m = randomOdd(256);
        BigUInt a = randomOdd(256) % m;
        BigUInt e1 = randomOdd(64), e2 = randomOdd(64);
        BigUInt left = modPow(a, e1 + e2, m);
        BigUInt right = (modPow(a, e1, m) * modPow(a, e2, m)) % m;
        if (left != right) {
            powOk = false;
            break;
        }
    }
    check(powOk, "模幂性质 20 组：a^(e1+e2) = a^e1 * a^e2 (mod m)");
    Key k;
    BigUInt p, q2;
    generateKey(k, 64, p, q2);
    BigUInt phi = (p - BigUInt(1)) * (q2 - BigUInt(1));
    check((k.e * k.d) % phi == BigUInt(1), "随机 64 位密钥：d*e mod φ(n) = 1");
    std::vector<uint8_t> pt = {'R', 'S', 'A'};
    std::vector<uint8_t> ct = rsaEncrypt(pt, k.n, k.e);
    std::vector<uint8_t> rt = rsaDecryptPlain(ct, k.n, k.d);
    check(rt == pt, "加解密往返：\"RSA\" 还原正确");
    // ---------- 4.1 新算法对拍 ----------
    bool powCmpOk = true;
    auto powCase = [&](const BigUInt& a, const BigUInt& e, const BigUInt& m) {
        if (modPow(a, e, m) != modPowFast(a, e, m))
            powCmpOk = false;
    };
    powCase(BigUInt(0), BigUInt(0), BigUInt(7));
    powCase(BigUInt(0), BigUInt(5), BigUInt(7));
    powCase(BigUInt(1), BigUInt(12345), BigUInt(7919));
    powCase(BigUInt(123456), BigUInt(0), BigUInt(65537));
    powCase(BigUInt(123456), BigUInt(1), BigUInt(65537));
    powCase(BigUInt(5), BigUInt(3), BigUInt(2));
    powCase(BigUInt(2), BigUInt(10), BigUInt(3));
    for (int i = 0; i < 100; ++i) {
        BigUInt a = randomOdd(256);
        BigUInt e = randomOdd(256);
        BigUInt m = randomOdd(256);
        powCase(a, e, m);
    }
    check(powCmpOk, "窗口模幂对拍 100 组 + 边界：modPow == modPowFast");
    bool primeOk = true;
    for (int i = 0; i < 20; ++i) {
        BigUInt pf = randomPrimeFast(128);
        BigUInt pr = randomPrimeRef(128);
        if (!isPrime(pf) || !isPrime(pr))
            primeOk = false;
    }
    check(primeOk, "素数生成对拍：fast/ref 各 20 个 128bit 素数均为素数");
    BigUInt pMix = randomPrimeFast(256), qMix = randomPrimeRef(256);
    while (qMix == pMix)
        qMix = randomPrimeRef(256);
    BigUInt nMix = pMix * qMix, eMix(65537);
    BigUInt phiMix = (pMix - BigUInt(1)) * (qMix - BigUInt(1)), dMix = modInverse(eMix, phiMix);
    Key mixKey;
    mixKey.n = nMix; mixKey.e = eMix; mixKey.d = dMix;
    mixKey.p = pMix; mixKey.q = qMix;
    mixKey.dp = dMix % (pMix - BigUInt(1)); mixKey.dq = dMix % (qMix - BigUInt(1));
    mixKey.qinv = modInverse(qMix, pMix);
    mixKey.hasE = mixKey.hasD = mixKey.hasCRT = true;
    std::vector<uint8_t> mixMsg = {'P', 'R', 'I', 'M', 'E', '-', 'C', 'O', 'M', 'P', 'A', 'R', 'E'};
    std::vector<uint8_t> mixCt = rsaEncrypt(mixMsg, mixKey.n, mixKey.e), mixPt = rsaDecryptPlain(mixCt, mixKey.n, mixKey.d);
    check(mixPt == mixMsg, "混合素数（fast+ref）生成密钥：加解密往返");
    auto randomBytes = [&](size_t n) {
        std::vector<uint8_t> v(n);
        std::uniform_int_distribution<unsigned> dist(0, 255);
        for (auto& b : v)
            b = static_cast<uint8_t>(dist(rng()));
        return v;
    };
    bool crtOk = true;
    for (int i = 0; i < 30; ++i) {
        Key ck; BigUInt cp, cq;
        generateKey(ck, 512, cp, cq);
        size_t block = (ck.n.bitLength() + 7) / 8 - 1;
        std::vector<uint8_t> m = randomBytes(std::min<size_t>(block, 24));
        if (m.empty()) m.push_back(1);
        m[0] |= 0x01;                  // 避免前导 0 影响明文比对
        std::vector<uint8_t> c = rsaEncrypt(m, ck.n, ck.e);
        std::vector<uint8_t> d1 = rsaDecryptCRT(c, ck.n, ck.p, ck.q,
                                                ck.dp, ck.dq, ck.qinv);
        std::vector<uint8_t> d2 = rsaDecryptPlain(c, ck.n, ck.d);
        if (d1 != d2) { crtOk = false; break; }
    }
    check(crtOk, "CRT 对拍 30 组随机密钥/明文：rsaDecryptCRT == rsaDecryptPlain");
    Key endKey; BigUInt ep, eq;
    generateKey(endKey, 512, ep, eq);
    std::vector<uint8_t> endMsg = {'H', 'e', 'l', 'l', 'o', 'R', 'S', 'A', '-', 'C', 'R', 'T'};
    std::vector<uint8_t> endCt = rsaEncrypt(endMsg, endKey.n, endKey.e);
    std::vector<uint8_t> endCrt = rsaDecryptCRT(endCt, endKey.n, endKey.p, endKey.q,
                                                endKey.dp, endKey.dq, endKey.qinv);
    std::vector<uint8_t> endRef = rsaDecryptPlain(endCt, endKey.n, endKey.d);
    check(endCrt == endMsg && endRef == endMsg,
          "端到端 CRT 对拍：HelloRSA-CRT 两次解密一致");
    // ---------- 4.2 性能基准（只输出数据，不参与 pass/fail） ----------
    std::cout << "\n---- 性能基准（仅供参考，不计入 pass/fail）----\n";
    volatile unsigned benchSink = 0;
    auto elapsedMs = [](const std::chrono::steady_clock::time_point& t0) {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
                   std::chrono::steady_clock::now() - t0).count();
    };
    BigUInt bBase = randomOdd(512), bExp = randomOdd(512), bMod = randomOdd(512);
    auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 100; ++i) { BigUInt r = modPow(bBase, bExp, bMod); benchSink ^= static_cast<unsigned>(r.bit(0)); }
    long long refPowMs = elapsedMs(t0);
    t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 100; ++i) { BigUInt r = modPowFast(bBase, bExp, bMod); benchSink ^= static_cast<unsigned>(r.bit(0)); }
    long long fastPowMs = elapsedMs(t0);
    std::cout << " 模幂 512bit x100：modPow " << refPowMs << " ms，modPowFast " << fastPowMs
              << " ms，加速比 " << (fastPowMs > 0 ? static_cast<double>(refPowMs) / fastPowMs : 0.0) << "x\n";
    t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 5; ++i) { BigUInt p = randomPrimeRef(256); benchSink ^= static_cast<unsigned>(p.bit(0)); }
    long long refPrimeMs = elapsedMs(t0);
    t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 5; ++i) { BigUInt p = randomPrimeFast(256); benchSink ^= static_cast<unsigned>(p.bit(0)); }
    long long fastPrimeMs = elapsedMs(t0);
    std::cout << " 素数生成 256bit x5：randomPrimeRef " << refPrimeMs << " ms，randomPrimeFast "
              << fastPrimeMs << " ms，加速比 "
              << (fastPrimeMs > 0 ? static_cast<double>(refPrimeMs) / fastPrimeMs : 0.0) << "x\n";
    Key dk; BigUInt dp, dq;
    generateKey(dk, 512, dp, dq);
    std::vector<uint8_t> benchMsg(32, 0x42), benchCt = rsaEncrypt(benchMsg, dk.n, dk.e);
    volatile size_t benchSize = 0;
    t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 200; ++i) { std::vector<uint8_t> out = rsaDecryptPlain(benchCt, dk.n, dk.d); benchSize += out.size(); }
    long long refDecMs = elapsedMs(t0);
    t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 200; ++i) { std::vector<uint8_t> out = rsaDecryptCRT(benchCt, dk.n, dk.p, dk.q, dk.dp, dk.dq, dk.qinv); benchSize += out.size(); }
    long long crtDecMs = elapsedMs(t0);
    std::cout << " 解密 512bit x200：rsaDecryptPlain " << refDecMs << " ms，rsaDecryptCRT "
              << crtDecMs << " ms，加速比 "
              << (crtDecMs > 0 ? static_cast<double>(refDecMs) / crtDecMs : 0.0) << "x\n";
    (void)benchSink;
    (void)benchSize;
    std::cout << " 自检结果：" << (fail ? "存在失败项" : "全部通过") << "\n";
    return fail;
}
Key loadPublicKeyForEncryption()
{
    Key k;
    if (fileExists("public.txt")) {
        k = loadKey("public.txt", false);
        std::cout << " 使用公钥文件：public.txt\n";
    } else if (fileExists("key.txt")) {
        k = loadKey("key.txt", false);
        std::cout << " 使用公钥文件：key.txt（旧版兼容，已忽略其中的 d）\n";
    } else {
        throw std::runtime_error("请先生成密钥对（public.txt）");
    }
    if (k.n.zero() || !k.hasE)
        throw std::runtime_error("公钥文件缺少 n 或 e");
    return k;
}
void encryptMenuFlow()
{
    Key k = loadPublicKeyForEncryption();
    std::string form = trim(readLine(" 明文形式（1=字符串/UTF-8，2=十六进制，默认 1）: "));
    std::string data = readLine(" 请输入明文: ");
    encryptFlow(k.n, k.e, form == "2" ? parseHex(data)
                                     : std::vector<uint8_t>(data.begin(), data.end()));
}
struct PrivateSource {
    std::string path;
    bool legacy = false;
};
// 只检查文件里有没有 d 字段，真正的 d 要等用户确认后再读取。
bool findPrivateSource(PrivateSource& src)
{
    if (fileExists("private.txt") && fileHasPrivateKey("private.txt")) {
        src.path = "private.txt";
        src.legacy = false;
        return true;
    }
    if (fileExists("key.txt") && fileHasPrivateKey("key.txt")) {
        src.path = "key.txt";
        src.legacy = true;
        return true;
    }
    return false;
}
void decryptFromPrivateFile()
{
    PrivateSource src;
    if (!findPrivateSource(src)) {
        std::cout << " 没有可用的私钥来源。\n";
        return;
    }
    if (src.legacy) {
        std::cout << "\n[安全提示] 检测到旧版 key.txt，其中包含明文私钥 d，仅用于教学演示。\n"
                  << "           真实环境应加密存储或选择\"手动输入 d\"。\n";
    } else {
        std::cout << "\n[安全提示] 即将从 private.txt 读取明文私钥 d，仅用于教学演示。\n"
                  << "           真实环境应加密存储或选择\"手动输入 d\"。\n";
    }
    std::string ans = trim(readLine(" 确认继续？(y/N): "));
    if (ans != "y" && ans != "Y") {
        std::cout << " 已取消。\n";
        return;
    }
    Key k = loadKey(src.path, true);
    if (k.n.zero() || !k.hasD)
        throw std::runtime_error("私钥文件缺少 n 或 d");
    std::cout << " 本次私钥来源：" << (src.legacy ? "key.txt（旧版）" : "private.txt") << "\n";
    std::string data = trim(readLine(" 请输入密文(HEX): "));
    decryptFlow(k, parseHex(data));
}
void decryptWithManualD()
{
    std::string dstr = trim(readSecret(" 请输入私钥指数 d: "));
    if (dstr.empty())
        throw std::runtime_error("私钥 d 不能为空");
    // 教学版：dstr 和 d 在作用域结束后不会主动擦除。
    BigUInt d = fromDecimal(dstr);
    BigUInt n;
    if (fileExists("public.txt")) {
        Key pk = loadKey("public.txt", false);
        if (pk.n.zero())
            throw std::runtime_error("public.txt 中缺少模数 n");
        n = pk.n;
        std::cout << " 使用公钥文件 public.txt 中的 n\n";
    } else {
        std::string ns = trim(readLine(" 请输入模数 n（十进制）: "));
        if (ns.empty())
            throw std::runtime_error("模数 n 不能为空");
        n = fromDecimal(ns);
    }
    std::cout << " 本次私钥来源：手动输入\n";
    std::string data = trim(readLine(" 请输入密文(HEX): "));
    Key mk;
    mk.n = n;
    mk.d = d;
    mk.hasD = true;
    decryptFlow(mk, parseHex(data));
}
void decryptMenuFlow()
{
    for (;;) {
        std::cout << "\n 请选择私钥 d 的来源：\n"
                  << "   a) 从 private.txt 读取（明文私钥，仅教学演示，需确认）\n"
                  << "   b) 手动输入 d（不回显）\n   c) 返回主菜单\n";
        std::string c = trim(readLine(" 请选择 [a/b/c]: "));
        if (c == "a" || c == "A") {
            decryptFromPrivateFile();
            return;
        }
        if (c == "b" || c == "B") {
            decryptWithManualD();
            return;
        }
        if (c == "c" || c == "C")
            return;
        if (c == "0" || c == "q" || c == "Q")
            return;
        std::cout << " 输入无效，请输入 a、b 或 c。\n";
    }
}
void viewKeyFiles()
{
    bool any = false;
    if (fileExists("public.txt")) {
        any = true;
        std::cout << "\n---- public.txt ----\n";
        printPublicFields(loadKey("public.txt", false));
    }
    if (fileExists("private.txt")) {
        any = true;
        std::cout << "\n---- private.txt ----\n";
        Key k = loadKey("private.txt", false);
        std::cout << " n = " << toDecimal(k.n) << "\n";
        if (fileHasPrivateKey("private.txt"))
            std::cout << " d = [已隐藏，教学版不在屏幕显示私钥]\n";
        if (fileHasCRTParams("private.txt"))
            std::cout << " CRT 参数 = [已隐藏，属于私钥材料]\n";
    }
    if (fileExists("key.txt")) {
        any = true;
        std::cout << "\n---- key.txt（旧版）----\n";
        Key k = loadKey("key.txt", false);
        printPublicFields(k);
        if (fileHasPrivateKey("key.txt"))
            std::cout << " d = [已隐藏，检测到旧版私钥字段]\n";
        if (fileHasCRTParams("key.txt"))
            std::cout << " CRT 参数 = [已隐藏，属于私钥材料]\n";
    }
    if (!any)
        std::cout << " 未找到 public.txt / private.txt / key.txt。\n";
}
void interactive()
{
    for (;;) {
        std::cout << "\n=================== RSA 加解密工具 ===================\n"
                  << " 1. 生成密钥对（默认 512 位，分别写入 public.txt / private.txt）\n"
                  << " 2. 加密（默认使用 public.txt 中的公钥）\n"
                  << " 3. 解密（私钥来源需手动选择）\n"
                  << " 4. 查看密钥文件\n"
                  << " 5. 核心运算自检\n"
                  << " 0. 退出\n"
                  << "======================================================\n";
        std::string choice = trim(readLine(" 请选择: "));
        try {
            if (choice == "1") {
                std::string s = trim(readLine(" 密钥位数（默认 512，32~1024 的偶数）: "));
                if (s == "0" || s == "q" || s == "Q") {
                    std::cout << " 已取消。\n";
                } else {
                    int bits = 512;
                    bool valid = true;
                    if (!s.empty()) {
                        for (char ch : s) {
                            if (ch < '0' || ch > '9') {
                                valid = false;
                                break;
                            }
                        }
                        if (valid) {
                            try {
                                size_t pos = 0;
                                bits = std::stoi(s, &pos);
                                if (pos != s.size())
                                    valid = false;
                            } catch (const std::invalid_argument&) {
                                valid = false;
                            } catch (const std::out_of_range&) {
                                valid = false;
                            }
                        }
                    }
                    if (!valid)
                        std::cout << " 错误：密钥位数必须是十进制整数\n";
                    else
                        keygenFlow(bits);
                }
            } else if (choice == "2") {
                encryptMenuFlow();
            } else if (choice == "3") {
                decryptMenuFlow();
            } else if (choice == "4") {
                viewKeyFiles();
            } else if (choice == "5" || choice == "9") {
                // 菜单按第 5 项显示；9 作为兼容入口保留。
                selfTest();
            } else if (choice == "0" || choice == "q" || choice == "Q") {
                return;
            } else {
                std::cout << " 输入无效，请重新选择。\n";
            }
        } catch (const std::exception& e) {
            std::cout << " 错误：" << e.what() << "\n";
            if (std::cin.eof())
                return;
        }
    }
}
} // namespace

int main(int argc, char** argv)
{
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif
    if (argc > 1)
        std::cout << "本程序为交互模式，已忽略命令行参数。\n\n";
    (void)argv;
    try {
        interactive();
    } catch (const std::exception& e) {
        std::cerr << "错误：" << e.what() << "\n";
        return 1;
    }
    return 0;
}
