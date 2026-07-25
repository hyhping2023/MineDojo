"""
Action handler for enchanting commands.
"""
from minedojo.sim.handlers.agent.action import Action
from minedojo.sim import spaces


class EnchantAction(Action):
    """
    An action handler for opening the enchanting table GUI.
    Uses the EnchantCommands Malmo handler on the Java side.
    """

    _command = "enchant"

    def to_string(self):
        return "enchant"

    def xml_template(self) -> str:
        return str("<EnchantCommands/>")

    def __init__(self):
        super().__init__(
            self._command,
            spaces.Enum("none", "enchant", "selectEnchant", default="none"),
        )
