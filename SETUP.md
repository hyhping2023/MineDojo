# MineDojo 部署与运行准备指南

在受限/离线环境部署 MineDojo 并跑起来需要三类产物 + 满足 GL 显示要求。本文汇总所有必要准备和坑点。

## 概览

| 必备项 | 位置 | 作用 |
|--------|------|------|
| 自包含 fat jar | `minedojo/sim/Malmo/Minecraft/build/libs/MalmoMod-0.37.0-fat.jar` | 启动 MC 的主程序(`java -jar`),含全部运行时依赖 |
| Gradle 缓存 | `~/.gradle/caches/` | MC/Forge/launchwrapper/LWJGL/log4j/SRG 映射/natives |
| mc conda 环境 | `/data/miniconda3/envs/mc` | Python 3.10 + 依赖,editable 安装指向源码树 |
| GL 显示 | 见 §5 | LWJGL 2.9.2 需要真 GLX,不能用 Mesa 软件渲染 |

---

## 1. 自包含 fat jar

`MalmoMod-0.37.0-fat.jar` 由 `./gradlew shadowJar` 产出,**必须 ~90M 且自包含**(bundle 了 MC/Forge/launchwrapper/LWJGL/log4j/guava)。`java -jar` 单独运行即可,无需组装 classpath。

### 构建(联网机器)

```bash
cd MineDojo/minedojo/sim/Malmo/Minecraft
./gradlew shadowJar --stacktrace
```

> **关键坑**:`build.gradle` 的 `shadowJar` 配置必须用 `canBeResolved`(打包所有可解析配置),不能用 `!it.dependencies.empty`(会漏掉 ForgeGradle 程序化添加的 MC 运行时配置,产出 29M 空壳)。正确配置已在 commit `829bd2a`:
> ```groovy
> configurations = project.configurations.all.findAll {
>     it.canBeResolved && it.name != 'shadow' && it.name != 'implementation'
> }.collect { it }
> ```
> `.collect { it }` 不能少(`findAll` 返回 Set,shadow 插件要 List,否则 `Cannot cast LinkedHashSet to List`)。

### 验证自包含

```bash
ls -lh build/libs/MalmoMod-0.37.0-fat.jar   # 应 ~90M(29M 是不完整的)
unzip -l build/libs/MalmoMod-0.37.0-fat.jar | grep "net/minecraft/launchwrapper/Launch.class"   # 应有
unzip -l build/libs/MalmoMod-0.37.0-fat.jar | grep "org/lwjgl/LWJGLException.class"             # 应有
unzip -p build/libs/MalmoMod-0.37.0-fat.jar META-INF/MANIFEST.MF | grep Main-Class              # com.microsoft.Malmo.Launcher.GradleStart
```

### 放置

放到源码树的 `build/libs/`:
```bash
mkdir -p MineDojo/minedojo/sim/Malmo/Minecraft/build/libs
cp MalmoMod-0.37.0-fat.jar MineDojo/minedojo/sim/Malmo/Minecraft/build/libs/
```

`instance.py` 的 `_ensure_fat_jar_built()` 检测到它存在就直接复用,不调 gradle。

---

## 2. Gradle 缓存

### 在联网机器上打包

```bash
# 先跑一次构建,确保依赖解析进缓存
cd MineDojo/minedojo/sim/Malmo/Minecraft
./gradlew shadowJar

# 打包整个 caches 目录(含 modules-2 依赖 + minecraft MC/Forge/SRG/natives + metadata-2.63 描述符)
tar -czf minedojo-gradle-caches.tar.gz -C ~/.gradle caches
```

> 缓存含关键元数据(如 `asm-6.0.pom` + `metadata-2.63/descriptors`),离线 gradle 解析靠它。只拷 jar 不拷元数据会报 "No cached version ... available for offline mode"。

### 离线机器上合并

```bash
# 合并提取(保留现有 natives/assets,只补缺失依赖和元数据)
tar -xzf minedojo-gradle-caches.tar.gz -C ~/.gradle
```

`tar -x` 是合并,不会删现有文件。离线机原有的 `natives/1.11.2/`、`assets/`、MC jar 都保留,只新增缺失的 `asm:6.0`、log4j 等。

### 验证关键项

```bash
ls ~/.gradle/caches/modules-2/files-2.1/org.ow2.asm/asm/6.0/*/asm-6.0.pom   # asm 元数据(离线解析关键)
ls ~/.gradle/caches/minecraft/net/minecraft/natives/1.11.2/                 # LWJGL natives(.so)
ls ~/.gradle/caches/minecraft/net/minecraft/minecraft_merged/1.11.2/        # MC deobf jar
ls ~/.gradle/caches/minecraft/de/oceanlabs/mcp/mcp_snapshot/20161220/1.11.2/srgs/  # SRG 反混淆映射
```

