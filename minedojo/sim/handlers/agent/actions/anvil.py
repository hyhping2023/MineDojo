"""
Action handler for anvil commands.
"""
from minedojo.sim.handlers.agent.action import Action
from minedojo.sim import spaces


class AnvilAction(Action):
    """
    An action handler for opening the anvil GUI and performing repairs/renaming.
    Uses the AnvilCommands Malmo handler on the Java side.
    """

    _command = "anvil"

    def to_string(self):
        return "anvil"

    def xml_template(self) -> str:
        return str("<AnvilCommands/>")

    def __init__(self):
        super().__init__(
            self._command,
            spaces.Enum("none", "anvil", "anvilRepair", default="none"),
        )
