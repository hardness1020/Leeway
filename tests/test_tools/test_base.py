"""Tests for tool base classes."""

from agenttree.tools.base import ToolRegistry
from agenttree.tools import create_default_tool_registry


def test_default_registry_has_expected_tools():
    registry = create_default_tool_registry()
    tool_names = {t.name for t in registry.list_tools()}
    assert "bash" in tool_names
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "edit_file" in tool_names
    assert "grep" in tool_names
    assert "glob" in tool_names
    assert "ask_user_question" in tool_names
    assert "web_fetch" in tool_names
    assert "web_search" in tool_names
    assert "task_create" in tool_names
    assert "task_list" in tool_names
    assert "task_get" in tool_names
    assert "task_stop" in tool_names
    assert "cron_create" in tool_names
    assert "cron_list" in tool_names
    assert "cron_delete" in tool_names
    assert "cron_toggle" in tool_names
    assert "remote_trigger" in tool_names
    assert "agent" in tool_names
    assert "memory_read" in tool_names
    assert "memory_write" in tool_names
    assert len(tool_names) == 21


def test_registry_get():
    registry = create_default_tool_registry()
    assert registry.get("bash") is not None
    assert registry.get("nonexistent") is None


def test_registry_to_api_schema():
    registry = create_default_tool_registry()
    schemas = registry.to_api_schema()
    assert len(schemas) == 21
    for schema in schemas:
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema
