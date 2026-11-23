from collections import Counter
from base64 import b64decode
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from random import Random
import re
import json

import pytest

from app.game import (
    AI_ML, LEVELS, MAX_ROUND_SIZE, PRO, QUESTION_MS, Match, Outcome, Progress, Turn, load_bank,
    load_question_bank, match_questions, matched_pairs, score, solo_questions,
)
from app.equations import equation_parts
from app.hints import CLUE_PROMPTS, GENERAL_PROMPTS, normalized, reflection_hint

ASSETS = Path(__file__).parents[1] / "app" / "assets"


@pytest.fixture
def bank():
    return load_bank(ASSETS / "sample-bank.v1.json")


def test_bundled_missed_question_hints_do_not_repeat_answers():
    generic = {*CLUE_PROMPTS.values(), *GENERAL_PROMPTS}
    questions = load_question_bank(ASSETS)
    for question in questions:
        hint = reflection_hint(question)
        answer = re.escape(normalized(question.answer))
        assert not re.search(rf"(?<!\w){answer}(?!\w)", normalized(hint)), question.id
        assert normalized(hint) != normalized(question.explanation), question.id
    examples = {reflection_hint(q) for q in questions if q.id in ("sample-100-04", "aiml-046")}
    assert len(examples) == 2 and not examples & generic


def test_bundled_equations_have_matching_offline_images():
    images = json.loads((ASSETS / "equations.json").read_text(encoding="utf-8"))
    authored = set()
    for question in load_question_bank(ASSETS):
        parts = {part for is_math, part in equation_parts(question.math_clue) if is_math}
        parts.update(question.math_choices.values())
        if question.clue_type == "formula":
            assert parts, question.id
        authored.update(parts)
    assert authored == images.keys()
    for image in images.values():
        assert image["width"] > 0 and image["height"] > 0
        assert b64decode(image["png"], validate=True).startswith(b"\x89PNG\r\n\x1a\n")


def test_answer_at_deadline_is_timeout_and_does_not_accept_second_outcome(bank):
    question = bank[0]
    turn = Turn(question, Random(1), 25)
    assert QUESTION_MS == 25_000
    assert turn.deadline_ms == 25_025
    assert turn.resolve(None, 24) is None
    assert turn.resolve(None, 25_024) is None
    assert turn.resolve(question.answer, 25_025) == Outcome(question, None, QUESTION_MS)
    assert turn.resolve(question.answer, 25_026) is None


def test_answer_one_millisecond_before_deadline_counts(bank):
    question = bank[0]
    turn = Turn(question, Random(1), 25)
    assert turn.resolve(question.answer, 25_024) == Outcome(question, question.answer, 24_999)


def test_pairing_keeps_all_possible_pairs_with_uneven_concept_counts(bank):
    questions = [
        replace(bank[0], id=str(i), concept=concept)
        for i, concept in enumerate(("A", "A", "A", "B", "B", "C"))
    ]
    pairs = matched_pairs(questions, "100", Random(4), count=3)
    assert all(a.concept != b.concept for a, b in pairs)
    assert len({q.id for pair in pairs for q in pair}) == 6


@pytest.mark.parametrize("level", LEVELS)
def test_full_round_and_match_for_each_level(level):
    questions = load_question_bank(ASSETS)
    rng = Random(91)
    solo = solo_questions(questions, level, rng)
    assert len(solo) == len({q.id for q in solo}) == 10
    timestamp = 0
    outcomes = []
    for i, question in enumerate(solo):
        turn = Turn(question, rng, timestamp)
        elapsed = 1000 if i < 6 else QUESTION_MS
        outcomes.append(turn.resolve(question.answer, timestamp + elapsed))
        timestamp += 20_000
    assert score(outcomes) == 6

    pairs = match_questions(questions, level, rng)
    assert len({q.id for pair in pairs for q in pair}) == 26
    assert all(
        a.level == b.level and LEVELS.index(a.level) <= LEVELS.index(level) and a.concept != b.concept
        and a.clue_type == b.clue_type and a.difficulty == b.difficulty
        for a, b in pairs
    )
    match = Match(pairs, rng)
    stale = None
    for i in range(20):
        assert match.turn is None and match.player == i % 2
        timestamp += 20_000
        turn = match.ready(timestamp)
        assert match.ready(timestamp + 1) is None
        assert match.resolve(stale, turn.question.answer, timestamp + 1) is None
        choice = turn.question.answer
        elapsed = 1200 if i % 2 == 0 else 1400
        assert match.resolve(turn, choice, timestamp + elapsed).correct
        stale = turn
    assert match.finished and match.winner == 0
    assert match.ready(timestamp + 5000) is None


@pytest.mark.parametrize(
    ("hits", "winner", "pairs_played"),
    [
        ([(True, False)], 0, 1),
        ([(False, False), (True, True), (True, False)], 0, 3),
        ([(False, False), (True, True), (False, False), (True, True)], None, 4),
    ],
)
def test_sudden_death_uses_correctness_or_finishes_as_draw(bank, hits, winner, pairs_played):
    rng = Random(6)
    match = Match(matched_pairs(bank, "100", rng, count=4), rng, rounds=1)
    now = 0
    for pair in hits:
        for player, hit in enumerate(pair):
            assert match.player == player and not match.finished
            turn = match.ready(now)
            # Correct answers in a sudden-death pair tie even with unequal times.
            elapsed = 500 + player * 500 if hit else QUESTION_MS
            match.resolve(turn, turn.question.answer, now + elapsed)
            now += 20_000
    assert match.finished and match.winner == winner
    assert match.pair_index == pairs_played


def test_progress_persists_best_and_only_a_perfect_round_unlocks_next_level(tmp_path, bank):
    path = tmp_path / "progress.json"
    progress = Progress(path)
    question = bank[0]
    hit = Outcome(question, question.answer, 200)
    miss = Outcome(question, None, QUESTION_MS)
    assert progress.unlocked("100") and not progress.unlocked("200")
    with pytest.raises(ValueError):
        progress.record("200", [hit] * 10)
    progress.record("100", [hit] * 19 + [miss])
    assert Progress(path).best == {"100": Fraction(19, 20)}
    assert not Progress(path).unlocked("200")
    progress.record("100", [hit] * 3)
    progress.record("100", [miss] * 10)
    reopened = Progress(path)
    assert reopened.best == {"100": Fraction(1)}
    assert reopened.unlocked("200") and not reopened.unlocked("300")


@pytest.mark.parametrize("level", LEVELS)
def test_all_round_lengths_draw_the_same_review_share_for_both_modes(level):
    questions = load_question_bank(ASSETS)
    rng = Random(8)
    for length in range(1, MAX_ROUND_SIZE + 1):
        expected_review = 0 if level == "100" else round(length / 5)
        solo = solo_questions(questions, level, rng, count=length)
        assert len({q.id for q in solo}) == length
        assert sum(q.level != level for q in solo) == expected_review
        assert all(LEVELS.index(q.level) <= LEVELS.index(level) for q in solo)

        pairs = match_questions(questions, level, rng, rounds=length)
        assert len(pairs) == length + 3
        assert len({q.id for pair in pairs for q in pair}) == 2 * len(pairs)
        assert sum(a.level != level for a, _ in pairs[:length]) == expected_review
        assert all(a.level == b.level == level for a, b in pairs[length:])
        assert all(
            a.level == b.level and LEVELS.index(a.level) <= LEVELS.index(level)
            and a.concept != b.concept and a.difficulty == b.difficulty and a.clue_type == b.clue_type
            for a, b in pairs
        )


def test_graduate_review_uses_all_earlier_levels_across_trials():
    bank = load_question_bank(ASSETS)
    rng = Random(11)
    origin_counts = Counter()
    match_origins = Counter()
    draws = set()
    for _ in range(25):
        draw = solo_questions(bank, "Graduate Mix", rng, 20)
        draws.add(frozenset(q.id for q in draw))
        origin_counts.update(q.level for q in draw)
        match_origins.update(a.level for a, _ in match_questions(bank, "Graduate Mix", rng, 20)[:20])
    assert set(origin_counts) == set(match_origins) == set(LEVELS)
    assert len(draws) == 25


def test_answer_choices_stay_fixed_and_positions_vary(bank):
    question = bank[0]
    rng = Random(13)
    positions = set()
    for _ in range(30):
        turn = Turn(question, rng, 0)
        assert set(turn.choices) == set(question.choices)
        positions.add(turn.choices.index(question.answer))
        assert turn.resolve(question.answer, 1).correct
    assert positions == set(range(5))


