"""The offline quiz opening and player preferences."""

from math import pi, sin
from pathlib import Path
from random import Random

from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.utils import platform

INTRO_SECONDS = 10


def nickname(text, fallback=""):
    return " ".join(text.split())[:24].strip() or fallback


def match_names(first, second):
    names = (nickname(first, "Player 1"), nickname(second, "Player 2"))
    if names[0].casefold() == names[1].casefold():
        return tuple(f"{name} (Player {seat})" for seat, name in enumerate(names, start=1))
    return names


def reduced_motion():
    if platform == "android":
        from jnius import autoclass

        settings = autoclass("android.provider.Settings$Global")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        return settings.getFloat(activity.getContentResolver(), "animator_duration_scale", 1.0) == 0
    if platform == "win":
        from ctypes import byref, c_int, windll

        enabled = c_int()
        return bool(windll.user32.SystemParametersInfoW(0x1042, 0, byref(enabled), 0)) and not enabled.value
    return False


def read_nickname(folder):
    try:
        return nickname((Path(folder) / "solo-nickname.txt").read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return ""


def save_nickname(folder, name):
    path = Path(folder) / "solo-nickname.txt"
    temporary = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(name, encoding="utf-8")
        temporary.replace(path)
    except OSError:
        # The current session can still use the nickname when local storage is unavailable.
        pass


class GaltonBoard(Widget):
    """Animate independent left/right choices and the resulting distribution."""

    rows = 10
    fall_seconds = 3.3

    def __init__(self, still=False):
        super().__init__()
        self.seconds = INTRO_SECONDS if still else 0
        rng = Random(20)
        self.paths = []
        for _ in range(104):
            offsets = [0]
            for _ in range(self.rows):
                offsets.append(offsets[-1] + rng.choice((-0.5, 0.5)))
            self.paths.append(offsets)
        self.bind(pos=self.draw, size=self.draw)

    def set_time(self, seconds):
        self.seconds = seconds
        self.draw()

    def draw(self, *_):
        spacing = min(self.width / (self.rows + 2), self.height * .135)
        ball_radius = min(spacing * .13, self.height * .015)
        top = self.top - self.height * .105
        ground = self.y + self.height * .06
        bins_top = self.y + self.height * .32
        peg_gap = (top - bins_top) / self.rows
        left = self.center_x - (self.rows + 1) * spacing / 2

        def dot(x, y, radius):
            Ellipse(pos=(x - radius, y - radius), size=(2 * radius, 2 * radius))

        self.canvas.clear()
        with self.canvas:
            Color(.42, .63, .69, .65)
            for row in range(self.rows):
                for column in range(row + 1):
                    dot(self.center_x + (column - row / 2) * spacing,
                        top - row * peg_gap, ball_radius * .65)
            Line(points=(left, ground, left + (self.rows + 1) * spacing, ground), width=dp(1))
            for column in range(self.rows + 2):
                x = left + column * spacing
                Line(points=(x, ground, x, bins_top), width=dp(1))

            piles = [0] * (self.rows + 1)
            for index, offsets in enumerate(self.paths):
                age = self.seconds - .16 - index * .059
                if age < 0:
                    break
                if index % 5 == 0:
                    Color(.97, .69, .34, 1)
                else:
                    Color(.67, .93, .82, 1)
                column = int(offsets[-1] + self.rows / 2)
                rank = piles[column]
                if age >= self.fall_seconds:
                    piles[column] += 1
                target_x = self.center_x + offsets[-1] * spacing + (rank % 3 - 1) * ball_radius * 2.15
                target_y = ground + ball_radius * (1.2 + 2.15 * (rank // 3))
                if age < .34:
                    dot(self.center_x, top + (1 - age / .34) * peg_gap * .9, ball_radius)
                elif age < 2.85:
                    progress = (age - .34) / 2.51 * self.rows
                    row = min(self.rows - 1, int(progress))
                    fraction = progress - row
                    offset = offsets[row] + (offsets[row + 1] - offsets[row]) * fraction
                    dot(self.center_x + offset * spacing,
                        top - progress * peg_gap + sin(fraction * pi) * ball_radius * .35, ball_radius)
                elif age < self.fall_seconds:
                    fraction = (age - 2.85) / (self.fall_seconds - 2.85)
                    x = self.center_x + offsets[-1] * spacing
                    dot(x + (target_x - x) * fraction,
                        bins_top + (target_y - bins_top) * fraction ** 2, ball_radius)
                else:
                    dot(target_x, target_y, ball_radius)
