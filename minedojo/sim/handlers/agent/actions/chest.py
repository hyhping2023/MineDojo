"""
Action handler for chest/container commands.
"""
from minedojo.sim.handlers.agent.action import Action
from minedojo.sim import spaces


class ChestAction(Action):
    """
    An action handler for opening/closing chests and moving items.
    Uses the ChestCommands Malmo handler on the Java side.
    """

    _command = "chest"

    def to_string(self):
        return "chest"

    def xml_template(self) -> str:
        return str("<ChestCommands/>")

    def __init__(self):
        super().__init__(
            self._command,
            spaces.Enum("none", "chest", "chestMove", default="none"),
        )
