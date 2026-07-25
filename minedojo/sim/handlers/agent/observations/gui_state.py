import numpy as np

from minedojo.sim import spaces
from minedojo.sim.handlers.translation import KeymapTranslationHandler


class GuiStateObservation(KeymapTranslationHandler):
    """
    Handles GUI state observations from the Java ObservationFromGuiScreen handler.
    Reports current_gui (string) and gui_slots (list of slot entries).
    """

    def to_string(self):
        return "gui_state"

    def xml_template(self) -> str:
        return str("""<ObservationFromGuiScreen/>""")

    def __init__(self):
        super().__init__(
            hero_keys=["current_gui"],
            univ_keys=["current_gui"],
            space=spaces.Text(shape=()),
            default_if_missing="none",
        )

    def from_hero(self, hero_dict, dtype=None):
        current_gui = hero_dict.get("current_gui", "none")
        gui_slots = hero_dict.get("gui_slots", [])
        return {"current_gui": current_gui, "gui_slots": gui_slots}

    def __or__(self, other):
        if isinstance(other, GuiStateObservation):
            return self
        else:
            raise ValueError("Incompatible observables!")
