from __future__ import annotations

from hallfix.domain.models.command import CommandSpec
from hallfix.infrastructure.commands.runner import PrivilegedCommandRunner
from tests.fixtures.fake_command_runner import FakeCommandRunner, ok_result


def test_prepends_sudo_when_root_required_and_not_root() -> None:
    inner = FakeCommandRunner()
    inner.stub(("sudo", "apt-get", "install", "-y", "git"), ok_result(("sudo", "apt-get")))
    runner = PrivilegedCommandRunner(inner=inner, running_as_root=False)
    spec = CommandSpec(argv=("apt-get", "install", "-y", "git"), requires_root=True)
    runner.run(spec)
    assert inner.calls[0].argv == ("sudo", "apt-get", "install", "-y", "git")


def test_no_sudo_when_already_root() -> None:
    inner = FakeCommandRunner()
    inner.stub(("apt-get", "install", "-y", "git"), ok_result(("apt-get",)))
    runner = PrivilegedCommandRunner(inner=inner, running_as_root=True)
    spec = CommandSpec(argv=("apt-get", "install", "-y", "git"), requires_root=True)
    runner.run(spec)
    assert inner.calls[0].argv == ("apt-get", "install", "-y", "git")


def test_no_sudo_when_root_not_required() -> None:
    inner = FakeCommandRunner()
    inner.stub(("dpkg-query", "-W", "git"), ok_result(("dpkg-query",)))
    runner = PrivilegedCommandRunner(inner=inner, running_as_root=False)
    spec = CommandSpec(argv=("dpkg-query", "-W", "git"), requires_root=False)
    runner.run(spec)
    assert inner.calls[0].argv == ("dpkg-query", "-W", "git")


def test_redact_indices_shift_by_one_when_sudo_prepended() -> None:
    inner = FakeCommandRunner()
    inner.stub(("sudo", "cmd", "--token", "secret"), ok_result(("sudo", "cmd")))
    runner = PrivilegedCommandRunner(inner=inner, running_as_root=False)
    spec = CommandSpec(
        argv=("cmd", "--token", "secret"), requires_root=True, redact_argv_indices=(1,)
    )
    runner.run(spec)
    assert inner.calls[0].redact_argv_indices == (2,)
