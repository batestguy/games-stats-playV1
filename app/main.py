"""Internal device prototype for the Kivy accessibility check."""

import json
import webbrowser
from base64 import b64decode
from io import BytesIO
from math import ceil
from pathlib import Path
from random import Random
from time import monotonic_ns

from kivy import kivy_data_dir
from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as TextureImage
from kivy.core.text import Label as TextureLabel
from kivy.core.window import Window
from kivy.graphics import Color, PopMatrix, PushMatrix, Rectangle, Rotate
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform

from game import (
    AI_ML, LEVELS, MAX_ROUND_SIZE, PASS_RATE, PLAY_LEVELS, PRO, QUESTION_MS, ROUND_SIZE,
    Match, Progress, Turn,
    load_question_bank, match_questions, score, solo_questions,
)
from equations import equation_parts
from hints import reflection_hint
from presentation import (
    INTRO_SECONDS, GaltonBoard, match_names, nickname,
    read_nickname, reduced_motion, save_nickname,
)

TITLE = "Games Statisticians Play"
INK = (0.95, 0.97, 1, 1)
MUTED = (0.72, 0.82, 0.9, 1)
BACKGROUND = (0.08, 0.13, 0.2, 1)
BUTTON = (0.17, 0.29, 0.41, 1)
ACCENT = (0.71, 0.91, 0.83, 1)
PLAYERS = ("Player 1", "Player 2")
SECRETARIES = {
    "ai": "Madame Overfit", "pro": "Mixed Effects",
    "year100": "Mean Streak", "year200": "Belle Curve", "year300": "P. Value",
    "year400": "High Leverage", "final": "Strata Sphere", "graduate": "Prior Belief",
}
SECTION_HOSTS = {
    "100": "year100", "200": "year200", "300": "year300", "400": "year400",
    "Final Year": "final", "Graduate Mix": "graduate", AI_ML: "ai", PRO: "pro",
}
FORMULA_FONT = str(Path(kivy_data_dir) / "fonts" / "DejaVuSans.ttf")
ASSETS = Path(__file__).with_name("assets")


class HomeSymbols(Widget):
    """Paint decorative marks without putting them in the reading order."""

    marks = (
        ("σ²", .07, .82, 24, -13), ("β₁", .22, .74, 20, 9), ("P(A)", .39, .85, 15, -10),
        ("ŷ", .52, .75, 23, 12), ("∇L", .64, .85, 19, -13), ("AUC", .8, .76, 15, 8),
        ("ρ", .94, .83, 23, -12), ("z", .04, .39, 17, 10), ("x̄", .16, .48, 27, -8),
        ("R²", .32, .41, 19, 8), ("∑", .46, .51, 30, -7), ("ReLU", .64, .45, 14, 10),
        ("θ", .79, .48, 24, -12), ("λ", .92, .43, 22, 9), ("μ", .09, .12, 22, -10),
        ("k-NN", .26, .15, 15, 7), ("F₁", .42, .15, 21, 10),
        ("W·x", .56, .17, 17, -9), ("π", .73, .14, 21, 8), ("√n", .89, .11, 17, -10),
    )

    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=dp(112), **kwargs)
        self.symbols = []
        with self.canvas:
            for index, (mark, x, y, size, angle) in enumerate(self.marks):
                texture = TextureLabel(text=mark, font_name=FORMULA_FONT, font_size=dp(size))
                texture.refresh()
                color = ACCENT if index % 3 == 0 else MUTED
                Color(*color[:3], 0.56 if index % 3 == 0 else 0.43)
                PushMatrix()
                rotation = Rotate(angle=angle)
                rectangle = Rectangle(texture=texture.texture, size=texture.texture.size)
                PopMatrix()
                self.symbols.append((x, y, rotation, rectangle))
        self.bind(pos=self.place_symbols, size=self.place_symbols)
        self.place_symbols()

    def place_symbols(self, *_):
        for x, y, rotation, rectangle in self.symbols:
            origin = self.x + x * self.width, self.y + y * self.height
            rotation.origin = (*origin, 0)
            rectangle.pos = origin[0] - rectangle.size[0] / 2, origin[1] - rectangle.size[1] / 2


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


