"""Tests for trigger registry."""

from pathlib import Path

from agenttree.cron.types import ShellAction
from agenttree.triggers.registry import TriggerRegistry
from agenttree.triggers.types import TriggerDefinition


def _make_trigger(name: str = "test") -> TriggerDefinition:
    return TriggerDefinition(name=name, action=ShellAction(command="echo hi"))


def test_save_and_get(tmp_path: Path):
    reg = TriggerRegistry(tmp_path / "triggers.json")
    t = _make_trigger()
    reg.save(t)
    loaded = reg.get(t.id)
    assert loaded is not None
    assert loaded.name == "test"
    assert loaded.secret == t.secret


def test_list(tmp_path: Path):
    reg = TriggerRegistry(tmp_path / "triggers.json")
    reg.save(_make_trigger("a"))
    reg.save(_make_trigger("b"))
    assert len(reg.list()) == 2


def test_delete(tmp_path: Path):
    reg = TriggerRegistry(tmp_path / "triggers.json")
    t = _make_trigger()
    reg.save(t)
    assert reg.delete(t.id) is True
    assert reg.get(t.id) is None
    assert reg.delete("nope") is False
