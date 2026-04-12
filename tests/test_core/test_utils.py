"""Tests for deep_merge utility."""

from audithive.core.utils import deep_merge


class TestDeepMerge:

    def test_empty_overrides_returns_base(self) -> None:
        base = {"a": 1, "b": {"c": 2}}
        result = deep_merge(base, {})
        assert result == base
        assert result is not base  # new object

    def test_top_level_override(self) -> None:
        base = {"a": 1, "b": 2}
        result = deep_merge(base, {"a": 99})
        assert result == {"a": 99, "b": 2}

    def test_nested_dict_merge(self) -> None:
        base = {"a": {"x": 1, "y": 2}}
        result = deep_merge(base, {"a": {"x": 10}})
        assert result == {"a": {"x": 10, "y": 2}}

    def test_three_levels_deep(self) -> None:
        base = {"a": {"b": {"c": 1, "d": 2}}}
        result = deep_merge(base, {"a": {"b": {"c": 99}}})
        assert result == {"a": {"b": {"c": 99, "d": 2}}}

    def test_list_replacement(self) -> None:
        base = {"tags": ["a", "b", "c"]}
        result = deep_merge(base, {"tags": ["x"]})
        assert result == {"tags": ["x"]}

    def test_new_key_added(self) -> None:
        base = {"a": 1}
        result = deep_merge(base, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_none_replaces_value(self) -> None:
        base = {"a": 1}
        result = deep_merge(base, {"a": None})
        assert result == {"a": None}

    def test_base_keys_preserved(self) -> None:
        base = {"a": 1, "b": 2, "c": 3}
        result = deep_merge(base, {"b": 99})
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_inputs_not_mutated(self) -> None:
        base = {"a": {"x": 1}}
        overrides = {"a": {"y": 2}}
        deep_merge(base, overrides)
        assert base == {"a": {"x": 1}}
        assert overrides == {"a": {"y": 2}}

    def test_empty_base(self) -> None:
        result = deep_merge({}, {"a": 1})
        assert result == {"a": 1}
