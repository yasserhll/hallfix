from __future__ import annotations

from hallfix.utils.version import compare_versions, meets_minimum, parse_version


def test_parse_version_extracts_leading_dotted_numeric() -> None:
    assert parse_version("git version 2.43.0") == (2, 43, 0)
    assert parse_version("Python 3.11.4") == (3, 11, 4)


def test_parse_version_returns_none_when_no_number_found() -> None:
    assert parse_version("no version here") is None


def test_compare_versions_basic_ordering() -> None:
    assert compare_versions("1.2.0", "1.10.0") == -1
    assert compare_versions("2.0.0", "1.9.9") == 1
    assert compare_versions("1.0.0", "1.0.0") == 0


def test_compare_versions_pads_shorter_component_list() -> None:
    assert compare_versions("1.2", "1.2.0") == 0
    assert compare_versions("1.2.1", "1.2") == 1


def test_compare_versions_none_when_unparseable() -> None:
    assert compare_versions("nope", "1.0.0") is None


def test_meets_minimum_true_when_installed_is_newer_or_equal() -> None:
    assert meets_minimum("3.11.4", "3.11") is True
    assert meets_minimum("3.11.0", "3.11.0") is True


def test_meets_minimum_false_when_installed_is_older() -> None:
    assert meets_minimum("3.10.0", "3.11") is False


def test_meets_minimum_none_when_either_side_missing_or_unparseable() -> None:
    assert meets_minimum(None, "3.11") is None
    assert meets_minimum("3.11.0", None) is None
    assert meets_minimum("nope", "3.11") is None
