"""
Action handler for brewing commands.
"""
from minedojo.sim.handlers.agent.action import Action
from minedojo.sim import spaces


class BrewAction(Action):
    """
    An action handler for opening the brewing stand GUI.
    Uses the BrewingCommands Malmo handler on the Java side.
    """

    _command = "brew"

    def to_string(self):
        return "brew"

    def xml_template(self) -> str:
        return str("<BrewingCommands/>")

    def __init__(self):
        super().__init__(
            self._command,
            spaces.Enum("none", "brew", "brewIngredient", "brewFuel", default="none"),
        )
