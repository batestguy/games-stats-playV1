"""Check a question bank and curriculum map before cutting a release."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
from random import Random

from app.game import (
    MAX_ROUND_SIZE, QUESTION_LEVELS, TIE_LIMIT, bank_files, load_question_bank, matched_pairs,
    review_count,
)


def bank_fingerprint(bank_path: Path) -> str:
    files = bank_files(bank_path)
    if not bank_path.is_dir():
        return sha256(files[0].read_bytes()).hexdigest()
    manifest = "".join(f"{file.name} {sha256(file.read_bytes()).hexdigest()}\n" for file in files)
    return sha256(manifest.encode("utf-8")).hexdigest()


def check_release(bank_path: Path, coverage_path: Path) -> list[str]:
    questions = load_question_bank(bank_path)
    by_id = {item.id: item for item in questions}
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    if coverage["version"] != 1:
        raise ValueError("Unsupported curriculum map version")

    errors = []
    if len(questions) < 525:
        errors.append(f"Question bank has {len(questions)} items. The release target is 525.")
    if coverage["approved_bank_sha256"] != bank_fingerprint(bank_path):
        errors.append("The curriculum map has no approval for this version of the bank.")

    outcome_ids = set()
    mapped_levels = set()
    for row in coverage["outcomes"]:
        outcome, level = row["id"], row["level"]
        if outcome in outcome_ids:
            errors.append(f"Duplicate outcome ID {outcome}.")
        outcome_ids.add(outcome)
        mapped_levels.add(level)
        if level not in QUESTION_LEVELS or not row["outcome"].strip() or not row["source"].strip():
            errors.append(f"{outcome} has an invalid level or missing outcome text or source.")
        correct_level_ids = set()
        for item_id in row["question_ids"]:
            if item_id in by_id and by_id[item_id].level == level:
                correct_level_ids.add(item_id)
            else:
                errors.append(f"{outcome} has an unknown or wrong-level question {item_id}.")
        if len(correct_level_ids) < 2:
            errors.append(f"{outcome} needs at least two distinct questions.")

    for level in QUESTION_LEVELS:
        if level not in mapped_levels:
            errors.append(f"{level} has no learning outcomes.")
        try:
            own_questions = MAX_ROUND_SIZE - review_count(level, MAX_ROUND_SIZE)
            matched_pairs(questions, level, Random(0), count=own_questions + TIE_LIMIT)
        except ValueError as error:
            errors.append(f"{error}.")
    return errors


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("bank", type=Path, help="Question bank JSON file or bundled bank folder")
    parser.add_argument("coverage", type=Path)
    args = parser.parse_args()
    errors = check_release(args.bank, args.coverage)
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")
    print("Question bank and coverage checks passed.")


if __name__ == "__main__":
    main()
