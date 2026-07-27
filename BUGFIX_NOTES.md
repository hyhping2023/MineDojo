# 视频生成流水线 Bug 修复记录

本文档记录了 MineDojo 并行视频生成流水线（`minedojo/workers/`）在冒烟测试中发现的 Bug 及其修复过程。修复涉及 7 个文件，涵盖 4 类问题：快照加载、操作终止检查、场景初始化、POV 帧像素对齐。

---

## 一、冒烟测试初始失败情况

运行 `scripts/smoke_test_videos.py` 对 7 个场景进行冒烟测试，初始结果：

| 场景 | 结果 | 错误 |
|------|------|------|
| `smoke_extreme_hills` | 失败 | `BrokenPipeError: [Errno 32] Broken pipe` |
| `smoke_forest` | 失败 | `RuntimeError: Attempted to step an environment server with done=True` |
| `smoke_village` | 失败 | `RuntimeError: Attempted to step an environment server with done=True` |
| `smoke_water` | 失败 | 帧=28，视频已编码但 `success=False`（智能体溺水） |
| `smoke_plains` | 通过 | — |
| `smoke_cave` | 通过 | — |
| `smoke_gui_item` | 通过 | — |

7 个场景中 3 个通过、4 个失败。

---

## 二、Bug 根因分析与修复

### Bug 1：Worker 丢弃预构建快照（关键）

**文件**：`minedojo/workers/worker.py:182-190`

**问题**：`_create_env_from_snapshot` 方法在检测到场景的 `world_type` 为 `specified_biome` 或 `flat` 时，将 `generate_world_type` 从 `"from_file"`（加载预构建快照）覆盖为 `"specified_biome"`/`"flat"`（重新生成地形）。这导致 `build_snapshots.py` 预构建的世界快照被完全丢弃，每个任务都从零开始重新生成地形。

**影响**：
- `extreme_hills`：重新生成极端丘陵地形时，Malmo 的生物群系查找失败（日志出现 `Unable to find spawn biome`），MC 进程崩溃，`reset()` 路径中未包装的 `send_message` 调用抛出 `BrokenPipeError`。
- `forest`/`water`：同样因重新生成地形引入随机性，导致 MC 进程不稳定或智能体在不安全位置生成。
- `cave`/`gui_item`：虽然冒烟测试操作不依赖预构建结构所以通过了，但快照中预构建的石洞房间和 GUI 房间实际被丢弃了。

**修复**：移除覆盖逻辑，始终使用 `generate_world_type="from_file"` 加载预构建快照。快照已由 `SnapshotBuilder` 使用正确的 `world_type`/`biome` 和场景特定设置（石洞房间、GUI 房间、水上平台等）构建完成。

```python
# 修复前：覆盖了 from_file，丢弃快照
if scene_cfg.world_type == "specified_biome" and scene_cfg.biome:
    kwargs["generate_world_type"] = "specified_biome"
    kwargs["specified_biome"] = scene_cfg.biome
elif scene_cfg.world_type == "flat":
    kwargs["generate_world_type"] = "flat"
    kwargs["regenerate_world_after_reset"] = True

# 修复后：始终从快照文件加载
return MineDojoSim(**kwargs)  # kwargs 中 generate_world_type 保持 "from_file"
```

---

### Bug 2：操作未检查环境终止状态（关键）

**文件**：`minedojo/operations/combat.py`、`entities.py`、`inventory.py`

**问题**：多个操作在调用 `env.spawn_mobs()` / `env.execute_cmd()` / `self.step()` 后**忽略返回值中的 `terminated` 标志**，紧接着调用 `self.noop()`（内部调用 `env.step()`）。如果环境在前一步已终止（MC 崩溃或智能体死亡），后续的 `step()` 调用会命中 `bridge_env.py:150` 的 `else` 分支，抛出 `RuntimeError("Attempted to step an environment server with done=True")`。

**影响**：这是 `smoke_forest` 和 `smoke_village` 失败的直接原因。`SpawnAttackOperation` 在 `spawn_mobs()` 后未检查终止状态，立即调用 `noop()` 触发崩溃。

**受影响的操作**：

| 操作 | 文件 | 问题 |
|------|------|------|
| `SpawnAttackOperation` | `combat.py:116-138` | 忽略 `spawn_mobs`/`execute_cmd` 返回值；终止时返回 `True`（应为 `False`） |
| `SpawnEntityOperation` | `entities.py:38-39` | 忽略 `spawn_mobs` 返回值 |
| `InteractEntityOperation` | `entities.py:63-64` | 忽略 `step` 返回值 |
| `MountOperation` | `entities.py:89-90` | 忽略 `step` 返回值 |
| `OpenInventoryOperation` | `inventory.py:21-23` | 忽略 `step` 返回值 |
| `CloseInventoryOperation` | `inventory.py:40-41` | 忽略 `step` 返回值 |
| `SelectItemOperation` | `inventory.py:83-105` | 忽略 `execute_cmd`/`step` 返回值 |
| `DropItemOperation` | `inventory.py:133-142` | 忽略 `step` 返回值 |

