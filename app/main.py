"""Internal device prototype for the Kivy accessibility check."""

from math import ceil
from pathlib import Path
from random import Random
from time import monotonic_ns

from kivy import kivy_data_dir
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import platform

from game import (
    AI_ML, LEVELS, MAX_ROUND_SIZE, PASS_RATE, PLAY_LEVELS, PRO, QUESTION_MS, ROUND_SIZE,
    Match, Progress, Turn,
    load_question_bank, match_questions, score, solo_questions,
)

TITLE = "Games Statisticians Play"
INK = (0.95, 0.97, 1, 1)
MUTED = (0.72, 0.82, 0.9, 1)
BACKGROUND = (0.08, 0.13, 0.2, 1)
BUTTON = (0.17, 0.29, 0.41, 1)
ACCENT = (0.71, 0.91, 0.83, 1)
PLAYERS = ("Player 1", "Player 2")
FORMULA_FONT = str(Path(kivy_data_dir) / "fonts" / "DejaVuSans.ttf")


def level_name(level):
    if level.isdigit():
        return f"Level {level}"
    return {AI_ML: "AI/ML Bonus", PRO: "Pro · Bring It All"}.get(level, level)


def clock_for_device():
    if platform == "android":
        from jnius import autoclass

        # Includes time spent in Android deep sleep.
        return autoclass("android.os.SystemClock").elapsedRealtime
    return lambda: monotonic_ns() // 1_000_000


class QuizPrototype(App):
    title = f"{TITLE} (Volume 1)"

    def build(self):
        self.rng = Random()
        self.now = clock_for_device()
        self.bank = load_question_bank(Path(__file__).with_name("assets"))
        self.progress = Progress(Path(self.user_data_dir) / "progress.json")
        self.match = None
        self.turn = None
        self.solo_results = []
        self.timer_label = None
        Window.clearcolor = BACKGROUND
        self.page = BoxLayout(orientation="vertical")
        self.home()
        self.ticker = Clock.schedule_interval(self.tick, 0.1)
        return self.page

    def on_pause(self):
        return True

    def on_resume(self):
        self.tick()

    def on_stop(self):
        self.ticker.cancel()

    def screen(self):
        self.page.clear_widgets()
        self.timer_label = None
        scroll = ScrollView(do_scroll_x=False)
        self.content = BoxLayout(
            orientation="vertical", size_hint_y=None, padding=dp(20), spacing=dp(12)
        )
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        self.page.add_widget(scroll)

    def label(self, text, font=18, color=INK, bold=False, font_name="Roboto"):
        label = Label(
            text=text, color=color, bold=bold, font_size=sp(font), font_name=font_name,
            size_hint_y=None, height=0, halign="left", valign="top",
        )
        label.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        label.bind(texture_size=lambda widget, size: setattr(widget, "height", size[1]))
        self.content.add_widget(label)
        return label

    def button(self, text, action, primary=False, disabled=False, font_name="Roboto"):
        button = Button(
            text=text, color=BACKGROUND if primary else INK, font_size=sp(18),
            font_name=font_name,
            size_hint_y=None, height=dp(52), halign="center", valign="middle",
            background_normal="", background_down="", background_color=ACCENT if primary else BUTTON,
            disabled=disabled,
        )
        button.bind(width=lambda widget, width: setattr(widget, "text_size", (max(dp(12), width - dp(24)), None)))
        button.bind(texture_size=lambda widget, size: setattr(widget, "height", max(dp(52), size[1] + dp(18))))
        button.bind(on_release=lambda *_: action())
        self.content.add_widget(button)

    def home(self):
        self.turn = None
        self.match = None
        self.screen()
        self.label("VOLUME 1 · ANDROID TEST", 14, ACCENT, bold=True)
        self.label(TITLE, 32, bold=True)
        self.label("Name the statistical concept. You have 10 seconds for each question.", color=MUTED)
        self.button("Solo", lambda: self.choose_level(solo=True), primary=True)
        self.button("Pass-and-play", lambda: self.choose_level(solo=False))

    def choose_level(self, solo):
        self.screen()
        self.label("Solo" if solo else "Pass-and-play", 28, bold=True)
        self.label("Choose a level", color=MUTED)
        for level in PLAY_LEVELS:
            name = level_name(level)
            locked = solo and not self.progress.unlocked(level)
            if locked:
                name += " · Locked"
            elif solo and level in self.progress.best:
                name += f" · Best {float(self.progress.best[level]):.0%}"
            self.button(name, lambda level=level: self.choose_round_length(level, solo), disabled=locked)
        self.button("Back to home", self.home)

    def choose_round_length(self, level, solo):
        self.screen()
        self.label("Round length", 28, bold=True)
        unit = "questions" if solo else "questions per player"
        self.label(f"{level_name(level)} · 1 to {MAX_ROUND_SIZE} {unit}", color=MUTED)
        if level == PRO:
            self.label("Mostly higher years, with AI/ML and earlier years mixed in.", color=MUTED)
        length = TextInput(
            text=str(ROUND_SIZE), multiline=False, input_filter="int",
            input_type="number", font_size=sp(20), size_hint_y=None,
            height=max(dp(60), sp(24) + dp(28)), padding=(dp(14), dp(14)),
            background_normal="", background_active="", background_color=INK,
        )
        self.content.add_widget(length)
        error = self.label("", color=MUTED)

        def start():
            value = length.text.strip()
            if not value.isdecimal() or len(value) > 2 or not 1 <= int(value) <= MAX_ROUND_SIZE:
                error.text = f"Enter a whole number from 1 to {MAX_ROUND_SIZE}."
                return
            length.focus = False
            play = self.start_solo if solo else self.start_match
            play(level, int(value))

        length.bind(on_text_validate=lambda *_: start())
        self.button("Start round" if solo else "Start match", start, primary=True)
        self.button("Back to levels", lambda: self.choose_level(solo))

    def start_solo(self, level, length):
        self.level = level
        self.round_length = length
        self.solo_results = []
        self.solo_items = solo_questions(self.bank, level, self.rng, count=length)
        self.next_solo()

    def next_solo(self):
        index = len(self.solo_results)
        if index == len(self.solo_items):
            self.screen()
            points = score(self.solo_results)
            self.label(f"{points} of {index} correct", 28, bold=True)
            if self.level in LEVELS[:-1] and self.progress.best[self.level] >= PASS_RATE:
                next_level = LEVELS[LEVELS.index(self.level) + 1]
                self.label(f"Next level available · {level_name(next_level)}", color=ACCENT)
            self.button("Play this level again", lambda: self.start_solo(self.level, self.round_length))
            self.button("Choose a level", lambda: self.choose_level(solo=True))
            self.button("Back to home", self.home, primary=True)
            return
        self.show_turn(
            Turn(self.solo_items[index], self.rng, self.now()),
            f"Solo · {index + 1} of {len(self.solo_items)}",
        )

    def start_match(self, level, length):
        self.level = level
        self.round_length = length
        self.match = Match(match_questions(self.bank, level, self.rng, rounds=length), self.rng, rounds=length)
        self.handover()

    def handover(self):
        self.screen()
        self.label("PASS THE PHONE", 14, ACCENT, bold=True)
        self.label(f"{PLAYERS[self.match.player]}, your turn", 28, bold=True)
        self.label("The countdown starts when you tap Ready.", color=MUTED)
        self.button("Ready", self.ready, primary=True)

    def ready(self):
        turn = self.match.ready(self.now())
        if turn:
            stage = f"Round {self.match.pair_index + 1} of {self.match.rounds}"
            if self.match.pair_index >= self.match.rounds:
                stage = "Sudden death"
            self.show_turn(turn, f"{PLAYERS[self.match.player]} · {stage}")

    def show_turn(self, turn, heading):
        self.screen()
        self.turn = turn
        self.label(heading, 16, MUTED, bold=True)
        self.timer_label = self.label("10 seconds", 20, ACCENT, bold=True)
        self.label(turn.question.clue, 23, font_name=FORMULA_FONT)
        for choice in turn.choices:
            self.button(choice, lambda choice=choice: self.answer(turn, choice), font_name=FORMULA_FONT)

    def tick(self, *_):
        if self.turn is None:
            return
        remaining = self.turn.deadline_ms - self.now()
        if remaining <= 0:
            self.answer(self.turn, None)
        else:
            self.timer_label.text = f"{ceil(remaining / (QUESTION_MS / 10))} seconds"

    def answer(self, turn, choice):
        if turn is not self.turn:
            return
        now = self.now()
        if self.match is None:
            outcome = turn.resolve(choice, now)
        else:
            outcome = self.match.resolve(turn, choice, now)
        if outcome is None:
            return
        self.turn = None
        if self.match is None:
            self.solo_results.append(outcome)
            if len(self.solo_results) == self.round_length:
                self.progress.record(self.level, self.solo_results)
            self.solo_feedback(outcome)
        elif self.match.finished:
            self.match_results()
        else:
            self.handover()

    def solo_feedback(self, outcome):
        self.screen()
        status = "Correct" if outcome.correct else "Time’s up" if outcome.choice is None else "Incorrect"
        self.label(status, 16, ACCENT, bold=True)
        self.label(outcome.question.answer, 27, font_name=FORMULA_FONT)
        self.label(outcome.question.explanation, font_name=FORMULA_FONT)
        self.button("Next", self.next_solo, primary=True)

    def match_results(self):
        self.screen()
        winner = self.match.winner
        self.label("Draw" if winner is None else f"{PLAYERS[winner]} wins", 28, bold=True)
        self.button("Play this level again", lambda: self.start_match(self.level, self.round_length))
        self.button("Choose a level", lambda: self.choose_level(solo=False))
        self.button("Back to home", self.home, primary=True)
        for player, outcomes in zip(PLAYERS, self.match.results):
            rounds = self.match.rounds
            self.label(f"{player} · {score(outcomes[:rounds])} of {rounds} correct", 20, ACCENT, bold=True)
            for outcome in outcomes:
                self.label(
                    f"{outcome.question.answer}\n{outcome.question.explanation}",
                    17, font_name=FORMULA_FONT,
                )


if __name__ == "__main__":
    QuizPrototype().run()
