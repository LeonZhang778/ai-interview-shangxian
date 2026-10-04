"""评分质量门禁：直接调用生产代码，锁死已知回归。

历史教训（本次重写的原因）：
本脚本原先自己复制了一份 HONEST_SKIP_KEYWORDS 与打分函数，**完全不 import 生产代码**，
拿 JSON 里写死的期望值对比自己算出来的结果 —— 于是它恒过，无论生产代码怎么改都是绿的。
线上「正常技术回答里带『不会』被直接判 4 分且完全不调用 AI」的 bug，就是这样一路绿灯
进生产的；更糟的是它把那个错误行为固化成了用例里的「期望 4.0」，等于把 bug 当成契约。

现在改为直接调用 AIService，任何行为退化都会让 gate 变红。
边界说明：这里只覆盖**确定性**判断（评分前置判断、降级路径）。AI 输出的分数没有确定性，
用固定分数去断言只会造出假绿，那部分靠抽检与可观测，不放进本门禁。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.client.ai_service import AIService  # noqa: E402  (需先注入 sys.path)

CASES_PATH = ROOT / "evaluation" / "interview_eval_cases.json"
HISTORY_PATH = ROOT / "evaluation" / "interview_eval_history.jsonl"
THRESHOLDS_PATH = ROOT / "evaluation" / "thresholds.json"

# 期望 pre_score 返回 None（即应交由 AI 评估）却实际返回了分数时，用这一下限占位，
# 让 score_mae 也能反映出「误判」而不只是 pass_rate 下降。
NONE_SCORE = 0.0


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_history():
    if not HISTORY_PATH.exists():
        return []
    rows = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def describe(actual) -> str:
    return "None" if actual is None else f"({actual[0]}, {actual[1]!r})"


def evaluate_case(case):
    """对单个用例调用生产函数，返回 (是否通过, 分数误差, 实际值描述, 期望值描述)。"""
    actual = AIService.pre_score(case.get("answer", ""))
    actual_score = float(actual[0]) if actual else NONE_SCORE

    if case.get("expect_none"):
        expected_repr = "None（必须交给 AI 评估，不得被关键词短路）"
        return actual is None, (0.0 if actual is None else actual_score), describe(actual), expected_repr

    expected_score = float(case["expect_score"])
    expected_skip_type = case["expect_skip_type"]
    passed = (
        actual is not None
        and actual_score == expected_score
        and actual[1] == expected_skip_type
    )
    return (
        passed,
        abs(expected_score - actual_score),
        describe(actual),
        f"({expected_score}, {expected_skip_type!r})",
    )


def evaluate_cases(cases):
    errors = []
    passed = 0
    for case in cases:
        ok, error, actual_repr, expected_repr = evaluate_case(case)
        errors.append(error)
        if ok:
            passed += 1
            continue
        print(
            "Evaluation case failed: "
            f"id={case.get('id')} expected={expected_repr} actual={actual_repr}"
        )
        if case.get("why"):
            print(f"  回归背景: {case['why']}")

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
