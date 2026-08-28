import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evaluation" / "interview_eval_cases.json"
HISTORY_PATH = ROOT / "evaluation" / "interview_eval_history.jsonl"
THRESHOLDS_PATH = ROOT / "evaluation" / "thresholds.json"

HONEST_SKIP_KEYWORDS = ["不知道", "不会", "不清楚", "不太了解", "不太清楚", "没学过", "没接触过", "不记得", "跳过"]
EMPTY_TALK_KEYWORDS = ["嗯", "对", "是的", "好的", "知道了"]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_history():
    rows = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def score_answer(answer: str) -> float:
    text = (answer or "").strip()
    if not text:
        return 1.0
    if text in EMPTY_TALK_KEYWORDS:
        return 1.0
    for keyword in HONEST_SKIP_KEYWORDS:
        if keyword in text and len(text) < 15:
            return 3.0
    for keyword in HONEST_SKIP_KEYWORDS:
        if keyword in text and len(text) >= 15:
            return 4.0
    if len(text) < 3:
        return 1.0
    return 5.0


def evaluate_cases(cases):
    errors = []
    passed = 0
    for case in cases:
        actual = score_answer(case["answer"])
        expected = float(case["expected_score"])
        tolerance = float(case.get("tolerance", 0))
        error = abs(actual - expected)
        errors.append(error)
        if error <= tolerance:
            passed += 1
        else:
            print(
                "Evaluation case failed: "
                f"id={case.get('id')} expected={expected:.3f} actual={actual:.3f} tolerance={tolerance:.3f}"
            )

    total = len(cases)
    if total == 0:
        return {"pass_rate": 0.0, "score_mae": 999.0, "cases": 0}
    return {
        "pass_rate": passed / total,
        "score_mae": sum(errors) / total,
        "cases": total,
    }


def main() -> int:
    thresholds = load_json(THRESHOLDS_PATH)
    cases = load_json(CASES_PATH)
    history = load_history()
    current = evaluate_cases(cases)

    pass_rate = float(current["pass_rate"])
    score_mae = float(current["score_mae"])
    min_pass_rate = float(thresholds["min_pass_rate"])
    max_score_mae = float(thresholds["max_score_mae"])

    print(
        "Evaluation current: "
        f"cases={current['cases']} pass_rate={pass_rate:.3f} score_mae={score_mae:.3f}"
    )
    if history:
        previous = history[-1]
        print(
            "Evaluation trend: "
            f"baseline_run_id={previous.get('run_id')} "
            f"pass_rate_delta={pass_rate - float(previous.get('pass_rate', 0)):.3f} "
            f"score_mae_delta={score_mae - float(previous.get('score_mae', 0)):.3f}"
        )

    failures = []
    if pass_rate < min_pass_rate:
        failures.append(f"pass_rate {pass_rate:.3f} < {min_pass_rate:.3f}")
    if score_mae > max_score_mae:
        failures.append(f"score_mae {score_mae:.3f} > {max_score_mae:.3f}")

    if failures:
        print("Evaluation gate failed: " + "; ".join(failures))
        return 1

    print("Evaluation gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
