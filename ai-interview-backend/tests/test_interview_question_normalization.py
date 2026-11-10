import pytest

from app.exceptions.http_exceptions import ValidationError
from app.services.client.interview_service import InterviewService


def test_normalize_questions_matches_requested_count_and_trims_text():
    questions = InterviewService._normalize_questions(
        [
            {"index": 0, "question": " 第一题 "},
            {"index": 1, "question": "第二题"},
            {"index": 2, "question": "模型多生成的题目"},
        ],
        expected_count=2,
    )

    assert questions == [
        {"index": 0, "question": "第一题"},
        {"index": 1, "question": "第二题"},
    ]


def test_normalize_questions_rejects_too_few_questions():
    with pytest.raises(ValidationError, match="题目生成失败"):
        InterviewService._normalize_questions(
            [{"question": "只有一题"}], expected_count=2
        )


def test_normalize_questions_rejects_invalid_later_question():
    with pytest.raises(ValidationError, match="题目生成失败"):
        InterviewService._normalize_questions(
            [{"question": "第一题"}, {"question": "  "}], expected_count=2
        )


def test_normalize_questions_keeps_legacy_string_questions_as_objects():
    assert InterviewService._normalize_questions([" 第一题 "]) == [
        {"index": 0, "question": "第一题"}
    ]
