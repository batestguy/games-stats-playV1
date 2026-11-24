"""Offline game rules shared by the prototype and future release screens."""

from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from random import Random
import json
import os
import tempfile

LEVELS = ("100", "200", "300", "400", "Final Year", "Graduate Mix")
AI_ML = "AI/ML"
PRO = "Pro"
QUESTION_LEVELS = (*LEVELS, AI_ML)
PLAY_LEVELS = (*QUESTION_LEVELS, PRO)
QUESTION_MS = 25_000
ROUND_SIZE = 10
MAX_ROUND_SIZE = 20
PASS_RATE = Fraction(1)
TIE_LIMIT = 3


@dataclass(frozen=True)
class Question:
    id: str
    concept: str
    level: str
    difficulty: str
    clue_type: str
    clue: str
    choices: tuple[str, ...]
    answer: str
    explanation: str
    reference: str
    convention: str = ""
    math_clue: str = ""
    math_choices: dict[str, str] = field(default_factory=dict, hash=False)
    math_explanation: str = ""


def load_bank(path: Path) -> list[Question]:
    bank = json.loads(path.read_text(encoding="utf-8"))
    if bank["version"] != 1:
        raise ValueError("Unsupported question bank version")
    questions = []
    seen = set()
    for row in bank["questions"]:
        if not isinstance(row["choices"], list):
            raise ValueError(f"Question {row['id']} must store choices in an array")
        item = Question(**{**row, "choices": tuple(row["choices"])})
        if not all(isinstance(value, str) and value.strip() for value in (
            item.id, item.concept, item.clue, item.reference, item.explanation,
            item.answer, *item.choices
        )):
            raise ValueError("Question fields must contain text")
        if (
            item.id in seen
            or item.level not in QUESTION_LEVELS
            or item.difficulty not in ("easy", "medium", "hard")
            or item.clue_type not in ("definition", "scenario", "formula")
            or len(item.choices) != 5
            or len({choice.strip().casefold() for choice in item.choices}) != 5
            or item.answer not in item.choices
            or not isinstance(item.convention, str)
            or not isinstance(item.math_clue, str)
            or not isinstance(item.math_explanation, str)
            or not isinstance(item.math_choices, dict)
            or any(choice not in item.choices or not isinstance(tex, str) or not tex.strip()
                   for choice, tex in item.math_choices.items())
        ):
            raise ValueError(f"Invalid question {item.id}")
        seen.add(item.id)
        questions.append(item)
    return questions


def bank_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return [path]
    return [path / "sample-bank.v1.json", *sorted(path.glob("questions-*.v1.json"))]


def load_question_bank(path: Path) -> list[Question]:
    questions = [question for file in bank_files(path) for question in load_bank(file)]
    if len({question.id for question in questions}) != len(questions):
        raise ValueError("Duplicate question ID across bank files")
    return questions


def eligible_levels(level):
    if level == PRO:
        return QUESTION_LEVELS
    if level == AI_ML:
        return (AI_ML,)
    return LEVELS[:LEVELS.index(level) + 1]


def review_count(level, count):
    if type(count) is not int or not 1 <= count <= MAX_ROUND_SIZE:
        raise ValueError(f"Round length must be a whole number from 1 to {MAX_ROUND_SIZE}")
    return 0 if level in (LEVELS[0], AI_ML) else (count + 2) // 5


def round_draws(level, count, rng: Random):
    """Return source pools and quotas, with the first pool supplying tie pairs."""
    review = review_count(level, count)
    if level == PRO:
        # Use one random offset to round both cumulative cutoffs. This keeps all
        # three pools eligible even at length one and gives exact quotas at 10 and 20.
        offset = rng.randrange(10)
        advanced = (7 * count + offset) // 10
        advanced_and_bonus = (9 * count + offset) // 10
        return (
            (LEVELS[3:], advanced),
            ((AI_ML,), advanced_and_bonus - advanced),
            (LEVELS[:3], count - advanced_and_bonus),
        )
    sources = eligible_levels(level)
    return ((sources[-1:], count - review), (sources[:-1], review))


def solo_questions(bank, level, rng: Random, count=ROUND_SIZE):
    questions = []
    for sources, quota in round_draws(level, count, rng):
        if quota:
            questions.extend(rng.sample([item for item in bank if item.level in sources], quota))
    rng.shuffle(questions)
    return questions


def pair_pool(bank, level, rng: Random):
    groups = defaultdict(list)
    for item in bank:
        if item.level == level:
            groups[item.difficulty, item.clue_type].append(item)
    pairs = []
    for items in groups.values():
        concepts = defaultdict(list)
        for item in items:
            concepts[item.concept.strip().casefold()].append(item)
        pools = list(concepts.values())
        for pool in pools:
            rng.shuffle(pool)
        # Taking from the two largest pools preserves the maximum pair count.
        while len(pools) >= 2:
            rng.shuffle(pools)
            pools.sort(key=len, reverse=True)
            pair = [pools[0].pop(), pools[1].pop()]
            rng.shuffle(pair)
            pairs.append(tuple(pair))
            pools = [pool for pool in pools if pool]
    return pairs


def matched_pairs(bank, level, rng: Random, count=ROUND_SIZE + TIE_LIMIT):
    pairs = pair_pool(bank, level, rng)
    if len(pairs) < count:
        raise ValueError(f"{level} has {len(pairs)} matched pairs, needs {count}")
    return rng.sample(pairs, count)


