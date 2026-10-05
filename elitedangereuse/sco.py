"""State tracking for Supercruise Overdrive (SCO)."""

from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Callable


# The Status.json documentation identifies SCO as Flags2 bit 20.
SCO_FLAGS2_BIT = 20
SCO_FLAGS2_MASK = 1 << SCO_FLAGS2_BIT
COOLDOWN_SETTING = "sco_cooldown_seconds"
SOUND_PATH_SETTING = "sco_ready_sound_path"
DEFAULT_COOLDOWN_SECONDS = 9


class SCOState(Enum):
    """The state shown by the plugin."""

    UNKNOWN = "unknown"
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    READY = "ready"


@dataclass(frozen=True)
class SCOSnapshot:
    """A display-ready view of the current SCO state."""

    state: SCOState
    seconds_remaining: float = 0.0
    just_became_ready: bool = False


class SCOCooldown:
    """Detect SCO deactivation and track its configurable cooldown."""

    def __init__(self, cooldown_seconds: float, clock: Callable[[], float] = monotonic):
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._is_active: bool | None = None
        self._cooldown_ends_at: float | None = None
        self._notify_when_ready = False

    def update(self, status: dict) -> None:
        """Consume one EDMC ``dashboard_entry`` Status.json payload."""
        flags2 = status.get("Flags2", 0)
        try:
            is_active = bool(int(flags2) & SCO_FLAGS2_MASK)
        except (TypeError, ValueError):
            return

        # The first Status.json payload establishes a baseline only.  A plugin
        # loaded while SCO is inactive must not pretend a cooldown just ended.
        if self._is_active is None:
            self._is_active = is_active
            return

        if self._is_active and not is_active:
            self._cooldown_ends_at = self._clock() + self.cooldown_seconds
            self._notify_when_ready = True
        elif is_active:
            # SCO was used again before the previous timer completed.
            self._cooldown_ends_at = None
            self._notify_when_ready = False

        self._is_active = is_active

    def snapshot(self) -> SCOSnapshot:
        """Return the current state, consuming the one-shot ready notification."""
        if self._is_active is None:
            return SCOSnapshot(SCOState.UNKNOWN)
        if self._is_active:
            return SCOSnapshot(SCOState.ACTIVE)
        if self._cooldown_ends_at is None:
            return SCOSnapshot(SCOState.READY)

        remaining = self._cooldown_ends_at - self._clock()
        if remaining > 0:
            return SCOSnapshot(SCOState.COOLDOWN, remaining)

        self._cooldown_ends_at = None
        just_became_ready = self._notify_when_ready
        self._notify_when_ready = False
        return SCOSnapshot(SCOState.READY, just_became_ready=just_became_ready)
