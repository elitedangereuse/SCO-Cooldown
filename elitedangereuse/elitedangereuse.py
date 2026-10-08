import semantic_version

from config import config
from elitedangereuse.debug import Debug
from elitedangereuse.httprequestmanager import HTTPRequestManager
from elitedangereuse.sco import COOLDOWN_SETTING, DEFAULT_COOLDOWN_SECONDS, SCOCooldown
from elitedangereuse.ships import CurrentShip, automatic_cooldown_seconds
from elitedangereuse.ui import UI
from elitedangereuse.updatemanager import UpdateManager


class EliteDangereuse:
    """
    Main plugin class
    """
    def __init__(self, plugin_name: str, version: semantic_version.Version):
        self.plugin_name: str = plugin_name
        self.version: semantic_version.Version = version


    def plugin_start(self, plugin_dir: str):
        """
        The plugin is starting up. Initialise all our objects.
        """
        self.plugin_dir = plugin_dir
        self.debug: Debug = Debug(self)
        self.fallback_cooldown_seconds = max(1, config.get_int(COOLDOWN_SETTING, default=DEFAULT_COOLDOWN_SECONDS))
        self.current_ship: CurrentShip | None = None
        self.sco = SCOCooldown(float(self.fallback_cooldown_seconds))
        self.ui: UI = UI(self)
        self.request_manager = HTTPRequestManager(self)
        self.update_manager = UpdateManager(self)


    def plugin_stop(self):
        """
        The plugin is shutting down.
        """
        self.ui.stop()

    def dashboard_entry(self, cmdr: str, is_beta: bool, entry: dict):
        """
        Parse an incoming dashboard entry and store the data we need
        """
        self.sco.update(entry)
        self.ui.refresh_sco_status()

    def journal_entry(self, cmdr: str, is_beta: bool, system: str | None, station: str | None, entry: dict, state: dict):
        """Use EDMC's existing state cache to learn the currently active ship."""
        ship = CurrentShip.from_state(state)
        if ship is None or ship == self.current_ship:
            return

        self.current_ship = ship
        self._apply_effective_cooldown()
        self.ui.refresh_sco_status()

    def current_cooldown_seconds(self) -> int:
        """Return the current ship override, automatic rule, or initial fallback."""
        if self.current_ship is None:
            return self.fallback_cooldown_seconds

        override = self.current_ship_override_seconds()
        if override is not None:
            return override
        return self.automatic_current_cooldown_seconds()

    def automatic_current_cooldown_seconds(self) -> int:
        """Return the built-in rule, without considering a per-ship override."""
        if self.current_ship is None:
            return self.fallback_cooldown_seconds
        return automatic_cooldown_seconds(self.current_ship.ship_type, self.fallback_cooldown_seconds)

    def current_ship_override_seconds(self) -> int | None:
        if self.current_ship is None or self.current_ship.ship_id is None:
            return None
        override = config.get_int(self._ship_override_key(self.current_ship.ship_id), default=0)
        return override if override > 0 else None

    def set_fallback_cooldown_seconds(self, cooldown: int) -> None:
        self.fallback_cooldown_seconds = cooldown
        self._apply_effective_cooldown()

    def set_current_ship_override(self, cooldown: int | None) -> None:
        if self.current_ship is None or self.current_ship.ship_id is None:
            return
        config.set(self._ship_override_key(self.current_ship.ship_id), cooldown or 0)
        self._apply_effective_cooldown()

    def _apply_effective_cooldown(self) -> None:
        self.sco.cooldown_seconds = float(self.current_cooldown_seconds())

    @staticmethod
    def _ship_override_key(ship_id: int) -> str:
        return f"sco_cooldown_ship_{ship_id}"
