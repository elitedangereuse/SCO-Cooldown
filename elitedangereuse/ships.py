"""Ship-aware SCO cooldown rules based on EDMC's journal state."""

from dataclasses import dataclass
from typing import Mapping


LEGACY_COOLDOWN_SECONDS = 17
NEW_GENERATION_COOLDOWN_SECONDS = 9
CASPIAN_COOLDOWN_SECONDS = 7
CASPIAN_SHIP_TYPE = "Explorer_NX"

# FDevIDs shipyard.csv entries from Python Mk II onwards.  Caspian is listed
# separately because its observed SCO cooldown is shorter than the group rule.
NEW_GENERATION_SHIP_TYPES = frozenset({
    "Python_NX",
    "Type8",
    "Mandalay",
    "CobraMkV",
    "Corsair",
    "PantherMkII",
    "LakonMiner",
    "SmallCombat01_NX",
    "MediumTransport01",
})


@dataclass(frozen=True)
class CurrentShip:
    """The parts of EDMC's journal state needed for SCO cooldown selection."""

    ship_type: str
    ship_id: int | None
    ship_name: str = ""
    ship_ident: str = ""

    @classmethod
    def from_state(cls, state: Mapping) -> "CurrentShip | None":
        ship_type = state.get("ShipType")
        if not isinstance(ship_type, str) or not ship_type:
            return None

        ship_id = state.get("ShipID")
        try:
            ship_id = int(ship_id) if ship_id is not None else None
        except (TypeError, ValueError):
            ship_id = None

        return cls(
            ship_type=ship_type,
            ship_id=ship_id,
            ship_name=str(state.get("ShipName") or ""),
            ship_ident=str(state.get("ShipIdent") or ""),
        )

    @property
    def display_name(self) -> str:
        """A concise label for EDMC's main panel and preferences page."""
        user_name = self.ship_name or self.ship_ident
        return f"{user_name} ({self.ship_type})" if user_name else self.ship_type


def automatic_cooldown_seconds(ship_type: str, fallback_seconds: int) -> int:
    """Return the best known cooldown for an EDMC internal ship identifier."""
    if ship_type == CASPIAN_SHIP_TYPE:
        return CASPIAN_COOLDOWN_SECONDS
    if ship_type in NEW_GENERATION_SHIP_TYPES:
        return NEW_GENERATION_COOLDOWN_SECONDS
    return LEGACY_COOLDOWN_SECONDS if ship_type else fallback_seconds
