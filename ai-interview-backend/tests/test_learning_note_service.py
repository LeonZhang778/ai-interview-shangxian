"""
Tests for LearningNoteService utility methods
"""
import asyncio
import json
import sys
import types
from types import SimpleNamespace

import pytest

try:
    from passlib.context import CryptContext as _CryptContext  # noqa: F401
except ModuleNotFoundError:
    passlib_module = types.ModuleType("passlib")
    context_module = types.ModuleType("passlib.context")

    class _CryptContext:
        def __init__(self, *args, **kwargs):
            pass

        def hash(self, password):
            return f"hashed:{password}"

        def verify(self, plain_password, hashed_password):
            return hashed_password == f"hashed:{plain_password}"

    context_module.CryptContext = _CryptContext
    passlib_module.context = context_module
    sys.modules.setdefault("passlib", passlib_module)
    sys.modules.setdefault("passlib.context", context_module)

from app.services.client.learning_note_service import LearningNoteService
from app.services.client.flashcard_service import SM2Algorithm
from app.services.client.note_recommend_service import NoteRecommendService
from app.services.client.weakness_service import WeaknessService
from app.exceptions.http_exceptions import NotFoundError, ValidationError
from app.models.learning_note import LearningNote
from app.models.notebook import Notebook


class FakeDb:
    def __init__(self, rows=None):
        self.rows = rows or {}
        self.committed = False

    async def get(self, model, entity_id):
        return self.rows.get((model, entity_id))

    async def commit(self):
        self.committed = True


class TestSafeParseJson:
    """Test _safe_parse_json robustness"""

    def test_none_input(self):
        """None 输入应返回默认值"""
        assert LearningNoteService._safe_parse_json(None, []) == []
        assert LearningNoteService._safe_parse_json(None, {}) == {}
        assert LearningNoteService._safe_parse_json(None, "default") == "default"
        # 无默认值应返回空 dict
        assert LearningNoteService._safe_parse_json(None) == {}

    def test_dict_input(self):
        """已为 dict 的输入应直接返回"""
        data = {"key": "value", "number": 42}
        result = LearningNoteService._safe_parse_json(data, {})
        assert result == data
        assert result is data  # 确保是同一个引用，不重新创建

    def test_list_input(self):
        """已为 list 的输入应直接返回"""
        data = [1, 2, 3]
        result = LearningNoteService._safe_parse_json(data, [])
        assert result == data
        assert result is data

    def test_valid_json_string_dict(self):
        """有效的 JSON 字符串应解析为 dict"""
        result = LearningNoteService._safe_parse_json('{"a": 1, "b": 2}', {})
        assert result == {"a": 1, "b": 2}

    def test_valid_json_string_list(self):
        """有效的 JSON 数组字符串应解析为 list"""
        result = LearningNoteService._safe_parse_json('[1, 2, 3]', [])
        assert result == [1, 2, 3]

    def test_invalid_json_string(self):
        """无效的 JSON 字符串应返回默认值"""
        result = LearningNoteService._safe_parse_json("not valid json", {})
        assert result == {}

    def test_type_error_on_int(self):
        """int 输入应被捕获（TypeError）并返回默认值"""
        result = LearningNoteService._safe_parse_json(12345, [])
        assert result == []

    def test_type_error_on_bool(self):
        """bool 输入应被捕获并返回默认值"""
        result = LearningNoteService._safe_parse_json(True, {})
        assert result == {}

    def test_empty_string(self):
        """空字符串应返回默认值"""
        result = LearningNoteService._safe_parse_json("", {})
        assert result == {}

    def test_nested_json_roundtrip(self):
        """复杂嵌套 JSON 应正确解析"""
        original = {"title": "test", "tags": ["a", "b"], "meta": {"views": 10}}
        json_str = json.dumps(original)
        result = LearningNoteService._safe_parse_json(json_str, {})
        assert result == original

    def test_default_not_overwritten_on_error(self):
        """解析失败时应返回传入的默认值，而非全局默认"""
        custom_default = {"fallback": True}
        result = LearningNoteService._safe_parse_json("{{{broken", custom_default)
        assert result == custom_default
        assert result["fallback"] is True


class TestLearningNoteGuards:
    def test_search_rejects_invalid_scope_before_query(self):
        """非法 scope 不能落到仅按 search_vector 查询，避免泄露私密笔记"""
        with pytest.raises(ValidationError):
            asyncio.run(
                LearningNoteService.search_notes(
                    db=FakeDb(),
                    keyword="redis",
                    scope="all",
                )
            )

    def test_search_my_scope_requires_user(self):
        """我的笔记搜索必须有当前用户"""
        with pytest.raises(ValidationError):
            asyncio.run(
                LearningNoteService.search_notes(
                    db=FakeDb(),
                    keyword="redis",
                    scope="my",
                    user_id=None,
                )
            )

    def test_create_note_rejects_foreign_notebook(self):
        """创建笔记时不能挂到其他用户的笔记本"""
        db = FakeDb({(Notebook, 10): SimpleNamespace(id=10, user_id=2)})

        with pytest.raises(NotFoundError):
            asyncio.run(
                LearningNoteService.create_note(
                    db=db,
                    user_id=1,
                    title="Redis 复盘",
                    notebook_id=10,
                )
            )

    def test_update_note_can_clear_owned_notebook(self):
        """更新时显式传 notebook_id=None 应允许移出笔记本"""
        note = SimpleNamespace(
            id=3,
            user_id=1,
            notebook_id=7,
            visibility="private",
            status="draft",
            published_at=None,
        )
        db = FakeDb({(LearningNote, 3): note})

        result = asyncio.run(
            LearningNoteService.update_note(
                db=db,
                user_id=1,
                note_id=3,
                notebook_id=None,
            )
        )

        assert result["id"] == 3
        assert note.notebook_id is None
        assert db.committed is True


class TestSM2Algorithm:
    def test_first_success_review_sets_one_day_interval(self):
        result = SM2Algorithm.calculate(quality=5, ease_factor=2.5, interval=0, repetitions=0)

        assert result["interval"] == 1
        assert result["repetitions"] == 1
        assert result["ease_factor"] == 2.6

    def test_second_success_review_sets_six_day_interval(self):
        result = SM2Algorithm.calculate(quality=4, ease_factor=2.5, interval=1, repetitions=1)

        assert result["interval"] == 6
        assert result["repetitions"] == 2
        assert result["ease_factor"] == 2.5

    def test_failed_review_resets_repetitions(self):
        result = SM2Algorithm.calculate(quality=2, ease_factor=2.5, interval=6, repetitions=3)

        assert result["interval"] == 1
        assert result["repetitions"] == 0
        assert result["ease_factor"] == 2.18

    def test_invalid_quality_rejected(self):
        with pytest.raises(ValidationError):
            SM2Algorithm.calculate(quality=6, ease_factor=2.5, interval=0, repetitions=0)


class TestNoteRecommendService:
    def test_jaccard_similarity_is_case_insensitive(self):
        result = NoteRecommendService._jaccard_similarity(["Redis", "SQL"], ["redis"])

        assert result == 0.5

    def test_jaccard_similarity_empty_input(self):
        assert NoteRecommendService._jaccard_similarity([], ["redis"]) == 0.0


class TestWeaknessService:
    def test_parse_report_returns_empty_dict_for_invalid_json(self):
        assert WeaknessService._parse_report("{broken") == {}

    def test_clean_keywords_deduplicates_and_truncates(self):
        long_keyword = "Redis" * 40
        result = WeaknessService._clean_keywords([" Redis ", "Redis", "", long_keyword])

        assert result == ["Redis", long_keyword[:100]]