def open_blog(url):
    if platform == "android":
        from jnius import autoclass

        intent = autoclass("android.content.Intent")
        uri = autoclass("android.net.Uri").parse(url)
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        activity.startActivity(intent(intent.ACTION_VIEW, uri))
    else:
        webbrowser.open(url)


class QuizPrototype(App):
    title = f"{TITLE} (Volume 1)"

    def build(self):
        self.rng = Random()
        self.now = clock_for_device()
        self.bank = load_question_bank(ASSETS)
        self.equations = json.loads((ASSETS / "equations.json").read_text(encoding="utf-8"))
        self.equation_textures = {}
        self.progress = Progress(Path(self.user_data_dir) / "progress.json")
        self.match = None
        self.turn = None
        self.solo_results = []
        self.solo_items = []
        self.timer_label = None
        self.exit_popup = None
        self.intro_event = None
        self.solo_nickname = read_nickname(self.user_data_dir)
        self.players = PLAYERS
        Window.clearcolor = BACKGROUND
        self.page = BoxLayout(orientation="vertical")
        self.ticker = Clock.schedule_interval(self.tick, 0.1)
        return self.page

    def on_start(self):
        Clock.schedule_once(lambda _: self.opening(self.home))

    def on_pause(self):
        return True

    def on_resume(self):
        self.tick()

    def on_stop(self):
        self.ticker.cancel()
        self.stop_opening()

    def stop_opening(self):
        if self.intro_event is not None:
            self.intro_event.cancel()
            self.intro_event = None

    def opening(self, destination):
        self.stop_opening()
        self.page.clear_widgets()
        self.content = BoxLayout(orientation="vertical")
        self.page.add_widget(self.content)
        still = reduced_motion()
        illustration = GaltonBoard(still=still)
        self.content.add_widget(illustration)
        started = self.now()

        def animate(_):
            elapsed = (self.now() - started) / 1000
            if elapsed >= INTRO_SECONDS:
                self.stop_opening()
                destination()
            elif not still:
                illustration.set_time(elapsed)

        self.intro_event = Clock.schedule_interval(animate, 1 / 30)

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

    def label(self, text, font=18, color=INK, bold=False, font_name="Roboto", *, container=None):
        label = Label(
            text=text, color=color, bold=bold, font_size=sp(font), font_name=font_name,
            size_hint_y=None, height=0, halign="left", valign="top",
        )
        label.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        label.bind(texture_size=lambda widget, size: setattr(widget, "height", size[1]))
        (self.content if container is None else container).add_widget(label)
        return label

    def level_button(self, level, name, action, disabled):
        key = SECTION_HOSTS[level]
        button = self.button(f"{name}\n{SECRETARIES[key]}", action, disabled=disabled)
        button.halign = "left"
        button.padding = (dp(82), 0, 0, 0)
        button.height = dp(82)
        portrait = Image(
            source=str(ASSETS / f"secretary-{key}.jpg"), fit_mode="contain",
            size_hint=(None, None), size=(dp(58), dp(72)),
        )
        button.add_widget(portrait)

        def position(*_):
            button.height = max(dp(82), button.texture_size[1] + dp(18))
            portrait.x = button.x + dp(12)
            portrait.center_y = button.center_y

        button.bind(pos=position, size=position, texture_size=position)
        position()

    def nickname_input(self, caption, value=""):
        self.label(caption, 16, MUTED, bold=True)
        field = TextInput(
            text=value, multiline=False, font_name=FORMULA_FONT, font_size=sp(19),
            size_hint_y=None, height=max(dp(54), sp(23) + dp(24)), padding=(dp(12), dp(12)),
            background_normal="", background_active="", background_color=INK,
        )
        self.content.add_widget(field)
        return field

    def button(self, text, action, primary=False, disabled=False, font_name="Roboto", *, container=None, equation=None):
        button = Button(
            text=text, color=BACKGROUND if primary else INK, font_size=sp(18),
            font_name=font_name,
            size_hint_y=None, height=dp(52), halign="center", valign="middle",
            background_normal="", background_down="", background_color=ACCENT if primary else BUTTON,
            disabled=disabled,
        )
        button.bind(width=lambda widget, width: setattr(widget, "text_size", (max(dp(12), width - dp(24)), None)))
        if equation in self.equations:
            button.color = (0, 0, 0, 0)
            image = self.equation_image(equation)
            image.size_hint = (None, None)
            button.height = max(dp(52), image.height + dp(18))

            def place_image(*_):
                image.width = min(sp(self.equations[equation]["width"] / 2), max(0, button.width - dp(24)))
                image.center = button.center

            button.add_widget(image)
            button.bind(pos=place_image, size=place_image)
            place_image()
        else:
            button.bind(texture_size=lambda widget, size: setattr(widget, "height", max(dp(52), size[1] + dp(18))))
        button.bind(on_release=lambda *_: action())
        (self.content if container is None else container).add_widget(button)
        return button

    def equation_image(self, equation):
        data = self.equations[equation]
        if equation not in self.equation_textures:
            source = BytesIO(b64decode(data["png"]))
            self.equation_textures[equation] = TextureImage(
                source, ext="png", nocache=True, keep_data=True,
            ).texture
        return Image(
            texture=self.equation_textures[equation], fit_mode="scale-down",
            size_hint_y=None, height=sp(data["height"] / 2),
        )

    def show_clue(self, question, font=23):
        parts = equation_parts(question.math_clue)
        if not parts or any(part not in self.equations for is_math, part in parts if is_math):
            self.label(question.clue, font, font_name=FORMULA_FONT)
            return
        for is_math, part in parts:
            if is_math:
                self.content.add_widget(self.equation_image(part))
            else:
                self.label(part, font, font_name=FORMULA_FONT)

    def home(self):
        self.turn = None
        self.match = None
        self.players = PLAYERS
        self.solo_results = []
        self.solo_items = []
        self.screen()
        self.label("VOLUME 1 · ANDROID TEST", 14, ACCENT, bold=True)
        self.label(TITLE, 32, bold=True)
        self.label(f"{QUESTION_MS // 1000} seconds per question.", color=MUTED)
        self.content.add_widget(HomeSymbols())
        if self.solo_nickname:
            self.label(f"Welcome, {self.solo_nickname}.", color=MUTED, font_name=FORMULA_FONT)
        self.button("Solo", lambda: self.choose_level(solo=True), primary=True)
        self.button("Pass-and-play", lambda: self.choose_level(solo=False))
        self.button("About", self.about)

    def about(self):
        author = json.loads((ASSETS / "author.json").read_text(encoding="utf-8"))
        self.screen()
        self.label("About", 28, bold=True)
        self.label(
            f"{TITLE} · Volume 1 is an offline quiz about recognizing statistical ideas, "
            "reading formulas, and choosing the right method for a problem. "
            "Each question gives you five choices and 25 seconds to answer."
        )
        for heading, description in (
            ("Solo", "Choose 1–20 questions. Get every answer right in a completed round to unlock "
             "the next statistics level. Review hints and explanations as you play."),
            ("Pass-and-play", "Share one device. Both players answer the same number of questions, "
             "matched by level and difficulty. Review answers together after the match."),
            ("More ways to play", "The six statistics levels run from Level 100 to Graduate Mix. "
             "AI/ML Bonus focuses on machine learning, and Pro mixes questions from across the game. "
             "Both are available from the start."),
        ):
            self.label(heading, 21, bold=True)
            self.label(description, color=MUTED)
        self.button("Watch the opening", lambda: self.opening(self.about))
        self.label("About the creator", 23, bold=True)
        self.content.add_widget(Image(
            source=str(ASSETS / author["photo"]), fit_mode="contain",
            size_hint_y=None, height=dp(160),
        ))
        self.label(author["name"], 25, bold=True)
        self.label(author["bio"], color=MUTED)
        self.button("Visit the author's blog", lambda: open_blog(author["url"]), primary=True)
        self.button("Back to home", self.home)

    def choose_level(self, solo):
        self.screen()
        self.label("Solo" if solo else "Pass-and-play", 28, bold=True)
        self.label("Choose a level", 21, bold=True)
        self.label("Meet the World Statistics Secretaries", 16, color=ACCENT)
        if solo:
            self.label("Get every question right in a round to unlock the next year.", color=MUTED)
        for level in PLAY_LEVELS:
            name = level_name(level)
            locked = solo and not self.progress.unlocked(level)
            if locked:
                name += " · Locked"
            if solo and level in self.progress.best:
                name += f" · Best {float(self.progress.best[level]):.0%}"
            self.level_button(level, name, lambda level=level: self.choose_round_length(level, solo), locked)
        self.button("Back to home", self.home)

    def choose_round_length(self, level, solo, initial_length=ROUND_SIZE):
        self.screen()
        self.label("Round setup" if solo else "Match setup", 28, bold=True)
        unit = "questions" if solo else "questions per player"
        self.label(f"{level_name(level)} · 1 to {MAX_ROUND_SIZE} {unit}", color=MUTED)
        if level == PRO:
            self.label("Mostly higher years, with AI/ML and earlier years mixed in.", color=MUTED)
        name_fields = ([self.nickname_input("Nickname (optional)", self.solo_nickname)] if solo else
                       [self.nickname_input(f"{player} nickname (optional)") for player in PLAYERS])
        self.label("Questions" if solo else "Questions per player", 16, MUTED, bold=True)
        length = TextInput(
            text=str(initial_length), multiline=False, input_filter="int",
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
            if solo:
                self.solo_nickname = nickname(name_fields[0].text)
                save_nickname(self.user_data_dir, self.solo_nickname)
                self.start_solo(level, int(value))
            else:
                self.players = match_names(*(field.text for field in name_fields))
                self.start_match(level, int(value))

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
            name = self.solo_nickname or "Player"
            message = f"Round complete, {name}."
            if points == index:
                message = f"Perfect round, {name}."
            self.label(message, color=MUTED, font_name=FORMULA_FONT)
            if self.level in LEVELS[:-1] and self.progress.best[self.level] >= PASS_RATE:
                next_level = LEVELS[LEVELS.index(self.level) + 1]
                self.label(f"Next level available · {level_name(next_level)}", color=ACCENT)
            self.button("Play this level again", lambda: self.start_solo(self.level, self.round_length))
            self.button("Choose a level", lambda: self.choose_level(solo=True))
            self.button("Back to home", self.home, primary=True)
            return
        self.show_turn(
            Turn(self.solo_items[index], self.rng, self.now()),
            f"{self.solo_nickname or 'Player'} · {index + 1} of {len(self.solo_items)}",
        )

    def start_match(self, level, length):
        self.level = level
        self.round_length = length
        self.match = Match(match_questions(self.bank, level, self.rng, rounds=length), self.rng, rounds=length)
        self.handover()

    def handover(self):
        self.screen()
        self.label("PASS THE PHONE", 14, ACCENT, bold=True)
        player = self.players[self.match.player]
        self.label(f"{player}, your turn", 28, bold=True, font_name=FORMULA_FONT)
        other = self.players[1 - self.match.player]
        message = (f"{player}, tap Ready when you have the phone." if self.match.pair_index == 0 and self.match.player == 0 else
                   f"{other}, pass the phone to {player}. The countdown starts at Ready.")
        self.label(message, color=MUTED, font_name=FORMULA_FONT)
        self.button("Ready", self.ready, primary=True)
        self.exit_button()

    def ready(self):
        turn = self.match.ready(self.now())
        if turn:
            stage = f"Round {self.match.pair_index + 1} of {self.match.rounds}"
            if self.match.pair_index >= self.match.rounds:
                stage = "Sudden death"
            self.show_turn(turn, f"{self.players[self.match.player]} · {stage}")

    def show_turn(self, turn, heading):
        self.screen()
        self.turn = turn
        self.label(heading, 16, MUTED, bold=True, font_name=FORMULA_FONT)
        self.timer_label = self.label(f"{QUESTION_MS // 1000} seconds", 20, ACCENT, bold=True)
        self.label("Answer the question", 26, bold=True)
        self.show_clue(turn.question)
        for choice in turn.choices:
            self.button(
                choice, lambda choice=choice: self.answer(turn, choice), font_name=FORMULA_FONT,
                equation=turn.question.math_choices.get(choice),
            )
        self.exit_button()

    def tick(self, *_):
        if self.turn is None:
            return
        remaining = self.turn.deadline_ms - self.now()
        seconds = max(0, ceil(remaining / 1000))
        unit = "second" if seconds == 1 else "seconds"
        self.timer_label.text = f"{seconds} {unit}"
        if remaining <= 0 and self.exit_popup is None:
            self.answer(self.turn, None)

    def exit_button(self):
        activity = "round" if self.match is None else "match"
        self.button(f"Exit {activity}", lambda: self.confirm_exit(activity))

    def confirm_exit(self, activity):
        if self.exit_popup is not None:
            return
        panel = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(panel)
        popup = Popup(
            title=f"Exit {activity}?", content=scroll, auto_dismiss=False,
            size_hint=(0.92, None), title_color=INK, separator_color=BUTTON,
        )

        def close(leave):
            popup.dismiss()
            self.exit_popup = None
            if leave:
                self.home()
            else:
                self.tick()

        self.label(f"Leave this {activity} and return home?", color=MUTED, container=panel)
        self.button("Keep playing", lambda: close(False), primary=True, container=panel)
        self.button(f"Exit {activity}", lambda: close(True), container=panel)
        def fit_popup(*_):
            popup.height = min(Window.height * .9, max(dp(230), panel.height + dp(66)))

        panel.bind(height=fit_popup)
        popup.bind(width=fit_popup)
        fit_popup()
        self.exit_popup = popup
        popup.open()

    def answer(self, turn, choice):
        if turn is not self.turn or self.exit_popup is not None:
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

    def show_outcome(self, outcome, *, review=False):
        status = "Correct" if outcome.correct else "Time’s up" if outcome.choice is None else "Incorrect"
        self.label(status, 16, ACCENT, bold=True)
        question = outcome.question
        if outcome.correct:
            equation = question.math_choices.get(question.answer)
            if equation in self.equations:
                self.content.add_widget(self.equation_image(equation))
            else:
                self.label(question.answer, 18 if review else 27, font_name=FORMULA_FONT)
            detail = question.explanation
        else:
            if review:
                self.show_clue(question, 18)
            detail = reflection_hint(question)
        self.label(detail, font_name=FORMULA_FONT)

    def solo_feedback(self, outcome):
        self.screen()
        self.show_outcome(outcome)
        self.button("Next", self.next_solo, primary=True)
        if len(self.solo_results) < self.round_length:
            self.exit_button()

    def match_results(self):
        self.screen()
        winner = self.match.winner
        self.label("Draw" if winner is None else f"{self.players[winner]} wins", 28, bold=True, font_name=FORMULA_FONT)
        self.label("Both players can review their answers below.", color=MUTED)
        self.button("Play this level again", lambda: self.choose_round_length(self.level, False, self.round_length))
        self.button("Choose a level", lambda: self.choose_level(solo=False))
        self.button("Back to home", self.home, primary=True)
        for player, outcomes in zip(self.players, self.match.results):
            rounds = self.match.rounds
            self.label(f"{player} · {score(outcomes[:rounds])} of {rounds} correct", 20, ACCENT,
                       bold=True, font_name=FORMULA_FONT)
            for outcome in outcomes:
                self.show_outcome(outcome, review=True)


if __name__ == "__main__":
    QuizPrototype().run()
