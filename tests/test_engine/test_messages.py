"""Tests for conversation message models."""

from agenttree.engine.messages import (
    ConversationMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    serialize_content_block,
)


def test_from_user_text():
    msg = ConversationMessage.from_user_text("hello")
    assert msg.role == "user"
    assert msg.text == "hello"
    assert len(msg.content) == 1


def test_text_property():
    msg = ConversationMessage(
        role="assistant",
        content=[TextBlock(text="a"), TextBlock(text="b")],
    )
    assert msg.text == "ab"


def test_tool_uses():
    msg = ConversationMessage(
        role="assistant",
        content=[
            TextBlock(text="thinking"),
            ToolUseBlock(id="t1", name="bash", input={"command": "ls"}),
        ],
    )
    assert len(msg.tool_uses) == 1
    assert msg.tool_uses[0].name == "bash"


def test_serialize_text_block():
    block = TextBlock(text="hello")
    result = serialize_content_block(block)
    assert result == {"type": "text", "text": "hello"}


def test_serialize_tool_use_block():
    block = ToolUseBlock(id="t1", name="bash", input={"command": "ls"})
    result = serialize_content_block(block)
    assert result["type"] == "tool_use"
    assert result["name"] == "bash"


def test_to_api_param():
    msg = ConversationMessage.from_user_text("test")
    param = msg.to_api_param()
    assert param["role"] == "user"
    assert len(param["content"]) == 1
