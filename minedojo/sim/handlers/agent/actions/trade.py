"""
Action handler for villager trading commands.
"""
from minedojo.sim.handlers.agent.action import Action
from minedojo.sim import spaces


class TradeAction(Action):
    """
    An action handler for initiating and completing villager trades.
    Uses the TradeCommands Malmo handler on the Java side.
    """

    _command = "trade"

    def to_string(self):
        return "trade"

    def xml_template(self) -> str:
        return str("<TradeCommands/>")

    def __init__(self):
        super().__init__(
            self._command,
            spaces.Enum("none", "trade", "selectTrade", default="none"),
        )


class SelectTradeAction(Action):
    """
    An action handler for selecting a specific trade offer from a villager.
    """

    _command = "selectTrade"

    def to_string(self):
        return "selectTrade"

    def xml_template(self) -> str:
        return str("<TradeCommands/>")

    def __init__(self):
        super().__init__(
            self._command,
            spaces.DiscreteRange(-1, 10),  # trade offer index 0-9, -1 for noop
        )
