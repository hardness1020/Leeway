"""Tests for memory store."""

from pathlib import Path

from leeway.memory.store import MemoryStore
from leeway.memory.types import MemoryEntry


def test_save_and_get(tmp_path: Path):
    store = MemoryStore(tmp_path)
    entry = MemoryEntry(name="test fact", content="The sky is blue.", description="A fact")
    store.save(entry)

    loaded = store.get("test fact")
    assert loaded is not None
    assert loaded.content == "The sky is blue."
    assert loaded.description == "A fact"


def test_list(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.save(MemoryEntry(name="a", content="first"))
    store.save(MemoryEntry(name="b", content="second"))
    assert len(store.list()) == 2


def test_delete(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.save(MemoryEntry(name="deleteme", content="gone"))
    assert store.delete("deleteme") is True
    assert store.get("deleteme") is None
    assert store.delete("nonexistent") is False


def test_search(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.save(MemoryEntry(name="python tips", content="Use list comprehensions.", tags=["python"]))
    store.save(MemoryEntry(name="rust tips", content="Use match statements.", tags=["rust"]))

    results = store.search("python")
    assert len(results) == 1
    assert results[0].name == "python tips"


def test_tags_preserved(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.save(MemoryEntry(name="tagged", content="content", tags=["a", "b"]))
    loaded = store.get("tagged")
    assert loaded is not None
    assert loaded.tags == ["a", "b"]