---

## 3. mc conda 环境

`mc` 环境(Python 3.10,依赖齐全)是运行 MineDojo 的环境。

```bash
# 创建(若没有)
conda create -n mc python=3.10 -y
conda activate mc
cd MineDojo && pip install -e .

# 验证依赖
python -c "import gymnasium, omegaconf, jinja2, lxml, numpy, Pyro4, psutil, cv2; print('deps OK')"
```

### 关键坑:editable 安装指向哪棵树

本机可能有多棵 MineDojo 源码树(如 `user_code` 和 `wm-data`),`pip install -e` 指向哪棵就跑哪棵的代码。**改了启动相关代码后必须确认 mc 环境加载的是改过的那棵**:

```bash
cd /tmp && /data/miniconda3/envs/mc/bin/python -c \
  "import minedojo.sim.bridge.mc_instance.instance as i; print(i.__file__)"
# 应指向你改过的源码树(如 /workspace/user_code/MineDojo/...)
```

若指向旧树,重新指向:
```bash
/data/miniconda3/envs/mc/bin/pip install -e /workspace/user_code/MineDojo --no-deps
```

---

## 4. 启动流程(launchClient.sh)

`launchClient.sh` 用 `java -jar fat.jar` 启动,fat jar 的 manifest Main-Class 是 `GradleStart`,它自动处理:
- SRG 反混淆系统属性(`GradleStartCommon.launch`)
- 默认启动参数(version/assetsDir/assetIndex/accessToken)
- `FMLTweaker` tweak class
- LWJGL natives 追加到 `java.library.path`(`GradleStart.hackNatives`)

### 关键 JVM 参数

```bash
java -Dfml.coreMods.load=com.microsoft.Malmo.OverclockingPlugin \
     -Dcom.microsoft.Malmo.GradleStartCommon.minecraftCacheDir=$HOME/.gradle/caches/minecraft/ \
     -Xmx2G -jar MalmoMod-0.37.0-fat.jar
```

> **`minecraftCacheDir` 必须设**:`GradleStartCommon` 用 `System.getenv("GRADLE_USER_HOME")` 拼缓存路径,批处理模式下 `GRADLE_USER_HOME` 通常未设置,会拼成 `"null/caches/minecraft/"` 找不到 SRG → FML 反混淆崩。`instance.py` 已自动设这个属性并传 `MALMO_FAT_JAR` 环境变量给 launchClient.sh。

### instance.py 的 fat jar 复用

`MinecraftInstance.launch()` 调 `_ensure_fat_jar_built()`:
- fat jar 存在 → 直接返回路径,不调 gradle(快)
- 不存在 → `./gradlew shadowJar` 构建(需联网/完整缓存)

`copytree` 时 ignore `build/`(不拷贝构建目录到临时实例),通过 `MALMO_FAT_JAR` 环境变量把源码树的 fat jar 路径传给 launchClient.sh。

---

## 5. GL/显示要求(最容易卡的地方)

MC 1.11.2 用 **LWJGL 2.9.2(2015)**,它的 GLX 查询与现代 Mesa 23 软件渲染(swrast/llvmpipe)**不兼容**——`getAvailableDisplayModes` 返回 0 FB configs,即使 `glxinfo` 能正常工作。

### GPU 选型

| GPU | 能跑 MC? | 说明 |
|-----|---------|------|
| L20 / L40 / L40S | ✅ | Ada 图形卡,有显示输出,真 GLX |
| 桌面 GPU(RTX 系列) | ✅ | 有显示输出 |
| H100 / H800 | ❌ | 纯计算卡,无显示头,不能直接做 GLX |
| ASPEED VGA(主板自带) | ❌ | 基础 VGA,Mesa swrast,LWJGL 2.9.2 用不了 |

### 必须装 NVIDIA **显示**驱动(不只是 CUDA)

```bash
ls /usr/lib64/xorg/modules/drivers/nvidia_drv.so   # NVIDIA X 驱动,必须有
nvidia-smi --query-gpu=driver_version --format=csv
```

只有 CUDA(计算驱动)不够,需要完整的 NVIDIA 驱动(含 `nvidia_drv.so` + NVIDIA `libGL.so`)。缺则装 `NVIDIA-Linux-x86_64-*.run` 或发行版包。

### 三种运行方式

**A. 有物理显示器(最简单)**
```bash
cd MineDojo && python scripts/validate_install.py   # 不加 MINEDOJO_HEADLESS
```

**B. 无显示器 + NVIDIA GPU(L20 等,headless Xorg+nvidia)**
```bash
# 建 nvidia 虚拟显示配置后:
sudo Xorg :99 -config /path/to/nvidia-headless.conf
DISPLAY=:99 python scripts/validate_install.py
```
nvidia_drv 的 GLX 是真硬件 GL,LWJGL 2.9.2 完全兼容。