@pytest.mark.parametrize("length", [0, 21, 1.5, True])
def test_rejects_invalid_round_lengths(bank, length):
    with pytest.raises(ValueError, match="whole number"):
        solo_questions(bank, "100", Random(0), length)
    with pytest.raises(ValueError, match="whole number"):
        match_questions(bank, "100", Random(0), length)


def test_old_progress_and_review_outcomes_save_as_accuracy(tmp_path, bank):
    path = tmp_path / "progress.json"
    path.write_text('{"version": 1, "best": {"100": 6}}', encoding="utf-8")
    progress = Progress(path)
    assert progress.best == {"100": Fraction(3, 5)}
    assert not progress.unlocked("200")
    review = bank[0]
    current = replace(review, id="200-test", level="200")
    outcomes = [Outcome(review, review.answer, 200)] + [Outcome(current, current.answer, 200)] * 4
    with pytest.raises(ValueError):
        progress.record("200", outcomes)
    progress.record("100", [Outcome(review, review.answer, 200)])
    assert progress.unlocked("200")
    progress.record("200", outcomes)
    progress.record("200", [Outcome(current, current.answer, 200)] * 16 + [Outcome(current, None, QUESTION_MS)] * 4)
    assert Progress(path).best == {"100": Fraction(1), "200": Fraction(1)}
    assert progress.unlocked("300")
    with pytest.raises(ValueError):
        progress.record("100", outcomes)


def test_ai_ml_is_a_standalone_question_pool_in_both_modes():
    bank = load_question_bank(ASSETS)
    rng = Random(23)
    for length in range(1, MAX_ROUND_SIZE + 1):
        solo = solo_questions(bank, AI_ML, rng, length)
        assert len({q.id for q in solo}) == length
        assert {q.level for q in solo} == {AI_ML}
        match = match_questions(bank, AI_ML, rng, length)
        assert len(match) == length + 3
        assert len({q.id for pair in match for q in pair}) == 2 * len(match)
        assert all(a.level == b.level == AI_ML for a, b in match)


def test_pro_mix_and_pairs_at_all_round_lengths():
    bank = load_question_bank(ASSETS)
    rng = Random(30)
    advanced = LEVELS[3:]
    earlier = LEVELS[:3]
    short_sources = set()

    for length in range(1, MAX_ROUND_SIZE + 1):
        solo = solo_questions(bank, PRO, rng, length)
        match = match_questions(bank, PRO, rng, length)
        assert len({q.id for q in solo}) == length
        assert len(match) == length + 3
        assert len({q.id for pair in match for q in pair}) == 2 * len(match)
        assert all(
            a.level == b.level and a.difficulty == b.difficulty
            and a.clue_type == b.clue_type and a.concept != b.concept
            for a, b in match
        )
        assert all(a.level in advanced for a, _ in match[length:])
        for selected in (solo, [a for a, _ in match[:length]]):
            for sources, share in ((advanced, 7), ((AI_ML,), 2), (earlier, 1)):
                expected = length * share
                actual = sum(item.level in sources for item in selected)
                assert expected // 10 <= actual <= (expected + 9) // 10

    for _ in range(150):
        short_sources.add(solo_questions(bank, PRO, rng, 1)[0].level)
    assert short_sources == {*LEVELS, AI_ML}


def test_optional_sections_save_separate_scores_without_unlocking_years(tmp_path):
    bank = load_question_bank(ASSETS)
    path = tmp_path / "progress.json"
    progress = Progress(path)
    bonus = next(item for item in bank if item.level == AI_ML)
    assert progress.unlocked(AI_ML) and progress.unlocked(PRO)
    progress.record(AI_ML, [Outcome(bonus, bonus.answer, 200)])
    progress.record(PRO, [Outcome(bonus, bonus.answer, 500)])
    with pytest.raises(ValueError):
        progress.record("100", [Outcome(bonus, bonus.answer, 300)])
    reopened = Progress(path)
    assert reopened.best == {AI_ML: Fraction(1), PRO: Fraction(1)}
    assert not reopened.unlocked("200")
