"""Tests for skill registry and discovery."""

from pathlib import Path

from agenttree.skills.registry import SkillRegistry, _parse_skill_file, load_skill_registry
from agenttree.skills.types import SkillDefinition


def test_parse_skill_with_frontmatter(tmp_path: Path):
    md = tmp_path / "review.md"
    md.write_text(
        "---\nname: code-review\ndescription: Review code changes\n---\n"
        "Review the code for correctness and style."
    )
    skill = _parse_skill_file(md, "user")
    assert skill is not None
    assert skill.name == "code-review"
    assert skill.description == "Review code changes"
    assert "Review the code" in skill.content
    assert skill.source == "user"


def test_parse_skill_without_frontmatter(tmp_path: Path):
    md = tmp_path / "simple.md"
    md.write_text("Just some instructions for the agent.")
    skill = _parse_skill_file(md, "project")
    assert skill is not None
    assert skill.name == "simple"
    assert skill.description == ""
    assert "Just some instructions" in skill.content


def test_parse_empty_skill(tmp_path: Path):
    md = tmp_path / "empty.md"
    md.write_text("---\nname: empty\n---\n")
    skill = _parse_skill_file(md, "user")
    assert skill is None


def test_registry_operations():
    registry = SkillRegistry()
    skill = SkillDefinition(name="test", content="Test content")
    registry.register(skill)
    assert registry.get("test") is not None
    assert registry.get("missing") is None
    assert len(registry.list_skills()) == 1


def test_project_overrides_user(tmp_path: Path):
    user_dir = tmp_path / "user" / "skills"
    user_dir.mkdir(parents=True)
    (user_dir / "fix.md").write_text("---\nname: fix\n---\nUser fix instructions")

    project_dir = tmp_path / "project" / ".agenttree" / "skills"
    project_dir.mkdir(parents=True)
    (project_dir / "fix.md").write_text("---\nname: fix\n---\nProject fix instructions")

    registry = SkillRegistry()
    from agenttree.skills.registry import _scan_directory

    _scan_directory(user_dir, "user", registry)
    _scan_directory(project_dir, "project", registry)

    skill = registry.get("fix")
    assert skill is not None
    assert "Project fix" in skill.content
    assert skill.source == "project"


def test_load_skill_registry(tmp_path: Path):
    skills_dir = tmp_path / ".agenttree" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "debug.md").write_text("---\nname: debug\ndescription: Debug help\n---\nDebug steps.")

    registry = load_skill_registry(tmp_path)
    assert registry.get("debug") is not None


def test_frontmatter_extra_metadata(tmp_path: Path):
    md = tmp_path / "tagged.md"
    md.write_text("---\nname: tagged\ntags: [python, testing]\n---\nContent here.")
    skill = _parse_skill_file(md, "user")
    assert skill is not None
    assert skill.metadata.get("tags") == ["python", "testing"]