**C. 无 NVIDIA 显示驱动(只有 Mesa swrast)——跑不了 MC 1.11.2**
- Xvfb:无 GLX 扩展,直接不行。
- Xorg+dummy+Mesa:`glxinfo` 能跑(OpenGL 4.5 llvmpipe),但 LWJGL 2.9.2 拿到 0 FB configs → 崩。`LIBGL_ALWAYS_INDIRECT`/`LIBGL_ALWAYS_SOFTWARE`/`__GLX_VENDOR_LIBRARY_NAME=mesa` 均无效。

> 结论:**必须用有显示输出 + NVIDIA 显示驱动的 GPU**(L20/L40/桌面卡)。纯计算卡(H800)或纯软件渲染(Mesa swrast)跑不了 MC 1.11.2。

---

## 6. 验证安装

```bash
# 不启动 MC,只测扩展模块(operations/pathfinding/world_snapshots/workers 导入 + A*)
python scripts/validate_extension.py

# 启动 MC 跑 20 步(需要 GL,见 §5)
python scripts/validate_install.py
# 成功标志:[INFO] Installation Success
```

---

## 7. 造数据(并行视频生成)

前提:MC 能启动(§5 的 GL 要求满足)。

```bash
# 1. 构建 7 个世界快照(plains/forest/extreme_hills/village/cave/water/gui_item)
python scripts/build_snapshots.py --output /data/snapshots/

# 2. 启动并行 workers 生成视频(每个 worker 启动一个 MC 实例)
python -m minedojo.workers.main \
    --snapshots-dir /data/snapshots/ \
    --output-dir /data/videos/ \
    --n-workers 4
```

也可用 API:`TaskScheduler` + `VideoTask`(见 CODEBUDDY.md "Parallel Video Generation" 段)。

> **并行 workers 的 GL**:每个 worker 进程启动一个 MC 实例,都需要 GL。headless 并行建议每个 worker 用独立 X display,或共享一个 nvidia X server。

---

## 附录:从联网机器迁移到离线机的完整步骤

```bash
# === 联网机器上 ===
cd /path/to/MineDojo
git pull   # 拿到启动相关修复(launchClient.sh / instance.py / build.gradle)

# 构建 fat jar(确认 build.gradle 的 shadowJar 用 canBeResolved,见 §1)
cd minedojo/sim/Malmo/Minecraft && ./gradlew shadowJar
# 验证 ~90M 且自包含(见 §1)

# 打包 gradle 缓存
tar -czf minedojo-gradle-caches.tar.gz -C ~/.gradle caches

# 传输
scp build/libs/MalmoMod-0.37.0-fat.jar          离线机:/tmp/
scp minedojo-gradle-caches.tar.gz               离线机:/tmp/

# === 离线机器上 ===
# 1. 合并 gradle 缓存
tar -xzf /tmp/minedojo-gradle-caches.tar.gz -C ~/.gradle

# 2. 放 fat jar
mkdir -p /workspace/user_code/MineDojo/minedojo/sim/Malmo/Minecraft/build/libs
cp /tmp/MalmoMod-0.37.0-fat.jar /workspace/user_code/MineDojo/minedojo/sim/Malmo/Minecraft/build/libs/

# 3. 确认 mc 环境指向正确源码树(见 §3)

# 4. 验证
cd /workspace/user_code/MineDojo
python scripts/validate_extension.py        # 扩展模块自检(不需 GL)
python scripts/validate_install.py          # MC 启动(需 GL,见 §5)
```

## 已知问题速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `NoClassDefFoundError: LogManager` | runClient classpath 缺 log4j | 用自包含 fat jar `java -jar`(已修复) |
| fat jar 只有 29M | shadowJar 配置 `!it.dependencies.empty` 漏掉 ForgeGradle 配置 | 改用 `canBeResolved`(commit `3541bf0`) |
| `Cannot cast LinkedHashSet to List` | shadowJar 的 `findAll` 返回 Set | 加 `.collect { it }`(commit `829bd2a`) |
| `No cached version ... for offline mode` | 缺模块元数据(pom/descriptor) | 从联网机合并完整 `~/.gradle/caches`(含 metadata-2.63) |
| `getAvailableDisplayModes` 返回 0 / `No OpenGL context` | LWJGL 2.9.2 用不了 Mesa swrast | 换有显示输出的 NVIDIA GPU(L20/L40)+ 显示驱动 |
| 改了代码不生效 | mc 环境 editable 安装指向旧树 | `pip install -e <正确树> --no-deps`,见 §3 |
| `null/caches/minecraft/` 路径 | `GRADLE_USER_HOME` 未设置 | 设 `minecraftCacheDir` 属性(instance.py 已自动设) |
