"""
Operations Framework for MineDojo.

Provides scripted Minecraft operations (navigate, craft, attack, mine, etc.)
that can be composed into sequences and executed against a MineDojoSim
environment.

Exports:
    Operation: Abstract base class for all operations.
    OPERATION_REGISTRY: Dict mapping operation names to their classes.
    OperationSequencer: Executes operation sequences and captures frames.
"""

from .base import Operation
from .registry import OPERATION_REGISTRY
from .sequencer import OperationSequencer

__all__ = ["Operation", "OPERATION_REGISTRY", "OperationSequencer"]
