from minedojo.world_snapshots.config import SCENE_CONFIGS
from minedojo.world_snapshots.builder import SnapshotBuilder
import tempfile, os

# 选择一个简单的场景
config = SCENE_CONFIGS["plains"]

# 临时目录
output = tempfile.mkdtemp(prefix="minedojo_snapshot_")

# 构建快照
builder = SnapshotBuilder(scene_config=config, image_size=(160, 256))
builder.build(output)
print(f"Snapshot saved to: {output}")
print(f"Files: {os.listdir(output)[:5]}")  # 应该看到 level.dat 等文件