**修复**：在每个可能终止环境的调用后捕获返回值，检查 `terminated` 标志，若终止则立即返回 `False`，不再调用任何后续 `step()`。同时将 `SpawnAttackOperation` 中终止时错误返回的 `True` 改为 `False`。

**对照**（已正确处理终止的 operation）：`LookAtOperation`（`movement.py:127-129`）、`AttackOperation`（`combat.py:65-66`）、`StrafeOperation`（`movement.py:166-168`）均正确检查 `terminated` 并返回 `False`。

```python
# 修复前（SpawnAttackOperation）
self.env.spawn_mobs([mob], [list(rel_pos)])  # 返回值被丢弃
self.noop()  # 若环境已终止，此处抛出 RuntimeError
...
if terminated:
    return True  # 错误：终止时应返回 False

# 修复后
_, _, terminated, _, _ = self.env.spawn_mobs([mob], [list(rel_pos)])
if terminated:
    return False
_, _, terminated, _, _ = self.noop()
if terminated:
    return False
...
if terminated:
    return False
```

---

### Bug 3：水域场景智能体溺水

**文件**：`minedojo/world_snapshots/config.py:155-168`、`minedojo/world_snapshots/builder.py:103-118`

**问题**：`water` 场景使用 `specified_biome="ocean"`，智能体在海平面（y=63）生成于水中。`look_at` 操作执行 20 步旋转，两个 `look_at` 共 40 步。智能体在约 28 步后溺水死亡（空气耗尽），导致 `smoke_water` 虽然成功编码了 28 帧视频，但 `success=False`。

此外，`spawn_region` 为 `xmin=-50, xmax=50, zmin=-50, zmax=50`，范围过大且缺少 `ymax`，随机传送会将智能体放到深海位置。

**修复**：
1. 在 `builder.py` 注册 `setup_water` 设置函数，在智能体生成点放置 5×5 橡木板平台（`y=-1` 相对位置，即智能体脚下），使智能体站在固体地面上而非踩水。
2. 在 `config.py` 中为 `water` 场景设置 `extra_setup="setup_water"`。
3. 将 `spawn_region` 缩小为 `xmin=-2, xmax=2, zmin=-2, zmax=2, ymin=63, ymax=63`，使随机传送落在平台范围内。

```python
@_register("setup_water")
def setup_water(env: MineDojoSim) -> None:
    """在海洋生成点放置 5×5 橡木板平台，使智能体站在地面上而非踩水。"""
    planks = "minecraft:planks"
    blocks, positions = [], []
    for x in range(-2, 3):
        for z in range(-2, 3):
            blocks.append(planks)
            positions.append([x, -1, z])
    env.set_block(blocks, positions)
```

**注意**：修改后需重新构建水域快照以包含平台：
```bash
python scripts/build_snapshots.py --scene water --output data/snapshots/
```

---

### Bug 4：Bridge reset 路径未包装 send_message

**文件**：`minedojo/sim/bridge/bridge_env/bridge_env.py:295-310, 347-360`

**问题**：`_send_mission` 和 `_quit_current_episode` 中的 `instance.client_socket_send_message()` 调用未包装 try/except。当 MC 进程在 `reset()` 期间崩溃时，这些调用抛出原始的 `BrokenPipeError`，错误信息晦涩（`[Errno 32] Broken pipe`），难以定位真实原因。

**修复**：
- `_send_mission`：包装 `send_message` 调用，捕获 `socket.error`/`BrokenPipeError`，抛出清晰的 `RuntimeError`，说明 MC 进程可能在世界生成/启动期间崩溃。
- `_quit_current_episode`：包装整个 quit 逻辑，捕获所有 socket 错误并记录警告（quit 是尽力而为的操作，失败不应阻止后续流程）。

---

### Bug 5：快照加载后时间未恢复（场景过暗/灰度）

**文件**：`minedojo/workers/worker.py:130-134`

**问题**：Malmo 的 `FileWorldGenerator` 不保证从快照的 `level.dat` 恢复时间和天气。快照在构建时设置为正午（time=6000）和晴天，但加载后世界可能回到夜晚或暴风雨。夜间 Minecraft 的环境光照极低，三个 RGB 通道值都接近 0，导致 POV 帧近乎黑白。

**修复**：在 `env.reset()` 后显式调用 `env.set_time(6000)` 和 `env.set_weather("clear")`，确保每个任务都在正午晴天开始，无论快照加载后恢复了什么状态。

---

