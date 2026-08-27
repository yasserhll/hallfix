from __future__ import annotations

from hallfix.infrastructure.logging.redaction import (
    REDACTED,
    is_sensitive_key,
    redact_env,
    redact_mapping,
    redact_text,
)


def test_is_sensitive_key_matches_known_fragments() -> None:
    assert is_sensitive_key("password")
    assert is_sensitive_key("DB_PASSWORD")
    assert is_sensitive_key("api_key")
    assert is_sensitive_key("Authorization")
    assert not is_sensitive_key("username")
    assert not is_sensitive_key("path")


def test_redact_text_replaces_key_value_pairs() -> None:
    text = "connecting with password=hunter2 to host=example.com"
    redacted = redact_text(text)
    assert "hunter2" not in redacted
    assert REDACTED in redacted
    assert "host=example.com" in redacted


def test_redact_text_handles_colon_separator() -> None:
    text = "token: abc123xyz"
    redacted = redact_text(text)
    assert "abc123xyz" not in redacted
    assert REDACTED in redacted


def test_redact_mapping_is_recursive() -> None:
    data = {
        "user": "alice",
        "auth": {"api_key": "sk-12345", "region": "eu"},
    }
    redacted = redact_mapping(data)
    assert redacted["user"] == "alice"
    assert redacted["auth"]["api_key"] == REDACTED
    assert redacted["auth"]["region"] == "eu"


def test_redact_env_only_touches_sensitive_names() -> None:
    env = {"PATH": "/usr/bin", "GITHUB_TOKEN": "ghp_secret"}
    redacted = redact_env(env)
    assert redacted["PATH"] == "/usr/bin"
    assert redacted["GITHUB_TOKEN"] == REDACTED
