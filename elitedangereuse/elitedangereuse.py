import semantic_version

from config import config
from elitedangereuse.debug import Debug
from elitedangereuse.httprequestmanager import HTTPRequestManager
from elitedangereuse.sco import COOLDOWN_SETTING, DEFAULT_COOLDOWN_SECONDS, SCOCooldown
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
        cooldown = max(1, config.get_int(COOLDOWN_SETTING, default=DEFAULT_COOLDOWN_SECONDS))
        self.sco = SCOCooldown(float(cooldown))
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
