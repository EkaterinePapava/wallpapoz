import os
import re
import subprocess
from pathlib import Path


STYLE_BY_DESKTOP = {
    "gnome": {"3": "zoom", "2": "scaled", "1": "stretched", "0": "centered", "4": "wallpaper"},
    "mate": {"3": "zoom", "2": "scaled", "1": "stretched", "0": "centered", "4": "wallpaper"},
    "cinnamon": {"3": "zoom", "2": "scaled", "1": "stretched", "0": "centered", "4": "wallpaper"},
    "xfce": {"3": "5", "2": "4", "1": "3", "0": "1", "4": "2"},
    "fluxbox": {"3": "--bg-fill", "2": "--bg-max", "1": "--bg-fill", "0": "--bg-center", "4": "--bg-tile"},
}


class WallpaperSystem:
    def __init__(self):
        self.desktop = self._detect_desktop()

    def _detect_desktop(self):
        current = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        combined = f"{current} {session}"

        if "xfce" in combined:
            return "xfce"
        if "mate" in combined:
            return "mate"
        if "cinnamon" in combined:
            return "cinnamon"
        if "fluxbox" in combined:
            return "fluxbox"
        return "gnome"

    def total_workspaces(self):
        output = self._run_output(["xprop", "-root", "_NET_NUMBER_OF_DESKTOPS"])
        match = re.search(r"=\s*(\d+)", output)
        if not match:
            return 1
        return max(int(match.group(1)), 1)

    def current_workspace(self):
        output = self._run_output(["xprop", "-root", "_NET_CURRENT_DESKTOP"])
        match = re.search(r"=\s*(\d+)", output)
        if not match:
            return 0
        return int(match.group(1))

    def set_wallpaper(self, filename, style_key):
        filename = str(Path(filename).expanduser())
        style = STYLE_BY_DESKTOP.get(self.desktop, STYLE_BY_DESKTOP["gnome"]).get(style_key, "scaled")

        if self.desktop == "gnome":
            uri = Path(filename).absolute().as_uri()
            self._run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri])
            self._run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri])
            self._run(["gsettings", "set", "org.gnome.desktop.background", "picture-options", style])
        elif self.desktop == "mate":
            self._run(["gsettings", "set", "org.mate.background", "picture-filename", filename])
            self._run(["gsettings", "set", "org.mate.background", "picture-options", style])
        elif self.desktop == "cinnamon":
            uri = Path(filename).absolute().as_uri()
            self._run(["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", uri])
            self._run(["gsettings", "set", "org.cinnamon.desktop.background", "picture-options", style])
        elif self.desktop == "xfce":
            self._run(
                [
                    "xfconf-query",
                    "-c",
                    "xfce4-desktop",
                    "-p",
                    "/backdrop/screen0/monitor0/image-path",
                    "-s",
                    filename,
                ]
            )
            self._run(
                [
                    "xfconf-query",
                    "-c",
                    "xfce4-desktop",
                    "-p",
                    "/backdrop/screen0/monitor0/image-style",
                    "-s",
                    style,
                ]
            )
        elif self.desktop == "fluxbox":
            self._run(["feh", style, filename])

    def _run(self, command):
        try:
            subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            return

    def _run_output(self, command):
        try:
            result = subprocess.run(command, check=False, text=True, capture_output=True)
        except FileNotFoundError:
            return ""
        return result.stdout
