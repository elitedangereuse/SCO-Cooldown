import tkinter as tk
from pathlib import Path
from shutil import which
from subprocess import DEVNULL, Popen
from tkinter import ttk
from tkinter import filedialog

import myNotebook as nb
from config import config
from elitedangereuse.debug import Debug
from elitedangereuse.sco import (
    COOLDOWN_SETTING,
    DEFAULT_COOLDOWN_SECONDS,
    SCOState,
    SOUND_PATH_SETTING,
)


class UI:
    """
    Display the user's activity
    """

    def __init__(self, elitedangereuse):
        self.elitedangereuse = elitedangereuse
        self.frame: tk.Frame = None
        self._refresh_timer: str | None = None
        self._cooldown_var = tk.IntVar(value=DEFAULT_COOLDOWN_SECONDS)
        self._progress_style_name = "SCOCooldown.Horizontal.TProgressbar"
        self._bundled_sound_path = Path(elitedangereuse.plugin_dir) / "sco_ready.wav"
        self._sound_path_var = tk.StringVar(value=config.get_str(SOUND_PATH_SETTING, default=""))
        self._sound_path_label: tk.Label | None = None


    def get_plugin_frame(self, parent_frame: tk.Frame) -> tk.Frame:
        """
        Return a TK Frame for adding to the EDMC main window
        """
        self.frame: tk.Frame = tk.Frame(parent_frame)
        self.frame.columnconfigure(0, weight=1)

        self.sco_status = tk.Label(self.frame)
        self.sco_status.grid(row=0, column=0, sticky=tk.W)
        self.sco_progress = ttk.Progressbar(
            self.frame,
            maximum=100,
            mode="determinate",
            length=160,
            style=self._progress_style_name,
        )
        self.sco_progress.grid(row=1, column=0, pady=(3, 0), sticky=tk.EW)
        self.refresh_sco_status()

        return self.frame


    def get_prefs_frame(self, parent_frame: tk.Frame):
        """
        Return a TK Frame for adding to the EDMC settings dialog
        """
        frame: nb.Frame = nb.Frame(parent_frame)
        cooldown = config.get_int(COOLDOWN_SETTING, default=DEFAULT_COOLDOWN_SECONDS)
        self._cooldown_var.set(max(1, cooldown))

        nb.Label(frame, text="SCO cooldown (seconds):").grid(row=0, column=0, padx=(0, 8), pady=4, sticky=tk.W)
        tk.Spinbox(frame, from_=1, to=120, textvariable=self._cooldown_var, width=5).grid(row=0, column=1, pady=4, sticky=tk.W)
        nb.Button(frame, text="Test sound", command=self._play_ready_sound).grid(
            row=1, column=0, columnspan=2, pady=(4, 0), sticky=tk.W
        )
        self._sound_path_label = nb.Label(frame)
        self._sound_path_label.grid(row=2, column=0, columnspan=2, pady=(10, 2), sticky=tk.W)
        self._update_sound_path_label()
        nb.Button(frame, text="Choose sound…", command=self._choose_sound).grid(
            row=3, column=0, padx=(0, 6), sticky=tk.W
        )
        nb.Button(frame, text="Use bundled sound", command=self._use_bundled_sound).grid(
            row=3, column=1, sticky=tk.W
        )

        return frame


    def save_prefs(self):
        """
        Preferences have been saved (from EDMC core or any plugin).
        """
        try:
            cooldown = max(1, self._cooldown_var.get())
        except tk.TclError:
            cooldown = DEFAULT_COOLDOWN_SECONDS
            self._cooldown_var.set(cooldown)
        config.set(COOLDOWN_SETTING, cooldown)
        config.set(SOUND_PATH_SETTING, self._sound_path_var.get().strip())
        self.elitedangereuse.sco.cooldown_seconds = float(cooldown)

    def refresh_sco_status(self):
        """Render the tracker state and keep the countdown moving."""
        if self.frame is None or not self.frame.winfo_exists():
            return

        if self._refresh_timer is not None:
            self.frame.after_cancel(self._refresh_timer)
            self._refresh_timer = None

        snapshot = self.elitedangereuse.sco.snapshot()
        if snapshot.state is SCOState.ACTIVE:
            self._set_progress(0, "orange", "SCO overdrive active")
        elif snapshot.state is SCOState.COOLDOWN:
            cooldown = max(1, self.elitedangereuse.sco.cooldown_seconds)
            progress = 100 * (1 - snapshot.seconds_remaining / cooldown)
            self._set_progress(progress, "orange", f"SCO cooldown: {snapshot.seconds_remaining:.1f}s")
            self._refresh_timer = self.frame.after(100, self.refresh_sco_status)
        elif snapshot.state is SCOState.READY:
            self._set_progress(100, "green", "SCO ready")
            if snapshot.just_became_ready:
                self._play_ready_sound()
        else:
            self._set_progress(0, "gray", "Waiting for Status.json")

    def stop(self):
        """Cancel pending Tk callbacks before EDMC destroys the plugin frame."""
        if self.frame is not None and self._refresh_timer is not None:
            self.frame.after_cancel(self._refresh_timer)
            self._refresh_timer = None

    def _set_progress(self, value: float, colour: str, text: str):
        """Set the fill percentage and status text for the determinate bar."""
        ttk.Style(self.frame).configure(self._progress_style_name, background=colour)
        self.sco_progress.configure(value=max(0, min(100, value)))
        self.sco_status.configure(text=text)

    def _play_ready_sound(self):
        """Play the selected alert on Windows, Linux, or macOS."""
        sound_path = self._get_sound_path()
        if not sound_path.is_file():
            Debug.logger.warning("SCO-ready sound file does not exist: %s", sound_path)
            self.frame.bell()
            return

        try:
            import winsound
            Debug.logger.info("Playing SCO-ready alert with winsound: %s", sound_path)
            winsound.PlaySound(
                str(sound_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
            return
        except ImportError:
            pass
        except RuntimeError as error:
            Debug.logger.warning("winsound could not play SCO-ready alert (%s)", error)

        for player, command in self._external_player_commands(sound_path):
            executable = which(command[0])
            if executable is None:
                continue
            try:
                Popen([executable, *command[1:]], stdout=DEVNULL, stderr=DEVNULL, start_new_session=True)
                Debug.logger.info("Playing SCO-ready alert with %s: %s", player, sound_path)
                return
            except OSError as error:
                Debug.logger.warning("Could not start %s for SCO-ready alert (%s)", player, error)

        Debug.logger.warning("No usable audio player was found for SCO-ready alert: %s", sound_path)
        self.frame.bell()

    def _get_sound_path(self) -> Path:
        """Return the saved custom sound, or the bundled default when unset."""
        selected = self._sound_path_var.get().strip()
        return Path(selected).expanduser() if selected else self._bundled_sound_path

    @staticmethod
    def _external_player_commands(sound_path: Path) -> tuple[tuple[str, list[str]], ...]:
        """Commands supported by common Linux and macOS desktop installations."""
        path = str(sound_path)
        return (
            ("paplay", ["paplay", path]),
            ("aplay", ["aplay", "-q", path]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]),
            ("play", ["play", "-q", path]),
            ("afplay", ["afplay", path]),
        )

    def _choose_sound(self):
        """Let the user select a local audio file for the ready alert."""
        selected = filedialog.askopenfilename(
            title="Choose SCO-ready sound",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.ogg *.flac *.m4a"),
                ("WAV files", "*.wav"),
                ("All files", "*"),
            ],
        )
        if selected:
            self._sound_path_var.set(selected)
            self._update_sound_path_label()

    def _use_bundled_sound(self):
        """Clear the custom selection and use ``sco_ready.wav`` again."""
        self._sound_path_var.set("")
        self._update_sound_path_label()

    def _update_sound_path_label(self):
        if self._sound_path_label is None:
            return
        selected = self._sound_path_var.get().strip()
        description = selected if selected else f"Bundled: {self._bundled_sound_path.name}"
        self._sound_path_label.configure(text=f"Ready sound: {description}")
