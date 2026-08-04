"""
Tests for LearningNoteService utility methods
"""
import json
import sys
import types

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