### Bug 6：POV 帧像素行对齐错误（关键 — 灰度+倾斜的根因）

**文件**：`minedojo/sim/Malmo/Minecraft/src/main/java/com/microsoft/Malmo/MissionHandlers/VideoProducerImplementation.java`

**问题**：这是导致输出视频**黑白且倾斜**的根本原因。MC 窗口渲染正常（有颜色），但保存的视频是灰度且场景倾斜。

**根因分析**：

Java 端 `getRGBFrame()` 使用 `glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, buffer)` 从 FBO 读取像素。OpenGL 的 `GL_PACK_ALIGNMENT` 默认值为 **4**（全代码库无人修改过），即每行数据按 4 字节边界对齐。

冒烟测试使用 `image_size=(480, 854)`，宽度 854：
- 每行像素数据大小 = 854 × 3 = **2562 字节**
- 2562 % 4 = **2** → OpenGL 在每行末尾填充 2 字节，实际行步长为 2564 字节

但 Python 端 `POVObservation.from_hero`（`pov.py:62`）执行 `pov.reshape((H, W, 3))`，假设**无填充**（每行 2562 字节）。两者不匹配，导致：

1. **倾斜（剪切失真）**：reshape 读取的第 N 行起始位置比实际数据落后 2N 字节，每行偏移 ⅔ 像素，累积产生对角线剪切。
2. **灰度**：2 字节偏移使 R、G、B 通道位置每 3 行循环一次，跨帧平均后三个通道趋近于亮度值，画面呈现近乎灰度。

**为什么默认分辨率正常但冒烟测试出错**：
- 默认 `image_size=(160, 256)`，宽度 256 → 256×3=768，768 % 4 = 0（已对齐，无填充）。
- 冒烟测试宽度 854 → 854×3=2562，2562 % 4 = 2（未对齐，触发 Bug）。

**修复**：在两处 `glReadPixels` 调用前（RGB 路径 line 177 和 RGBA+深度路径 line 83）添加 `glPixelStorei(GL_PACK_ALIGNMENT, 1)`，强制 1 字节行对齐，使 `glReadPixels` 不填充行尾。这样缓冲区布局与 Python 的 `reshape((H, W, 3))` 完全匹配。

```java
// 修复前
glReadPixels(0, 0, width, height, format, GL_UNSIGNED_BYTE, buffer);

// 修复后
glPixelStorei(GL_PACK_ALIGNMENT, 1);
glReadPixels(0, 0, width, height, format, GL_UNSIGNED_BYTE, buffer);
```

这是标准的 OpenGL 修复方法，适用于**所有**分辨率，而非仅限对齐宽度。

**验证方法**：修复前若将宽度改为 856（856×3=2568，% 4=0，已对齐），输出即为彩色且正常。修复后 854 及任意宽度均可正常输出。

**重建 Malmo mod**：Java 源码修改后需重新编译 fat jar：
```bash
cd minedojo/sim/Malmo/Minecraft && ./gradlew shadowJar
```

---

## 三、修复文件清单

| 文件 | 修改内容 |
|------|----------|
| `minedojo/workers/worker.py` | 移除快照覆盖逻辑（Bug 1）；添加 `set_time`/`set_weather`（Bug 5） |
| `minedojo/operations/combat.py` | `SpawnAttackOperation` 添加终止检查，终止返回 `False`（Bug 2） |
| `minedojo/operations/entities.py` | `SpawnEntity`/`InteractEntity`/`Mount` 添加终止检查（Bug 2） |
| `minedojo/operations/inventory.py` | `Open`/`Close`/`Select`/`Drop` 添加终止检查（Bug 2） |
| `minedojo/world_snapshots/config.py` | `water` 场景添加 `extra_setup`、缩小 `spawn_region`、添加 `ymax`（Bug 3） |
| `minedojo/world_snapshots/builder.py` | 新增 `setup_water` 平台构建函数（Bug 3） |
| `minedojo/sim/bridge/bridge_env/bridge_env.py` | 包装 `_send_mission`/`_quit_current_episode` 的 `send_message`（Bug 4） |
| `minedojo/sim/Malmo/.../VideoProducerImplementation.java` | 添加 `glPixelStorei(GL_PACK_ALIGNMENT, 1)`（Bug 6） |

---

## 四、验证

修复后运行冒烟测试，7 个场景全部通过，输出视频为彩色、场景正常：

```bash
MINEDOJO_LOG_LEVEL=WARN python scripts/smoke_test_videos.py \
    --snapshots-dir data/snapshots/ --output-dir data/videos_smoke/ --n-workers 4
```

扩展验证（不需启动 MC）：
```bash
python scripts/validate_extension.py
```
该脚本检查模块导入、22 个操作注册、7 个场景配置、A* 寻路算法，全部通过。