def match_questions(bank, level, rng: Random, rounds=ROUND_SIZE):
    """Match both players' source levels and draw reserves from the primary pool."""
    regular = []
    reserve = []
    for index, (sources, quota) in enumerate(round_draws(level, rounds, rng)):
        extra = TIE_LIMIT if index == 0 else 0
        if quota + extra:
            pool = [pair for source in sources for pair in pair_pool(bank, source, rng)]
            if len(pool) < quota + extra:
                raise ValueError(f"{', '.join(sources)} has {len(pool)} matched pairs, needs {quota + extra}")
            pairs = rng.sample(pool, quota + extra)
            regular.extend(pairs[:quota])
            reserve.extend(pairs[quota:])
    rng.shuffle(regular)
    return regular + reserve


@dataclass(frozen=True)
class Outcome:
    question: Question
    choice: str | None
    elapsed_ms: int

    @property
    def correct(self):
        return self.choice == self.question.answer


class Turn:
    def __init__(self, question: Question, rng: Random, start_ms: int):
        self.question = question
        self.choices = rng.sample(question.choices, len(question.choices))
        self.start_ms = start_ms
        self.deadline_ms = start_ms + QUESTION_MS
        self.outcome = None

    def resolve(self, choice: str | None, now_ms: int):
        if self.outcome is not None or now_ms < self.start_ms:
            return None
        if now_ms >= self.deadline_ms:
            self.outcome = Outcome(self.question, None, QUESTION_MS)
        elif choice in self.choices:
            self.outcome = Outcome(self.question, choice, now_ms - self.start_ms)
        return self.outcome


def score(outcomes):
    return sum(outcome.correct for outcome in outcomes)


def average_correct_ms(outcomes):
    correct_times = [outcome.elapsed_ms for outcome in outcomes if outcome.correct]
    if correct_times:
        return Fraction(sum(correct_times), len(correct_times))
    return None


class Match:
    """Owns turn order, handover, regulation scoring, and sudden death."""

    def __init__(self, pairs, rng: Random, rounds=ROUND_SIZE, tie_limit=TIE_LIMIT):
        if rounds < 1 or tie_limit < 0 or len(pairs) < rounds + tie_limit:
            raise ValueError("Insufficient pairs for the match")
        self.pairs = pairs
        self.rng = rng
        self.rounds = rounds
        self.tie_limit = tie_limit
        self.results = ([], [])
        self.index = 0
        self.turn = None
        self.winner = None
        self.finished = False

    @property
    def player(self):
        return self.index % 2

    @property
    def pair_index(self):
        return self.index // 2

    def ready(self, now_ms):
        if self.finished or self.turn is not None:
            return None
        self.turn = Turn(self.pairs[self.pair_index][self.player], self.rng, now_ms)
        return self.turn

    def resolve(self, turn, choice, now_ms):
        if turn is None or turn is not self.turn:
            return None
        outcome = turn.resolve(choice, now_ms)
        if outcome is None:
            return None
        self.results[self.player].append(outcome)
        self.index += 1
        self.turn = None
        if self.player == 0 and self.pair_index >= self.rounds:
            self._complete_pair()
        return outcome

    def _complete_pair(self):
        left, right = self.results
        if self.pair_index == self.rounds:
            scores = [score(outcomes) for outcomes in self.results]
            if scores[0] != scores[1]:
                self.winner = 0 if scores[0] > scores[1] else 1
            elif scores[0]:
                times = [average_correct_ms(outcomes) for outcomes in self.results]
                if times[0] != times[1]:
                    self.winner = 0 if times[0] < times[1] else 1
        elif left[-1].correct != right[-1].correct:
            self.winner = 0 if left[-1].correct else 1
        self.finished = self.winner is not None or self.pair_index == self.rounds + self.tie_limit


class Progress:
    """Save the best accuracy per level, deriving unlocks from completed rounds."""

    def __init__(self, path: Path):
        self.path = path
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {"version": 2, "best": {}}
        if data["version"] not in (1, 2):
            raise ValueError("Unsupported progress version")
        self.best = {}
        for level, value in data["best"].items():
            if data["version"] == 1:
                value = [value, ROUND_SIZE]
            if level in PLAY_LEVELS and isinstance(value, list) and len(value) == 2:
                points, count = value
                if type(points) is int and type(count) is int and 1 <= count <= MAX_ROUND_SIZE and 0 <= points <= count:
                    self.best[level] = Fraction(points, count)

    def unlocked(self, level):
        return level in (AI_ML, PRO) or all(
            self.best.get(prior, 0) >= PASS_RATE for prior in eligible_levels(level)[:-1]
        )

    def record(self, level, outcomes):
        sources = eligible_levels(level)
        if (
            not 1 <= len(outcomes) <= MAX_ROUND_SIZE or not self.unlocked(level)
            or any(item.question.level not in sources for item in outcomes)
        ):
            raise ValueError("Only completed rounds at unlocked levels can be saved")
        accuracy = Fraction(score(outcomes), len(outcomes))
        if accuracy <= self.best.get(level, -1):
            return
        best = {**self.best, level: accuracy}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as stream:
                temp = Path(stream.name)
                scores = {level: [rate.numerator, rate.denominator] for level, rate in best.items()}
                json.dump({"version": 2, "best": scores}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            temp.replace(self.path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        self.best = best
